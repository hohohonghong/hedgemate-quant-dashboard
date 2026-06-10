# Hedge Action Plan

- run_id: 20260605T225345344426-c0d015ec
- engine_version: hedge_action_engine_v1
- formal gate: 기존 PASS_RECOMMEND 기준을 완화하지 않음

## Portfolio
- NVDA: 26.544302163069656%
- 005930.KS: 39.83558998079684%
- 035420.KS: 20.62409977729198%
- 035720.KS: 12.996008078841523%

## Status Counts
- FAIL_ACTION: 27
- REVIEW_ACTION: 21

## Top Vulnerabilities
- 지정학·공급망 충격 (geopolitical_supply_chain): net=0.68085825, sources=005930.KS, NVDA, 035420.KS, offsets=-
- 장기금리·성장주 듀레이션 (rate_shock_growth_duration): net=0.50399944, sources=NVDA, 005930.KS, 035420.KS, offsets=-
- 달러강세·원화약세 (usdkrw_fx_korea): net=0.47941143, sources=005930.KS, 035420.KS, 035720.KS, offsets=-
- 침체·유동성 스트레스 (recession_liquidity_stress): net=0.18556805, sources=NVDA, 005930.KS, 035720.KS, offsets=-
- AI·반도체 사이클 (semiconductor_ai_cycle): net=0, sources=-, offsets=-
- 물가·에너지 재상승 (inflation_energy_shock): net=0, sources=-, offsets=-
- 한국 내수·신용 스트레스 (korea_domestic_credit): net=0, sources=-, offsets=-

## Selected Actions
- REVIEW_ACTION · TRIM_AND_HEDGE · geopolitical_supply_chain: IAU / delta=-0.06144688 / turnover=10.0% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0614 감소; CVaR 0.13%p 개선; MDD 0.96%p 개선; stress 0.02%p 개선; Sharpe 0.03 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · TRIM_AND_HEDGE · rate_shock_growth_duration: FXY / delta=-0.05733506 / turnover=10.0% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0573 감소; CVaR 0.22%p 개선; MDD 1.87%p 개선; stress 0.00%p 개선; Sharpe 0.02 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: bootstrap_not_robust|linked_formal_gate_blocked|linked_recommendation_not_formal
- REVIEW_ACTION · ADD_HEDGE · usdkrw_fx_korea: GLD / delta=-0.07095775 / turnover=18.592526% / reason=trim 가능한 source holding이 제한적이어서 ADD_HEDGE를 선택했습니다.
  - expected_effect: 취약성 0.0710 감소; CVaR 0.29%p 개선; MDD 3.74%p 개선; stress 0.03%p 개선; Sharpe 0.06 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · TRIM_AND_HEDGE · recession_liquidity_stress: 017670.KS / delta=-0.02351198 / turnover=10.0% / reason=취약성 기여가 큰 보유자산이 확인되어 단순 추가 헷지보다 TRIM_AND_HEDGE가 우선입니다.
  - expected_effect: 취약성 0.0235 감소; CVaR 0.15%p 개선; MDD 1.52%p 개선; stress 0.01%p 악화; Sharpe 0.02 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: bootstrap_not_robust|cash_baseline_lag|cash_bootstrap_not_robust|linked_formal_gate_blocked|linked_recommendation_not_formal|stress_after_cost_not_improved
- REVIEW_ACTION · ADD_HEDGE · usdkrw_fx_korea: FXE / delta=-0.05755243 / turnover=17.0112% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0576 감소; CVaR 0.28%p 개선; MDD 2.95%p 개선; stress 0.03%p 개선; Sharpe 0.00 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: EWJ / delta=-0.05665558 / turnover=17.0111% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0567 감소; CVaR 0.22%p 개선; MDD 2.34%p 개선; stress 0.03%p 개선; Sharpe 0.00 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: XLP / delta=-0.05559775 / turnover=17.0112% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0556 감소; CVaR 0.26%p 개선; MDD 3.19%p 개선; stress 0.03%p 개선; Sharpe 0.02 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: EFA / delta=-0.05355027 / turnover=17.0112% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0536 감소; CVaR 0.20%p 개선; MDD 2.31%p 개선; stress 0.03%p 개선; Sharpe 0.00 악화
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · ADD_HEDGE · geopolitical_supply_chain: XLU / delta=-0.05222372 / turnover=17.0111% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0522 감소; CVaR 0.23%p 개선; MDD 3.29%p 개선; stress 0.02%p 개선; Sharpe 0.03 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|not_trim_and_hedge
- REVIEW_ACTION · TRIM_AND_HEDGE · rate_shock_growth_duration: 068270.KS / delta=-0.03770623 / turnover=10.0% / reason=상위 sleeve 커버리지 이후 남은 후보 중 상태, 개선폭, turnover 기준으로 선택했습니다.
  - expected_effect: 취약성 0.0377 감소; CVaR 0.08%p 개선; MDD 1.84%p 개선; stress 0.01%p 악화; Sharpe 0.00 개선
  - formal_action_gap: FORMAL_ACTION excluded by action-level gate: bootstrap_not_robust|cash_baseline_lag|linked_formal_gate_blocked|linked_recommendation_not_formal|stress_after_cost_not_improved

## Action Type Coverage
- ADD_HEDGE: present, selected, count=27, selected=6 · 기존 보유자산을 유지하면서 헷지를 더하는 후보입니다.
- TRIM_AND_HEDGE: present, selected, count=21, selected=4 · 취약성 원인 보유자산을 일부 줄이고 헷지를 더하는 후보입니다.
- DE_RISK_CASH: absent, not selected, count=0, selected=0 · cash가 hedge보다 낫고 trim 자체가 비용 차감 후 위험을 낮춘다는 근거가 없어 formal cash 후보가 없습니다.
  - not_selected_reason: cash가 hedge보다 낫고 trim 자체가 비용 차감 후 위험을 낮춘다는 근거가 없어 formal cash 후보가 없습니다.
- REPLACE_SLEEVE: absent, not selected, count=0, selected=0 · 대체 proxy가 이미 보유 중이거나 해당 sleeve를 방어하지 않아 생성되지 않았습니다.
  - not_selected_reason: REPLACE_SLEEVE 후보가 없습니다. 대체 proxy가 이미 보유 중이거나, 해당 sleeve를 방어하지 못했거나, bounded turnover/집중도 제약 안에서 취약성을 줄이지 못했습니다.
- NO_ACTION: absent, not selected, count=0, selected=0 · 모든 취약 sleeve에서 최소 하나 이상의 bounded action 후보가 생성되어 NO_ACTION row가 필요하지 않았습니다.
  - not_selected_reason: 모든 취약 sleeve에서 최소 하나 이상의 bounded action 후보가 생성되어 NO_ACTION row가 필요하지 않았습니다.

## Next Validation Needed
- REVIEW_ACTION을 FORMAL_ACTION으로 올리려면 기존 formal recommendation gate, stress/backtest 근거, CVaR/MDD 안정성, 거래 제약 검증이 모두 충족되어야 합니다.
- FORMAL_ACTION이 없을 때는 실행 추천이 아니라 실행 전 검토용 시뮬레이션으로만 해석해야 합니다.
