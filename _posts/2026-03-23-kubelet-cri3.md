---
title: "kubernetes data plane: containerd 플러그인 시스템과 gRPC 서버 초기화"
date: 2026-03-23 00:00:00 +0900
categories:
  - containerd
tags:
  - containerd
  - kubernetes
  - plugin
  - gRPC
excerpt: "containerd의 플러그인 등록 메커니즘과 gRPC 서버 초기화 과정을 init()부터 소켓 리스너 실행까지 코드 수준으로 분석합니다."
toc: true
toc_sticky: true
author_profile: false
header:
  teaser: /assets/images/posts/kubernetes.png
---

지금까지 scheduler, kubelet의 동작을 코드로 살펴봤고 kubelet에서 CRI의 호출 지점과 쉘에서 containerd, shim 프로세스를 살펴봤습니다. shim은 kubelet과 containerd 사이에서 파드의 라이프사이클을 관리하는 역할을 수행함을 알 수 있었습니다. 이번에는 쉘에서 확인한 containerd의 내부 동작을 살펴보도록 하겠습니다.

---

kubelet은 containerd의 gRPC API를 통해 컨테이너 런타임과 상호작용합니다. 이전 아티클에서 kubelet이 CRI를 통해 `RunPodSandbox`, `CreateContainer`, `StartContainer` 등의 메서드를 호출하는 것을 확인했습니다. 이제 containerd가 이러한 요청을 처리하는 과정을 살펴보겠습니다.

containerd는 gRPC 서버로 동작하며, kubelet이 보낸 요청을 처리하기 위해 다양한 메서드를 구현하고 있습니다. 예를 들어, `RunPodSandbox` 요청이 들어오면 containerd는 해당 요청을 처리하기 위해 내부적으로 여러 단계를 거칩니다.

containerd는 기능별 컴포넌트를 플러그인으로 분리하고, 플러그인이 `grpcService` 인터페이스를 구현하면 자동으로 gRPC 서버에 등록되는 구조를 가집니다. 이 흐름을 `main()`부터 이미지 RPC 호출까지 단계별로 추적해 보겠습니다.

# 플러그인 사전 등록

[cmd/containerd/main.go](https://github.com/containerd/containerd/blob/v2.2.1/cmd/containerd/main.go)의 `main()`은 단순합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/main.go#L24
import (
    _ "github.com/containerd/containerd/v2/cmd/containerd/builtins"
)

func main() {
    app := command.App()
    if err := app.Run(os.Args); err != nil { ... }
}
```

핵심은 blank import `_`입니다. Go 런타임은 `main()`이 실행되기 전에 import된 패키지의 `init()` 함수를 모두 실행합니다. [cmd/containerd/builtins/builtins.go](https://github.com/containerd/containerd/blob/v2.2.1/cmd/containerd/builtins/builtins.go)는 containerd가 제공하는 모든 빌트인 플러그인 패키지를 blank import하고 있습니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/builtins/builtins.go#L20
import (
    _ "github.com/containerd/containerd/v2/plugins/services/images"
    _ "github.com/containerd/containerd/v2/plugins/services/containers"
    _ "github.com/containerd/containerd/v2/plugins/services/tasks"
    // ... 기타 서비스 플러그인들
)
```

각 플러그인 패키지의 `init()` 함수가 import 될 때 실행됩니다. 이때 `registry.Register()`를 호출하여 플러그인의 타입, ID, 의존성, 초기화 함수(`InitFn`)를 전역 레지스트리에 등록합니다. 예를 들어 `GRPCPlugin`("images")은 gRPC 게이트웨이 역할을 하며 `ServicePlugin` 의존성을 선언합니다 ([plugins/services/images/service.go#L31](https://github.com/containerd/containerd/blob/v2.2.1/plugins/services/images/service.go#L31)).

여기서 중요한 점은 builtins 패키지가 플러그인 인스턴스를 만드는 곳이 아니라, "어떤 플러그인이 존재하는지"를 미리 등록하는 곳이라는 점입니다. 이미지 경로만 놓고 보면 바깥쪽 `GRPCPlugin("images")`가 gRPC 핸들러를 노출하고, 안쪽 `ServicePlugin("images")`가 실제 이미지 store와 GC 의존성을 조립하는 두 겹 구조입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/plugins/services/images/service.go#L31
func init() {
    registry.Register(&plugin.Registration{
        Type: plugins.GRPCPlugin,
        ID:   "images",
        Requires: []plugin.Type{
            plugins.ServicePlugin,
        },
        InitFn: func(ic *plugin.InitContext) (interface{}, error) {
            i, err := ic.GetByID(plugins.ServicePlugin, services.ImagesService)
            // ...
            return &service{local: i.(imagesapi.ImagesClient)}, nil
        },
    })
}
```

`ServicePlugin`("images")은 실제 비즈니스 로직을 담당하며 `MetadataPlugin`, `GCPlugin` 등을 의존성으로 선언합니다 ([plugins/services/images/local.go#L45](https://github.com/containerd/containerd/blob/v2.2.1/plugins/services/images/local.go#L45)).

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/plugins/services/images/local.go#L45
func init() {
    registry.Register(&plugin.Registration{
        Type: plugins.ServicePlugin,
        ID:   services.ImagesService,
        Requires: []plugin.Type{
            plugins.MetadataPlugin,
            plugins.GCPlugin,
            plugins.WarningPlugin,
        },
        InitFn: func(ic *plugin.InitContext) (interface{}, error) {
            m, _ := ic.GetSingle(plugins.MetadataPlugin)  // bolt DB
            g, _ := ic.GetSingle(plugins.GCPlugin)
            // ...
            return &local{
                store: metadata.NewImageStore(m.(*metadata.DB)),
                gc:    g.(gcScheduler),
            }, nil
        },
        // ...
    })
}
```

이 시점에서는 인스턴스를 생성하지 않고 `Registration` 구조체만 전역 레지스트리에 저장합니다. 실제 인스턴스 생성(`InitFn` 실행)은 이후 `server.New()` 단계에서 이루어집니다.


# 플러그인 로드 및 gRPC 서버 실행

이번에는 blank import로 쌓인 등록 정보가 실제 초기화 순서로 바뀌는 지점을 보겠습니다. 이 흐름은 `main()`에서 출발하지만, 핵심 helper는 `LoadPlugins()`와 `registry.Graph()`입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/main.go#L28
func main() {
    app := command.App() // ✅ cli.App 인스턴스 생성 (app.Action 포함)
    if err := app.Run(os.Args); err != nil { // ✅ urfave/cli가 인수 파싱 후 app.Action 호출
        // ...
    }
}
```

`command.App()` 내부에서 데몬 실행 로직을 등록합니다. 이때 서브커맨드가 주어지지 않으면 urfave/cli는 기본 동작으로 등록된 `app.Action` 클로저를 실행합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/command/main.go#L73
func App() *cli.App {
    app := cli.NewApp()
    app.Commands = []*cli.Command{
        configCommand,
        publishCommand,
        ociHook,
    }
    app.Action = func(cliContext *cli.Context) error { // ✅ 서브커맨드 없을 때 실행되는 기본 동작
        // ...
    }
    return app
}
```

`app.Action` 클로저 본문에서는 설정 로드 → `server.New()` 호출 → 소켓 리스너 생성 → `serve()` 순으로 진행됩니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/command/main.go#L121
func App() *cli.App {
    // ...
    app.Action = func(cliContext *cli.Context) error {
        // ...
        go func() { // ✅ 고루틴에서 서버 초기화 (bolt DB 잠금 등 장시간 블로킹 방지)
            server, err := server.New(ctx, config) // ✅ 플러그인 로드 + gRPC 서버 생성
            // ...
        }()
        // ...
        l, err := sys.GetLocalListener(config.GRPC.Address, config.GRPC.UID, config.GRPC.GID)
        // ...
        serve(ctx, l, server.ServeGRPC) // ✅ 별도 고루틴에서 grpcServer.Serve(l) 실행
    }
}
```

`server.New()`는 바로 인스턴스를 만드는 대신, 먼저 어떤 순서로 `InitFn`을 실행해야 하는지부터 확정합니다. 이를 담당하는 첫 단계가 `LoadPlugins()`입니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/server/server.go#L132
func New(ctx context.Context, config *srvconfig.Config) (*Server, error) {
    // ...
    loaded, err := LoadPlugins(ctx, config) // ✅ 위상 정렬된 []plugin.Registration 반환
    // ...
}
```

`LoadPlugins`는 proxy 플러그인을 추가로 등록한 뒤 `registry.Graph()`를 호출합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/server/server.go#L494
func LoadPlugins(ctx context.Context, config *srvconfig.Config) ([]plugin.Registration, error) {
    // ... proxy plugin 등록 ...
    return registry.Graph(filter(config.DisabledPlugins)), nil // ✅ 비활성화 필터 적용 후 위상 정렬
}
```

`registry.Graph()`는 DFS 방식으로 각 플러그인의 `Requires` 의존성을 재귀적으로 먼저 삽입하여, 피의존 플러그인이 항상 의존 플러그인보다 앞에 오도록 정렬합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/vendor/github.com/containerd/plugin/plugin.go#L112
func (registry Registry) Graph(filter DisableFilter) []Registration {
    // ...
    for _, r := range registry {
        if disabled[r] {
            continue
        }
        children(r, registry, added, disabled, &ordered) // ✅ DFS로 Requires 먼저 삽입
        if !added[r] {
            ordered = append(ordered, *r)
            added[r] = true
        }
    }
    return ordered
}
```

## 플러그인 초기화와 의존성 주입

다시 돌아와서 `server.New()`는 위상 정렬된 `loaded`를 순회하며 각 플러그인을 순차적으로 초기화합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/server/server.go#L246
func New(ctx context.Context, config *srvconfig.Config) (*Server, error) {
    // ...
    var (
        grpcServer  = grpc.NewServer(serverOpts...)  // ✅ gRPC 서버 인스턴스 생성
        // ...
        initialized = plugin.NewPluginSet()          // ✅ 초기화 완료 플러그인 집합
    )
    for _, p := range loaded { // ✅ 위상 정렬 순서로 순차 초기화
        // ...
        initContext := plugin.NewContext(
            ctx,
            initialized, // ✅ 이미 초기화된 플러그인만 담긴 집합 전달
            map[string]string{
                plugins.PropertyRootDir:      filepath.Join(config.Root, id),
                plugins.PropertyGRPCAddress:  config.GRPC.Address,
                plugins.PropertyTTRPCAddress: config.TTRPC.Address,
                // ...
            },
        )
        result := p.Init(initContext)    // ✅ InitFn 실행, instance 또는 err 저장
        initialized.Add(result)          // ✅ 완료 집합에 추가 (이후 플러그인이 참조 가능)

        instance, err := result.Instance()
        // ...
        if src, ok := instance.(grpcService); ok { // ✅ grpcService 구현 여부 확인
            grpcServices = append(grpcServices, src)
        }
    }
}
```

모든 플러그인 초기화가 완료된 후 `grpcServices`에 수집된 서비스들을 gRPC 서버에 등록합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/server/server.go#L359
func New(ctx context.Context, config *srvconfig.Config) (*Server, error) {
    // ...
    for _, service := range grpcServices {
        if err := service.Register(grpcServer); err != nil { // ✅ gRPC 서버에 RPC 메서드 등록
            return nil, err
        }
    }
    return s, nil
}
```

`service.Register()`는 예를 들어 이미지 서비스의 경우 내부적으로 `imagesapi.RegisterImagesServer(s, &service{...})`를 호출하여 protobuf로부터 자동 생성된 핸들러를 gRPC 서버에 연결합니다.

이후 `command/main.go`에서 Unix 소켓 리스너를 생성하고 `serve()`를 통해 `grpcServer.Serve(l)`를 고루틴으로 실행합니다.

```go
// https://github.com/containerd/containerd/blob/dea7da592f5d1/cmd/containerd/command/main.go#L284
func App() *cli.App {
    // ...
    app.Action = func(cliContext *cli.Context) error {
        // ...
        l, err := sys.GetLocalListener(config.GRPC.Address, config.GRPC.UID, config.GRPC.GID)
        // ...
        serve(ctx, l, server.ServeGRPC) // ✅ 고루틴에서 grpcServer.Serve(l) 실행
        // ...
    }
}
```

이로써 containerd는 소켓 파일(`/run/containerd/containerd.sock`)에서 gRPC 요청을 수신할 준비가 완료됩니다. kubelet이 CRI 요청을 보내면 해당 소켓을 통해 등록된 핸들러로 라우팅됩니다.

지금까지의 흐름을 정리하면 다음과 같습니다.

1. blank import → 각 플러그인 패키지의 `init()` 실행 → `registry.Register()`로 타입·ID·`InitFn`을 전역 레지스트리에 등록합니다.
2. `server.New()` → `LoadPlugins()` → `registry.Graph()`로 의존 관계를 DFS 위상 정렬하여 `[]Registration` 슬라이스를 얻습니다.
3. 정렬된 순서로 `p.Init(initContext)`를 실행하고 결과를 `initialized` 집합에 누적합니다. `grpcService`를 구현한 인스턴스는 `grpcServices`에 수집합니다.
4. 수집된 서비스마다 `service.Register(grpcServer)`를 호출하여 protobuf 핸들러를 gRPC 서버에 연결합니다.
5. Unix 소켓에서 `grpcServer.Serve(l)`를 실행하여 kubelet 요청을 수신합니다.

앞서 이미지 서비스(`GRPCPlugin "images"`)를 예시로 플러그인 등록 메커니즘을 살펴봤습니다. kubelet의 파드 생성 요청인 `RunPodSandbox`, `CreateContainer`, `StartContainer`도 마찬가지로 플러그인으로 등록된 핸들러가 처리하며, 이를 담당하는 핵심 플러그인이 `GRPCPlugin "cri"`입니다.

다음 편에서는 kubelet의 CRI 요청이 이 gRPC 서버에 도달했을 때 내부에서 어떤 일이 일어나는지, `GRPCPlugin "cri"` 플러그인의 등록 구조부터 `RunPodSandbox` 처리 과정까지 살펴봅니다.
