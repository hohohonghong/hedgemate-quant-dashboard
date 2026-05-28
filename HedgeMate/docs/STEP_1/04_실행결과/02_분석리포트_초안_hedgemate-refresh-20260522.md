# HedgeMate 분석 리포트 초안

## 0. 리포트 메타
- 작성일: 2026-05-22
- 작성자: 자동 파이프라인
- 데이터 버전: 20260522
- 분석 기간: 최근 5년 목표, 데이터 부족 시 가용 구간 기준 계산 허용
- 데이터 주기: 일봉
- 기준통화: KRW
- 위기구간 정의: SPY + ^KS200 20거래일 수익률 <= -8%

- 현재 장세 요약: 현재 장세: 장기금리 부담장(ACTIVE, us_global, score=62.723495) / 달러강세/원화약세장(ACTIVE, fx_krw, score=57.838824) / 우호적 위험선호장(WATCH, us_global, score=57.358838)
## 1. 데이터 품질 요약
- 수집 성공: 150/150
- DQ 판정(캘린더 기준): PASS 27, WARN 122, FAIL 1

## 2. 리스크 상위(KRW MDD 기준)
- BTC-USD: MDD_1y_krw=-0.4795, CVaR_95_1y_krw=-0.0554
- BTAL: MDD_1y_krw=-0.3444, CVaR_95_1y_krw=-0.0323
- 011200.KS: MDD_1y_krw=-0.2809, CVaR_95_1y_krw=-0.0499
- 068270.KS: MDD_1y_krw=-0.2781, CVaR_95_1y_krw=-0.0489
- PSQ: MDD_1y_krw=-0.2450, CVaR_95_1y_krw=-0.0274

## 3. 헷징 후보 Top10
- 시나리오 벡터: `scenario_research\outputs\scenario_vectors\current_scenario_vector_final-refresh-20260522.csv`
1. PSQ (inverse_etf) - HES=0.3726 [Corr=0.888, CVaR=0.683, Stress=0.517, Sharpe=0.176, LiqPenalty=1.000]
2. 153130.KS (kr_etf) - HES=0.3721 [Corr=0.713, CVaR=1.000, Stress=0.469, Sharpe=0.000, LiqPenalty=1.000]
3. SH (inverse_etf) - HES=0.3693 [Corr=0.808, CVaR=0.735, Stress=0.523, Sharpe=0.192, LiqPenalty=1.000]
4. TAIL (tail_risk_etf) - HES=0.3619 [Corr=0.682, CVaR=0.799, Stress=0.547, Sharpe=0.216, LiqPenalty=1.000]
5. 261240.KS (kr_etf) - HES=0.3413 [Corr=0.557, CVaR=0.816, Stress=0.524, Sharpe=0.288, LiqPenalty=1.000]
6. BTC-USD (crypto) - HES=0.3284 [Corr=0.290, CVaR=0.356, Stress=0.687, Sharpe=0.196, LiqPenalty=0.000]
7. 055550.KS (kr_stock) - HES=0.3284 [Corr=0.977, CVaR=0.513, Stress=0.232, Sharpe=0.397, LiqPenalty=1.000]
8. BTAL (equity_etf) - HES=0.3240 [Corr=0.779, CVaR=0.626, Stress=0.491, Sharpe=0.163, LiqPenalty=1.000]
9. 068270.KS (kr_stock) - HES=0.3218 [Corr=0.997, CVaR=0.433, Stress=0.362, Sharpe=0.280, LiqPenalty=1.000]
10. 011200.KS (kr_stock) - HES=0.3181 [Corr=0.953, CVaR=0.421, Stress=0.431, Sharpe=0.257, LiqPenalty=1.000]

## 4. 포트폴리오 개선 효과 (KRW 기준)
| 시나리오 | 변동성 | MDD | CVaR(95%) | 연환산수익률 | Sharpe | 변동성 개선률(%) | MDD 개선률(%) | CVaR 개선률(%) | Sharpe 개선률(%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 기존 포트폴리오 | 0.241033 | -0.477382 | -0.033113 | 0.278032 | 1.029036 | 0.00 | 0.00 | 0.00 | 0.00 |
| 제안(1:1) - XLV | 0.223208 | -0.436996 | -0.030740 | 0.266973 | 1.061669 | 7.40 | 8.46 | 7.17 | 3.17 |

## 6. 다음 액션
- FX carry-forward 허용 범위 및 예외 처리 검토
- 단일 종목 질의 결과를 API/UI 입력 흐름에 연결
- 무위험수익률 실데이터 연결로 Sharpe proxy 고도화
