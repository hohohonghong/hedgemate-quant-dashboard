# Market State Research Brief

발표 목적:  
처음 보는 사람도 `왜 이 연구를 하는지`, `무슨 자료를 참고했는지`, `지금 어떤 작업을 하고 있는지`를 짧고 쉽게 이해할 수 있도록 정리한 발표용 초안이다.

---

## Slide 1. HedgeMate 안에서 왜 필요한가

- HedgeMate는 `포트폴리오 분석 및 리스크 관리 솔루션`을 지향하는 프로젝트다.
- 이 안에서 현재 진행 중인 시나리오 리서치는 `메인 기능 전체`가 아니라, 시장을 해석하는 보조 엔진에 가깝다.
- 즉, 자산 추천이나 헤지 아이디어를 제시하기 전에 `지금 시장이 어떤 환경인지`를 먼저 읽어주는 역할을 한다.

핵심 질문:
- 지금 시장은 어떤 상태인가?
- 이 상태를 왜 그렇게 해석했는가?
- 이 해석을 HedgeMate의 리스크 관리와 나중에 연결할 수 있는가?

---

## Slide 2. 이 리서치의 목표

- HedgeMate 안에서 사용할 수 있는 `시장 상태 판별 로직`을 만든다.
- 사람이 이해할 수 있는 시장 시나리오를 정의한다.
- 정형 시계열 데이터를 이용해 시나리오 강도를 계산한다.
- 나중에는 뉴스와 정책문도 붙여서 더 풍부한 해석을 만든다.
- 최종적으로는 `오늘 시장 상태 + 근거 + 경고 수준`을 출력한다.

한 줄 요약:

`시장 데이터 -> 시나리오 점수 -> 상태 분류 -> 설명 가능한 요약`

---

## Slide 3. 왜 이런 방식이 필요한가

- 최근 퀀트와 AI 연구는 단순히 `예측 모델 하나`를 만드는 방향보다, `시장 상태에 따라 해석과 대응을 바꾸는 방향`으로 발전하고 있다.
- 하지만 개인 프로젝트나 저사양 환경에서는 대형 RL, 대형 LLM, 복잡한 멀티에이전트 구조보다 `설명 가능하고 가벼운 상태 엔진`이 더 현실적이다.
- 따라서 이번 연구는 최신 흐름을 참고하되, 실제 구현은 `단순하고 검증 가능한 구조`로 가져간다.

---

## Slide 4. 이 로직이 HedgeMate 안에서 하는 일

- HedgeMate의 메인 목적은 `포트폴리오 분석`과 `리스크 관리`다.
- 시나리오 리서치 로직은 그 안에서 `현재 시장 해석 레이어` 역할을 맡는다.
- 즉, 바로 매매하거나 포트폴리오를 자동 변경하는 것이 아니라,
  - 현재 시장 상태를 분류하고
  - 그 판단 근거를 보여주고
  - 나중에 리스크 오버레이와 연결할 수 있게 준비하는 역할이다.

정리하면:
- HedgeMate 본체: 자산 분석, 포트폴리오 분석, 리스크 관리
- 시나리오 리서치: 시장 상태 판별과 설명

---

## Slide 5. 현재 리서치 작업 흐름

현재 작업은 크게 4단계로 이해하면 된다.

1. `시나리오 정의`
- 어떤 시장 상태를 추적할지 정리

2. `정형 데이터 수집`
- 환율, 금리, 지수, 원자재, 변동성, 한국/중국 관련 데이터를 수집

3. `시나리오 점수 계산`
- 각 시나리오를 설명하는 신호들을 합쳐 점수화

4. `시장 상태 요약`
- 오늘 어떤 시나리오가 활성화됐는지와 근거를 요약

즉,  
지금은 `시장 상태를 읽는 엔진`을 먼저 만들고 있는 단계다.

---

## Slide 6. Phase 1~10 로드맵

### Phase 1. 시나리오 정의
- 어떤 시장 상태를 추적할지 정리

### Phase 2. 데이터 수집 기반 구축
- 정형 데이터 파이프라인 확보

### Phase 3. 시나리오 점수 엔진 V1
- 시계열 기반 점수 계산

### Phase 4. 설명 가능 요약 레이어
- 근거와 함께 상태 요약

### Phase 5. 비정형 이벤트 오버레이
- 뉴스, 정책문, 속보를 구조화

### Phase 6. 정형 + 비정형 병합
- 최종 시장 상태 판단

### Phase 7. 역사적 검증
- `Global Financial Crisis type`
- `Pandemic shock`
- `War / Energy shock`
- `Global rate shock`
- 이런 범용 역사 구간에서 상태 전환이 자연스러운지 검증

### Phase 8. 운영화
- 매일 자동 실행, 저장, 리포트화

### Phase 9. 경량 고도화
- 필요 시 HMM, Markov, 경량 분류기 보완

### Phase 10. 포트폴리오 연결
- 시장 상태를 추천 우선순위, 리스크 오버레이에 연결

---

## Slide 8. 기대 효과

- 시장을 `설명 가능하게` 읽을 수 있다.
- 추천이나 헤지 로직에 앞서 `왜 이런 판단이 나왔는지`를 말할 수 있다.
- 나중에 포트폴리오 추천과 연결할 때도 구조가 자연스럽다.
- 한국 투자자 관점에서 `원화`, `대외 충격`, `중국`, `금리`를 함께 해석할 수 있다.

마무리 한 줄:

`이번 연구는 AI와 퀀트의 최신 흐름을 참고하되, 먼저 설명 가능한 시장 상태 엔진을 만드는 작업이다.`

---

## Slide 9. 참고한 핵심 연구

### 1. AI in Quant Survey

- [From Deep Learning to LLMs: A survey of AI in Quantitative Investment (2025)](https://arxiv.org/abs/2503.21422)
- AI가 퀀트 투자 전반을 어떻게 바꾸고 있는지 정리한 서베이
- 시사점: 시장 분석도 `정형 + 비정형 + 자동화` 구조로 가고 있음

### 2. Adaptive / Mixture of Experts 계열

- [Adaptive Market Intelligence: A Mixture of Experts Framework for Volatility-Sensitive Stock Forecasting (2025)](https://arxiv.org/abs/2508.02686)
- [MIGA: Mixture-of-Experts with Group Aggregation for Stock Market Prediction (2024)](https://arxiv.org/abs/2410.02241)
- 시사점: 시장 상태가 다르면 `단일 모델`보다 `적응형 구조`가 더 유리할 수 있음

### 3. Regime Switching 고전적 접근

- [statsmodels MarkovRegression 문서](https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html)
- [Markov switching dynamic regression notebook](https://www.statsmodels.org/dev/examples/notebooks/generated/markov_regression.html)
- 시사점: 꼭 딥러닝이 아니어도 `시장 상태 전환`을 통계적으로 다룰 수 있음

### 4. 실무형 오픈소스 참고

- [Qlib](https://github.com/microsoft/qlib)
- [Qlib Meta / market dynamics docs](https://qlib.readthedocs.io/en/stable/component/meta.html)
- [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT)
- [FinRL-X](https://arxiv.org/abs/2603.21330)

시사점:
- Qlib: 시장 동학 적응
- FinGPT: 금융 비정형 데이터 처리
- FinRL-X: 나중에 포트폴리오 연결 시 참고 가능한 시스템 구조

---

## References

1. [From Deep Learning to LLMs: A survey of AI in Quantitative Investment (2025)](https://arxiv.org/abs/2503.21422)
2. [Adaptive Market Intelligence: A Mixture of Experts Framework for Volatility-Sensitive Stock Forecasting (2025)](https://arxiv.org/abs/2508.02686)
3. [MIGA: Mixture-of-Experts with Group Aggregation for Stock Market Prediction (2024)](https://arxiv.org/abs/2410.02241)
4. [Qlib GitHub](https://github.com/microsoft/qlib)
5. [Qlib Meta / market dynamics docs](https://qlib.readthedocs.io/en/stable/component/meta.html)
6. [statsmodels MarkovRegression docs](https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html)
7. [statsmodels Markov regression notebook](https://www.statsmodels.org/dev/examples/notebooks/generated/markov_regression.html)
8. [FinGPT GitHub](https://github.com/AI4Finance-Foundation/FinGPT)
9. [FinRL-X: An AI-Native Modular Infrastructure for Quantitative Trading (2026)](https://arxiv.org/abs/2603.21330)
