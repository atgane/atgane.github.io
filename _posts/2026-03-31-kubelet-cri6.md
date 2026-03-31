---
title: "kubernetes data plane: containerd는 언제 결정하는가"
date: 2026-03-31 00:00:00 +0900
categories:
  - containerd
tags:
  - containerd
  - kubernetes
  - CRI
  - 설계
  - plugin
  - netns
  - shim
excerpt: "containerd 소스코드에서 등장하는 설계 선택의 이유를 추적합니다."
toc: true
toc_sticky: true
author_profile: false
header:
  teaser: /assets/images/posts/kubernetes.png
---

앞선 시리즈에서 containerd의 내부 동작을 코드 수준으로 추적했습니다. blank import로 플러그인을 등록하고, netns를 생성한 뒤 CNI를 실행하고, 스냅샷 디렉터리를 준비한 다음 shim에게 실제 마운트를 위임하는 과정을 따라갔습니다. 이번 아티클은 이전 코드 분석 시리즈와 다르게 containerd의 설계 결정에 집중합니다.설계 결정 하나하나를 제약 조건부터 출발해서 선택의 이유까지 풀어보되, 각각이 어떻게 연결되는지 하나의 흐름으로 엮어보겠습니다.

---

# 왜 netns를 먼저 만들고 CNI를 나중에 실행하는가

플러그인 초기화와 서비스 간 호출 이야기에서 조금 더 구체적인 영역으로 내려오면, `RunPodSandbox`의 처리 순서가 눈에 띕니다. netns를 생성하고, 그 다음에 CNI를 실행합니다. 이 순서는 뒤집을 수 없습니다.

CNI 플러그인이 수행하는 핵심 작업은 veth pair를 만들어 한쪽 끝을 파드의 네트워크 네임스페이스 안으로 이동시키는 것입니다. `ip link set eth0 netns <ns>` 와 같은 조작인데, 이것이 가능하려면 대상이 되는 네임스페이스가 먼저 존재해야 합니다. CNI 플러그인은 `CNI_NETNS` 환경 변수로 netns 경로(`/var/run/netns/cni-<uuid>`)를 전달받습니다. 이 경로가 없으면 플러그인은 실행할 수 없습니다.

반대로 생각하면 더 명확합니다. CNI가 먼저 실행된다면, 인터페이스를 어느 네임스페이스에 넣어야 하는지 알 수가 없습니다. netns는 CNI의 전제 조건입니다.

이 관계는 사실 네임스페이스의 작동 방식 자체에서 비롯됩니다. 네트워크 네임스페이스는 인터페이스를 담는 그릇과 같습니다. 그릇이 없으면 담을 수 없습니다.

---

# 왜 네트워크 파일 단위로는 병렬이지만 플러그인 체인 내부는 직렬인가

CNI 실행 방식에서 흥미로운 비대칭이 있습니다. `attachNetworks()`는 `/etc/cni/net.d/` 의 설정 파일마다 goroutine을 만들어 병렬로 실행합니다. 그런데 `AddNetworkList()` 안에서는 플러그인들을 순서대로 하나씩 직렬로 실행합니다.

이 차이는 의존성 구조에서 비롯됩니다.

서로 다른 설정 파일은 서로 다른 네트워크를 담당합니다. 예를 들어 `10-bridge.conf`가 메인 CNI 체인을 처리하고 `99-loopback.conf`가 loopback 인터페이스를 처리한다면, 이 둘은 독립적입니다. 10번 파일의 결과가 99번 파일의 입력이 되지 않습니다. 따라서 병렬 실행이 안전합니다.

반면 하나의 설정 파일 안에 나열된 플러그인들(`bridge` → `host-local` → `portmap` 등)은 파이프라인을 구성합니다. CNI 스펙은 앞 플러그인의 출력 결과(`Result`)를 다음 플러그인의 `prevResult` 입력으로 전달하도록 정의합니다. `bridge` 플러그인이 veth pair를 만들고 반환한 인터페이스 정보가, `host-local`이 어느 인터페이스에 IP를 할당할지 알기 위해 필요합니다. `portmap`은 이미 IP가 할당된 인터페이스를 알아야 포트 포워딩 규칙을 만들 수 있습니다. 순서가 곧 의미입니다.

병렬성의 단위는 독립성의 단위와 같습니다. 독립적인 것은 병렬로, 의존적인 것은 직렬로. 이 원칙이 go-cni 구현에 그대로 반영되어 있습니다.

---

# 왜 CreateSandbox와 StartSandbox를 두 단계로 나누었는가

네트워크 설정이 완료되면 `RunPodSandbox`는 `sandboxService.CreateSandbox()`와 `StartSandbox()`를 순서대로 호출합니다. 코드를 읽다 보면 `CreateSandbox`는 메타데이터를 인메모리 store에 등록하는 것이 전부라는 걸 알 수 있습니다. 실행 로직은 전혀 없습니다. 왜 CreateSandbox와 StartSandbox를 분리했을까요.

이유는 취소 가능성과 관찰 가능성입니다.

`CreateSandbox` 단계는 의도만 기록합니다. 어떤 샌드박스를 만들겠다는 메타데이터를 저장하고, 이름을 예약하고, 상태를 `StateUnknown`으로 초기화합니다. 이 단계는 부작용이 없습니다. 실패하면 메타데이터만 지우면 됩니다.

`StartSandbox` 단계는 실제로 프로세스를 만들고 파일시스템을 구성하고 네트워크 네임스페이스에 진입시킵니다. 실패했을 때 되돌리기 어려운 작업들이 여기에 있습니다. 이 단계를 분리해두면, 외부에서 샌드박스가 "생성 요청됨"과 "실제로 실행 중"을 구분하는 것이 가능합니다. `criService.RunPodSandbox`는 두 단계 사이에서 추가적인 검증을 할 수도 있고, 필요한 경우 Start를 다시 시도하거나 다른 Controller 구현체로 위임할 수도 있습니다.

같은 원칙이 `Controller` 인터페이스 전체에 적용됩니다. `CreateSandbox`, `StartSandbox`, `StopSandbox`, `ShutdownSandbox`는 각각 명확하게 다른 의미를 가집니다. 상태 전이를 명시적으로 표현하면 각 단계에서 어떤 보장이 필요한지가 코드에 드러나고, 재시도나 롤백 로직을 각 경계에서 독립적으로 다룰 수 있습니다.

---

# 왜 스냅샷 디렉터리는 CreateContainer에서 만들고 마운트는 shim까지 미루는가

`CreateContainer`에서 overlayfs 스냅샷을 준비할 때, `createSnapshot()`은 `lowerdir`, `upperdir`, `workdir` 디렉터리를 생성하고 `[]mount.Mount` 구조체를 반환합니다. 그런데 `withNewSnapshot`은 이 반환값을 명시적으로 무시합니다. 실제 `mount(2)` 시스템 콜은 이 시점에 발생하지 않습니다.

왜 마운트를 미루는가에는 두 가지 이유가 있습니다.

첫째, overlayfs 마운트는 컨테이너의 마운트 네임스페이스 안에서 수행되어야 합니다. containerd가 호스트 마운트 네임스페이스에서 overlayfs를 미리 마운트하면, 컨테이너가 시작될 때 그 마운트를 컨테이너의 마운트 네임스페이스로 옮기는 복잡한 과정이 필요합니다. shim이 runc를 실행하면, runc는 컨테이너의 마운트 네임스페이스를 설정하는 과정에서 overlayfs를 구성합니다. 이것이 훨씬 자연스럽습니다.

둘째, 정리(cleanup) 책임이 명확해집니다. `CreateContainer`는 디렉터리와 메타데이터를 만들었습니다. `StartContainer`가 호출되지 않은 채 컨테이너가 삭제된다면, 정리해야 할 것은 디렉터리와 메타데이터뿐입니다. 마운트가 이미 걸려있었다면, 마운트를 해제하고 나서 디렉터리를 지워야 하는 두 단계가 됩니다. 마운트 해제 실패가 디렉터리 정리를 막는 상황도 생길 수 있습니다. 마운트 시점을 shim으로 미루면, 마운트 수명이 shim 수명과 일치하게 됩니다. shim이 종료되면 마운트도 해제됩니다.

---

# 왜 이미지 Unpack이 pull 시점이 아닌 CreateContainer에서 처음 발생할 수 있는가

containerd에서 `image pull`은 이미지 레이어를 content store에 압축된 tar 형태로 내려받는 것입니다. 각 레이어는 SHA256 다이제스트로 식별되며, `/var/lib/containerd/io.containerd.content.v1.content/blobs/` 아래에 저장됩니다. 이 시점에는 아직 스냅샷터가 관여하지 않습니다.

Unpack은 이 압축 tar를 풀어 스냅샷터가 이해하는 형태로 변환하는 과정입니다. overlay 스냅샷터라면 `snapshots/<N>/fs/`에 레이어 내용을 기록하고, bolt DB에 Committed 상태로 등록합니다. pull 시점에 미리 하면 안 되는 이유가 있습니다.

어느 스냅샷터를 쓸지를 pull 시점에는 모를 수 있습니다. 같은 이미지가 나중에 어떤 런타임 클래스와 함께 사용될지 알 수 없으며, 클러스터에는 overlay, nydus, zfs 등 여러 스냅샷터가 공존할 수 있습니다. `CreateContainer`가 호출되어야 비로소 런타임 클래스가 결정되고, 그에 따라 어떤 스냅샷터로 Unpack할지도 결정됩니다.

게다가 pull 후 바로 Unpack하면 "이미지를 캐시해두기 위해 pull했으나 실제로 컨테이너는 만들지 않는" 시나리오에서 디스크를 낭비합니다. content store는 레이어를 압축 형태로 효율적으로 저장합니다. Unpack은 압축을 풀어 더 많은 공간을 사용하는 작업입니다. 실제로 컨테이너를 만들 때까지 이 비용을 지불하지 않아도 됩니다.

`WithNewSnapshot`이 `s.Prepare`를 먼저 시도하고, `errdefs.IsNotFound`일 때만 `i.Unpack`을 호출하는 구조가 이 지연 평가를 구현합니다. 이미 Unpack된 적이 있다면(다른 컨테이너가 같은 이미지를 먼저 사용했다면) 스냅샷이 존재하므로 Unpack을 건너뜁니다. Unpack은 필요할 때, 필요한 대상을 위해 한 번만 수행됩니다.

---

# 왜 CreateContainer와 StartContainer를 분리했는가

---

# 요약: containerd가 반복하는 원칙

지금까지 여덟 가지 설계 결정을 살펴봤습니다. 개별 이유들을 모아보면 공통된 패턴이 있습니다.

첫째, 부작용을 가능한 한 늦게 발생시킵니다. 스냅샷 마운트는 shim까지 미루고, Unpack은 컨테이너 생성 시점까지 미루고, Create 단계에는 실행 로직을 두지 않습니다. 취소하기 어려운 작업일수록, 반드시 필요한 시점까지 뒤로 밉니다.

둘째, 결정을 가장 많은 정보를 아는 지점에서 내립니다. 어느 스냅샷터를 쓸지는 런타임 클래스를 알 때까지 결정하지 않습니다. 마운트는 컨테이너의 마운트 네임스페이스가 만들어지는 시점, 즉 shim이 처리하는 시점에 수행합니다. 네트워크 플러그인 체인의 순서는 플러그인 작성자가 `Requires`로 선언하고, 시스템이 이를 위상 정렬로 해석합니다.

셋째, 동등한 수준의 것만 같은 수준에서 호출합니다. 같은 프로세스 내부의 서비스는 인메모리로, 프로세스 경계를 넘는 호출은 gRPC로, shim과의 통신은 ttrpc로 다룹니다. 성능과 격리의 필요가 실제로 있는 경계에서만 IPC 레이어를 씁니다.

넷째, 독립적인 것은 병렬로, 의존적인 것은 직렬로. CNI 설정 파일 단위는 병렬, 플러그인 체인 내부는 직렬. 플러그인 초기화는 `Requires`로 표현된 의존성 순서대로.

```mermaid
flowchart TD
    subgraph "컴파일 타임"
        A["blank import plug-in 등록"]
    end

    subgraph "프로세스 시작"
        B["registry.Graph() DFS 위상 정렬 초기화"]
        C["WithInMemoryServices 소켓 없이 직접 호출"]
    end

    subgraph "RunPodSandbox"
        D["unshare(CLONE_NEWNET) + bind mount netns 생성"]
        E["CNI 실행 netns 경로 전달"]
        F["파일별 병렬 체인 내부 직렬"]
        D --> E --> F
    end

    subgraph "CreateContainer"
        G["Controller.Create 메타데이터만"]
        H["스냅샷 디렉터리 준비 mount(2) 없음"]
        I["Unpack 지연 필요할 때만"]
        G --> H --> I
    end

    subgraph "StartContainer → shim"
        J["Controller.Start 실제 실행"]
        K["mount(2) 수행 shim이 담당"]
        J --> K
    end

    A --> B --> C
    C --> D
    F --> G
    I --> J
```

각 설계 결정을 한 줄로 정리하면 다음과 같습니다.

- blank import: 플러그인 조합을 컴파일 타임에 확정하여 런타임 로딩 실패를 제거합니다.
- WithInMemoryServices: 같은 프로세스 안에서 불필요한 직렬화 비용을 제거합니다.
- netns 선행: CNI는 대상 네임스페이스가 존재해야만 동작할 수 있습니다.
- unshare + bind mount: 프로세스를 살려두지 않고 netns 참조를 파일시스템 경로로 유지합니다.
- 병렬/직렬 비대칭: 독립적인 단위는 병렬로, 의존 관계가 있는 파이프라인은 직렬로 처리합니다.
- Create/Start 분리: 의도 기록과 실행을 분리하여 부작용 범위를 명확히 합니다.
- mount 지연: 마운트 수명을 shim 수명과 일치시켜 정리 책임을 단순화합니다.
- Unpack 지연: 어느 스냅샷터를 쓸지 알 때까지 비가역적 작업을 미룹니다.

이 결정들 사이의 공통된 철학은 하나입니다. 무언가를 결정하는 시점은 그것을 결정할 수 있는 최소한의 정보가 갖춰진 가장 늦은 순간이어야 하며, 그 결정이 만드는 부작용은 가능한 한 좁은 범위에 머물러야 한다는 것입니다. containerd는 이것을 시스템 소프트웨어 수준에서 일관되게 실천하고 있습니다.
