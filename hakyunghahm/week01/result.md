# Week 01 - Execution Model (Serverless vs Container)

## 📊 Result

### 1. 실행 구조 차이

- Serverless: 이벤트 기반으로 함수 실행 후 종료 (on-demand)
- Container: 항상 실행되는 프로세스 기반 (always-on)

→ Serverless는 요청이 있을 때만 실행되며, Container는 지속적으로 리소스를 점유

---

### 2. Cold Start 특성

- 초기 요청 시 실행 환경 생성 → 지연 발생
- 주요 단계:
  1. VM 할당
  2. 코드 다운로드
  3. 런타임 초기화
  4. 함수 실행

- 영향 요인:
  - VPC 내부 배치 시 지연 증가
  - 라이브러리 무거울수록 지연 증가

---

### 3. CPU 할당 방식 비교

#### Serverless (Lambda)
- 메모리 설정에 따라 CPU 자동 할당
- 저메모리 → 저CPU → 성능 저하
- 멀티코어 사용 제한적

#### Kubernetes
- CPU / Memory 독립적으로 설정 가능
- request / limit 기반 자원 관리
- limit 초과 시 throttling 발생

---

### 4. 자원 및 성능 특성 비교

| 항목 | Serverless | Kubernetes |
|------|-----------|------------|
| 실행 방식 | 요청 기반 | 상시 실행 |
| CPU 제어 | 간접 (메모리 기반) | 직접 (core 단위) |
| 성능 안정성 | 요청마다 변동 | 안정적 |
| 확장 방식 | 자동 | 설정 기반 |
| 자원 구조 | 완전 격리 | 노드 내 공유 |

---

## 💡 Insight

### 1. Serverless는 “비용 최적화”, Kubernetes는 “성능 안정성”에 강점

- Serverless는 idle 상태 비용 없음 → 저트래픽에 유리
- Kubernetes는 항상 실행 → 고정 비용 있지만 성능 일정

→ **트래픽 패턴이 아키텍처 선택의 핵심 기준**

---

### 2. Cold Start는 단순 지연이 아니라 “UX 문제”

- 평균 latency보다 초기 응답 지연이 더 체감됨
- 특히 사용자 인터랙션 기반 서비스에서 영향 큼

→ **P99 latency 기준으로 설계 필요**

---

### 3. Serverless의 “추상화”는 편하지만 제어권이 제한됨

- CPU를 직접 제어할 수 없음
- 성능 튜닝이 메모리 설정에 의존

→ **정밀한 성능 제어가 필요한 경우 Kubernetes가 적합**

---

### 4. Kubernetes는 “유연성” 대신 “운영 복잡도” 증가

- 리소스 설정, scaling, 배포 전략 직접 관리 필요
- 잘못 설정 시 throttling 등 성능 문제 발생

→ **운영 역량이 아키텍처 선택에 직접적인 영향을 미침**

---

### 5. 단순 기술 비교가 아니라 “상황 기반 선택”이 중요

- Low traffic + 이벤트 기반 → Serverless
- 지속 처리 + 안정성 요구 → Kubernetes

→ **아키텍처는 기술이 아니라 “문제에 대한 선택”**