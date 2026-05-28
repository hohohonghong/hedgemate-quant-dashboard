# HedgeMate 분석 리포트 초안

## 0. 리포트 메타
- 작성일: 2026-05-28
- 작성자: 자동 파이프라인
- 데이터 버전: 20260528
- 분석 기간: 최근 5년 목표, 데이터 부족 시 가용 구간 기준 계산 허용
- 데이터 주기: 일봉
- 기준통화: KRW
- 위기구간 정의: SPY + ^KS200 20거래일 수익률 <= -8%

- 현재 장세 요약: 현재 장세: 우호적 위험선호장(ACTIVE, us_global, score=63.617751) / 달러강세/원화약세장(ACTIVE, fx_krw, score=56.521013) / 장기금리 부담장(WATCH, us_global, score=52.243315)
## 1. 데이터 품질 요약
- 수집 성공: 150/150
- DQ 판정(캘린더 기준): PASS 27, WARN 122, FAIL 1

## 2. 리스크 상위(KRW MDD 기준)
- BTC-USD: MDD_1y_krw=-0.4795, CVaR_95_1y_krw=-0.0554
- 207940.KS: MDD_1y_krw=-0.3196, CVaR_95_1y_krw=-0.0507
- 011200.KS: MDD_1y_krw=-0.2809, CVaR_95_1y_krw=-0.0499
- 068270.KS: MDD_1y_krw=-0.2781, CVaR_95_1y_krw=-0.0483
- 132030.KS: MDD_1y_krw=-0.2467, CVaR_95_1y_krw=-0.0471

## 3. 헷징 후보 Top10
- 시나리오 벡터: `scenario_research\outputs\scenario_vectors\current_scenario_vector_final-refresh-20260528.csv`
1. 153130.KS (kr_etf) - HES=0.3897 [Corr=0.680, CVaR=1.000, Stress=0.599, Sharpe=0.000, LiqPenalty=1.000]
2. 261240.KS (kr_etf) - HES=0.3602 [Corr=0.521, CVaR=0.817, Stress=0.669, Sharpe=0.279, LiqPenalty=1.000]
3. BTC-USD (crypto) - HES=0.3478 [Corr=0.242, CVaR=0.336, Stress=0.876, Sharpe=0.188, LiqPenalty=0.000]
4. 068270.KS (kr_stock) - HES=0.3356 [Corr=0.991, CVaR=0.421, Stress=0.462, Sharpe=0.267, LiqPenalty=1.000]
5. 011200.KS (kr_stock) - HES=0.3344 [Corr=0.961, CVaR=0.402, Stress=0.550, Sharpe=0.224, LiqPenalty=1.000]
6. 055550.KS (kr_stock) - HES=0.3302 [Corr=0.973, CVaR=0.497, Stress=0.296, Sharpe=0.357, LiqPenalty=1.000]
7. 132030.KS (kr_etf) - HES=0.3294 [Corr=0.793, CVaR=0.436, Stress=0.646, Sharpe=0.286, LiqPenalty=1.000]
8. 207940.KS (kr_stock) - HES=0.3293 [Corr=1.000, CVaR=0.393, Stress=0.498, Sharpe=0.210, LiqPenalty=1.000]
9. 017670.KS (kr_stock) - HES=0.3203 [Corr=0.858, CVaR=0.417, Stress=0.491, Sharpe=0.356, LiqPenalty=1.000]
10. 032830.KS (kr_stock) - HES=0.3051 [Corr=0.891, CVaR=0.342, Stress=0.321, Sharpe=0.552, LiqPenalty=1.000]

## 4. 포트폴리오 개선 효과 (KRW 기준)
| 시나리오 | 변동성 | MDD | CVaR(95%) | 연환산수익률 | Sharpe | 변동성 개선률(%) | MDD 개선률(%) | CVaR 개선률(%) | Sharpe 개선률(%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 기존 포트폴리오 | 0.217322 | -0.293939 | -0.029725 | 0.376889 | 1.596197 | 0.00 | 0.00 | 0.00 | 0.00 |
| 참고안(다자산) - 261240.KS + TLT | 0.152724 | -0.202999 | -0.020578 | 0.280105 | 1.637626 | 29.72 | 30.94 | 30.77 | 2.60 |

- 추천 결과 없음: Gate 통과 후보가 없어 참고안을 표시합니다. 리스크 관리가 어렵습니다.

## 6. 다음 액션
- FX carry-forward 허용 범위 및 예외 처리 검토
- 단일 종목 질의 결과를 API/UI 입력 흐름에 연결
- 무위험수익률 실데이터 연결로 Sharpe proxy 고도화
