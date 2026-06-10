# Daily Market State Summary

- 기준일: `2026-06-04`
- 상태 분포: STRESS 1 / ACTIVE 2 / WATCH 2 / OFF 5
- contract note: this scenario vector is diagnostic-only market-state evidence, not a buy/sell, hedge, or portfolio recommendation.
- 해석 범위: Phase 4 정형 데이터 기반 설명 요약입니다. 포트폴리오 자동 변경 신호가 아니라 시장 상태 해석 보조 신호입니다.
- confidence 읽는 법: 현재 값은 데이터 coverage와 신호 breadth 기반의 임시 confidence proxy입니다. 뉴스/정책문 병합 confidence는 Phase 6 범위입니다.

## 팩터 압축 요약
- 추가 지표는 개별 신호를 그대로 나열하지 않고 8개 팩터로 압축해 시나리오 판단을 보조합니다.
- `USD / KRW Pressure` — 리스크 팩터, ELEVATED (score=73.14, confidence=85.32, coverage=1.00)
  - 해석: 달러 강세와 원화 약세가 한국 투자자 관점의 리스크로 작동하는지 봅니다.
- `Korea Market Health` — 우호 팩터, NEUTRAL (score=60.60, confidence=51.54, coverage=0.75)
  - 해석: 한국 지수·EWY·국내 종목 breadth가 글로벌 위험선호와 같이 개선되는지 봅니다.
- `Growth / Risk Appetite` — 우호 팩터, NEUTRAL (score=58.27, confidence=37.43, coverage=0.65)
  - 해석: 주식·신용·시장 breadth가 함께 좋아지는지 확인합니다.
- `Rates Pressure` — 리스크 팩터, NEUTRAL (score=54.74, confidence=54.50, coverage=1.00)
  - 해석: 장기채·중기채 가격 하락과 장단기 구간 부담을 통해 금리 압박을 봅니다.

## 전체 시나리오 스냅샷
- 모든 시나리오의 최신 상태와 대표 driver를 함께 표시합니다.
- `usd_strength_krw_weakness` USD Strength / KRW Weakness · 달러강세/원화약세장: STRESS, score=79.26, confidence=82.16, coverage=0.96
  - supporting: USD/KRW level (+0.3000, z=+2.05) | USD/KRW 20d return (+0.2500, z=+2.62) | FXI 20d return (+0.1108, z=-1.48)
  - offsetting: -
- `china_trade_fragmentation_shock` China / Trade Fragmentation Shock · 중국·무역분절 충격장: ACTIVE, score=64.60, confidence=73.22, coverage=0.92
  - supporting: FXI 20d return (+0.2216, z=-1.48) | USD/KRW 20d return (+0.1500, z=+2.62) | FXI minus SPY 20d return (+0.1000, z=-2.11)
  - offsetting: -
- `higher_for_longer_long_rate_shock` Higher-for-Longer / Long-Rate Shock · 장기금리 부담장: ACTIVE, score=61.07, confidence=60.33, coverage=1.00
  - supporting: USD/KRW 20d return (+0.1500, z=+2.62) | UUP 20d return (+0.0818, z=+1.09)
  - offsetting: QQQ 20d return (-0.0734, z=+0.73)
- `geopolitical_escalation_supply_shock` Geopolitical Escalation / Supply Shock · 지정학 확전·공급충격장: WATCH, score=51.07, confidence=55.20, coverage=0.95
  - supporting: USD/KRW 20d return (+0.1000, z=+2.62) | USO 5d return (+0.0471, z=+0.47)
  - offsetting: VIX level (-0.0616, z=-0.82)
- `acute_global_stress_liquidity_crunch` Acute Global Stress / Liquidity Crunch · 급성 리스크오프/유동성 경색장: WATCH, score=45.81, confidence=45.80, coverage=0.92
  - supporting: HYG 5d return (+0.0211, z=-0.28)
  - offsetting: VIX level (-0.1231, z=-0.82) | GLD 5d return (-0.0143, z=-0.29)
- `soft_landing_goldilocks` Soft Landing / Goldilocks · 우호적 위험선호장: OFF, score=44.39, confidence=55.28, coverage=0.87
  - supporting: QQQ 20d return (+0.0917, z=+0.73)
  - offsetting: USD/KRW 20d return (-0.1500, z=+2.62) | UUP 20d return (-0.0818, z=+1.09)
- `stagflation_reinflation_energy_shock` Stagflation / Reinflation / Energy Shock · 물가·에너지 재상승장: OFF, score=41.51, confidence=53.20, coverage=1.00
  - supporting: -
  - offsetting: DBC 20d return (-0.0903, z=-0.90) | USO 20d return (-0.0509, z=-0.34) | TIP 20d return (-0.0486, z=-0.65)
- `korea_domestic_financial_stress` Korea Domestic Financial Stress · 한국 내수 금융스트레스장: OFF, score=34.34, confidence=84.81, coverage=1.00
  - supporting: Korea construction basket 20d return (+0.1168, z=-1.56)
  - offsetting: Korea financials basket 20d return (-0.1738, z=+1.74) | Korea AA- 3Y credit spread (-0.1439, z=-1.44)
- `semiconductor_ai_cycle_shock` Semiconductor / AI Cycle Shock · AI·반도체 사이클 충격장: OFF, score=29.81, confidence=77.30, coverage=1.00
  - supporting: -
  - offsetting: Korea semis basket 20d return (-0.1500, z=+2.11) | SOXX 20d return (-0.1244, z=+1.00) | SOXX minus SPY 20d return (-0.1178, z=+1.18)
- `slowdown_recession_deflation_risk` Slowdown / Recession / Deflation Risk · 경기둔화/침체 우려장: OFF, score=25.45, confidence=66.21, coverage=0.92
  - supporting: -
  - offsetting: SPY 60d return (-0.1697, z=+1.13) | QQQ 60d return (-0.1318, z=+1.76) | TLT 60d return (-0.0991, z=-0.79)

## 1. USD Strength / KRW Weakness · 달러강세/원화약세장
- 관점 lens: `fx_krw` (관련: `korea_market`)
- 상태 해석: `STRESS` (raw: `STRESS`) — 강한 스트레스 구간입니다. 단기 리스크 해석을 보수적으로 봐야 합니다.
- 수치: score=79.26 | confidence=82.16(높음) | coverage=0.96(충분)
- 장세 설명: 달러가 강하고 원화가 약해져 KRW 기준 투자자의 환율 리스크가 커지는 장세입니다. 한국 자산과 USD 노출의 역할을 분리해 봅니다.
- 사용자 관점: KRW 기준 투자자는 환율 노출과 USD 방어력을 함께 점검해야 합니다.
- 주요 지지 근거:
  - `USD/KRW level` — 지지 (contribution=+0.3000, normalized=+2.0464)
  - `USD/KRW 20d return` — 지지 (contribution=+0.2500, normalized=+2.6155)
  - `FXI 20d return` — 지지 (contribution=+0.1108, normalized=-1.4771)
- 반대/완화 근거:
  - 상위 영향 지표 기준 뚜렷한 반대 신호는 제한적입니다.
- 주의점: 현재 정형 proxy 기준으로 큰 결측 caveat는 없습니다.

## 2. China / Trade Fragmentation Shock · 중국·무역분절 충격장
- 관점 lens: `china_asia` (관련: `korea_market|korea_semiconductor|fx_krw`)
- 상태 해석: `ACTIVE` (raw: `ACTIVE`) — 활성 구간입니다. 현재 시장을 설명하는 주요 상태로 볼 수 있습니다.
- 수치: score=64.60 | confidence=73.22(높음) | coverage=0.92(충분)
- 장세 설명: 중국 경기·무역갈등·공급망 충격이 한국/아시아와 반도체 자산에 번지는 장세입니다. 한국 반도체 factor와 원화 약세를 함께 확인합니다.
- 사용자 관점: 중국·무역·반도체 경로가 한국/아시아 자산에 주는 영향을 확인해야 합니다.
- 주요 지지 근거:
  - `FXI 20d return` — 지지 (contribution=+0.2216, normalized=-1.4771)
  - `USD/KRW 20d return` — 지지 (contribution=+0.1500, normalized=+2.6155)
  - `FXI minus SPY 20d return` — 지지 (contribution=+0.1000, normalized=-2.1126)
- 반대/완화 근거:
  - 상위 영향 지표 기준 뚜렷한 반대 신호는 제한적입니다.
- 주의점: 현재 정형 proxy 기준으로 큰 결측 caveat는 없습니다.

## 3. Higher-for-Longer / Long-Rate Shock · 장기금리 부담장
- 관점 lens: `us_global` (관련: `korea_semiconductor|fx_krw`)
- 상태 해석: `ACTIVE` (raw: `ACTIVE`) — 활성 구간입니다. 현재 시장을 설명하는 주요 상태로 볼 수 있습니다.
- 수치: score=61.07 | confidence=60.33(중간) | coverage=1.00(충분)
- 장세 설명: 장기금리와 달러 강세 부담이 채권·성장주·신용자산을 압박하는 장세입니다. 고밸류 성장주와 반도체 factor 민감도를 점검합니다.
- 사용자 관점: 장기채와 성장주처럼 금리에 민감한 자산의 해석을 보수적으로 봐야 합니다.
- 주요 지지 근거:
  - `USD/KRW 20d return` — 지지 (contribution=+0.1500, normalized=+2.6155)
  - `UUP 20d return` — 지지 (contribution=+0.0818, normalized=+1.0908)
- 반대/완화 근거:
  - `QQQ 20d return` — 완화/반대 (contribution=-0.0734, normalized=+0.7340)
- 주의점: 현재 정형 proxy 기준으로 큰 결측 caveat는 없습니다.

## 데이터 커버리지 메모
- quality status: `OK`
- 정렬 기준일: `2026-06-04`
- anchor coverage: 44/44 (100.0%)
- expected/loaded tickers: 44/44
- 70개 자산 breadth 원천 ticker 수: 0
- shared raw fallback 사용: `benchmark:fallback_prior, fx:fallback_prior`
- synthetic basket latest: `AI_BASKET=665.64 (AMD|AVGO|GOOGL|MSFT|NVDA), KR_SEMIS_BASKET=1051.64 (000660.KS|005930.KS), KR_FINANCIAL_BASKET=463.16 (032830.KS|055550.KS|105560.KS), KR_CONSTRUCTION_BASKET=199.93 (000720.KS|006360.KS|047040.KS)`
- low-frequency indicators forward-filled: `KR_CREDIT_SPREAD_AA3Y_GOV3Y:last=2026-04-30, stale=35d, source_quality=seed, KR_CP_CD_SPREAD_91D:last=2026-04-30, stale=35d, source_quality=seed, KR_HOUSEHOLD_LOAN_YOY:last=2026-04-30, stale=35d, source_quality=seed, GEOPOLITICAL_EVENT_OVERLAY:last=2026-05-11, stale=24d, source_quality=manual`
- low-frequency/event sources: `C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\scenario_research\inputs\market_state_external_indicators.csv, C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\scenario_research\outputs\events\event_overlay_daily_event-refresh-20260528.csv, C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\scenario_research\outputs\events\event_overlay_daily_event-refresh-20260605.csv`
- anchor gap 보정 ticker: `KRW=X:2026-06-04<=2026-06-03`
- anchor date보다 최신 관측치가 별도로 있는 ticker: `000660.KS:2026-06-05, 000720.KS:2026-06-05, 005930.KS:2026-06-05, 006360.KS:2026-06-05, 032830.KS:2026-06-05, 047040.KS:2026-06-05, 055550.KS:2026-06-05, 105560.KS:2026-06-05, KRW=X:2026-06-05, ^KS200:2026-06-05, ^VIX:2026-06-05`
- 이 summary는 데이터 coverage가 낮거나 특정 핵심 ticker가 빠진 경우 보수적으로 해석해야 합니다.
