# HedgeMate 시나리오 민감도 요약

- run_id: 20260610T191953943306-da0898b3
- data_version: 20260610
- scenario_vector: `C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\scenario_research\outputs\scenario_vectors\current_scenario_vector_final-refresh-20260610.csv`
- as_of_date: 2026-06-09
- selected_by: explicit_path
- scenario_vector_candidates: 1
- 해석: 현재 장세: 달러강세/원화약세장(STRESS, fx_krw, score=87.602036) / 중국·무역분절 충격장(STRESS, china_asia, score=81.561023) / 급성 리스크오프/유동성 경색장(STRESS, us_global, score=71.081278)
- row_count: 1500

## Lens 분포
- china_asia: 150
- fx_krw: 150
- geopolitical: 150
- korea_market: 150
- korea_semiconductor: 150
- us_global: 750

## Scenario 분포
- acute_global_stress_liquidity_crunch: 150
- china_trade_fragmentation_shock: 150
- geopolitical_escalation_supply_shock: 150
- higher_for_longer_long_rate_shock: 150
- korea_domestic_financial_stress: 150
- semiconductor_ai_cycle_shock: 150
- slowdown_recession_deflation_risk: 150
- soft_landing_goldilocks: 150
- stagflation_reinflation_energy_shock: 150
- usd_strength_krw_weakness: 150

## v2 Evidence 분포
- sensitivity_version: v3
- gate_eligible rows: 600
- method `rolling_beta`: 1500
- evidence_quality `high`: 1050
- evidence_quality `medium`: 450
- source_quality `manual`: 150
- source_quality `market`: 1200
- source_quality `seed`: 150

## Active adverse scenario
- 달러강세/원화약세장
- 중국·무역분절 충격장
- 급성 리스크오프/유동성 경색장
- 장기금리 부담장
- AI·반도체 사이클 충격장
- 한국 내수 금융스트레스장
- 지정학 확전·공급충격장

## Trade-gated adverse scenario
- 달러강세/원화약세장
- 중국·무역분절 충격장
- 급성 리스크오프/유동성 경색장
- 장기금리 부담장

## 주의
- 현재 민감도 v2는 가격 기반 beta/stress feature와 구조 태그를 결합합니다.
- positive scenario_beta는 해당 시나리오 활성 시 취약도가 커지는 방향, negative는 방어/상쇄 가능성을 의미합니다.
- WATCH/manual/seed 시나리오는 기본적으로 context로만 표시하며 trade gate에는 사용하지 않습니다.
