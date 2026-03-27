# 추가 분석 목차

## shim 내부 동작

- shim 프로세스 기동 흐름: `container.NewTask()` → shim 바이너리 실행과 소켓 핸드셰이크
- containerd ↔ shim 통신: ttrpc 프로토콜과 `TaskService` API
- shim → runc 호출: OCI 번들 생성(`config.json`, rootfs 마운트), `runc create`, `runc start`
- shim 재사용: 파드 내 컨테이너가 동일 shim을 공유하는 `Endpoint` 메커니즘

## 이미지 관리

- `ensureImageExists` 흐름: 로컬 존재 여부 확인과 `Pull` 트리거 조건
- content store와 레이어 다운로드: digest 기반 중복 제거와 청크 저장
- 이미지 언팩과 스냅샷 생성: overlay 레이어 스택 구성과 `Snapshotter.Prepare()`
- `CreateContainer`의 `WithNewSnapshot`: 쓰기 가능 레이어(active snapshot) 생성과 마운트 정보 확보

## bolt DB 상태 관리

- bolt DB 버킷 구조: `containers`, `images`, `snapshots`, `leases`, `content` 버킷 배치
- 컨테이너 메타데이터 스키마: spec proto 직렬화 저장 방식과 `NewContainer` 트랜잭션
- 이미지·스냅샷 메타데이터: 레이어 체인 레퍼런스 저장과 GC lease 연동
- containerd 재시작 복구: 인메모리 store 재구성 흐름 (`loadContainers`, `loadSandboxes`)

## GC와 lease

- lease의 역할: `RunPodSandbox`에서 lease를 먼저 생성하는 이유 — 중간 실패 시 고아 리소스 방지
- GC 스케줄러 동작: `GCPlugin`이 트리거하는 mark-and-sweep와 버킷 순회
- lease → snapshot·content 참조 체인: 어떤 리소스가 보호되고 어떤 리소스가 수거 대상이 되는지
- 컨테이너 삭제 시 lease 해제와 스냅샷 정리 순서

## 컨테이너·샌드박스 종료 흐름

- `StopContainer`: SIGTERM 전송 → 타임아웃 후 SIGKILL, task stop 이후 상태 전환
- `exitMonitor` 고루틴: `task.Wait()` 채널에서 종료 이벤트를 수신하고 컨테이너 상태를 `EXITED`로 업데이트하는 흐름
- `StopPodSandbox`: 샌드박스 내 컨테이너 일괄 정지 → pause 컨테이너 종료 → CNI Del 호출로 네트워크 해제
- `RemovePodSandbox`: task 삭제 → 스냅샷 제거 → netns 마운트 해제 → store·DB에서 레코드 삭제

## 이벤트 시스템

- containerd 이벤트 버스: exchange 패키지와 `publisher`/`subscriber` 인터페이스
- `generateAndSendContainerEvent`의 실제 경로: 이벤트 객체 직렬화 → exchange publish → 구독자 전달
- kubelet의 이벤트 소비: `GetContainerEvents` gRPC 스트림으로 containerd 이벤트를 수신하는 흐름
- EventMonitor: shim에서 발생하는 task 이벤트(OOM, exit)를 containerd가 수신·처리하는 방식
