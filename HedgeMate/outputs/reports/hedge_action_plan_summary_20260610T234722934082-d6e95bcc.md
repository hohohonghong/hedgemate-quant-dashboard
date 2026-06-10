# Hedge Action Plan

- run_id: 20260610T234722934082-d6e95bcc
- engine_version: hedge_action_engine_v1
- formal gate: 기존 PASS_RECOMMEND 기준을 완화하지 않음

## Portfolio
- AAPL: 38.29319923803064%
- MSFT: 21.354217722940945%
- GLD: 40.3525830390284%

## Status Counts
- FAIL_ACTION: 28
- RESEARCH_ONLY: 2
- REVIEW_ACTION: 3

## Top Vulnerabilities
- 장기금리·성장주 듀레이션 (rate_shock_growth_duration): net=0.59880825, sources=AAPL, MSFT, GLD, offsets=-
- 침체·유동성 스트레스 (recession_liquidity_stress): net=0.10671306, sources=AAPL, MSFT, offsets=GLD
- AI·반도체 사이클 (semiconductor_ai_cycle): net=0.04147699, sources=AAPL, MSFT, offsets=GLD
- 물가·에너지 재상승 (inflation_energy_shock): net=0, sources=-, offsets=-
- 지정학·공급망 충격 (geopolitical_supply_chain): net=-0.04408878, sources=AAPL, MSFT, offsets=GLD
- 달러강세·원화약세 (usdkrw_fx_korea): net=-0.15436597, sources=-, offsets=GLD, AAPL, MSFT
- 한국 내수·신용 스트레스 (korea_domestic_credit): net=-0.18685133, sources=-, offsets=GLD, AAPL, MSFT

## Selected Actions
- REVIEW_ACTION · DE_RISK_CASH · rate_shock_growth_duration: __CASH__ / delta=-0.05001347 / turnover=10.000001% / reason=hedge/cash 대안 비교에서 현금성 de-risk 후보만 selectable하여 선택했습니다.
  - expected_effect: 취약성 0.0500 감소; CVaR 0.16%p 개선; MDD 1.56%p 개선; stress 0.00%p 악화; Sharpe 0.00 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: stress_after_cost_not_improved
- REVIEW_ACTION · REPLACE_SLEEVE · semiconductor_ai_cycle: PSQ / delta=-0.01338792 / turnover=20.0% / reason=취약성 기여가 특정 sleeve에 강하게 집중되어 REPLACE_SLEEVE가 trim 대비 유사하거나 더 큰 개선을 보여 선택했습니다.
  - expected_effect: 취약성 0.0134 감소; CVaR 0.41%p 개선; MDD 4.52%p 개선; stress 0.00%p 악화; Sharpe 0.06 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: linked_recommendation_not_formal|not_trim_and_hedge|stress_after_cost_not_improved

## Action Type Coverage
- ADD_HEDGE: present, not selected, count=7, selected=0 · 기존 보유자산을 유지하면서 헷지를 더하는 후보입니다.
  - not_selected_reason: 후보는 있었지만 selected action plan은 top vulnerability 다양성과 개선도 순서를 우선해 다른 액션을 선택했습니다.
- TRIM_AND_HEDGE: present, not selected, count=23, selected=0 · 취약성 원인 보유자산을 일부 줄이고 헷지를 더하는 후보입니다.
  - not_selected_reason: 후보는 있었지만 selected action plan은 top vulnerability 다양성과 개선도 순서를 우선해 다른 액션을 선택했습니다.
- DE_RISK_CASH: present, selected, count=1, selected=1 · 취약 자산을 줄이고 같은 비중을 cash bucket에 둔 대안입니다.
- REPLACE_SLEEVE: present, selected, count=2, selected=1 · 위험 sleeve 일부를 방어 proxy로 바꾸는 후보입니다.
- NO_ACTION: absent, not selected, count=0, selected=0 · 모든 취약 sleeve에서 최소 하나 이상의 bounded action 후보가 생성되어 NO_ACTION row가 필요하지 않았습니다.
  - not_selected_reason: 모든 취약 sleeve에서 최소 하나 이상의 bounded action 후보가 생성되어 NO_ACTION row가 필요하지 않았습니다.

## Next Validation Needed
- REVIEW_ACTION을 FORMAL_ACTION으로 올리려면 기존 formal recommendation gate, stress/backtest 근거, CVaR/MDD 안정성, 거래 제약 검증이 모두 충족되어야 합니다.
- FORMAL_ACTION이 없을 때는 실행 추천이 아니라 실행 전 검토용 시뮬레이션으로만 해석해야 합니다.
