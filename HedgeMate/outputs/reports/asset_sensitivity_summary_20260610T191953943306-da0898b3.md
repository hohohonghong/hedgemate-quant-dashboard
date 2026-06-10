# HedgeMate 자산 민감도 요약

- run_id: 20260610T191953943306-da0898b3
- data_version: 20260610
- 현재 run에서 사용한 정량 민감도 축:
  - `market_beta_sp500` (beta_sp500_1y_krw)
  - `downside_beta_sp500` (downside_beta_sp500_1y_krw)
  - `corr_sp500_60d` (corr_sp500_60d_krw)
  - `corr_kospi200_60d` (corr_kospi200_60d_krw)
  - `stress_response` (avg_stress_ret_krw)
- 방향(sign) 규칙: `positive`=같은 방향, `negative`=반대 방향, `neutral`=유의미한 민감도 미약
- 크기(magnitude): 각 factor raw value의 절대값
- 민감도 강도(sensitivity_level): magnitude 기반 휴리스틱(low/medium/high)
- 구조 태그(structural_tags): `usd_exposure`, `rate_proxy`, `inflation_proxy`, `geopolitical_proxy`, `defensive_proxy`
- 참고: 직접 매크로 시계열(FX/금리/인플레이션) 민감도는 차기 단계에서 확장 예정이며, 현재 run은 시장/스트레스 기반 factor + 구조 태그를 저장한다.

## market_beta_sp500
- metric: `beta_sp500_1y_krw`
- positive 의미: SPY와 같은 방향
- negative 의미: SPY와 반대 방향
- direction count: positive 122, negative 9, neutral 19, unknown 0
- magnitude 상위 5개:
  - NVDA: direction=positive, magnitude=1.895602, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.895602
  - AMD: direction=positive, magnitude=1.860257, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.860257
  - TSLA: direction=positive, magnitude=1.78056, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.78056
  - LRCX: direction=positive, magnitude=1.719003, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.719003
  - MU: direction=positive, magnitude=1.667428, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.667428

## downside_beta_sp500
- metric: `downside_beta_sp500_1y_krw`
- positive 의미: 미국 증시 하락일에 함께 하락
- negative 의미: 미국 증시 하락일에 반대로 움직임
- direction count: positive 122, negative 12, neutral 16, unknown 0
- magnitude 상위 5개:
  - NVDA: direction=positive, magnitude=1.802142, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.802142
  - TSLA: direction=positive, magnitude=1.737014, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.737014
  - MU: direction=positive, magnitude=1.728861, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.728861
  - AMD: direction=positive, magnitude=1.646519, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.646519
  - AVGO: direction=positive, magnitude=1.558283, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.558283

## corr_sp500_60d
- metric: `corr_sp500_60d_krw`
- positive 의미: SPY와 같은 방향
- negative 의미: SPY와 반대 방향
- direction count: positive 120, negative 9, neutral 21, unknown 0
- magnitude 상위 5개:
  - SPY: direction=positive, magnitude=1.0, sensitivity_level=high, evidence=corr_sp500_60d_krw=1.0
  - VTI: direction=positive, magnitude=0.997745, sensitivity_level=high, evidence=corr_sp500_60d_krw=0.997745
  - QUAL: direction=positive, magnitude=0.971662, sensitivity_level=high, evidence=corr_sp500_60d_krw=0.971662
  - IWF: direction=positive, magnitude=0.964563, sensitivity_level=high, evidence=corr_sp500_60d_krw=0.964563
  - VUG: direction=positive, magnitude=0.958077, sensitivity_level=high, evidence=corr_sp500_60d_krw=0.958077

## corr_kospi200_60d
- metric: `corr_kospi200_60d_krw`
- positive 의미: KOSPI200과 같은 방향
- negative 의미: KOSPI200과 반대 방향
- direction count: positive 56, negative 54, neutral 40, unknown 0
- magnitude 상위 5개:
  - 069500.KS: direction=positive, magnitude=0.998237, sensitivity_level=high, evidence=corr_kospi200_60d_krw=0.998237
  - 114800.KS: direction=negative, magnitude=0.997793, sensitivity_level=high, evidence=corr_kospi200_60d_krw=-0.997793
  - 005930.KS: direction=positive, magnitude=0.942671, sensitivity_level=high, evidence=corr_kospi200_60d_krw=0.942671
  - 000660.KS: direction=positive, magnitude=0.933042, sensitivity_level=high, evidence=corr_kospi200_60d_krw=0.933042
  - 000270.KS: direction=positive, magnitude=0.779, sensitivity_level=high, evidence=corr_kospi200_60d_krw=0.779

## stress_response
- metric: `avg_stress_ret_krw`
- positive 의미: 위기구간에서 플러스 성과
- negative 의미: 위기구간에서 마이너스 성과
- direction count: positive 41, negative 52, neutral 57, unknown 0
- magnitude 상위 5개:
  - SOL-USD: direction=positive, magnitude=0.011753, sensitivity_level=high, evidence=avg_stress_ret_krw=0.011753
  - 035720.KS: direction=negative, magnitude=0.009532, sensitivity_level=high, evidence=avg_stress_ret_krw=-0.009532
  - 003670.KS: direction=negative, magnitude=0.009102, sensitivity_level=high, evidence=avg_stress_ret_krw=-0.009102
  - BNB-USD: direction=positive, magnitude=0.008047, sensitivity_level=high, evidence=avg_stress_ret_krw=0.008047
  - 006400.KS: direction=negative, magnitude=0.007502, sensitivity_level=high, evidence=avg_stress_ret_krw=-0.007502

