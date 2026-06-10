# Hedge Action Plan

- run_id: 20260610T191953943306-da0898b3
- engine_version: hedge_action_engine_v1
- formal gate: 기존 PASS_RECOMMEND 기준을 완화하지 않음

## Portfolio
- NVDA: 27.565907067389254%
- 005930.KS: 39.43957481031034%
- 035420.KS: 19.73065230179713%
- 035720.KS: 13.263865820503268%

## Status Counts
- FAIL_ACTION: 8
- RESEARCH_ONLY: 5
- REVIEW_ACTION: 55

## Top Vulnerabilities
- 지정학·공급망 충격 (geopolitical_supply_chain): net=0.90112533, sources=005930.KS, NVDA, 035420.KS, offsets=-
- 장기금리·성장주 듀레이션 (rate_shock_growth_duration): net=0.69986662, sources=NVDA, 005930.KS, 035420.KS, offsets=-
- 침체·유동성 스트레스 (recession_liquidity_stress): net=0.53266093, sources=NVDA, 005930.KS, 035420.KS, offsets=-
- 달러강세·원화약세 (usdkrw_fx_korea): net=0.49431165, sources=005930.KS, 035420.KS, 035720.KS, offsets=-
- AI·반도체 사이클 (semiconductor_ai_cycle): net=0.34163828, sources=005930.KS, NVDA, 035420.KS, offsets=-
- 한국 내수·신용 스트레스 (korea_domestic_credit): net=0.27126628, sources=005930.KS, 035420.KS, 035720.KS, offsets=NVDA
- 물가·에너지 재상승 (inflation_energy_shock): net=0, sources=-, offsets=-

## Selected Actions
- REVIEW_ACTION · TRIM_AND_HEDGE · geopolitical_supply_chain: 132030.KS / delta=-0.04132614 / turnover=10.0% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0413 감소; CVaR 0.11%p 개선; MDD 0.66%p 개선; stress 0.04%p 개선; Sharpe 0.09 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · rate_shock_growth_duration: 153130.KS + 017670.KS / delta=-0.07087905 / turnover=10.000001% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0709 감소; CVaR 0.15%p 개선; MDD 2.33%p 개선; stress 0.00%p 개선; Sharpe 0.17 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: bootstrap_not_robust|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · recession_liquidity_stress: 114800.KS + 000270.KS / delta=-0.06305987 / turnover=10.000001% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0631 감소; CVaR 0.19%p 개선; MDD 2.88%p 개선; stress 0.02%p 개선; Sharpe 0.19 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: bootstrap_not_robust|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · usdkrw_fx_korea: 055550.KS / delta=-0.00695506 / turnover=10.0% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0070 감소; CVaR 0.12%p 개선; MDD 0.89%p 개선; stress 0.01%p 개선; Sharpe 0.03 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|cash_bootstrap_not_robust|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · semiconductor_ai_cycle: 153130.KS + 105560.KS / delta=-0.02196321 / turnover=10.0% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0220 감소; CVaR 0.12%p 개선; MDD 0.88%p 개선; stress 0.04%p 개선; Sharpe 0.08 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · korea_domestic_credit: 017670.KS / delta=-0.01736422 / turnover=10.0% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0174 감소; CVaR 0.13%p 개선; MDD 0.12%p 개선; stress 0.03%p 개선; Sharpe 0.01 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · recession_liquidity_stress: 261240.KS + 017670.KS / delta=-0.05770771 / turnover=10.000001% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0577 감소; CVaR 0.16%p 개선; MDD 2.60%p 개선; stress 0.00%p 개선; Sharpe 0.16 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: bootstrap_not_robust|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · recession_liquidity_stress: 132030.KS + 017670.KS / delta=-0.05758812 / turnover=10.000001% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0576 감소; CVaR 0.12%p 개선; MDD 2.16%p 개선; stress 0.00%p 개선; Sharpe 0.17 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: bootstrap_not_robust|cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · recession_liquidity_stress: 153130.KS / delta=-0.05188967 / turnover=10.000001% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0519 감소; CVaR 0.16%p 개선; MDD 2.66%p 개선; stress 0.01%p 개선; Sharpe 0.18 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: bootstrap_not_robust|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: 000270.KS / delta=-0.05009729 / turnover=18.1986% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0501 감소; CVaR 0.19%p 개선; MDD 2.63%p 개선; stress 0.03%p 개선; Sharpe 0.00 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge

## Action Type Coverage
- ADD_HEDGE: present, selected, count=13, selected=1 · 기존 보유자산을 유지하면서 헷지를 더하는 후보입니다.
- TRIM_AND_HEDGE: present, selected, count=49, selected=9 · 취약성 원인 보유자산을 일부 줄이고 헷지를 더하는 후보입니다.
- DE_RISK_CASH: present, not selected, count=5, selected=0 · 취약 자산을 줄이고 같은 비중을 cash bucket에 둔 대안입니다.
  - not_selected_reason: 후보는 있었지만 selected action plan은 top vulnerability 다양성과 개선도 순서를 우선해 다른 액션을 선택했습니다.
- REPLACE_SLEEVE: present, not selected, count=1, selected=0 · 위험 sleeve 일부를 방어 proxy로 바꾸는 후보입니다.
  - not_selected_reason: 후보는 있었지만 selected action plan은 top vulnerability 다양성과 개선도 순서를 우선해 다른 액션을 선택했습니다.
- NO_ACTION: absent, not selected, count=0, selected=0 · 모든 취약 sleeve에서 최소 하나 이상의 bounded action 후보가 생성되어 NO_ACTION row가 필요하지 않았습니다.
  - not_selected_reason: 모든 취약 sleeve에서 최소 하나 이상의 bounded action 후보가 생성되어 NO_ACTION row가 필요하지 않았습니다.

## Next Validation Needed
- REVIEW_ACTION을 FORMAL_ACTION으로 올리려면 기존 formal recommendation gate, stress/backtest 근거, CVaR/MDD 안정성, 거래 제약 검증이 모두 충족되어야 합니다.
- FORMAL_ACTION이 없을 때는 실행 추천이 아니라 실행 전 검토용 시뮬레이션으로만 해석해야 합니다.
