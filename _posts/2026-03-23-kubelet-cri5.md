---
title: "kubernetes data plane: containerd CreateContainer & StartContainer"
date: 2026-03-23 00:00:00 +0900
categories:
  - containerd
tags:
  - containerd
  - kubernetes
  - CRI
  - CreateContainer
  - StartContainer
  - shim
excerpt: "kubelet의 CreateContainer와 StartContainer 요청에 대한 containerd 내부 처리 과정을 스냅샷 생성부터 runc start까지 코드 수준으로 분석합니다."
toc: true
toc_sticky: true
author_profile: false
header:
  teaser: /assets/images/posts/kubernetes.png
---

이전 편에서는 `RunPodSandbox`가 netns를 생성하고 CNI를 구성한 뒤 shim을 기동하여 pause 컨테이너를 실행하는 과정을 살펴봤습니다. 이번 편은 다음 단계입니다. kubelet은 샌드박스가 준비되면 각 워크로드 컨테이너에 대해 먼저 `CreateContainer`, 그 다음 `StartContainer`를 호출합니다.

이 두 메서드는 이름이 비슷해서 한 덩어리처럼 보이지만, 실제 역할은 분명하게 갈립니다. `CreateContainer`는 컨테이너 실행에 필요한 메타데이터와 파일시스템 레이어를 준비하는 단계이고, `StartContainer`는 그 준비물을 바탕으로 task를 만들고 실제 컨테이너 프로세스를 시작하는 단계입니다. 이 구분을 먼저 잡아두면 이후 코드가 훨씬 자연스럽게 읽힙니다.

이번 글은 다음 질문을 따라가겠습니다.

- `CreateContainer`가 끝났을 때 정확히 무엇이 준비되어 있는가
- `StartContainer`는 그 준비물을 어디서 꺼내 실제 실행으로 연결하는가

또한 아래를 가정합니다: 

CreateContainer가 호출되기 전에 kubelet은 이미 PullImage로 이미지를 받아두었습니다. 따라서 이 글에서 LocalResolve가 등장할 때는 content store에 레이어가 존재한다는 전제입니다.

---

## CreateContainer

`CreateContainer`는 이미 실행 중인 샌드박스 안에 새 컨테이너를 등록하는 단계입니다. 아직 프로세스를 만들지는 않지만, 나중에 `StartContainer`가 곧바로 사용할 수 있도록 이미지 스냅샷, OCI 스펙, IO 파이프, 컨테이너 메타데이터를 미리 준비합니다. 따라서 이 절의 핵심은 "어디까지가 준비이고, 무엇이 아직 실행되지 않았는가"를 구분해서 보는 것입니다.

구현은 `internal/cri/server/container_create.go`의 `criService.CreateContainer`에 있습니다. 흐름은 크게 샌드박스 확인 → 이미지와 스펙 준비 → 스냅샷 생성 → store 등록 순서로 진행됩니다.

이 절에서 바로 등장하는 helper의 역할도 먼저 고정해 두면 좋습니다.

- `LocalResolve()`: 이미지 레퍼런스를 로컬 image store에서 찾습니다.
- `toContainerdImage()`: CRI 쪽 이미지 정보를 `containerd.Image` 객체로 변환합니다.
- `createContainer()`: spec, snapshot, container metadata 준비를 한곳에서 묶어 처리합니다.

### 샌드박스 조회와 컨테이너 ID 예약

가장 먼저 해야 할 일은 이 컨테이너가 합류할 샌드박스를 확정하는 것입니다. 같은 파드의 네임스페이스를 공유해야 하므로, containerd는 요청에 담긴 샌드박스 ID로 인메모리 store를 조회하고 pause 프로세스 PID를 확보합니다. 이 PID는 이후 net/IPC/UTS 네임스페이스 공유 경로(`/proc/<pid>/ns/...`)를 만들 때 필요합니다. 이어서 새 컨테이너 ID를 생성하고 이름 인덱스에 예약해, 이후 단계에서 사용할 식별자를 먼저 고정합니다.

```go
// https://github.com/containerd/containerd/blob/v2.2.1/internal/cri/server/container_create.go#L57
func (c *criService) CreateContainer(ctx context.Context, r *runtime.CreateContainerRequest) (_ *runtime.CreateContainerResponse, retErr error) {
    // ...
    sandbox, err := c.sandboxStore.Get(r.GetPodSandboxId()) // ✅ 인메모리 store에서 샌드박스 조회

    cstatus, err := c.sandboxService.SandboxStatus(ctx, sandbox.Sandboxer, sandbox.ID, false)

    id := util.GenerateID()
    if err = c.containerNameIndex.Reserve(name, id); err != nil { // ✅ 컨테이너 이름 중복 방지 예약
        return nil, fmt.Errorf("failed to reserve container name %q: %w", name, err)
    }
```

### 이미지 해석과 스냅샷 생성

샌드박스와 식별자가 준비되면, 다음 관심사는 "이 컨테이너를 어떤 이미지와 어떤 rootfs 위에서 실행할 것인가"입니다. containerd는 컨테이너 스펙에 적힌 이미지 레퍼런스를 로컬 이미지 store에서 해석해 `containerd.Image` 객체로 바꾼 뒤, 이를 샌드박스 PID와 netns 경로와 함께 `createContainer`로 넘깁니다. `createContainer` 내부에서는 OCI 스펙 생성 → IO FIFO 파이프 초기화 → overlay 스냅샷 생성 → `NewContainer` 호출 순으로 진행됩니다. 이 중 `NewContainer`가 `ContainerService().Create()`를 호출하여 spec을 포함한 컨테이너 메타데이터를 bolt DB에 트랜잭션으로 영구 저장합니다. 반면 `/run` 하위의 `config.json`은 아직 만들어지지 않으며, `StartContainer`의 `NewTask → NewBundle` 단계에서 bolt DB에 저장된 spec을 읽어 파일로 내려갑니다.

```go
// https://github.com/containerd/containerd/blob/v2.2.1/internal/cri/server/container_create.go#L167
func (c *criService) CreateContainer(...) {
    // ...
    image, err := c.LocalResolve(config.GetImage().GetImage()) // ✅ 로컬 이미지 store에서 이미지 해석
    containerdImage, err := c.toContainerdImage(ctx, image)    // ✅ containerd Image 객체로 변환

    _, err = c.createContainer(
        &createContainerRequest{
            containerdImage: &containerdImage,
            sandboxPid:      sandboxPid,
            NetNSPath:       sandbox.NetNSPath, // ✅ 샌드박스의 netns 경로 전달 (네임스페이스 공유)
            // ...
        },
    )
```

`createContainer` 내부에서는 OCI 스펙 생성, IO 파이프 초기화, containerd Container 생성까지 진행합니다.

```go
// https://github.com/containerd/containerd/blob/v2.2.1/internal/cri/server/container_create.go#L222
func (c *criService) createContainer(r *createContainerRequest) (_ string, retErr error) {
    // ...
    spec, err := c.buildContainerSpec(           // ✅ OCI 런타임 스펙 생성 - 결과는 메모리 상의 Go 구조체
        platform, r.containerID, r.sandboxID, r.sandboxPid, r.NetNSPath, ...,
    )

    // ...
    containerIO, err = cio.NewContainerIO(r.containerID,
        cio.WithNewFIFOs(volatileContainerRootDir, ...)) // ✅ stdout/stderr FIFO 파이프 생성

    opts := []containerd.NewContainerOpts{
        containerd.WithSnapshotter(c.RuntimeSnapshotter(r.ctx, ociRuntime)),
        customopts.WithNewSnapshot(r.containerID, *r.containerdImage, ...), // ✅ 이미지 레이어 위에 쓰기 가능 레이어(overlay) 생성
        containerd.WithSpec(spec, specOpts...),  // ✅ spec을 proto로 마샬링하여 container.Spec 필드에 할당 (아직 메모리)
        containerd.WithRuntime(runtimeName, runtimeOption),
        containerd.WithSandbox(r.sandboxID),
    }

    cntr, err = c.client.NewContainer(r.ctx, r.containerID, opts...)
    // ✅ ContainerService().Create() → bolt DB 트랜잭션으로 spec 포함 컨테이너 메타데이터 영구 저장
```

`NewContainer`는 opt 목록을 순차적으로 적용하는데, 이 중 `customopts.WithNewSnapshot`이 실제로 파일시스템 레이어를 디스크에 구성하는 역할을 담당합니다. 여기서부터는 흐름이 잠깐 스냅샷터 내부로 내려갑니다. 다만 독자 입장에서는 스냅샷터가 아래 세 가지를 담당한다고 잡고 보면 전체 흐름이 잘 정리됩니다.

- content store에 보관된 압축 tar 형태의 이미지 레이어를 읽기 전용 디렉터리로 추출하는 이미지 레이어 언팩(lower dir 생성)
- 컨테이너마다 쓰기 변경사항을 기록하는 writable 디렉터리를 생성하는 컨테이너 쓰기 레이어(upper dir 생성)
- overlayfs가 이 레이어들을 하나의 파일시스템으로 합성할 수 있도록 마운트 옵션 구조체(`[]mount.Mount`)를 반환 — 단, `mount(2)` 시스템 콜은 이 단계에서 발생하지 않음

#### 이미지 레이어 → lower dir 변환 (Unpack)

`customopts.WithNewSnapshot`은 먼저 이미지의 최상위 체인 ID를 parent로 하여 `s.Prepare`를 시도합니다. parent 스냅샷이 아직 없으면(`errdefs.IsNotFound`) `i.Unpack`을 호출하여 레이어별 언팩을 수행합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/opts/container.go#L39
func WithNewSnapshot(id string, i containerd.Image, ...) containerd.NewContainerOpts {
    f := containerd.WithNewSnapshot(id, i, opts...) // ✅ client/container_opts.go:237의 withNewSnapshot으로 위임
    return func(...) error {
        if err := f(ctx, client, c); err != nil {
            if !errdefs.IsNotFound(err) {
                return err
            }
            if err := i.Unpack(ctx, c.Snapshotter); err != nil { // ✅ client/image.go:301의 image.Unpack 호출
                return fmt.Errorf("error unpacking image: %w", err)
            }
            return f(ctx, client, c)
        }
        return nil
    }
}
```

`image.Unpack`은 이미지의 레이어 목록을 순회하며 각 레이어마다 `ApplyLayerWithOpts`를 호출합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/client/image.go#L346
func (i *image) Unpack(...) error {
    // ...
    for _, layer := range layers {
        unpacked, err = rootfs.ApplyLayerWithOpts(ctx, layer, chain, sn, a, ...)
        // ✅ pkg/rootfs/apply.go:91의 ApplyLayerWithOpts → applyLayers 호출 (레이어마다 반복)
    }
}
```

`applyLayers`는 레이어마다 Prepare → Apply → Commit을 순서대로 수행합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/pkg/rootfs/apply.go#L112
func applyLayers(...) error {
    // ...
    mounts, err = sn.Prepare(ctx, key, parent.String(), opts...)
    // ✅ overlay.go:265의 (o *snapshotter).Prepare → overlay.go:428의 createSnapshot
    // ✅ createSnapshot 내부에서 prepareDirectory: snapshots/<N>/fs/, work/ 디렉터리 생성
    // ✅ 반환된 mounts는 tar 추출 시 임시 마운트 경로로 사용 (unpack 전용, mount(2) 발생)
    // ...
    diff, err = a.Apply(ctx, layer.Blob, mounts, applyOpts...)
    // ✅ content store의 tar → mounts 경로에 추출 → snapshots/<N>/fs/ 하위에 레이어 파일트리 기록
    // ...
    if err = sn.Commit(ctx, chainID.String(), key, opts...); err != nil {
    // ✅ bolt DB에서 snapshot kind: Active → Committed; snapshots/<N>/fs/ 가 lower dir로 확정
        ...
    }
}
```

레이어 수만큼 이 과정이 반복되어, 이미지의 각 레이어가 `snapshots/<N>/fs/`에 개별적으로 커밋됩니다.

#### 컨테이너 쓰기 레이어 준비 (Prepare)

이미지 레이어가 lower dir로 모두 준비되면, 그 위에 컨테이너 전용 쓰기 레이어를 얹을 차례입니다. 이를 위해 `withNewSnapshot`은 컨테이너 ID를 key, 최상위 이미지 체인 ID를 parent로 하여 다시 `s.Prepare`를 호출합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/client/container_opts.go#L237
func withNewSnapshot(id string, i Image, readonly bool, ...) NewContainerOpts {
    return func(ctx context.Context, client *Client, c *containers.Container) error {
        // ...
        _, err = s.Prepare(ctx, id, parent, opts...)
        // ✅ 반환값 []mount.Mount 무시 — overlay.go:265의 (o *snapshotter).Prepare 호출
        // ...
        c.SnapshotKey = id   // ✅ bolt DB 저장 시 스냅샷 키로 참조
        c.Image = i.Name()
        return nil
    }
}
```

`(o *snapshotter).Prepare`는 단순히 `createSnapshot`에 `KindActive`를 넘겨 위임합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/plugins/snapshots/overlay/overlay.go#L265
func (o *snapshotter) Prepare(ctx context.Context, key, parent string, opts ...snapshots.Opt) ([]mount.Mount, error) {
    return o.createSnapshot(ctx, snapshots.KindActive, key, parent, opts)
    // ✅ overlay.go:428의 createSnapshot 호출
}
```

`createSnapshot`은 디렉터리를 생성하고 마지막으로 `mounts()`를 호출하여 마운트 옵션 구조체를 반환합니다. 이 시점에 `mount(2)` 시스템 콜은 발생하지 않습니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/plugins/snapshots/overlay/overlay.go#L428
func (o *snapshotter) createSnapshot(...) (_ []mount.Mount, err error) {
    // ...
    td, err = o.prepareDirectory(ctx, snapshotDir, kind)
    // ✅ overlay.go:533의 prepareDirectory: snapshots/<M>/fs/, work/ 디렉터리 생성
    // ...
    path = filepath.Join(snapshotDir, s.ID)
    os.Rename(td, path)   // ✅ 임시 디렉터리를 snapshots/<M>/ 위치에 확정
    // ...
    return o.mounts(s, info), nil
    // ✅ overlay.go:552의 mounts() 호출 → []mount.Mount 반환 (mount(2) 없음)
}
```

`mounts()`는 overlayfs 마운트에 필요한 경로 정보를 `[]mount.Mount` 구조체로 조립하여 반환할 뿐 `mount(2)` 시스템 콜을 발생시키지 않습니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/plugins/snapshots/overlay/overlay.go#L552
func (o *snapshotter) mounts(s storage.Snapshot, info snapshots.Info) []mount.Mount {
    // ...
    if s.Kind == snapshots.KindActive {
        options = append(options,
            fmt.Sprintf("workdir=%s", o.workPath(s.ID)),   // ✅ snapshots/<M>/work → overlay work dir 경로
            fmt.Sprintf("upperdir=%s", o.upperPath(s.ID)), // ✅ snapshots/<M>/fs  → 컨테이너 쓰기 레이어 경로
        )
    }
    // ...
    parentPaths := make([]string, len(s.ParentIDs))
    for i := range s.ParentIDs {
        parentPaths[i] = o.upperPath(s.ParentIDs[i])       // ✅ 이미지 레이어 fs/ 경로들 → lower dirs 경로
    }
    options = append(options, fmt.Sprintf("lowerdir=%s", strings.Join(parentPaths, ":")))

    return []mount.Mount{{Type: "overlay", Source: "overlay", Options: options}}
    // ✅ 마운트 옵션 구조체만 반환 — mount(2) 없음
}
```

`withNewSnapshot`은 `s.Prepare`의 반환값을 명시적으로 무시(`_, err = ...`)하고 `c.SnapshotKey = containerID`만 기록합니다. 즉, 이 단계에서는 overlayfs 마운트를 위한 디렉터리 구조(`lowerdir`, `upperdir`, `workdir`)만 디스크에 준비되며, 실제 `mount(2)` 시스템 콜은 `StartContainer → NewTask → NewBundle` 단계에서 shim이 rootfs를 마운트할 때 비로소 발생합니다.

### 컨테이너 store 등록과 이벤트 발송

여기까지 오면 파일시스템과 스펙 준비는 끝났습니다. 하지만 `CreateContainer`의 목적은 단순히 디스크에 흔적을 남기는 데서 끝나지 않습니다. 바로 이어질 `StartContainer`가 이 결과를 즉시 찾을 수 있도록, containerd는 준비된 컨테이너 객체를 자신의 관리 store에도 등록합니다.

`NewContainer`로 bolt DB에 저장된 컨테이너 객체를 인메모리 container store에도 등록하여 이후 `StartContainer`에서 빠르게 조회할 수 있도록 합니다. 등록 후에는 `CONTAINER_CREATED` 이벤트를 발송하고 NRI post-create 훅을 실행합니다. 이 시점까지 컨테이너 프로세스는 생성되지 않으며, 실제 실행은 kubelet이 `StartContainer`를 호출할 때 이루어집니다.

여기까지가 "실행 재료 저장" 단계입니다. 다음 `StartContainer`는 방금 저장한 재료를 다시 읽어 shim과 `runc` 실행으로 넘깁니다.

```go
// https://github.com/containerd/containerd/blob/v2.2.1/internal/cri/server/container_create.go#L461
func (c *criService) createContainer(r *createContainerRequest) (_ string, retErr error) {
    // ...
    container, err := containerstore.NewContainer(*r.meta,
        containerstore.WithStatus(status, containerRootDir),
        containerstore.WithContainer(cntr),
        containerstore.WithContainerIO(containerIO),
    )

    if err := c.containerStore.Add(container); err != nil { ... } // ✅ 인메모리 container store에 추가

    c.generateAndSendContainerEvent(r.ctx, r.containerID, r.sandboxID,
        runtime.ContainerEventType_CONTAINER_CREATED_EVENT)      // ✅ CONTAINER_CREATED 이벤트 발송

    err = c.nri.PostCreateContainer(r.ctx, r.sandbox, &container) // ✅ NRI post-create 훅 실행

    return containerRootDir, nil
    // ✅ 프로세스는 아직 실행되지 않음 - StartContainer 호출을 대기
```

## StartContainer

이제 `CreateContainer`가 준비해 둔 결과물을 실제 실행으로 넘길 차례입니다. `StartContainer`는 containerd task를 만들고, shim을 통해 `runc create`와 `runc start`를 이어 붙여 컨테이너 프로세스를 기동합니다. 앞 절이 준비 단계였다면, 이 절은 실제 프로세스로 바꾸는 단계입니다.

구현은 `internal/cri/server/container_start.go`의 `criService.StartContainer`에 있습니다. 이 절에서는 상태 검증 → task 생성 → 프로세스 시작 순서로 따라가면 흐름이 가장 자연스럽습니다.

### 상태 검증과 IO 로거 설정

실행 직전에 containerd가 먼저 확인하는 것은 단순합니다. "지금 이 컨테이너를 시작해도 되는가"입니다. `setContainerStarting`은 컨테이너가 `CONTAINER_CREATED` 상태일 때만 Starting 플래그를 설정하며, 이미 실행 중이거나 종료된 컨테이너에 대한 중복 호출을 원천 차단합니다. 이와 함께 샌드박스가 아직 `StateReady`인지도 확인합니다. pause 컨테이너가 종료된 뒤에는 네트워크 네임스페이스가 사라지므로, 새 컨테이너를 그 네임스페이스에 합류시키는 것 자체가 불가능하기 때문입니다.

이 검증이 끝나면 IO 로거를 준비합니다. `CreateContainer` 단계에서 stdout/stderr FIFO 파이프를 이미 만들어 두었기 때문에, 여기서는 그 FIFO를 실제 로그 파일과 연결하면 됩니다. `createContainerLoggers`는 `meta.LogPath`에 해당하는 로그 파일을 열고, FIFO에서 읽어 파일에 쓰는 리다이렉션 고루틴을 백그라운드에서 시작합니다.

```go
// https://github.com/containerd/containerd/blob/v2.2.1/internal/cri/server/container_start.go#L45
func (c *criService) StartContainer(ctx context.Context, r *runtime.StartContainerRequest) (retRes *runtime.StartContainerResponse, retErr error) {
    // ...
    cntr, err := c.containerStore.Get(r.GetContainerId()) // ✅ container store에서 조회

    if err := setContainerStarting(cntr); err != nil {    // ✅ CONTAINER_CREATED 상태 검증 + Starting 플래그 설정
        return nil, fmt.Errorf("failed to set starting state for container %q: %w", id, err)
    }

    sandbox, err := c.sandboxStore.Get(meta.SandboxID)
    if sandbox.Status.Get().State != sandboxstore.StateReady { // ✅ 샌드박스가 Ready 상태인지 확인
        return nil, fmt.Errorf("sandbox container %q is not running", sandboxID)
    }

    ioCreation := func(id string) (_ containerdio.IO, err error) {
        stdoutWC, stderrWC, err := c.createContainerLoggers(meta.LogPath, config.GetTty())
        // ✅ 로그 파일 오픈 + FIFO → 로그 파일 리다이렉션 고루틴 시작
        cntr.IO.AddOutput("log", stdoutWC, stderrWC)
        cntr.IO.Pipe()
        return cntr.IO, nil
    }
```

### Task 생성 — shim 기동과 OCI 번들 준비

여기서부터 `CreateContainer`가 남겨 둔 메타데이터가 실행 단위로 바뀝니다. `container.NewTask`는 bolt DB에 저장된 컨테이너 메타데이터(spec 포함)를 읽어 `/run/containerd/io.containerd.runtime.v2.task/<namespace>/<id>/` 하위에 OCI 번들(`config.json`, rootfs 마운트 등)을 구성하고, shim 프로세스를 통해 `runc create`를 실행합니다. 즉, 독자 입장에서는 이 지점을 "저장된 준비물이 실제 실행 환경으로 변환되는 경계"로 이해하면 됩니다. 다만 이 단계는 아직 프로세스를 시작하는 것이 아니라, 컨테이너 환경(cgroup, 네임스페이스, rootfs)을 초기화하는 단계입니다.

sandbox의 `Endpoint`가 유효하면 별도 shim을 새로 기동하지 않고 기존 샌드박스 shim의 API 엔드포인트를 재사용합니다. Kata Containers처럼 VM 기반 런타임에서는 모든 컨테이너가 같은 VM 위에서 동작해야 하므로, 하나의 shim이 샌드박스 전체의 생명주기를 담당합니다. 일반 runc 환경에서도 같은 파드 내 컨테이너들은 동일한 shim을 공유하여 불필요한 프로세스 생성을 줄입니다.

`task.Wait`는 이 시점에 task 종료 이벤트를 구독하는 채널을 미리 확보합니다. `task.Start` 이후에 Wait를 호출하면 컨테이너가 이미 종료되어 이벤트를 놓칠 수 있기 때문에 순서가 중요합니다. 즉, 번들과 task는 만들어졌지만 프로세스는 아직 달리지 않는, 짧지만 중요한 중간 지점이 여기입니다.

```go
// https://github.com/containerd/containerd/blob/v2.2.1/internal/cri/server/container_start.go#L216
func (c *criService) StartContainer(...) {
    // ...
    endpoint := sandbox.Endpoint
    if endpoint.IsValid() {
        taskOpts = append(taskOpts,
            containerd.WithTaskAPIEndpoint(endpoint.Address, endpoint.Version)) // ✅ 샌드박스 shim 재사용 (같은 VM/네임스페이스 공유)
    }

    task, err := container.NewTask(ctx, ioCreation, taskOpts...)
    // ✅ containerd → shim API → runc create 순서로 OCI 번들 준비
    // ✅ shim이 이미 실행 중이면 재사용, 없으면 새로 기동

    exitCh, err := task.Wait(ctrdutil.NamespacedContext()) // ✅ task 종료 이벤트 구독 채널 획득
```

### NRI 훅 실행과 프로세스 시작

바로 그 중간 지점이 NRI가 개입할 수 있는 마지막 순간입니다. `NewTask`(runc create)까지 완료된 시점에는 컨테이너 환경이 완전히 초기화되어 있지만 프로세스는 아직 frozen 상태입니다. NRI `StartContainer` 훅은 이 틈을 활용해 OCI 스펙이 확정된 직후, 실제 프로세스 실행 직전에 CPU 핀닝이나 메모리 NUMA 정책처럼 실행 전에 반드시 적용되어야 할 리소스 설정을 주입할 수 있습니다.

훅이 완료되면 `task.Start`로 `runc start`를 호출하여 frozen 상태의 컨테이너 프로세스를 실제로 실행합니다. 이후 PID와 시작 시각을 store에 기록하고, 종료 이벤트를 감시하는 고루틴을 시작합니다. 마지막으로 `CONTAINER_STARTED` 이벤트를 발송하고 NRI post-start 훅을 실행한 뒤 kubelet에 응답을 반환합니다.

```go
// https://github.com/containerd/containerd/blob/v2.2.1/internal/cri/server/container_start.go#L253
func (c *criService) StartContainer(...) {
    // ...
    err = c.nri.StartContainer(ctx, &sandbox, &cntr) // ✅ NRI start 훅: CPU/메모리 리소스 조정 가능

    if err := task.Start(ctx); err != nil {           // ✅ shim → runc start → 컨테이너 프로세스 실행
        return nil, fmt.Errorf("failed to start containerd task %q: %w", id, err)
    }

    if err := cntr.Status.UpdateSync(func(status containerstore.Status) (containerstore.Status, error) {
        status.Pid = task.Pid()          // ✅ 실행 중인 프로세스의 PID 기록
        status.StartedAt = time.Now().UnixNano()
        return status, nil
    }); err != nil { ... }

    c.startContainerExitMonitor(context.Background(), id, task.Pid(), exitCh) // ✅ 종료 모니터 고루틴 시작

    c.generateAndSendContainerEvent(ctx, id, sandboxID,
        runtime.ContainerEventType_CONTAINER_STARTED_EVENT)    // ✅ CONTAINER_STARTED 이벤트 발송

    err = c.nri.PostStartContainer(ctx, &sandbox, &cntr)       // ✅ NRI post-start 훅

    return &runtime.StartContainerResponse{}, nil
```

# 정리

이 글에서 독자가 마지막에 남겨야 할 흐름은 비교적 단순합니다. `RunPodSandbox`가 파드의 공용 실행 기반을 만들고, `CreateContainer`가 각 컨테이너의 실행 재료를 준비한 뒤, `StartContainer`가 그 재료를 실제 프로세스로 바꿉니다. 세 단계는 이어져 있지만, 각자 담당하는 경계는 분명합니다.

### RunPodSandbox

- 샌드박스 ID를 생성하고 이름을 예약한 뒤, lease를 발급하여 리소스 누수를 방지합니다.
- 호스트 네트워크를 사용하지 않는 경우, 전용 고루틴에서 `LockOSThread` + `unshare(CLONE_NEWNET)`으로 새 netns를 생성하고, 바인드 마운트로 `/var/run/netns/cni-<uuid>` 경로에 고정합니다.
- go-cni를 통해 CNI 플러그인 체인을 실행하여 veth pair 생성과 IP 할당을 수행합니다.
- `sandboxService`를 통해 `sandbox.Controller`(기본 `podsandbox.Controller`)의 `Create` → `Start`를 차례로 호출합니다.
  - `Create`는 메타데이터를 인메모리 store에 등록하는 것이 전부입니다.
  - `Start`는 pause 이미지 확인, OCI 스펙 생성, `NewContainer` 호출(bolt DB 저장), `NewTask` 호출(shim 기동 + `runc create`), `task.Start()`(`runc start`)까지 진행합니다.
- NRI `RunPodSandbox` 훅을 실행하고 상태를 Ready로 전환한 뒤, 종료 모니터 고루틴을 시작하고 kubelet에 샌드박스 ID를 반환합니다.

### CreateContainer

- 이미 준비된 샌드박스를 기준점으로 삼아 pause PID와 네임스페이스 공유 경로를 확보합니다.
- 이미지 레퍼런스를 해석하고 OCI 런타임 스펙, FIFO 파이프, overlay 스냅샷을 차례로 준비합니다.
- `NewContainer`로 spec을 포함한 컨테이너 메타데이터를 bolt DB에 영구 저장하고, 인메모리 store에도 등록합니다.
- `CONTAINER_CREATED` 이벤트와 NRI post-create 훅까지 처리하지만, 이 시점에는 아직 프로세스를 실행하지 않습니다.
- 즉, 이 단계의 결과물은 "곧 실행할 수 있는 상태로 정리된 메타데이터와 파일시스템"입니다.

### StartContainer

- 먼저 이 컨테이너가 정말 시작 가능한 상태인지 검증하고, `CreateContainer`에서 만들어 둔 FIFO를 실제 로그 파일과 연결합니다.
- `container.NewTask`가 bolt DB의 메타데이터를 읽어 OCI 번들과 task를 만들고, shim을 통해 `runc create`를 호출합니다. 같은 파드 안에서는 기존 shim을 재사용할 수도 있습니다.
- 이 중간 지점에서 `task.Wait`와 NRI `StartContainer` 훅이 개입하여 종료 이벤트 구독과 실행 직전 리소스 조정을 처리합니다.
- 마지막으로 `task.Start`가 `runc start`를 호출해 frozen 상태의 프로세스를 실제로 실행하고, containerd는 PID 기록, 종료 모니터 등록, `CONTAINER_STARTED` 이벤트 발송까지 마무리합니다.

이렇게 나누어 보면 `CreateContainer`와 `StartContainer`의 경계가 분명해집니다. 전자는 "실행 재료를 저장해 두는 단계"이고, 후자는 "저장된 재료를 꺼내 실제 프로세스로 바꾸는 단계"입니다. 다음 편에서는 이 구현에서 반복적으로 등장하는 설계 패턴들이 왜 이런 형태를 갖게 되었는지, 그 기술적 배경을 살펴봅니다.
