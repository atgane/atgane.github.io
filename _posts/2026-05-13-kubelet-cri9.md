---
title: "kubernetes data plane: CRI에서 CNI호출하는 흐름 자세히 알아보기"
date: 2026-05-13 00:00:00 +0900
categories:
  - containerd
tags:
  - containerd
  - kubernetes
  - CRI
  - CNI
  - RunPodSandbox
  - go-cni
excerpt: "RunPodSandbox 이후 setupPodNetwork만이 아니라, containerd가 CNI config를 읽고 실제 CNI 바이너리에 env와 stdin JSON을 넘기는 지점까지 추적합니다."
toc: true
toc_sticky: true
author_profile: false
header:
  teaser: /assets/images/posts/kubernetes.png
---

# CNI 설정과 입력

## 복습

이전 아티클에서 추적한 범위는 `RunPodSandbox()`가 파드 전용 netns를 만든 뒤, 그 경로를 `sandbox.NetNSPath`에 저장하는 지점까지였습니다. 즉 이전 글은 파드별 네트워크 네임스페이스 준비에서 멈췄고, 아직 containerd가 어떤 CNI 설정 파일을 읽고 그 설정이 언제 실제 바이너리 실행으로 이어지는지는 다루지 않았습니다.

```go
func (c *criService) RunPodSandbox(...) {
  // ...
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/sandbox_run.go#L195
  if !hostNetwork(config) {
    if !userNsEnabled {
      // ✅ 파드 전용 netns 생성
      sandbox.NetNS, err = netns.NewNetNS(netnsMountDir)
    } else {
      usernsOpts := config.GetLinux().GetSecurityContext().GetNamespaceOptions().GetUsernsOptions()
      // ✅ userns 경로에서도 netns 준비
      sandbox.NetNS, err = c.setupNetnsWithinUserns(netnsMountDir, usernsOpts)
    }
    // ...
    // ✅ 이후 CNI 바이너리에 전달될 netns 경로 확정
    sandbox.NetNSPath = sandbox.NetNS.GetPath()

    // ✅ 다음 단계는 setupPodNetwork 내부
    if err := c.setupPodNetwork(ctx, &sandbox); err != nil {
      return nil, fmt.Errorf("failed to setup network for sandbox %q: %w", id, err)
    }
  }
}
```

여기까지가 이전 글의 실제 범위였습니다. 이 글은 먼저 서비스 시작 시 CNI config가 어떻게 선택되고 메모리에 올라가는지 정리합니다. 이어서 같은 설정이 파드 생성 시점에 어떤 env와 stdin JSON으로 바뀌는지도 추적합니다.

## CNI 설정 읽기

containerd는 파드 생성 시점마다 CNI 설정 파일을 임의로 찾는 것이 아니라, 서비스 초기화 단계에서 먼저 CNI 로더를 만들고 `conf_dir`, `bin_dirs`, `max_conf_num`을 주입합니다. Linux 기본값은 CNI 바이너리 디렉터리 `/opt/cni/bin`, CNI 설정 디렉터리 `/etc/cni/net.d`, 그리고 최대 1개의 설정 로드입니다. 이 절은 서비스 초기화, `Load()` opt 실행, 그리고 watch 기반 재로드 순서로 읽으면 흐름이 자연스럽습니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/config/config_unix.go#L26-L27
func defaultNetworkPluginBinDirs() []string {
  return []string{"/opt/cni/bin"}
}

// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/config/config_unix.go#L82-L91
func DefaultRuntimeConfig() RuntimeConfig {
  return RuntimeConfig{
    CniConfig: CniConfig{
      NetworkPluginBinDirs:       defaultNetworkPluginBinDirs(),
      NetworkPluginConfDir:       "/etc/cni/net.d",
      NetworkPluginMaxConfNum:    1,
      // ✅ 기본은 첫 번째 유효한 CNI config 1개만 로드
      NetworkPluginSetupSerially: false,
    },
    // ...
  }
}
```

이 섹션의 호출 흐름은 다음과 같습니다.

- `NewCRIService()`: runtime handler별 `conf_dir`를 고르고 CNI monitor를 붙일 대상을 정합니다.
- `initPlatform()`: `cni.New(...)`로 `conf_dir`, `bin_dirs`, `max_conf_num`이 들어간 CNI 로더를 만듭니다.
- `newCNINetConfSyncer()`: 설정 디렉터리 감시 객체를 만들고 초기 CNI 로드 상태를 준비합니다.
- `Load()`: `conf_dir`를 스캔해 사용할 CNI 설정을 실제로 읽어 메모리에 올립니다.

여기서 `conf_dir`는 설정 JSON을 읽는 위치이고, `bin_dirs`는 나중에 실제 플러그인 바이너리를 찾는 검색 경로입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/service.go#L184-L242
func NewCRIService(options *CRIServiceOptions) (CRIService, runtime.RuntimeServiceServer, error) {
  // ...
  if err := c.initPlatform(); err != nil {
    // ✅ 먼저 platform별 CNI 로더 준비
    return nil, nil, fmt.Errorf("initialize platform: %w", err)
  }
  // ...
  c.cniNetConfMonitor = make(map[string]*cniNetConfSyncer)
  for name, i := range c.netPlugin {
    // ...
    // ✅ initPlatform()이 준비한 netPlugin으로 syncer 생성
    m, err := newCNINetConfSyncer(path, i, c.cniLoadOptions())
    if err != nil {
      // ...
    }
  }
  // ...
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/service_linux.go#L79-L91
func (c *criService) initPlatform() error {
  // ...
  i, err := cni.New(cni.WithMinNetworkCount(networkAttachCount),
    cni.WithPluginConfDir(dir),
    cni.WithPluginMaxConfNum(max),
    cni.WithPluginDir(c.config.NetworkPluginBinDirs))
  if err != nil {
    return fmt.Errorf("failed to initialize cni: %w", err)
  }
  // ✅ conf_dir에서 설정을 읽을 로더와 bin_dirs 검색 경로를 함께 준비
  c.netPlugin[name] = i
  // ...
}
```

`NewCRIService()`가 서비스 초기화의 top이고, 그 안에서 `initPlatform()`으로 로더를 만든 다음 같은 함수 안에서 `newCNINetConfSyncer()`를 붙입니다. monitor 생성 시점에 바로 `Load()`를 호출하므로 파드가 뜨기 전에 이미 설정 파일 파싱이 시작됩니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/cni_conf_syncer.go#L44-L73
func newCNINetConfSyncer(confDir string, netPlugin cni.CNI, loadOpts []cni.Opt) (*cniNetConfSyncer, error) {
  // ...
  if err := syncer.netPlugin.Load(syncer.loadOpts...); err != nil {
    // ✅ 시작 시점에 1회 로드
    log.L.WithError(err).Error("failed to load cni during init, please check CRI plugin status before setting up network for pods")
    syncer.updateLastStatus(err)
  }
  return syncer, nil
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/cni.go#L123-L136
func (c *libcni) Load(opts ...Opt) error {
  var err error
  c.Lock()
  defer c.Unlock()

  // ✅ 이전 network 목록 초기화
  c.reset()

  for _, o := range opts {
    // ✅ load option이 conf_dir 스캔과 기본 config 선택 수행
    if err = o(c); err != nil {
      return fmt.Errorf("cni config load failed: %v: %w", err, ErrLoad)
    }
  }
  return nil
}
```

위의 `Load()` 안의 `for _, o := range opts`가 Linux 경로에서 넘겨받은 opt를 순서대로 실행하고, 그 opt 목록은 `cniLoadOptions()`가 만듭니다. 코드를 보기 전에 역할만 먼저 고정하면, `WithLoNetwork`는 loopback 네트워크를 추가하고 `WithDefaultConf`는 실제 기본 CNI 설정 파일을 고르는 helper입니다. 즉 이 구간은 `cniLoadOptions()`가 `WithLoNetwork`, `WithDefaultConf`를 돌려주고, `Load()`가 그중 `WithDefaultConf()`를 실행한 뒤, 그 함수 안에서 `loadFromConfDir()`로 내려가게 됩니다.

이 지점의 호출 흐름은 다음과 같습니다.

- `cniLoadOptions()`: Linux에서 `Load()`에 넘길 opt 목록을 구성합니다.
- `Load()`: 전달받은 opt를 앞에서부터 순서대로 실행합니다.
- `WithLoNetwork()`: loopback network를 먼저 추가합니다.
- `WithDefaultConf()`: 기본 CNI config 탐색 로직으로 들어갑니다.
- `loadFromConfDir()`: `conf_dir` 후보 파일을 읽고 기본 network를 고릅니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/service_linux.go#L112-L117
func (c *criService) cniLoadOptions() []cni.Opt {
  return []cni.Opt{cni.WithLoNetwork, cni.WithDefaultConf}
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/cni.go#L123-L136
func (c *libcni) Load(opts ...Opt) error {
  // ✅ 이전 network 목록 초기화
  c.reset()

  for _, o := range opts {
    // ✅ 넘겨받은 opt를 순서대로 실행
    if err := o(c); err != nil {
      return fmt.Errorf("cni config load failed: %v: %w", err, ErrLoad)
    }
  }
  return nil
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/opts.go#L88-L96
func WithLoNetwork(c *libcni) error {
  loConfig, _ := cnilibrary.ConfListFromBytes([]byte(`{
"cniVersion": "0.3.1",
"name": "cni-loopback",
"plugins": [{
  "type": "loopback"
}]
}`))
  // ✅ loopback network를 먼저 추가
  c.networks = append(c.networks, &Network{
    cni:    c.cniConfig,
    config: loConfig,
    ifName: "lo",
  })
  return nil
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/opts.go#L194-L199
func WithDefaultConf(c *libcni) error {
  // ✅ 기본 config 선택 로직은 loadFromConfDir로 위임
  return loadFromConfDir(c, c.pluginMaxConfNum)
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/opts.go#L206-L240
func loadFromConfDir(c *libcni, maxConfigs int) error {
  files, err := cnilibrary.ConfFiles(c.pluginConfDir, []string{".conf", ".conflist", ".json"})
  // ✅ conf_dir 아래의 후보 파일 수집
  sort.Strings(files)
  // ✅ 사전순 정렬 후 default network 결정
  for _, confFile := range files {
    if strings.HasSuffix(confFile, ".conflist") {
      // ✅ conflist는 그대로 로드
      confList, err = cnilibrary.ConfListFromFile(confFile)
    } else {
      conf, err := cnilibrary.ConfFromFile(confFile)
      if conf.Network.Type == "" {
        // ✅ 단일 conf/json도 반드시 type이 있어야 함
        return fmt.Errorf("network type not found in %s: %w", confFile, ErrInvalidConfig)
      }
      // ✅ 단일 conf/json은 내부적으로 conflist로 승격
      confList, err = cnilibrary.ConfListFromConf(conf)
    }
    // ...
  }
  // ...
}

```


즉 `cilium`, `calico` 같은 환경 이름을 containerd가 따로 아는 것은 아닙니다. containerd는 `conf_dir` 아래의 `.conf`, `.conflist`, `.json` 파일을 읽고, 기본값 기준으로는 사전순으로 가장 먼저 오는 유효한 파일 1개를 선택합니다. 그리고 그 파일 안의 각 plugin entry에서 `type`을 읽습니다.

여기서 비로소 아래와 같은 해석이 가능합니다.

- 선택된 plugin entry의 `type: "cilium-cni"`이면 나중에 `/opt/cni/bin/cilium-cni`를 찾습니다.
- 선택된 plugin entry의 `type: "ptp"`이면 나중에 `/opt/cni/bin/ptp`를 찾습니다.
- 아직 이 단계에서는 실행하지 않고, 어떤 설정 JSON을 쓸지와 그 안의 `type`만 확정합니다.

### 재로드

`newCNINetConfSyncer()`는 init 시점에 1회 `Load()`만 호출하고 끝나지 않고, `criService.Run()`에서 goroutine으로 시작된 `syncLoop()`를 통해 `conf_dir`의 변경 이벤트를 계속 감시합니다. 즉 `containerd` 시작 때만 읽는 구조가 아니라, 설정 디렉터리 변경 시 재로드를 시도하는 구조입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/service.go#L277-L285
func (c *criService) Run(ready func()) error {
  // ...
  for name, h := range c.cniNetConfMonitor {
    log.L.Infof("Start cni network conf syncer for %s", name)
    go func(h *cniNetConfSyncer) {
      // ✅ monitor goroutine에서 watch loop 시작
      cniNetConfMonitorErrCh <- h.syncLoop()
      netSyncGroup.Done()
    }(h)
  }
}

// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/cni_conf_syncer.go#L81-L110
func (syncer *cniNetConfSyncer) syncLoop() error {
  for {
    select {
    case event, ok := <-syncer.watcher.Events:
      // ✅ watcher channel이 닫히면 loop 종료
      if !ok {
        return nil
      }
      // ✅ chmod, create 이벤트는 무시
      if event.Has(fsnotify.Chmod) || event.Has(fsnotify.Create) {
        continue
      }
      // ✅ conf dir 자체가 사라지면 watch 중단
      if event.Name == syncer.confDir && (event.Has(fsnotify.Rename) || event.Has(fsnotify.Remove)) {
        return fmt.Errorf("cni conf dir is removed, stop watching")
      }
      // ✅ write, rename, remove 계열 이벤트마다 Load() 재실행
      lerr := syncer.netPlugin.Load(syncer.loadOpts...)
      syncer.updateLastStatus(lerr)
    case err := <-syncer.watcher.Errors:
      // ✅ watcher 자체 오류는 즉시 반환
      if err != nil {
        return err
      }
    }
  }
}
```

watch loop가 특정 확장자를 직접 거르는 것은 아닙니다. 대신 디렉터리 이벤트를 받으면 `Load()` 전체를 다시 실행하고, 그 안의 `ConfFiles()`가 `.conf`, `.conflist`, `.json`만 다시 고릅니다. 따라서 CNI를 나중에 설치하거나 설정 파일을 교체해도 재시작 없이 반영될 수 있고, 그 시도의 성공 여부는 `lastCNILoadStatus`에서 확인할 수 있습니다.

## `crictl`을 이용한 확인 지점

이 흐름은 운영 환경에서도 세 군데에서 바로 확인할 수 있습니다.

- containerd 설정 파일이나 `containerd config dump`에서 `bin_dirs`, `conf_dir`, `max_conf_num`을 확인합니다.
- 실제 후보 파일은 `conf_dir` 기본값인 `/etc/cni/net.d` 아래에서 확인합니다.
- containerd가 현재 메모리에 로드해 둔 결과는 `crictl info`의 `cniconfig`, `lastCNILoadStatus`에서 확인합니다.

`crictl info`가 유용한 이유는 `Status()`와 `GetConfig()`가 현재 로드된 CNI 설정과 마지막 CNI 로드 상태를 그대로 노출하기 때문입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/status.go#L82-L102
func (c *criService) Status(ctx context.Context, r *runtime.StatusRequest) (*runtime.StatusResponse, error) {
  // ...
  if netPlugin != nil {
    cniConfig, err := json.Marshal(netPlugin.GetConfig())
    if err != nil {
      // ...
    }
    // ✅ 현재 로드된 CNI 설정을 status info에 그대로 노출
    resp.Info["cniconfig"] = string(cniConfig)
  }
  // ✅ 마지막 CNI 재로드 성공/실패도 함께 노출
  resp.Info["lastCNILoadStatus"] = defaultStatus
  // ...
}

// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/cni.go#L300-L322
func (c *libcni) GetConfig() *ConfigResult {
  r := &ConfigResult{
    PluginDirs:       c.config.pluginDirs,
    PluginConfDir:    c.config.pluginConfDir,
    PluginMaxConfNum: c.config.pluginMaxConfNum,
    Prefix:           c.config.prefix,
  }
  for _, network := range c.networks {
    conf := &NetworkConfList{
      Name:       network.config.Name,
      CNIVersion: network.config.CNIVersion,
      // ✅ 로드된 원본 JSON 문자열도 함께 보존
      Source: string(network.config.Bytes),
    }
    // ...
    r.Networks = append(r.Networks, &ConfNetwork{Config: conf, IFName: network.ifName})
  }
  return r
}
```

즉 `crictl info`를 보면 단순히 `conf_dir` 경로만이 아니라, containerd가 실제로 어떤 CNI 설정을 파싱해 들고 있는지도 확인할 수 있습니다. 반대로 `lastCNILoadStatus`에 에러가 보이면 `/etc/cni/net.d` 아래 파일 형식이나 `type`에 맞는 바이너리 존재 여부를 먼저 의심하면 됩니다.

## 파드 생성 시점

이제 시점을 파드 생성으로 옮기겠습니다. 서비스 시작 시점에는 방금 본 `Load()` 경로가 어떤 CNI config를 쓸지 먼저 확정하고, 파드 생성 시점에는 `RunPodSandbox()`에서 `setupPodNetwork()`로 내려오며 이미 로드된 그 config에 파드별 런타임 값을 주입합니다.

즉 실제 흐름은 다음과 같습니다.

- `Load()`: 서비스 시작 시 사용할 CNI 설정과 plugin 목록을 먼저 메모리에 올립니다.
- `RunPodSandbox()`: sandbox용 netns 경로를 준비하고 네트워크 설정 진입점까지 내려갑니다.
- `setupPodNetwork()`: `PodSandboxConfig`를 CNI 입력 옵션으로 변환합니다.
- `netPlugin.Setup()`: sandbox ID, netns 경로, capability를 `RuntimeConf`로 묶습니다.
- libcni `addNetwork()`: `type`으로 바이너리를 찾고 env와 stdin JSON을 구성해 실제 플러그인을 실행합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/cni.go#L123-L136
func (c *libcni) Load(opts ...Opt) error {
  // ✅ 이전 network 목록을 지우고
  c.reset()

  for _, o := range opts {
    // ✅ load option으로 실제 config 로드 수행
    if err := o(c); err != nil {
      return fmt.Errorf("cni config load failed: %v: %w", err, ErrLoad)
    }
  }
  return nil
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/sandbox_run.go#L252-L264
func (c *criService) RunPodSandbox(...) {
  // ...
  // ✅ netns 준비 뒤 CNI 설정 진입
  if err := c.setupPodNetwork(ctx, &sandbox); err != nil {
    return nil, fmt.Errorf("failed to setup network for sandbox %q: %w", id, err)
  }
  // ...
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/sandbox_run.go#L394
func (c *criService) setupPodNetwork(ctx context.Context, sandbox *sandboxstore.Sandbox) error {
  var (
    // ✅ RunPodSandbox에서 준비한 sandbox ID, netns 경로, PodSandboxConfig 사용
    id        = sandbox.ID
    config    = sandbox.Config
    path      = sandbox.NetNSPath
    netPlugin = c.getNetworkPlugin(sandbox.RuntimeHandler)
  )

  // ✅ PodSandboxConfig를 CNI 입력으로 변환
  opts, err := cniNamespaceOpts(id, config)
  if err != nil {
    return fmt.Errorf("get cni namespace options: %w", err)
  }

  // ✅ 다음 단계는 go-cni Setup
  result, err := netPlugin.Setup(ctx, id, path, opts...)
  // ...
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/cni.go#L167
func (c *libcni) Setup(ctx context.Context, id string, path string, opts ...NamespaceOpts) (*Result, error) {
  if err := c.ready(); err != nil {
    return nil, err
  }
  // ✅ sandbox ID, netns 경로, capability를 RuntimeConf 재료로 묶음
  ns, err := newNamespace(id, path, opts...)
  if err != nil {
    return nil, err
  }
  // ✅ attachNetworks 아래에서 결국 addNetwork까지 내려감
  result, err := c.attachNetworks(ctx, ns)
  if err != nil {
    return nil, err
  }
  return c.createResult(result)
}
```

즉 복습 코드와 이번 글의 실제 기준점 사이에는 `setupPodNetwork()`와 `netPlugin.Setup()`이 한 단계 끼어 있습니다. 그다음부터가 실제 CNI 바이너리 경로를 고르고 입력을 넘기는 구간입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/libcni/api.go#L490
func (c *CNIConfig) addNetwork(ctx context.Context, name, cniVersion string, net *PluginConfig, prevResult types.Result, rt *RuntimeConf) (types.Result, error) {
  // ✅ "cilium-cni", "ptp", "portmap" 같은 type으로 실제 바이너리 경로 결정
  pluginPath, err := c.exec.FindInPath(net.Network.Type, c.Path)
  if err != nil {
    return nil, err
  }

  // ✅ stdin으로 넘길 JSON 조립
  newConf, err := buildOneConfig(name, cniVersion, net, prevResult, rt)
  if err != nil {
    return nil, err
  }

  // ✅ env + stdin JSON을 함께 전달
  return invoke.ExecPluginWithResult(ctx, pluginPath, newConf.Bytes, c.args("ADD", rt), c.exec)
}
```

실제 exec는 `RawExec.ExecPlugin()`이 수행합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/pkg/invoke/raw_exec.go#L34
func (e *RawExec) ExecPlugin(ctx context.Context, pluginPath string, stdinData []byte, environ []string) ([]byte, error) {
  // ✅ 실제 CNI 바이너리는 환경 변수와 stdin JSON을 입력으로 받아 실행됨
  c := exec.CommandContext(ctx, pluginPath)
  c.Env = environ
  c.Stdin = bytes.NewBuffer(stdinData)
  c.Stdout = stdout
  c.Stderr = stderr

  err := c.Run()
  // ...
}
```

즉 containerd는 `bridge --netns ...` 같은 커맨드라인 인자를 붙여 실행하지 않습니다. `type`으로 바이너리를 고른 뒤, CNI 표준 입력 형식에 맞게 env와 stdin을 채워 실행합니다.

여기서 중요한 점은 `PodSandboxConfig`가 두 갈래로 나뉜다는 것입니다.

- 단순 key/value 메타데이터는 `CNI_ARGS`로 갑니다.
- 구조화된 값은 stdin JSON의 `runtimeConfig`로 갑니다.

## CNI_ARGS

여기서부터는 `setupPodNetwork()`가 만든 입력이 env와 stdin으로 어떻게 갈라지는지를 나누어 봅니다. 먼저 파드 메타데이터는 `WithLabels()`를 통해 `Args`로 들어갑니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/sandbox_run.go#L440
func cniNamespaceOpts(id string, config *runtime.PodSandboxConfig) ([]cni.NamespaceOpts, error) {
  opts := []cni.NamespaceOpts{
    cni.WithLabels(toCNILabels(id, config)),
    // ✅ 메타데이터와 어노테이션 수집
    cni.WithCapability(annotations.PodAnnotations, config.Annotations),
  }

  portMappings := toCNIPortMappings(config.GetPortMappings())
  if len(portMappings) > 0 {
    // ✅ portMappings는 runtimeConfig 후보
    opts = append(opts, cni.WithCapabilityPortMap(portMappings))
  }

  // ...
  return opts, nil
}

// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/sandbox_run.go#L474
func toCNILabels(id string, config *runtime.PodSandboxConfig) map[string]string {
  // ✅ 이 값들이 최종적으로 CNI_ARGS로 직렬화됨
  return map[string]string{
    "K8S_POD_NAMESPACE":          config.GetMetadata().GetNamespace(),
    "K8S_POD_NAME":               config.GetMetadata().GetName(),
    "K8S_POD_INFRA_CONTAINER_ID": id,
    "K8S_POD_UID":                config.GetMetadata().GetUid(),
    "IgnoreUnknown":              "1",
  }
}
```

go-cni는 이 값을 `RuntimeConf.Args`로 옮깁니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/go-cni/namespace.go#L70
func (ns *Namespace) config(ifName string) *cnilibrary.RuntimeConf {
  c := &cnilibrary.RuntimeConf{
    ContainerID: ns.id,
    NetNS:       ns.path,
    IfName:      ifName,
  }
  for k, v := range ns.args {
    // ✅ CNI_ARGS 후보
    c.Args = append(c.Args, [2]string{k, v})
  }
  // ✅ runtimeConfig 후보
  c.CapabilityArgs = ns.capabilityArgs
  return c
}
```

그리고 libcni가 이를 표준 환경 변수로 직렬화합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/libcni/api.go#L891
func (c *CNIConfig) args(action string, rt *RuntimeConf) *invoke.Args {
  return &invoke.Args{
    Command:     action,
    ContainerID: rt.ContainerID,
    NetNS:       rt.NetNS,
    PluginArgs:  rt.Args,
    IfName:      rt.IfName,
    Path:        strings.Join(c.Path, string(os.PathListSeparator)),
  }
}

// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/pkg/invoke/args.go#L56
func (args *Args) AsEnv() []string {
  env = append(env,
    "CNI_COMMAND="+args.Command,
    "CNI_CONTAINERID="+args.ContainerID,
    "CNI_NETNS="+args.NetNS,
    "CNI_ARGS="+pluginArgsStr,
    "CNI_IFNAME="+args.IfName,
    "CNI_PATH="+args.Path,
  )
  return dedupEnv(env)
}
```

즉 실제 바이너리는 대략 이런 env를 받습니다.

- `CNI_COMMAND=ADD`
- `CNI_CONTAINERID=<sandbox id>`
- `CNI_NETNS=/var/run/netns/cni-<uuid>`
- `CNI_IFNAME=eth0`
- `CNI_PATH=/opt/cni/bin:...`
- `CNI_ARGS=K8S_POD_NAMESPACE=...;K8S_POD_NAME=...;K8S_POD_INFRA_CONTAINER_ID=...;K8S_POD_UID=...;IgnoreUnknown=1`

## stdin JSON

구조화된 값은 stdin JSON 쪽으로 갑니다. 이 섹션의 흐름은 다음과 같습니다.

- `addNetwork()`: `type`으로 실제 플러그인 바이너리 경로를 찾고 stdin JSON 조립을 시작합니다.
- `buildOneConfig()`: 원본 plugin JSON에 `name`, `cniVersion`, 필요하면 `prevResult`를 덧씌웁니다.
- `injectRuntimeConfig()`: 플러그인이 지원한다고 선언한 capability만 골라 `runtimeConfig`를 주입합니다.

즉 `conflist`에 적힌 `mtu`, `ipam`, `bridge` 같은 값이 언제 쓰이느냐에 대한 답도 바로 여기 있습니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/libcni/api.go#L490-L512
func (c *CNIConfig) addNetwork(ctx context.Context, name, cniVersion string, net *PluginConfig, prevResult types.Result, rt *RuntimeConf) (types.Result, error) {
  // ✅ type으로 실제 바이너리 경로 결정
  pluginPath, err := c.exec.FindInPath(net.Network.Type, c.Path)
  if err != nil {
    return nil, err
  }

  // ✅ 다음 단계에서 stdin JSON 조립
  newConf, err := buildOneConfig(name, cniVersion, net, prevResult, rt)
  if err != nil {
    return nil, err
  }

  // ✅ env와 stdin을 함께 넘겨 실행
  return invoke.ExecPluginWithResult(ctx, pluginPath, newConf.Bytes, c.args("ADD", rt), c.exec)
}
```

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/libcni/api.go#L155
func buildOneConfig(name, cniVersion string, orig *PluginConfig, prevResult types.Result, rt *RuntimeConf) (*PluginConfig, error) {
  inject := map[string]interface{}{
    "name":       name,
    "cniVersion": cniVersion,
  }
  if prevResult != nil {
    // ✅ 앞 플러그인 결과를 다음 플러그인 stdin에 추가
    inject["prevResult"] = prevResult
  }

  // ✅ 원본 plugin JSON을 base로 유지하면서 name, cniVersion, prevResult만 덧씌움
  orig, err = InjectConf(orig, inject)
  if err != nil {
    return nil, err
  }
  return injectRuntimeConfig(orig, rt)
}

// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/libcni/api.go#L191
func injectRuntimeConfig(orig *PluginConfig, rt *RuntimeConf) (*PluginConfig, error) {
  rc := make(map[string]interface{})
  for capability, supported := range orig.Network.Capabilities {
    if !supported {
      continue
    }
    if data, ok := rt.CapabilityArgs[capability]; ok {
      // ✅ 플러그인이 지원한다고 선언한 capability만 runtimeConfig에 포함
      rc[capability] = data
    }
  }

  if len(rc) > 0 {
    // ✅ runtimeConfig만 추가하고 ipam, mtu 같은 기존 필드는 그대로 둠
    orig, err = InjectConf(orig, map[string]interface{}{"runtimeConfig": rc})
  }
  return orig, nil
}
```

핵심은 `buildOneConfig()`가 원본 plugin 설정 JSON을 버리지 않는다는 점입니다. `InjectConf()`는 `orig`를 base로 `name`, `cniVersion`, `prevResult`만 얹고, `injectRuntimeConfig()`는 필요한 경우 `runtimeConfig`만 추가합니다. 따라서 `ipam`, `mtu`, `bridge` 같은 플러그인 고유 필드는 원래 값 그대로 stdin JSON에 남아 실제 바이너리로 전달됩니다.

여기서 들어가는 대표 값은 다음과 같습니다.

- `portMappings`: `config.GetPortMappings()`에서 변환된 hostPort 정보
- `dns`: `config.GetDnsConfig()`에서 변환된 DNS 설정
- `bandwidth`: 파드 어노테이션에서 추출한 대역폭 제한
- `cgroupPath`: `config.GetLinux().GetCgroupParent()`
- `io.kubernetes.cri.pod-annotations`: 플러그인이 이 capability를 선언한 경우 파드 어노테이션

중요한 점은 아무 값이나 자동으로 들어가지 않는다는 것입니다. 플러그인 설정 JSON의 `capabilities`에 선언된 키만 `runtimeConfig`에 주입됩니다.

## Result 타입

`addNetwork()`의 반환 타입이 `types.Result`인 이유도 이 흐름 안에 있습니다. CNI 바이너리는 stdout으로 결과 JSON을 돌려주고, `ExecPluginWithResult()`는 그 JSON의 `cniVersion`을 확인한 뒤 버전에 맞는 concrete result struct로 파싱해서 `types.Result` 인터페이스로 돌려줍니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/pkg/types/types.go#L128-L140
type Result interface {
  // ✅ 결과가 현재 지원하는 최고 CNI spec 버전
  Version() string
  // ✅ 필요한 버전으로 변환 가능
  GetAsVersion(version string) (Result, error)
  Print() error
  PrintTo(writer io.Writer) error
}

// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/pkg/invoke/exec.go#L111-L127
func ExecPluginWithResult(ctx context.Context, pluginPath string, netconf []byte, args CNIArgs, exec Exec) (types.Result, error) {
  stdoutBytes, err := exec.ExecPlugin(ctx, pluginPath, netconf, args.AsEnv())
  // ...
  // ✅ stdout JSON의 cniVersion 보정
  resultVersion, fixedBytes, err := fixupResultVersion(netconf, stdoutBytes)
  // ✅ 020, 040, 100 구현체 중 맞는 타입으로 생성
  return create.Create(resultVersion, fixedBytes)
}
```

그래서 `prevResult`는 단순한 `map[string]interface{}`가 아니라, 버전 정보를 유지한 `types.Result`로 체인 안을 이동합니다. `pkg/types/040`, `pkg/types/100` 같은 디렉터리에 버전별 `Result` 구현체가 있고, 필요하면 `GetAsVersion()`으로 다음 플러그인이 기대하는 버전으로 변환할 수 있습니다.

## 예시

아래에서는 `cilium`과 `kind`를 같은 입력 형식에 대입해 해석합니다.

- `cilium-cni`: `type`이 `cilium-cni`이므로 `/opt/cni/bin/cilium-cni`를 실행합니다. 단일 플러그인이면 첫 번째 호출이므로 `prevResult`는 없고, 아래 `ptp` 예시와 같은 규칙으로 원본 plugin JSON에 `name`, `cniVersion`만 맞춰져 stdin으로 들어갑니다.
- `ptp`: `type`이 `ptp`이므로 `/opt/cni/bin/ptp`를 실행합니다. 첫 번째 플러그인이므로 `prevResult`가 없고, `runtimeConfig`도 capability가 없으면 비어 있습니다. 즉 원본 plugin 섹션이 거의 그대로 stdin JSON이 됩니다.
- `portmap`: `type`이 `portmap`이므로 `/opt/cni/bin/portmap`를 실행합니다. 이 호출은 `ptp` 다음 단계이므로 stdin JSON 안에 `prevResult`가 들어가고, `capabilities.portMappings: true`가 선언되어 있으므로 `runtimeConfig.portMappings`도 함께 들어갑니다.

첫 번째 플러그인인 `ptp`는 실제로 이런 모양의 stdin JSON을 받습니다. 아래 예시는 containerd 테스트에서 concrete 값으로 생성한 ptp 설정을 기준으로, `buildOneConfig()`가 첫 번째 플러그인에 넘기는 입력을 그대로 풀어쓴 것입니다.

```jsonc
// https://github.com/containerd/containerd/blob/dea7da592f5d1/internal/cri/server/update_runtime_config_test.go#L31-L61
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/libcni/api.go#L155-L174
{
  "cniVersion": "1.0.0",
  "name": "test-pod-network",
  "type": "ptp",
  "mtu": 1460,
  "ipam": {
    "type": "host-local",
    "subnet": "10.0.0.0/24",
    "ranges": [
      [
        {
          "subnet": "10.0.0.0/24"
        }
      ],
      [
        {
          "subnet": "2001:4860:4860::/64"
        }
      ]
    ],
    "routes": [
      {
        "dst": "0.0.0.0/0"
      },
      {
        "dst": "::/0"
      }
    ]
  }
}
```

여기에는 `prevResult`가 없습니다. 첫 번째 플러그인이기 때문입니다. `runtimeConfig`도 없습니다. `ptp` 설정 자체가 별도 capability를 선언하지 않았기 때문입니다. 대신 `mtu`, `ipam`, `routes`처럼 conflist에 적혀 있던 필드가 그대로 남아 stdin으로 전달됩니다.

예를 들어 두 번째 플러그인인 `portmap` 호출 직전 stdin JSON은 대략 이렇게 됩니다.

```jsonc
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cluster/gce/cni.template#L1-L19
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containernetworking/cni/libcni/api.go#L155-L205
{
  "cniVersion": "1.0.0",
  "name": "k8s-pod-network",
  "type": "portmap",
  "capabilities": {
    "portMappings": true
  },
  "prevResult": {
    "...": "ptp 결과"
  },
  "runtimeConfig": {
    "portMappings": [
      {
        "hostPort": 80,
        "containerPort": 8080,
        "protocol": "tcp"
      }
    ]
  }
}
```

즉 `host-local`이나 `bridge` 같은 내부 동작을 알기 전에, containerd가 실제 바이너리에 넘기는 입력 형식은 이미 여기서 확정됩니다.

## 정리

이 글의 답은 세 줄로 정리할 수 있습니다.

- 설정 선택과 재로드: 서비스 시작 시 `Load()`로 한 번 읽고, 이후 `syncLoop()`가 변경 이벤트마다 다시 `Load()`를 호출합니다.
- 표준 CNI 환경 변수: `CNI_COMMAND`, `CNI_CONTAINERID`, `CNI_NETNS`, `CNI_ARGS`, `CNI_IFNAME`, `CNI_PATH`
- stdin JSON: 원래 플러그인 설정에 `name`, `cniVersion`을 맞추고, 필요할 때만 `prevResult`와 `runtimeConfig`를 주입한 값

그래서 `type`은 바이너리 이름을 고르는 데 쓰이는 값이지, 그 자체가 실행 인자가 아닙니다. containerd는 netns 경로와 CRI 런타임 정보를 CNI 표준 형식으로 포장해 넘기고, 실제 네트워크 장치 조작은 그다음부터 각 CNI 바이너리가 수행합니다.

