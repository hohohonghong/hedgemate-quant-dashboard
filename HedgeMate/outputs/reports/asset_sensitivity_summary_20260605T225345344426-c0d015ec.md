# HedgeMate 자산 민감도 요약

- run_id: 20260605T225345344426-c0d015ec
- data_version: 20260605
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
- direction count: positive 119, negative 4, neutral 27, unknown 0
- magnitude 상위 5개:
  - SOL-USD: direction=positive, magnitude=1.643201, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.643201
  - MS: direction=positive, magnitude=1.549904, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.549904
  - BAC: direction=positive, magnitude=1.456622, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.456622
  - MU: direction=positive, magnitude=1.451785, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.451785
  - NVDA: direction=positive, magnitude=1.441192, sensitivity_level=high, evidence=beta_sp500_1y_krw=1.441192

## downside_beta_sp500
- metric: `downside_beta_sp500_1y_krw`
- positive 의미: 미국 증시 하락일에 함께 하락
- negative 의미: 미국 증시 하락일에 반대로 움직임
- direction count: positive 126, negative 6, neutral 18, unknown 0
- magnitude 상위 5개:
  - SOL-USD: direction=positive, magnitude=1.573198, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.573198
  - MS: direction=positive, magnitude=1.548153, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.548153
  - TSLA: direction=positive, magnitude=1.484307, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.484307
  - BAC: direction=positive, magnitude=1.47999, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.47999
  - AMD: direction=positive, magnitude=1.404009, sensitivity_level=high, evidence=downside_beta_sp500_1y_krw=1.404009

## corr_sp500_60d
- metric: `corr_sp500_60d_krw`
- positive 의미: SPY와 같은 방향
- negative 의미: SPY와 반대 방향
- direction count: positive 115, negative 16, neutral 19, unknown 0
- magnitude 상위 5개:
  - SPY: direction=positive, magnitude=1.0, sensitivity_level=high, evidence=corr_sp500_60d_krw=1.0
  - VTI: direction=positive, magnitude=0.99764, sensitivity_level=high, evidence=corr_sp500_60d_krw=0.99764
  - QUAL: direction=positive, magnitude=0.97574, sensitivity_level=high, evidence=corr_sp500_60d_krw=0.97574
  - IWF: direction=positive, magnitude=0.962082, sensitivity_level=high, evidence=corr_sp500_60d_krw=0.962082
  - VUG: direction=positive, magnitude=0.956005, sensitivity_level=high, evidence=corr_sp500_60d_krw=0.956005

## corr_kospi200_60d
- metric: `corr_kospi200_60d_krw`
- positive 의미: KOSPI200과 같은 방향
- negative 의미: KOSPI200과 반대 방향
- direction count: positive 43, negative 67, neutral 40, unknown 0
- magnitude 상위 5개:
  - 069500.KS: direction=positive, magnitude=0.998283, sensitivity_level=high, evidence=corr_kospi200_60d_krw=0.998283
  - 114800.KS: direction=negative, magnitude=0.997644, sensitivity_level=high, evidence=corr_kospi200_60d_krw=-0.997644
  - 005930.KS: direction=positive, magnitude=0.940514, sensitivity_level=high, evidence=corr_kospi200_60d_krw=0.940514
  - 000660.KS: direction=positive, magnitude=0.93734, sensitivity_level=high, evidence=corr_kospi200_60d_krw=0.93734
  - 000270.KS: direction=positive, magnitude=0.798984, sensitivity_level=high, evidence=corr_kospi200_60d_krw=0.798984

## stress_response
- metric: `avg_stress_ret_krw`
- positive 의미: 위기구간에서 플러스 성과
- negative 의미: 위기구간에서 마이너스 성과
- direction count: positive 21, negative 102, neutral 27, unknown 0
- magnitude 상위 5개:
  - SOL-USD: direction=positive, magnitude=0.011753, sensitivity_level=high, evidence=avg_stress_ret_krw=0.011753
  - 000660.KS: direction=negative, magnitude=0.01021, sensitivity_level=high, evidence=avg_stress_ret_krw=-0.01021
  - 034020.KS: direction=negative, magnitude=0.008922, sensitivity_level=high, evidence=avg_stress_ret_krw=-0.008922
  - BNB-USD: direction=positive, magnitude=0.008653, sensitivity_level=high, evidence=avg_stress_ret_krw=0.008653
  - ETH-USD: direction=positive, magnitude=0.00827, sensitivity_level=high, evidence=avg_stress_ret_krw=0.00827

