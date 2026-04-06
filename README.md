# ☁️ 구름빵 — Cloud Infrastructure Study
---
클라우드 환경에서의 **아키텍처 선택 기준을 데이터 기반으로 이해하고 설명하는 능력**을 기르기 위한 스터디입니다.  

최근 클라우드 환경은 성능뿐 아니라 비용과 운영까지 함께 최적화하는 방향으로 발전하고 있습니다.  
FinOps를 통한 비용 관리, Observability/AIOps 기반 운영, 그리고 하이브리드·멀티 클라우드 전략이 점점 중요해지고 있습니다.  

이러한 흐름 속에서 상황에 맞는 아키텍처를 선택하고 그 근거를 설명할 수 있는 능력을 목표로 합니다.  

실습을 통해 얻은 결과를 기반으로 성능, 비용, 운영 측면의 이슈를 분석하고,  
아키텍처 간 차이를 비교·토론하며 실무적인 인프라 설계 역량을 기릅니다.

---

## 👥 Members
<table style="table-layout: fixed; width: 100%;">
  <tr>
    <td align="center" ><img src="https://github.com/hyewonchoi-cs.png" width="100" /></td>
    <td align="center"><img src="https://github.com/hakyunghahm.png" width="100" /></td>
    <td align="center" ><img src="https://github.com/hvvup.png" width="100" /></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/hyewonchoi-cs"><strong>@hyewonchoi-cs</strong></a></td>
    <td align="center"><a href="https://github.com/hakyunghahm"><strong>@hakyunghahm</strong></a></td>
    <td align="center"><a href="https://github.com/hvvup"><strong>@hvvup</strong></a></td>
  </tr>
  <tr>
    <td align="center">최혜원</td>
    <td align="center">함하경</td>
    <td align="center">조휘정</td>
  </tr>
</table>

---

## 🎯 목표
1. 다양한 클라우드 아키텍처의 **실행 방식과 내부 동작을 구조적으로 이해**하게 됩니다.  
2. 실습을 통해 수집한 데이터를 기반으로 **성능, 비용, 운영 측면을 정량적으로 분석**할 수 있게 됩니다.  
3. 트래픽 패턴과 서비스 요구사항에 맞춰 **최적의 아키텍처를 선택하고 그 근거를 명확히 설명**할 수 있게 됩니다.   

---

## 🗓️ 스터디 일정
- 정기 모임: 매주 월요일 오후 6:20 (대면)
- 과제 제출: 매주 일요일 23:59까지 (Notion)

---

## 🔄 스터디 진행 방식

- 매주 정해진 분량에 대해 기술 블로그 및 공식 문서를 기반으로 개념 학습
- 개별 실습을 통해 결과 측정 및 인사이트 정리
- 지난 주차 개념을 기반으로 공통 시나리오 아키텍처 설계
- 팀원 실습 결과를 사전 확인하고 질문 및 다음 주차 시나리오 준비

---

## 🧪 커리큘럼

| 주차 | 주제 | 핵심 내용 |
|------|------|-----------|
| 1주차 | 실행 모델 | Container vs Serverless, Cold Start, P99 Latency |
| 2주차 | Kubernetes | Pod / Deployment / Self-healing |
| 3주차 | Network | Ingress, HTTP/HTTPS, TLS |
| 4주차 | GitOps | ArgoCD, Configuration Drift |
| 5주차 | Observability | Metrics / Logs, Golden Signals |
| 6주차 | FinOps | 비용 구조, Break-even Point |
| 7주차 | Scaling | 트래픽 패턴, Autoscaling |
| 8주차 | 정리 | Trade-off 분석 및 아키텍처 선택 기준 |

---
## 🌿 브랜치 전략

- 개인 작업은 **주차별 브랜치**에서 진행
- 모든 PR은 `main` 브랜치로 머지

### 브랜치 네이밍
- `<githubID>-week-<NN>`
- 예: `hakyunghahm-week-01`
