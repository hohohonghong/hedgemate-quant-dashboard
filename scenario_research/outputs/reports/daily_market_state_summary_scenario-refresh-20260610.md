# Daily Market State Summary

- 기준일: `2026-06-09`
- 상태 분포: STRESS 4 / ACTIVE 0 / WATCH 3 / OFF 3
- contract note: this scenario vector is diagnostic-only market-state evidence, not a buy/sell, hedge, or portfolio recommendation.
- 해석 범위: Phase 4 정형 데이터 기반 설명 요약입니다. 포트폴리오 자동 변경 신호가 아니라 시장 상태 해석 보조 신호입니다.
- confidence 읽는 법: 현재 값은 데이터 coverage와 신호 breadth 기반의 임시 confidence proxy입니다. 뉴스/정책문 병합 confidence는 Phase 6 범위입니다.

## 팩터 압축 요약
- 추가 지표는 개별 신호를 그대로 나열하지 않고 8개 팩터로 압축해 시나리오 판단을 보조합니다.
- `USD / KRW Pressure` — 리스크 팩터, ELEVATED (score=85.86, confidence=70.58, coverage=0.85)
  - 해석: 달러 강세와 원화 약세가 한국 투자자 관점의 리스크로 작동하는지 봅니다.
- `Defensive Rotation` — 리스크 팩터, ELEVATED (score=70.90, confidence=67.88, coverage=1.00)
  - 해석: 방어 섹터 상대강도와 소형주/breadth 약세로 방어적 회전을 확인합니다.
- `Credit Stress` — 리스크 팩터, ELEVATED (score=69.88, confidence=63.86, coverage=1.00)
  - 해석: 하이일드·투자등급 신용자산과 변동성으로 스트레스 확산 여부를 봅니다.
- `Rates Pressure` — 리스크 팩터, NEUTRAL (score=64.53, confidence=57.44, coverage=1.00)
  - 해석: 장기채·중기채 가격 하락과 장단기 구간 부담을 통해 금리 압박을 봅니다.

## 전체 시나리오 스냅샷
- 모든 시나리오의 최신 상태와 대표 driver를 함께 표시합니다.
- `usd_strength_krw_weakness` USD Strength / KRW Weakness · 달러강세/원화약세장: STRESS, score=87.60, confidence=77.72, coverage=0.91
  - supporting: USD/KRW level (+0.2919, z=+1.95) | FXI 20d return (+0.1454, z=-1.94) | USD/KRW 20d return (+0.1144, z=+0.91)
  - offsetting: -
- `china_trade_fragmentation_shock` China / Trade Fragmentation Shock · 중국·무역분절 충격장: STRESS, score=81.56, confidence=71.38, coverage=0.92
  - supporting: FXI 20d return (+0.2908, z=-1.94) | EWY 20d return (+0.1030, z=-1.37) | FXI minus SPY 20d return (+0.0810, z=-1.62)
  - offsetting: -
- `acute_global_stress_liquidity_crunch` Acute Global Stress / Liquidity Crunch · 급성 리스크오프/유동성 경색장: STRESS, score=71.08, confidence=76.13, coverage=1.00
  - supporting: SPY 5d return (+0.2000, z=-2.19) | QQQ 5d return (+0.1500, z=-2.61)
  - offsetting: GLD 5d return (-0.0801, z=-1.60)
- `higher_for_longer_long_rate_shock` Higher-for-Longer / Long-Rate Shock · 장기금리 부담장: STRESS, score=68.44, confidence=62.13, coverage=1.00
  - supporting: UUP 20d return (+0.1129, z=+1.50) | HYG 20d return (+0.0882, z=-1.18) | QQQ 20d return (+0.0760, z=-0.76)
  - offsetting: -
- `semiconductor_ai_cycle_shock` Semiconductor / AI Cycle Shock · AI·반도체 사이클 충격장: WATCH, score=58.25, confidence=48.52, coverage=0.90
  - supporting: AI leaders basket 20d return (+0.0765, z=-1.02) | USD/KRW 20d return (+0.0457, z=+0.91) | SOXX 20d return (+0.0356, z=-0.28)
  - offsetting: -
- `korea_domestic_financial_stress` Korea Domestic Financial Stress · 한국 내수 금융스트레스장: WATCH, score=48.28, confidence=68.48, coverage=0.90
  - supporting: Korea construction basket 20d return (+0.1417, z=-1.89)
  - offsetting: Korea AA- 3Y credit spread (-0.1404, z=-1.40) | Korea CP-CD 91D spread (-0.0754, z=-1.51)
- `geopolitical_escalation_supply_shock` Geopolitical Escalation / Supply Shock · 지정학 확전·공급충격장: WATCH, score=44.53, confidence=69.06, coverage=0.95
  - supporting: SPY 5d return (+0.1000, z=-2.19)
  - offsetting: GLD 5d return (-0.1202, z=-1.60) | DBC 20d return (-0.0979, z=-1.96)
- `slowdown_recession_deflation_risk` Slowdown / Recession / Deflation Risk · 경기둔화/침체 우려장: OFF, score=32.76, confidence=72.59, coverage=1.00
  - supporting: -
  - offsetting: SPY 60d return (-0.1531, z=+1.02) | GLD 20d return (-0.1500, z=-2.00) | QQQ 60d return (-0.1050, z=+1.40)
- `stagflation_reinflation_energy_shock` Stagflation / Reinflation / Energy Shock · 물가·에너지 재상승장: OFF, score=31.46, confidence=72.54, coverage=1.00
  - supporting: -
  - offsetting: DBC 20d return (-0.1957, z=-1.96) | TIP 20d return (-0.1500, z=-2.79) | USO 20d return (-0.1303, z=-0.87)
- `soft_landing_goldilocks` Soft Landing / Goldilocks · 우호적 위험선호장: OFF, score=28.79, confidence=65.46, coverage=1.00
  - supporting: -
  - offsetting: UUP 20d return (-0.1129, z=+1.50) | SPY 20d return (-0.1108, z=-0.74) | QQQ 20d return (-0.0950, z=-0.76)

## 1. USD Strength / KRW Weakness · 달러강세/원화약세장
- 관점 lens: `fx_krw` (관련: `korea_market`)
- 상태 해석: `STRESS` (raw: `STRESS`) — 강한 스트레스 구간입니다. 단기 리스크 해석을 보수적으로 봐야 합니다.
- 수치: score=87.60 | confidence=77.72(높음) | coverage=0.91(충분)
- 장세 설명: 달러가 강하고 원화가 약해져 KRW 기준 투자자의 환율 리스크가 커지는 장세입니다. 한국 자산과 USD 노출의 역할을 분리해 봅니다.
- 사용자 관점: KRW 기준 투자자는 환율 노출과 USD 방어력을 함께 점검해야 합니다.
- 주요 지지 근거:
  - `USD/KRW level` — 지지 (contribution=+0.2919, normalized=+1.9462)
  - `FXI 20d return` — 지지 (contribution=+0.1454, normalized=-1.9385)
  - `USD/KRW 20d return` — 지지 (contribution=+0.1144, normalized=+0.9148)
- 반대/완화 근거:
  - 상위 영향 지표 기준 뚜렷한 반대 신호는 제한적입니다.
- 주의점: 현재 정형 proxy 기준으로 큰 결측 caveat는 없습니다.

## 2. China / Trade Fragmentation Shock · 중국·무역분절 충격장
- 관점 lens: `china_asia` (관련: `korea_market|korea_semiconductor|fx_krw`)
- 상태 해석: `STRESS` (raw: `STRESS`) — 강한 스트레스 구간입니다. 단기 리스크 해석을 보수적으로 봐야 합니다.
- 수치: score=81.56 | confidence=71.38(높음) | coverage=0.92(충분)
- 장세 설명: 중국 경기·무역갈등·공급망 충격이 한국/아시아와 반도체 자산에 번지는 장세입니다. 한국 반도체 factor와 원화 약세를 함께 확인합니다.
- 사용자 관점: 중국·무역·반도체 경로가 한국/아시아 자산에 주는 영향을 확인해야 합니다.
- 주요 지지 근거:
  - `FXI 20d return` — 지지 (contribution=+0.2908, normalized=-1.9385)
  - `EWY 20d return` — 지지 (contribution=+0.1030, normalized=-1.3740)
  - `FXI minus SPY 20d return` — 지지 (contribution=+0.0810, normalized=-1.6206)
- 반대/완화 근거:
  - 상위 영향 지표 기준 뚜렷한 반대 신호는 제한적입니다.
- 주의점: 현재 정형 proxy 기준으로 큰 결측 caveat는 없습니다.

## 3. Acute Global Stress / Liquidity Crunch · 급성 리스크오프/유동성 경색장
- 관점 lens: `us_global` (관련: `korea_market|fx_krw`)
- 상태 해석: `STRESS` (raw: `STRESS`) — 강한 스트레스 구간입니다. 단기 리스크 해석을 보수적으로 봐야 합니다.
- 수치: score=71.08 | confidence=76.13(높음) | coverage=1.00(충분)
- 장세 설명: 변동성이 튀고 위험자산이 동반 약세를 보이는 단기 스트레스 장세입니다. 상관관계 상승과 유동성 악화를 우선 점검합니다.
- 사용자 관점: 상관관계가 급격히 높아질 수 있어 분산효과와 유동성 리스크를 함께 봐야 합니다.
- 주요 지지 근거:
  - `SPY 5d return` — 지지 (contribution=+0.2000, normalized=-2.1910)
  - `QQQ 5d return` — 지지 (contribution=+0.1500, normalized=-2.6082)
- 반대/완화 근거:
  - `GLD 5d return` — 완화/반대 (contribution=-0.0801, normalized=-1.6022)
- 주의점: 현재 정형 proxy 기준으로 큰 결측 caveat는 없습니다.

## 데이터 커버리지 메모
- quality status: `DEGRADED`
- 정렬 기준일: `2026-06-09`
- anchor coverage: 43/44 (97.7%)
- expected/loaded tickers: 44/44
- 70개 자산 breadth 원천 ticker 수: 150
- synthetic breadth latest: `__BREADTH_ALL_20D_POSITIVE__=42.0%, __BREADTH_ALL_60D_POSITIVE__=61.3%, __BREADTH_ALL_ABOVE_200D__=65.3%, __BREADTH_US_STOCK_20D_POSITIVE__=57.5%, __BREADTH_KR_STOCK_20D_POSITIVE__=45.0%`
- synthetic basket latest: `AI_BASKET=13985.08 (AMD|AVGO|GOOGL|MSFT|NVDA), KR_SEMIS_BASKET=7605.78 (000660.KS|005930.KS), KR_FINANCIAL_BASKET=536.00 (032830.KS|055550.KS|105560.KS), KR_CONSTRUCTION_BASKET=177.60 (000720.KS|006360.KS|047040.KS)`
- low-frequency indicators forward-filled: `KR_CREDIT_SPREAD_AA3Y_GOV3Y:last=2026-04-30, stale=40d, source_quality=seed, KR_CP_CD_SPREAD_91D:last=2026-04-30, stale=40d, source_quality=seed, KR_HOUSEHOLD_LOAN_YOY:last=2026-04-30, stale=40d, source_quality=seed, GEOPOLITICAL_EVENT_OVERLAY:last=2026-05-11, stale=29d, source_quality=manual`
- low-frequency/event sources: `C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\scenario_research\inputs\market_state_external_indicators.csv, C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\scenario_research\outputs\events\event_overlay_daily_event-refresh-20260528.csv, C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\scenario_research\outputs\events\event_overlay_daily_event-refresh-20260605.csv`
- anchor date에 없어 제외된 ticker: `^KS200`
- anchor gap 보정 ticker: `KRW=X:2026-06-09<=2026-06-08`
- anchor date보다 최신 관측치가 별도로 있는 ticker: `KRW=X:2026-06-10, ^KS200:2026-06-10`
- 이 summary는 데이터 coverage가 낮거나 특정 핵심 ticker가 빠진 경우 보수적으로 해석해야 합니다.
