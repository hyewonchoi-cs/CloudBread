## 1. 요구사항 분석

### 명시적 요구사항

| 항목 | 내용 |
| --- | --- |
| 평소 트래픽 | 거의 0 (오픈 전까지 대기 상태) |
| 티켓 오픈 시 | 수천~수만 req/s 순간 폭발 |
| 좌석 수 | 공연장별 500~5,000석 한정 |
| 정합성 요구 | 중복 예매 절대 불가 |
| 배포 요구 | 오픈 직후 버그 발견 시 서비스 중단 없이 수정 배포 가능 |
| 장애 내성 | Pod 일부가 죽어도 예매 서비스가 계속 동작 |

### 암묵적 요구사항

- 오픈 시각이 **사전에 공지된다** → HPA 반응 속도에 의존하지 않아도 됨
- 예매 실패 사유를 "매진"과 "오류"로 구분해야 한다 → 에러 처리를 세분화해야 함
- 오픈 전에는 비용을 최소화해야 한다 → 평시 Pod 수를 최소로 유지

### 이 문제의 본질

: 오픈 시각이 정해진 순간, 수만 명이 동시에 접속해 한정된 좌석을 선착순으로 예매한다.
 이 과정에서 중복 예매는 절대 안 되고, 배포 중에도 예매가 유실되면 안 된다.
 Pod가 언제든 죽을 수 있는 환경에서 이걸 어떻게 보장할 것인가?

---

## 2. 핵심 Trade-off

### 2-1. 스케일링: HPA 단독 vs Scheduled Scaling + HPA 조합

HPA는 **반응형**이다. 트래픽이 올라오고 CPU가 임계치를 넘고 Metrics Server가 감지하고 새 Pod가 Running이 될 때까지 **최소 1~3분**이 걸린다.

```
트래픽 급증 (T+0초)
  → Metrics Server 감지 (T+15~30초)
  → HPA 스케일아웃 결정 (T+30~45초)
  → 새 Pod Running (T+90~180초)
  → 실제 트래픽 분담 시작 (T+2~3분)
```

티켓 오픈은 "지금 이 순간" 수만 건이 동시에 들어온다. HPA가 스케일아웃을 완료하는 동안 기존 Pod들이 모든 부하를 혼자 감당하면서 SLA가 무너진다.

오픈 시각이 공지된 서비스에서는 **Scheduled Scaling + HPA 조합**이 답이다.

```
오픈 30분 전 → CronJob으로 replicas를 피크 대응 수로 올림 (Scheduled)
오픈 후     → HPA가 실제 트래픽 기반으로 fine-tuning (Reactive)
이벤트 종료 → HPA가 천천히 스케일다운 (stabilizationWindowSeconds)
```

### 2-2. 중복 예매 방지: 어느 레이어에서 막을 것인가

```
레이어별 방어 전략 비교

DB 레벨 (WHERE remaining > 0 + CHECK 제약):
  장점: 구현 단순, 원자적 보장, 방어선 확실
  단점: 동시 요청이 많으면 DB가 병목. 수만 req/s가 전부 DB UPDATE를 때림

Redis 레벨 (DECR 원자적 연산):
  장점: 초당 수십만 건 처리 가능. DB 부하를 극적으로 줄임
  단점: Redis 장애 시 DB 레벨로 폴백하는 로직 필요. Redis-DB 정합성 관리 필요

앱 레벨 (Lock 기반):
  장점: 복잡한 비즈니스 로직 구현 가능
  단점: Pod가 여러 개면 분산 Lock(Redis) 필요. 관리 복잡도 증가
```

**선택: Redis 선점 + DB 원자적 UPDATE + DB CHECK 제약 3중 방어**

이유: 오픈 순간 수만 req/s가 전부 DB를 직접 때리면 DB가 먼저 죽는다. Redis로 먼저 걸러서 실제 좌석이 있는 요청만 DB에 도달하도록 하고, DB는 최후 보루로 남긴다.

### 2-3. 배포 전략: RollingUpdate vs Blue-Green

```
RollingUpdate:
  장점: 추가 인프라 없음, 설정이 단순
  단점: 배포 중 v1/v2 Pod가 공존하는 순간 존재. 스키마 변경 시 위험

Blue-Green:
  장점: v2 완전 검증 후 트래픽 전환. 즉시 롤백 가능
  단점: 피크 시간에는 리소스가 2배 필요. 설정 복잡도 증가
```

**선택: maxUnavailable: 0 RollingUpdate + Readiness Probe**

이유: Blue-Green은 오픈 직후 피크 때 리소스가 2배 필요해서 비용이 크다. maxUnavailable: 0으로 기존 Pod를 유지하면서 새 Pod가 Readiness Probe를 통과한 후에만 트래픽을 받도록 하면 실질적으로 안전한 배포가 된다.

---

## 3. 전체 아키텍처 흐름

```
[사용자]
    │
    ▼
[Ingress / LoadBalancer]
    │
    ├──► [좌석 조회 API Pod ×N]          ← 읽기 전용. 캐시로 DB 부하 분리
    │
    └──► [예매 처리 API Pod ×N]
              │
              ├── 1단계: Redis DECR (좌석 선점)
              │         └─ 실패 → 즉시 409 "매진" 반환
              │
              ├── 2단계: DB 트랜잭션
              │     ├── reservations INSERT
              │     └── seats UPDATE remaining = remaining - 1
              │             WHERE remaining > 0 (원자적 보장)
              │         └─ 실패 → Redis 되돌리기 + 409 "매진" 반환
              │
              └── 3단계: 예매 완료 응답
                        결제는 비동기 (MQ → Payment Worker)

[Redis]           ← 좌석별 잔여 수 카운터 (DECR 원자적 연산)
[MySQL / PostgreSQL]  ← reservations, seats 테이블 (CHECK 제약)
[Message Queue]   ← 결제 처리 비동기화
```

### 읽기/쓰기 분리

좌석 조회(읽기)와 예매 처리(쓰기)를 별도 Deployment로 분리했다. 오픈 직전 수만 명이 좌석 현황을 새로고침하는 읽기 폭발이 예매 처리 API에 영향을 주지 않도록 격리한다.

좌석 조회는 Redis 캐시에서 응답하고, 실제 DB에는 쓰기 요청만 도달하도록 설계했다.

---

## 4. Kubernetes 설정 상세

### 4-1. 예매 처리 Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ticket-booking-api
spec:
  replicas: 3                         # 평시 최소 유지 수 (HPA minReplicas와 일치)
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0               # 배포 중 처리 용량 절대 감소 없음
      maxSurge: 3                     # 새 Pod 3개씩 올리고 확인 후 교체
  template:
    spec:
      terminationGracePeriodSeconds: 30
      # 결제 API 호출 최대 5초 × 2 + preStop 5초 = 15초 → 여유 30초
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: ticket-booking-api
            topologyKey: kubernetes.io/hostname
          # 같은 노드에 예매 API Pod 2개가 함께 뜨지 않도록 강제 분산
          # 노드 하나가 죽어도 서비스 전체가 다운되지 않음
      containers:
      - name: ticket-booking-api
        image: ticket-booking-api:v1
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"           # OOM 방지. SIGKILL은 Graceful Shutdown 우회함
            cpu: "500m"
        readinessProbe:               # 이게 없으면 새 Pod가 실제로 준비되기 전에 트래픽을 받음
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 3
        livenessProbe:                # 앱이 무한루프/데드락에 빠지면 자동 재시작
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 10
        lifecycle:
          preStop:
            exec:
              command: ["sleep", "5"] # kube-proxy Endpoints 업데이트 대기
```

**Pod Anti-Affinity를 넣은 이유:**

실습에서 멀티노드 환경에서 Pod가 여러 노드에 분산 배치되는 걸 관찰했다. 하지만 기본 스케줄링은 분산을 보장하지 않는다. `requiredDuringScheduling`으로 강제하면 노드 1개가 죽어도 서비스가 살아남는다. 오픈 당일 노드 장애가 전체 서비스 다운으로 이어지는 걸 막는 핵심 설정이다.

**Readiness / Liveness Probe를 넣은 이유:**

Readiness Probe 없이 Rolling Update를 하면 새 Pod의 컨테이너가 시작됐다고 해서 앱이 준비된 게 아니다. DB 커넥션 풀 초기화, 캐시 워밍이 끝나기 전에 트래픽을 받으면 초기 요청들이 실패한다. Readiness Probe가 통과한 Pod에만 Service가 트래픽을 보내도록 보장한다.

---

### 4-2. HPA + CronJob 조합

```yaml
# HPA: 반응형 스케일링
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ticket-booking-api
  minReplicas: 3
  maxReplicas: 80
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0       # 스케일업은 즉시
      policies:
      - type: Percent
        value: 100                         # 현재 수의 최대 2배까지 30초마다
        periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 300     # 스케일다운은 5분 관찰 후
```

```yaml
# CronJob: 오픈 30분 전 Scheduled Scaling
apiVersion: batch/v1
kind: CronJob
metadata:
  name: ticket-open-scale-up
spec:
  schedule: "30 18 * * 5"               # 공연 오픈 30분 전 (예: 금요일 18:30)
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: deployment-scaler
          containers:
          - name: kubectl-scaler
            image: bitnami/kubectl:latest
            command:
            - kubectl
            - scale
            - deployment/ticket-booking-api
            - --replicas=60             # 피크 대응 수로 미리 올림
          restartPolicy: OnFailure
```

HPA만 믿으면 안 되는 이유를 수치로 정리하면:

```
오픈 순간 트래픽 폭발 (T=0)
HPA가 Pod를 충분히 늘릴 때까지: T+2~3분
→ 이 2~3분 동안 기존 3개 Pod가 수만 req/s를 혼자 감당
→ 거의 확실하게 SLA 위반 및 일부 요청 실패

CronJob으로 오픈 30분 전에 60개로 올려두면:
→ 오픈 순간에 이미 60개 Pod가 Running
→ HPA는 오픈 후 실제 트래픽을 보면서 fine-tuning만 담당
```

---

### 4-3. PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ticket-booking-pdb
spec:
  minAvailable: 2                        # 노드 유지보수, 업그레이드 시에도 최소 2개 보장
  selector:
    matchLabels:
      app: ticket-booking-api
```

노드 유지보수나 클러스터 업그레이드 시 Kubernetes가 Pod를 강제로 evict한다. PDB 없이는 동시에 여러 Pod가 evict되어 서비스가 순간 다운될 수 있다. `minAvailable: 2`는 어떤 상황에서도 최소 2개 Pod가 살아있음을 보장한다.

---

## 5. 중복 예매 방지 설계

### 3중 방어선

```
1차: Redis DECR (속도 담당)
     ↓ 실패 시 즉시 409 반환 (DB 미도달)
2차: SQL WHERE remaining > 0 (정합성 담당)
     ↓ 실패 시 Redis 복구 + 409 반환
3차: DB CHECK 제약 (최후 방어)
     remaining >= 0 보장. 앱 코드 버그도 DB가 막음
```

```sql
-- 예매 처리 핵심 쿼리
BEGIN;
  INSERT INTO reservations (user_id, seat_id, status)
  VALUES ($1, $2, 'confirmed');

  UPDATE seats
  SET remaining = remaining - 1
  WHERE seat_id = $2 AND remaining > 0
  RETURNING remaining;
  -- 반환값 없음 → ROLLBACK + Redis 복구 + 409 "매진"
COMMIT;
```

```sql
-- DB 레벨 최후 방어선
ALTER TABLE seats
ADD CONSTRAINT remaining_non_negative CHECK (remaining >= 0);
```

### 에러 응답 구분

```
409 Conflict  + {"reason": "SOLD_OUT"}   → 매진. 다른 좌석을 선택하세요.
409 Conflict  + {"reason": "DUPLICATE"}  → 이미 예매한 좌석입니다.
500           + {"reason": "SYSTEM_ERROR"} → 시스템 오류. 잠시 후 다시 시도해주세요.
```

사용자 경험 측면에서 "매진"과 "오류"를 같은 에러로 내려보내면 사용자가 매진 좌석을 계속 시도하거나, 반대로 시스템 오류를 매진으로 오해하는 문제가 생긴다.

---

## 6. Pod 장애 대응

### 종료 흐름 (SIGTERM — 정상 배포/삭제)

```
kubectl delete pod / Rolling Update
  │
  ├── preStop: sleep 5초
  │   → kube-proxy가 Endpoints에서 이 Pod IP 제거 완료
  │   → Service가 이 Pod로 새 트래픽 보내는 것 중단
  │
  └── SIGTERM → 앱 종료 로직 실행
        → 처리 중인 예매 요청 완료 대기
        → DB 트랜잭션 commit 또는 rollback
        → DB 커넥션 풀 정상 종료 (FIN 전송)
        → 프로세스 종료
```

preStop이 없으면 kube-proxy가 Endpoints를 업데이트하기 전에 Pod가 이미 종료 중이다. 이 짧은 gap 동안 들어온 요청들이 연결 거절을 받아 502/504로 사용자에게 노출된다.

### OOM 상황 (SIGKILL — 즉사)

```
Flash Sale 중 메모리 사용량 급증 → limits 초과 → SIGKILL
  → Graceful Shutdown 코드 실행 안 됨
  → 처리 중 예매 요청 강제 종료
  → DB 트랜잭션 자동 롤백 (정합성 유지)
  → DB 커넥션 강제 종료 → zombie 커넥션 누적
  → 새 Pod들 DB 커넥션 못 얻음 → 서비스 다운 위험
```

OOM 자체를 막는 게 먼저다. `limits.memory`를 `requests`의 2배로 잡아서 피크 때 메모리 사용량이 올라가도 여유가 있게 한다.

### Self-healing과의 연결

실습에서 Pod가 죽으면 ReplicaSet이 새 Pod를 만드는 걸 관찰했다. 여기서 중요한 건 새 Pod가 Running이 돼도 바로 트래픽을 받지 않아야 한다는 것이다. Readiness Probe가 통과해야만 Service의 Endpoints에 등록된다. 이 구간 동안은 나머지 Pod들이 트래픽을 분담한다.

```
Pod OOM 죽음 → ReplicaSet이 새 Pod 생성 요청
  → Pending → ContainerCreating → Running (컨테이너 시작)
  → Readiness Probe 통과 대기 (앱 초기화 완료 확인)
  → Endpoints 등록 → Service가 트래픽 전달 시작
```

---

## 7. 모니터링 지표

| 지표 | 임계값 | 의미 |
| --- | --- | --- |
| HTTP 5xx rate | > 0.1% | 예매 처리 오류 발생 |
| p99 응답 시간 | > 1초 | SLA 위험 신호 |
| Redis DECR 실패율 급증 | - | 매진 임박 또는 Redis 장애 구분 필요 |
| DB 커넥션 풀 사용률 | > 80% | zombie 커넥션 누적 위험 |
| Pod Restart Count 급증 | - | OOM 또는 앱 크래시 |
| Readiness Probe 실패 | 연속 실패 | 새 Pod 정상화 지연 |

### Alert 설정

```
오픈 30분 전:  CronJob 성공 확인 → 실패 시 수동으로 즉시 스케일업
오픈 직후:     5xx rate 모니터링 → 급증 시 이전 버전으로 즉시 롤백
               kubectl rollout undo deployment/ticket-booking-api
피크 종료 후:  HPA 스케일다운 확인, zombie 커넥션 정리
```

---

## 8. 비용 최적화

티켓 오픈은 "예고된 이벤트"라는 특성상, **평소에는 최소로 유지하고 오픈 전에만 늘리는 전략**이 맞다.

```
평시 (오픈 없는 날):
  → minReplicas: 3 (HPA 하한선)
  → 좌석 조회 트래픽만 처리. 읽기 Pod는 캐시로 대부분 처리

오픈 30분 전:
  → CronJob이 60대로 올림 → 오픈 후 HPA가 fine-tuning

오픈 종료 후:
  → HPA stabilizationWindowSeconds: 300으로 천천히 스케일다운
  → 갑작스러운 스케일다운으로 남은 예매 요청이 Pod 부족으로 실패하는 것 방지
```

---

## 9. 결론

### 이 설계의 핵심 3가지

**첫째, HPA를 믿지 마라.**

HPA는 반응형이다. 오픈 시각을 알고 있다면 Scheduled Scaling으로 미리 준비하고, HPA는 보조 역할로만 쓴다.

**둘째, 중복 예매 방지는 레이어 분리로 설계한다.**

Redis(속도) + SQL(정합성) + DB CHECK(최후 방어). 단일 레이어에 의존하면 그 레이어가 병목이 되거나 장애가 날 때 전체가 무너진다.

**셋째, Pod는 언제든 죽을 수 있다는 전제로 설계한다.**

preStop + terminationGracePeriodSeconds + Readiness Probe + PDB + Anti-Affinity. 이 다섯 가지는 "Pod가 죽어도 서비스가 살아남는" 구조의 필수 요소다.

> 실습에서 관찰한 것 — Pod를 삭제하면 새 Pod가 생긴다, Service는 Running Pod에만 트래픽을 보낸다, standalone Pod는 복구되지 않는다 — 이 모든 관찰이 이 설계의 근거다.
>