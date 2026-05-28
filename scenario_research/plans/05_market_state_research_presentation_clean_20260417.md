

---

## Slide 1. 이 로직은 HedgeMate 안에서 무엇을 하나

- HedgeMate는 `포트폴리오 분석 및 리스크 관리 솔루션`이다.
- 그 안에서 시나리오 리서치 로직은 `시장 상태를 읽어주는 해석 레이어` 역할을 한다.
- 즉, 자산 분석이나 리스크 관리 결과를 보여주기 전에  
  `지금 시장이 어떤 환경인지`를 먼저 설명해주고 현 포트폴리오에 어떤 영향을 끼칠지를 설명해주기 위한 기반이 되는 로직이다.

핵심 역할:
- 오늘 시장 상태를 분류한다
- 왜 그렇게 판단했는지 근거를 보여준다
- 나중에 포트폴리오 분석과 리스크 관리 로직에 연결될 수 있게 한다

---

## Slide 2. 왜 필요한가

- 같은 자산이라도 `시장 환경`에 따라 의미가 달라진다.
- 예를 들어 원화 약세 장세, 리스크오프 장세, 금리 충격 장세에서는  
  같은 자산도 전혀 다르게 해석될 수 있다.
- 따라서 HedgeMate 안에서는 `자산 자체 분석`만이 아니라  
  `현재 시장 상태 해석`이 같이 있어야 더 설득력 있는 결과를 줄 수 있다.

핵심 질문:
- 지금 시장은 어떤 상태인가?
- 왜 그렇게 판단했는가?
- 그 결과를 리스크 관리 관점에서 어떻게 활용할 수 있는가?

---

## Slide 3. 현재 만들고 있는 방식

현재 방향은 아주 단순하게 시작한다.

1. `시나리오 정의`
- 어떤 시장 상태를 추적할지 정리

2. `정형 데이터 수집`
- 환율, 금리, 주가지수, 원자재, 변동성 등 시장 데이터를 수집

3. `시나리오 점수 계산`
- 각 시나리오를 설명하는 신호들을 합쳐 강도를 계산

4. `시장 상태 요약`
- 오늘 어떤 시나리오가 활성화됐는지와 근거를 출력

한 줄 요약:

`시장 데이터 -> 시나리오 점수 -> 상태 분류 -> 설명 가능한 요약`

---

## Slide 4. 지금 무엇을 출력하려는가

현재 단계의 목표는 `시장 상태 엔진`이다.

즉, 지금은
- 포트폴리오를 바꾸는 것이 아니라
- 시장 상태를 설명 가능하게 읽고
- 그 결과를 리스크 관리 관점에서 해석할 수 있게 만드는 단계다

현재 출력 목표:
- 일별 시나리오 상태
- 시나리오별 점수
- 주요 근거 지표
- 반대 방향 근거 또는 결측 caveat
- confidence / coverage 해석
- 짧은 시장 상태 요약 문서

---

## Slide 5. Phase 1~10 로드맵

### Phase 1. 시나리오 정의
- 어떤 시장 상태를 추적할지 정리

### Phase 2. 데이터 수집 기반 구축
- 정형 데이터 파이프라인 확보

### Phase 3. 시나리오 점수 엔진 V1
- 시계열 기반 점수 계산

### Phase 4. 설명 가능 요약 레이어  ( 현재 여기까지 구현중 )
- 근거와 함께 상태 요약
- 이 단계의 결과는 포트폴리오 자동 변경이 아니라, 현재 시장 환경을 이해하기 위한 설명 레이어
- 사용자에게는 `무엇`, `왜`, `얼마나 믿을 수 있는지`, `주의할 점`을 함께 보여주는 것이 목표
- 추가 정형 지표는 8개 팩터로 압축해서 보여준다. 데이터가 늘어나도 사용자는 상위 팩터와 상위 driver만 보면 된다.
- 70개 자산 유니버스는 시나리오를 직접 결정하기보다 breadth/추세 확산도로 현재 장세의 폭을 검증한다.

### Phase 5. 비정형 데이터 수집 및 분석
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



---

## Slide 6. 기대 효과

- HedgeMate 안에서 시장을 `설명 가능하게` 읽을 수 있다.
- 자산 분석 결과에 앞서 `왜 이런 환경인지`를 같이 제시할 수 있다.
- 나중에 포트폴리오 분석 및 리스크 관리 로직과 자연스럽게 연결할 수 있다.
- 한국 투자자 관점에서 `원화`, `대외 충격`, `중국`, `금리`를 함께 해석할 수 있다.

마무리 한 줄:

`이번 작업은 HedgeMate 안에서 시장 환경을 읽어주는 설명 가능한 리서치 엔진을 만드는 과정이다.`

---

## Appendix. 참고한 핵심 연구

### 1. AI in Quant Survey
- [From Deep Learning to LLMs: A survey of AI in Quantitative Investment (2025)](https://arxiv.org/abs/2503.21422)
- 시사점: 시장 분석도 `정형 + 비정형 + 자동화` 구조로 발전하고 있음

### 2. Adaptive / Mixture of Experts 계열
- [Adaptive Market Intelligence: A Mixture of Experts Framework for Volatility-Sensitive Stock Forecasting (2025)](https://arxiv.org/abs/2508.02686)
- [MIGA: Mixture-of-Experts with Group Aggregation for Stock Market Prediction (2024)](https://arxiv.org/abs/2410.02241)
- 시사점: 상태가 다르면 `단일 모델`보다 `적응형 구조`가 유리할 수 있음

### 3. Regime Switching 고전적 접근
- [statsmodels MarkovRegression docs](https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html)
- [Markov regression notebook](https://www.statsmodels.org/dev/examples/notebooks/generated/markov_regression.html)
- 시사점: 시장 상태 전환을 통계적으로 다룰 수 있음

### 4. 실무형 오픈소스 참고
- [Qlib](https://github.com/microsoft/qlib)
- [Qlib Meta / market dynamics docs](https://qlib.readthedocs.io/en/stable/component/meta.html)
- [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT)
- [FinRL-X](https://arxiv.org/abs/2603.21330)

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
