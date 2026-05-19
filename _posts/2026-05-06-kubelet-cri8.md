---
title: "kubernetes data plane: containerd shim 재연결과 bootstrap.json 복구 경로"
date: 2026-05-06 00:00:00 +0900
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

# TaskManager와 Shim 재연결

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
		if err := m.loadShims(namespaces.WithNamespace(ctx, ns), stateDir); err != nil { // ✅ containerd namespace를 고정한 뒤 그 아래 bundle들을 복구
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

여기서 먼저 도는 것은 컨테이너 디렉터리가 아니라 containerd namespace 디렉터리입니다. 즉 `LoadExistingShims()`의 첫 단계는 `stateDir` 바로 아래에서 `k8s.io`, `default` 같은 namespace를 고르고, 실제 task/container bundle 복구는 그 다음 `loadShims()` 안에서 `stateDir/<namespace>/` 아래 항목들을 다시 순회하면서 일어납니다. 여기서 말하는 namespace는 `ip netns`에 보이는 리눅스 네트워크 namespace가 아니라 containerd metadata namespace입니다.

여기서 `stateDir`는 기본 구성에서 대략 `/run/containerd/io.containerd.runtime.v2.task`입니다. 또 kubernetes는 containerd를 `k8s.io` namespace로 띄우는 게 일반적이므로, 실제 복구 대상 디렉터리는 `/run/containerd/io.containerd.runtime.v2.task/k8s.io/`가 됩니다. 이 아래에 pod sandbox나 workload container 단위로 bundle 디렉터리가 놓이는 형태입니다.

# bundle 단위 복구

containerd namespace 하나를 고른 뒤 containerd가 실제로 다시 여는 것은 bundle 디렉터리들입니다. 즉 복구의 실질적인 단위는 "namespace 아래의 각 task/container bundle"입니다. 여기서 bundle은 `stateDir/<namespace>/<task-id>/` 아래에 놓이는 OCI bundle 디렉터리이며, 이후 복구 코드는 이 디렉터리 안의 `bootstrap.json`과 상태 파일을 다시 읽는 방식으로 진행됩니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim_load.go#L65-L123
func (m *ShimManager) loadShims(ctx context.Context, stateDir string) error {
	// ...
	shimDirs, err := os.ReadDir(filepath.Join(stateDir, ns)) // ✅ ns 아래의 bundle 디렉터리 순회
	if err != nil {
		return err
	}
	for _, sd := range shimDirs { // ✅ bundle마다 복구 시도
		// ...
		bundle, err := LoadBundle(ctx, stateDir, id)
		if err != nil {
			break
		}
		eg.Go(func() error {
			// ...
			if err := m.loadShim(ctx2, bundle); err != nil {
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

여기서 말하는 bundle은 이미지 레이어나 snapshot 이름이 아니라 OCI bundle 디렉터리입니다. runtime v2 task manager는 이 디렉터리를 task ID 기준으로 만들고, CRI의 일반 workload container 경로에서는 그 task ID가 사실상 container ID처럼 보입니다.

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

runtime v2의 `Bundle` 구조체도 이 디렉터리를 `stateDir/<namespace>/<task-id>` 형태로 계산합니다.

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

따라서 `LoadExistingShims()`가 복구할 때 실제로 하는 일은 `stateDir/<namespace>/<task-id>/` 디렉터리들을 다시 열어 보고, 각 디렉터리마다 살아 있는 shim에 다시 붙을 수 있는지 확인하는 것입니다.

여기까지 읽으면 자연스럽게 질문이 생깁니다. "bundle 디렉터리만 보고 containerd가 어떻게 어떤 shim endpoint에 다시 붙어야 하는지 알 수 있을까?"

# bundle의 endpoint 정보

복구 시점에 containerd가 새로 추론하는 것은 많지 않습니다. 핵심 정보는 컨테이너를 처음 만들 때 이미 bundle 안에 기록해 둡니다. 가장 일반적인 경로에서는 shim bootstrap이 끝나는 순간 `bootstrap.json`이 바로 쓰입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/binary.go#L63-L95
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

	if err := writeBootstrapParams(filepath.Join(b.bundle.Path, "bootstrap.json"), params); err != nil { // ✅ shim bootstrap이 끝나는 순간 bootstrap.json에 endpoint 정보 기록
		return nil, fmt.Errorf("failed to write bootstrap.json: %w", err)
	}

	return &shim{bundle: b.bundle, client: conn, address: fmt.Sprintf("%s+%s", params.Protocol, params.Address), version: params.Version}, nil
}
```

즉 helper shim이 stdout으로 돌려준 `BootstrapParams`를 containerd가 파싱하고, 그 결과를 bundle 아래 `bootstrap.json`에 저장합니다. 재시작 뒤 복구는 이 파일을 다시 읽는 과정입니다.

Linux의 `containerd-shim-runc-v2`는 보통 shim endpoint를 `unix:///run/containerd/s/<sha256>` 같은 unix 주소 문자열로 돌려주고, 그 값이 그대로 `bootstrap.json`의 `address` 필드에 저장됩니다. 따라서 해당 필드를 읽으면 재시작 뒤에도 같은 주소로 다시 붙을 수 있습니다.

## shared shim 복구 과정

한편 sandbox-aware shim의 경우 여러 컨테이너가 같은 pod sandbox shim을 공유한다면, 각 workload container bundle만 보고 어떻게 같은 shim에 다시 붙을 수 있는지 확인할 필요가 있습니다.

답은 여기도 같습니다. 복구 시점에 다시 알아내는 것이 아니라, 생성 시점에 이미 각 workload bundle에 같은 endpoint 정보를 복제해 둡니다.

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

즉 pod 단위로 공유되는 것은 bundle이 아니라 shim endpoint입니다. pause sandbox 자체는 자기 bundle을 하나 갖고, 같은 pod의 일반 workload container들도 자기 bundle을 각각 갖습니다. 다만 sandbox-aware shim 경로에서는 이 여러 bundle의 `bootstrap.json`이 같은 endpoint를 가리키게 됩니다. 그래서 재시작 뒤 `LoadExistingShims()`는 각 bundle을 독립적으로 훑어도 결과적으로 같은 shared shim에 다시 붙을 수 있습니다.

참고로 v2.2.1 기준으로 `sandbox` 파일은 이 컨테이너가 어느 sandbox에 속하는지 기록해 두는 용도이고, `LoadExistingShims()`가 재시작 복구 중에 다시 읽는 핵심 입력은 아닙니다. 재연결의 직접 입력은 `bootstrap.json`입니다.

# restoreBootstrapParams 복구 입력

재시작 뒤에는 `restoreBootstrapParams()`가 bundle 아래의 `bootstrap.json`을 읽어 복구에 필요한 `Version`, `Protocol`, `Address`를 되살립니다. 구버전 shim이면 예전 `address` 파일에서 migrate하는 경로도 여기 포함됩니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim_manager.go#L313-L338
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

# shim endpoint 재연결

복구 입력을 얻은 뒤 실제 연결을 다시 만드는 곳은 `loadShim()`입니다. 여기서 중요한 점은 새 shim 프로세스를 띄우는 것이 아니라, 기존 bundle 경로에서 복원한 bootstrap 파라미터로 `makeConnection(...)`을 호출한다는 것입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim.go#L72-L134
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

# shim task 연결 확인

여기서 복구가 끝나지 않는다는 점이 중요합니다. `loadShimTask()`는 단순히 주소 문자열을 읽고 `shim` 객체를 만드는 데서 멈추지 않습니다. 임시 `shimTask` client를 만든 뒤 `PID()` 호출로 TaskService가 실제로 응답하는지 확인합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/core/runtime/v2/shim_load.go#L202-L237
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

---

여기까지의 흐름을 묶으면, containerd 재시작 뒤 복구는 아래 순서로 이해하는 편이 가장 정확합니다.

1. `NewTaskManager()`가 올라오면서 `LoadExistingShims()`를 호출합니다.
2. `LoadExistingShims()`가 namespace와 bundle을 다시 훑습니다.
3. 각 bundle은 자기 `bootstrap.json`에 복구 입력을 이미 들고 있고, shared shim이라면 여러 bundle이 같은 endpoint를 가리킵니다.
4. `loadShim()`이 그 정보를 읽고 기존 shim endpoint에 다시 붙습니다.
5. `loadShimTask()`가 `PID()` 호출로 TaskService 응답 여부를 확인하고, 연결이 유효하면 containerd는 기존 shim과 컨테이너에 대한 control plane을 다시 회복합니다.

이 관점에서 보면 shim은 데이터 플레인에 매우 가까운 프로세스입니다. kubelet과 containerd가 control plane 쪽에 더 가깝다면, shim은 이미 실행 중인 컨테이너 상태, stdio/FIFO, exec 프로세스, 종료 상태, 그리고 재접속 가능한 endpoint를 붙들고 있습니다. 그래서 containerd가 한 번 내려가더라도 컨테이너가 곧바로 사라져야 할 이유는 없습니다.

---

# 마치며

shim 재연결은 `bootstrap.json`을 읽는 작은 helper 하나로 설명되기 쉽지만, 실제 코드는 더 구조적입니다. task manager 초기화가 복구를 시작하고, `loadShims()`가 bundle들을 다시 찾고, 각 bundle에 남아 있는 `bootstrap.json`이 복구 입력을 제공하며, `loadShim()`이 endpoint를 복원하고, `loadShimTask()`가 마지막으로 실제 응답까지 검증합니다.

따라서 containerd 재시작 이후의 복원은 "새 shim 기동"도 아니고 "컨테이너 재실행"도 아닙니다. 이미 살아 있는 shim과 컨테이너에 다시 제어 채널을 연결하는 절차입니다. shared shim도 이 기본 흐름의 예외가 아니라, 여러 bundle이 같은 endpoint를 미리 공유하도록 기록해 두는 변형으로 이해하는 편이 자연스럽습니다.
