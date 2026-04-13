# Architecture Decision: Serverless vs Container

## 1. Scenario

AI 기반 이미지 변환 서비스 (Toon Generator)

- 입력: 사용자 이미지 업로드
- 처리: AI 모델 기반 이미지 변환 (CPU-bound)
- 처리 시간: 약 1.5s ~ 2.5s
- 트래픽 패턴: 평소 low traffic, 특정 시점 spike 발생
- UX 요구사항: 응답 시간 5초 이내

---

## 2. Architecture Options

### Option 1. Serverless (AWS Lambda)

- API Gateway + Lambda + S3 + DynamoDB
- S3 Event 기반 비동기 처리
- Provisioned Concurrency로 cold start 대응

### Option 2. Container (Amazon EKS)

- ALB + EKS (Pod 기반 처리)
- CPU 1000m 고정 할당
- HPA 기반 autoscaling

---

## 3. Experimental Findings

### 3.1 Execution Time

- AI inference: 약 2초
- Lambda cold start 포함 worst-case: 약 3.1초

→ 총 응답 시간: 약 5.1초 (기본 상태)

### 3.2 Optimization Effect

- Lambda memory 1024MB 설정
→ CPU 성능 증가 → 실행 시간 단축
- Provisioned Concurrency 적용
→ cold start 제거

→ P99 latency: 약 3초 수준으로 안정화

---

## 4. Decision: Serverless (Lambda) 선택

### 4.1 Cost Efficiency

- EKS: 항상 노드 실행 → idle cost 발생
- Lambda: 요청 없을 시 비용 0

→ 간헐적 트래픽 환경에서 압도적 비용 효율

### 4.2 Scalability

- EKS: scale-out에 수 분 소요 (node provisioning)
- Lambda: 요청 기반 즉시 확장

→ spike traffic 대응에 Lambda가 유리

### 4.3 Performance (UX Constraint)

- 요구사항: 5초 이하

실험 결과:

- cold start 포함: 약 5.1초
- 최적화 후: 약 3초 (P99)

→ UX 요구사항 안정적으로 만족

---

## 5. Key Insight

### 5.1 아키텍처 선택은 “트래픽 패턴” 문제

- steady traffic → Kubernetes
- burst traffic → Serverless

→ 기술 선택이 아니라 workload 특성 기반 결정

### 5.2 Cold Start는 설계로 해결 가능한 문제

- memory tuning + provisioned concurrency

→ Serverless의 단점은 구조적으로 보완 가능

### 5.3 비용 vs 성능 Trade-off

- Kubernetes: 안정적 성능, 높은 고정 비용
- Serverless: 낮은 비용, 초기 지연 존재

→ 이번 시나리오는 비용 구조가 더 중요한 문제

### 5.4 비동기 구조가 UX를 결정함

- S3 event 기반 처리로 API 응답과 분리

→ 단순 compute 선택보다 **workflow 설계가 더 중요**

## AI Inference Strategy

현재 시나리오에서는 Lambda 내부에서 직접 inference를 수행하는 방식을 우선 고려한다.

- 작업 특성이 CPU-bound이며, 추론 시간이 약 1.5~2.5초 수준
- 트래픽 패턴이 burst + sparse 형태이므로 상시 실행형 inference 서버보다 비용 효율적
- 별도 모델 서버를 두지 않아도 되어 초기 구조가 단순하고 운영 부담이 낮음

다만, 향후 모델 크기가 증가하거나 GPU 기반 추론이 필요해질 경우에는

Lambda를 orchestration 계층으로 두고, 별도의 inference endpoint(EKS 기반 모델 서버 등)로 분리하는 구조를 고려할 수 있다.