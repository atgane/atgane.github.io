---
title: "kubernetes data plane: containerd shim 재연결과 bootstrap.json 복구 경로"
date: 2026-04-02 00:00:00 +0900
categories:
  - containerd
tags:
  - containerd
  - kubernetes
  - CRI
  - shim
  - bootstrap
  - ttrpc
  - restart
excerpt: "containerd가 재시작된 뒤 기존 shim에 다시 붙는 복구 경로를 NewTaskManager부터 loadShimTask까지 코드 수준으로 추적합니다."
toc: true
toc_sticky: true
author_profile: false
header:
  teaser: /assets/images/posts/kubernetes.png
---

이전 글에서는 `containerd-shim-runc-v2`가 왜 필요한지, 어떻게 bootstrap되고, 왜 `runc`가 떠난 뒤에도 계속 살아 있어야 하는지를 정리했습니다. 이번에는 shim이 어떻게 containerd 재시작 뒤에도 살아 있는 shim에 다시 붙어서 제어를 회복하는지, 그 복구 경로를 코드 수준으로 추적해 보겠습니다.

---

## TaskManager 초기화에서 일어나는 재연결

재연결은 나중에 어떤 요청이 들어왔을 때 즉흥적으로 일어나는 동작이 아닙니다. containerd의 runtime v2 task manager가 올라오는 순간, 먼저 기존 shim들을 복구하려고 시도합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/task_manager.go#L135-L145
func NewTaskManager(ctx context.Context, root, state string, shims *ShimManager) (*TaskManager, error) {
	if err := shims.LoadExistingShims(ctx, state, root); err != nil { // ✅ task manager 초기화에서 shim 복구 시도
		return nil, fmt.Errorf("failed to load existing shims for task manager")
	}
	m := &TaskManager{
		root:    root,
		state:   state,
		manager: shims,
	}
	return m, nil
}
```

재시작 뒤 복구의 출발점은 `loadShim()` 같은 개별 helper가 아니라 `NewTaskManager()`입니다. 다시 말해, shim 재연결은 task manager 구성 단계의 일부입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim_load.go#L38-L62
func (m *ShimManager) LoadExistingShims(ctx context.Context, stateDir string, rootDir string) error {
	nsDirs, err := os.ReadDir(stateDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	for _, nsd := range nsDirs {
		// ...
		if err := m.loadShims(namespaces.WithNamespace(ctx, ns), stateDir); err != nil {
			// ✅ network namespace 단위로 shim 디렉토리 순회
			continue
		}
		if err := m.cleanupWorkDirs(namespaces.WithNamespace(ctx, ns), rootDir); err != nil {
			// ...
			continue
		}
	}
	return nil
}
```

즉 containerd는 state directory 아래 namespace들을 먼저 순회하고, 그 안에서 기존 bundle들을 다시 살펴봅니다. 복구가 한 컨테이너의 API 호출에 종속되는 것이 아니라, 프로세스 재기동 직후의 초기화 루프에 묶여 있다는 점이 중요합니다.

여기서 `stateDir`는 기본 구성에서 대략 `/run/containerd/io.containerd.runtime.v2.task`입니다.

실제 시스템에서는 두 층으로 확인하시면 됩니다. 먼저 `containerd config dump | grep '^state'`로 daemon의 `config.State` 값을 보고, 그다음 그 아래 task plugin 디렉터리와 namespace 하위를 확인하면 됩니다. 기본값이라면 `ls /run/containerd/io.containerd.runtime.v2.task/` 아래에 namespace 디렉터리가 보이고, 그 아래가 다시 task ID별 bundle 디렉터리입니다.

## bundle 단위 재연결과 bootstrap.json 복구

namespace에 들어간 뒤에는 bundle 단위로 복구가 진행됩니다. 여기서 중요한 것은 `loadShims()`가 state directory를 훑고, 각 bundle마다 `m.loadShim(...)`으로 들어간다는 점입니다.

여기서 pod별 bundle처럼 읽히면 안 됩니다. runtime v2 task manager가 만드는 bundle은 기본적으로 task ID별이며, CRI의 일반 workload container 경로에서는 사실상 container ID별입니다. 실제 생성 호출도 `TaskManager.Create()`가 `NewBundle(ctx, m.root, m.state, taskID, opts.Spec)`를 부르는 형태입니다.

pause sandbox 자체도 containerd 입장에서는 하나의 sandbox task이므로 자기 bundle을 갖습니다. 다만 그 뒤에 붙는 일반 workload container들이 sandbox-aware shim을 쓸 때는, 각자 자기 bundle을 가지면서도 같은 sandbox shim endpoint를 공유할 수 있습니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/task_manager.go#L153-L194
func (m *TaskManager) Create(ctx context.Context, taskID string, opts runtime.CreateOpts) (_ runtime.Task, retErr error) {
	bundle, err := NewBundle(ctx, m.root, m.state, taskID, opts.Spec) // ✅ bundle은 taskID 기준 생성
	if err != nil {
		return nil, err
	}
	// ...
	shim, err := m.manager.Start(ctx, taskID, bundle, opts)
	if err != nil {
		return nil, fmt.Errorf("failed to start shim: %w", err)
	}
	// ...
	return t, nil
}
```

다만 sandbox-aware shim에서는 여러 컨테이너가 같은 pod sandbox shim을 공유할 수 있습니다. 이 경우 pod 단위로 공유되는 것은 bundle이 아니라 shim endpoint입니다. `ShimManager.Start()`는 `opts.SandboxID`가 있을 때 기존 sandbox shim의 bootstrap 정보를 가져와 현재 task의 bundle에 `bootstrap.json`과 `sandbox` 파일을 써 두고, 그 bundle을 통해 같은 shim에 다시 붙습니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim_manager.go#L169-L243
func (m *ShimManager) Start(ctx context.Context, id string, bundle *Bundle, opts runtime.CreateOpts) (_ ShimInstance, retErr error) {
	// ...
	if opts.SandboxID != "" {
		// ✅ 기존 sandbox shim의 bootstrap params를 가져옴
		process, err := m.Get(ctx, opts.SandboxID)
		if err != nil {
			return nil, fmt.Errorf("can't find shim for sandbox %s: %w", opts.SandboxID, err)
		}

		p, err := restoreBootstrapParams(process.Bundle())
		if err != nil {
			return nil, fmt.Errorf("failed to get bootstrap params of sandbox %s: %w", opts.SandboxID, err)
		}
		params = p
	}
	// ...
	if !shouldInvokeShimBinary {
		if err := os.WriteFile(filepath.Join(bundle.Path, "sandbox"), []byte(opts.SandboxID), 0600); err != nil {
			return nil, err
		}
		if err := writeBootstrapParams(filepath.Join(bundle.Path, "bootstrap.json"), params); err != nil {
			return nil, fmt.Errorf("failed to write bootstrap.json for bundle %s: %w", bundle.Path, err)
		}
		shim, err := loadShim(ctx, bundle, func() {})
		if err != nil {
			return nil, fmt.Errorf("failed to load sandbox task %q: %w", opts.SandboxID, err)
		}
		return shim, nil
	}
	// ...
	return m.startShim(ctx, bundle, id, opts)
}
```

즉 이 글에서 말하는 bundle은 이미지 레이어나 snapshot 이름이 아니라 OCI bundle 디렉터리이고, 보통은 task/container 단위입니다. 반면 pod 단위로 묶여 공유될 수 있는 것은 shim 쪽입니다. runtime v2의 `Bundle` 구조체는 `ID`, `Path`, `Namespace`를 들고 있고, `LoadBundle(ctx, stateDir, id)`는 그 경로를 `filepath.Join(stateDir, ns, id)`로 계산합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/bundle.go#L30-L39
func LoadBundle(ctx context.Context, root, id string) (*Bundle, error) {
	ns, err := namespaces.NamespaceRequired(ctx)
	if err != nil {
		return nil, err
	}
	return &Bundle{
		ID:        id,
		Path:      filepath.Join(root, ns, id), // ✅ stateDir/<namespace>/<task-id>
		Namespace: ns,
	}, nil
}

// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/bundle.go#L118-L125
type Bundle struct {
	ID        string
	Path      string
	Namespace string
}
```

이 디렉터리 아래에는 `config.json`, `rootfs`, `work` 링크, 그리고 shim bootstrap 뒤에는 `bootstrap.json` 같은 파일들이 놓입니다. 그래서 `loadShims()`가 bundle을 순회한다는 말은 결국 `stateDir/<namespace>/<task-id>/` 형태의 복구 대상 디렉터리들을 하나씩 다시 열어 본다는 뜻입니다.

// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim_load.go#L65-L123
```go
func (m *ShimManager) loadShims(ctx context.Context, stateDir string) error {
	// ...
	shimDirs, err := os.ReadDir(filepath.Join(stateDir, ns)) // ✅ ns 단위로 shim 디렉토리 순회
	if err != nil {
		return err
	}
	for _, sd := range shimDirs { // ✅ shim 디렉토리마다 bundle 단위로 복구 시도
		// ...
		bundle, err := LoadBundle(ctx, stateDir, id)
		if err != nil {
			break
		}
		eg.Go(func() error {
			// ...
			if err := m.loadShim(ctx2, bundle); err != nil {
				// ✅ bundle마다 개별 shim 재연결 시도
				bundle.Delete() // ✅ 복구 실패 시 bundle 삭제
				return nil
			}
			return nil
		})
	}
	_ = eg.Wait()
	return errLoad
}
```

이 시점의 핵심은 containerd가 새 shim을 무조건 다시 띄우지 않는다는 점입니다. 먼저 state directory에 남아 있는 bundle을 기준으로, 이미 존재하는 shim에 다시 붙을 수 있는지부터 확인합니다.

## `bootstrap.json`은 bootstrap 단계에서 이미 기록되어 있습니다

복구에서 `bootstrap.json`이 중요한 이유는 이 파일이 재시작 뒤에 갑자기 만들어지는 메모가 아니기 때문입니다. shim을 처음 bootstrap할 때 containerd가 이미 endpoint 정보를 이 파일에 써 둡니다.

// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/binary.go#L63-L95
```go
func (b *binary) Start(ctx context.Context, opts *types.Any, onClose func()) (_ *shim, err error) {
	args := []string{"-id", b.bundle.ID}
	args = append(args, "start")

	cmd, err := client.Command(ctx, &client.CommandConfig{
		Runtime:      b.runtime,
		Address:      b.containerdAddress,
		TTRPCAddress: b.containerdTTRPCAddress,
		Path:         b.bundle.Path,
		Opts:         opts,
		Args:         args,
		Env:          b.env,
	})
	// ...
	out, err := cmd.CombinedOutput()
	response := bytes.TrimSpace(out)

	params, err := parseStartResponse(response)
	conn, err := makeConnection(ctx, b.bundle.ID, params, onCloseWithShimLog)

	if err := writeBootstrapParams(filepath.Join(b.bundle.Path, "bootstrap.json"), params); err != nil {
		return nil, fmt.Errorf("failed to write bootstrap.json: %w", err)
	}

	return &shim{bundle: b.bundle, client: conn, address: fmt.Sprintf("%s+%s", params.Protocol, params.Address), version: params.Version}, nil
}
```

즉 재연결의 핵심 단서는 bootstrap 단계에서 이미 준비되어 있습니다. helper shim이 stdout으로 돌려준 `BootstrapParams`를 containerd가 파싱하고, 그 결과를 bundle 아래 `bootstrap.json`에 기록해 둡니다. 재시작 뒤 복구는 바로 이 정보를 다시 사용하는 과정입니다.

## `restoreBootstrapParams()`가 복구 입력을 되살립니다

재시작 뒤에는 `restoreBootstrapParams()`가 bundle 아래의 `bootstrap.json`을 읽어 복구에 필요한 `Version`, `Protocol`, `Address`를 되살립니다. 구버전 shim이면 예전 `address` 파일에서 migrate하는 경로도 여기 포함됩니다.

// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim_manager.go#L313-L338
```go
func restoreBootstrapParams(bundlePath string) (shimbinary.BootstrapParams, error) {
	filePath := filepath.Join(bundlePath, "bootstrap.json")

	if _, err := os.Stat(filePath); err == nil {
		return readBootstrapParams(filePath) // ✅ 이미 있으면 그대로 복원
	} else if !errors.Is(err, os.ErrNotExist) {
		return shimbinary.BootstrapParams{}, fmt.Errorf("failed to stat %s: %w", filePath, err)
	}

	address, err := shimbinary.ReadAddress(filepath.Join(bundlePath, "address"))
	if err != nil {
		return shimbinary.BootstrapParams{}, fmt.Errorf("unable to migrate shim: failed to get socket address for bundle %s: %w", bundlePath, err)
	}

	params := shimbinary.BootstrapParams{
		Version:  2,
		Address:  address,
		Protocol: "ttrpc", // ✅ 구버전 shim이면 address 파일에서 migration
	}

	if err := writeBootstrapParams(filePath, params); err != nil {
		return shimbinary.BootstrapParams{}, fmt.Errorf("unable to migrate: failed to write bootstrap.json file: %w", err)
	}

	return params, nil
}
```

즉 `bootstrap.json`은 단순 캐시가 아닙니다. containerd가 다시 떠올랐을 때 shim endpoint를 복구하는 기준점이며, 동시에 구버전 shim과의 호환성 migration까지 맡고 있습니다.

## `loadShim()`은 같은 shim endpoint에 다시 연결합니다

복구 입력을 얻은 뒤 실제 연결을 다시 만드는 곳은 `loadShim()`입니다. 여기서 중요한 점은 새 shim 프로세스를 띄우는 것이 아니라, 기존 bundle 경로에서 복원한 bootstrap 파라미터로 `makeConnection(...)`을 호출한다는 것입니다.

// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim.go#L72-L134
```go
func loadShim(ctx context.Context, bundle *Bundle, onClose func()) (_ ShimInstance, retErr error) {
	// ...
	params, err := restoreBootstrapParams(bundle.Path)
	if err != nil {
		return nil, fmt.Errorf("failed to read bootstrap.json when restoring bundle %q: %w", bundle.ID, err)
	}

	conn, err := makeConnection(ctx, bundle.ID, params, onCloseWithShimLog)
	if err != nil {
		return nil, fmt.Errorf("unable to make connection: %w", err)
	}

	address := fmt.Sprintf("%s+%s", params.Protocol, params.Address)
	shim := &shim{
		bundle:  bundle,
		client:  conn,
		address: address,
		version: params.Version,
	}

	return shim, nil
}
```

즉 재시작 뒤의 복원은 "컨테이너를 다시 실행한다"가 아닙니다. 더 정확히는 "이미 살아 있는 shim에 다시 연결해 control plane 핸들을 회복한다"입니다.

## `loadShimTask()`가 실제 응답까지 확인합니다

여기서 복구가 끝나지 않는다는 점이 중요합니다. `loadShimTask()`는 단순히 주소 문자열을 읽고 `shim` 객체를 만드는 데서 멈추지 않습니다. 임시 `shimTask` client를 만든 뒤 `PID()` 호출로 TaskService가 실제로 응답하는지 확인합니다.

// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim_load.go#L202-L237
```go
func loadShimTask(ctx context.Context, bundle *Bundle, onClose func()) (_ *shimTask, retErr error) {
	shim, err := loadShim(ctx, bundle, onClose)
	if err != nil {
		return nil, err
	}
	// ✅ TaskService 연결 확인용 임시 client 생성
	s, err := newShimTask(shim)
	if err != nil {
		return nil, err
	}

	ctx, cancel := timeout.WithContext(ctx, loadTimeout)
	defer cancel()

	if _, err := s.PID(ctx); err != nil {
		if !errdefs.IsNotImplemented(err) {
			return nil, err
		}
		// ...
	}
	return s, nil
}
```

즉 재연결은 "주소를 복원했다"에서 끝나는 정적 복구가 아닙니다. 실제 shim endpoint에 붙어서 task service가 살아 있는지까지 확인하는 동적 복구입니다.

## 이것이 의미하는 바

여기까지의 흐름을 묶으면, containerd 재시작 뒤 복구는 아래 순서로 이해하는 편이 가장 정확합니다.

1. `NewTaskManager()`가 올라오면서 `LoadExistingShims()`를 호출합니다.
2. `LoadExistingShims()`가 namespace와 bundle을 다시 훑습니다.
3. 각 bundle마다 `loadShim()`이 `bootstrap.json`을 읽고 기존 shim endpoint에 다시 붙습니다.
4. `loadShimTask()`가 `PID()` 호출로 TaskService 응답 여부를 확인합니다.
5. 연결이 유효하면 containerd는 기존 shim과 컨테이너에 대한 control plane을 다시 회복합니다.

이 관점에서 보면 shim은 데이터 플레인에 매우 가까운 프로세스입니다. kubelet과 containerd가 control plane 쪽에 더 가깝다면, shim은 이미 실행 중인 컨테이너 상태, stdio/FIFO, exec 프로세스, 종료 상태, 그리고 재접속 가능한 endpoint를 붙들고 있습니다. 그래서 containerd가 한 번 내려가더라도 컨테이너가 곧바로 사라져야 할 이유는 없습니다.

---

## 마치며

shim 재연결은 `bootstrap.json`을 읽는 작은 helper 하나로 설명되기 쉽지만, 실제 코드는 더 구조적입니다. task manager 초기화가 복구를 시작하고, `loadShims()`가 bundle들을 다시 찾고, `loadShim()`이 endpoint를 복원하고, `loadShimTask()`가 마지막으로 실제 응답까지 검증합니다.

따라서 containerd 재시작 이후의 복원은 "새 shim 기동"도 아니고 "컨테이너 재실행"도 아닙니다. 이미 살아 있는 shim과 컨테이너에 다시 제어 채널을 연결하는 절차입니다.

이제 다음 단계로 넘어가면, 이런 shim이 CRI에서 pod sandbox와 일반 workload container를 어떤 단위로 묶는지까지도 더 자연스럽게 이해할 수 있습니다.