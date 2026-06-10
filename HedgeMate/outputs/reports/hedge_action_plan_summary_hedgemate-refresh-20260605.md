# Hedge Action Plan

- run_id: hedgemate-refresh-20260605
- engine_version: hedge_action_engine_v1
- formal gate: 기존 PASS_RECOMMEND 기준을 완화하지 않음

## Portfolio
- NVDA: 28.233958800872923%
- 005930.KS: 39.879812648789034%
- 035420.KS: 17.84183830186088%
- 035720.KS: 14.044390248477157%

## Status Counts
- FAIL_ACTION: 30
- REVIEW_ACTION: 18

## Top Vulnerabilities
- 지정학·공급망 충격 (geopolitical_supply_chain): net=0.6837991, sources=005930.KS, NVDA, 035720.KS, offsets=-
- 장기금리·성장주 듀레이션 (rate_shock_growth_duration): net=0.51671815, sources=NVDA, 005930.KS, 035420.KS, offsets=-
- 달러강세·원화약세 (usdkrw_fx_korea): net=0.47020644, sources=005930.KS, 035420.KS, 035720.KS, offsets=-
- 침체·유동성 스트레스 (recession_liquidity_stress): net=0.19094217, sources=NVDA, 005930.KS, 035720.KS, offsets=-
- AI·반도체 사이클 (semiconductor_ai_cycle): net=0, sources=-, offsets=-
- 물가·에너지 재상승 (inflation_energy_shock): net=0, sources=-, offsets=-
- 한국 내수·신용 스트레스 (korea_domestic_credit): net=0, sources=-, offsets=-

## Selected Actions
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: IAU / delta=-0.09729892 / turnover=19.9999% / reason=trim 가능한 source holding이 제한적이어서 ADD_HEDGE를 선택했습니다.
  - expected_effect: 취약성 0.0973 감소; CVaR 0.31%p 개선; MDD 4.38%p 개선; stress 0.04%p 개선; Sharpe 0.07 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · TRIM_AND_HEDGE · rate_shock_growth_duration: FXY / delta=-0.05733506 / turnover=10.000001% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0573 감소; CVaR 0.23%p 개선; MDD 2.22%p 개선; stress 0.00%p 개선; Sharpe 0.02 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · ADD_HEDGE · usdkrw_fx_korea: GLD / delta=-0.07540848 / turnover=19.9999% / reason=trim 가능한 source holding이 제한적이어서 ADD_HEDGE를 선택했습니다.
  - expected_effect: 취약성 0.0754 감소; CVaR 0.31%p 개선; MDD 4.37%p 개선; stress 0.04%p 개선; Sharpe 0.06 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · TRIM_AND_HEDGE · recession_liquidity_stress: SH / delta=-0.02658762 / turnover=10.000001% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0266 감소; CVaR 0.28%p 개선; MDD 3.67%p 개선; stress 0.01%p 개선; Sharpe 0.04 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · ADD_HEDGE · usdkrw_fx_korea: FXE / delta=-0.07472834 / turnover=19.9999% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0747 감소; CVaR 0.32%p 개선; MDD 3.78%p 개선; stress 0.03%p 개선; Sharpe 0.00 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: EWJ / delta=-0.06601866 / turnover=19.9999% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0660 감소; CVaR 0.20%p 개선; MDD 2.60%p 개선; stress 0.03%p 개선; Sharpe 0.01 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: FXI / delta=-0.06531402 / turnover=19.9999% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0653 감소; CVaR 0.12%p 개선; MDD 1.42%p 개선; stress 0.04%p 개선; Sharpe 0.04 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: XLP / delta=-0.06338873 / turnover=19.9999% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0634 감소; CVaR 0.28%p 개선; MDD 4.23%p 개선; stress 0.03%p 개선; Sharpe 0.05 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · recession_liquidity_stress: 017670.KS / delta=-0.02903126 / turnover=19.9999% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0290 감소; CVaR 0.24%p 개선; MDD 2.63%p 개선; stress 0.02%p 개선; Sharpe 0.03 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|cash_bootstrap_not_robust|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · usdkrw_fx_korea: FXF / delta=-0.07670393 / turnover=19.9999% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0767 감소; CVaR 0.33%p 개선; MDD 4.33%p 개선; stress 0.03%p 개선; Sharpe 0.02 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge

## Action Type Coverage
- ADD_HEDGE: present, selected, count=35, selected=8 · 기존 보유자산을 유지하면서 헷지를 더하는 후보입니다.
- TRIM_AND_HEDGE: present, selected, count=11, selected=2 · 취약성 원인 보유자산을 일부 줄이고 헷지를 더하는 후보입니다.
- DE_RISK_CASH: absent, not selected, count=0, selected=0 · cash가 hedge보다 낫고 trim 자체가 비용 차감 후 위험을 낮춘다는 근거가 없어 formal cash 후보가 없습니다.
  - not_selected_reason: cash가 hedge보다 낫고 trim 자체가 비용 차감 후 위험을 낮춘다는 근거가 없어 formal cash 후보가 없습니다.
- REPLACE_SLEEVE: present, not selected, count=2, selected=0 · 위험 sleeve 일부를 방어 proxy로 바꾸는 후보입니다.
  - not_selected_reason: 후보는 있었지만 selected action plan은 top vulnerability 다양성과 개선도 순서를 우선해 다른 액션을 선택했습니다.
- NO_ACTION: absent, not selected, count=0, selected=0 · 모든 취약 sleeve에서 최소 하나 이상의 bounded action 후보가 생성되어 NO_ACTION row가 필요하지 않았습니다.
  - not_selected_reason: 모든 취약 sleeve에서 최소 하나 이상의 bounded action 후보가 생성되어 NO_ACTION row가 필요하지 않았습니다.

## Next Validation Needed
- REVIEW_ACTION을 FORMAL_ACTION으로 올리려면 기존 formal recommendation gate, stress/backtest 근거, CVaR/MDD 안정성, 거래 제약 검증이 모두 충족되어야 합니다.
- FORMAL_ACTION이 없을 때는 실행 추천이 아니라 실행 전 검토용 시뮬레이션으로만 해석해야 합니다.
