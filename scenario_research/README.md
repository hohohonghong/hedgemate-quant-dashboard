# Scenario Research

이 폴더는 HedgeMate 본체 문서와 분리된 **시나리오 리서치 전용 작업공간**이다.

목적:
- 시장 시나리오 정의
- 시나리오별 데이터 소스 조사
- 정형/비정형 feature 설계
- 검증 계획 및 리서치 메모 축적
- HedgeMate 연결 전의 실험적 가설 관리

운영 원칙:
- 제품 확정 전 문서는 이 폴더에서 먼저 관리한다.
- HedgeMate 내부 문서에는 확정된 설계만 옮긴다.
- 시나리오 파일럿은 가능하면 `plans/` 아래에 버전 단위로 저장한다.
- 데이터 소스 표준, 이벤트 taxonomy, validation 결과는 추후 별도 문서로 분리한다.

권장 구조:
- `plans/`: 시나리오별 연구계획, 파일럿 설계, 로드맵
- `references/`: 데이터 소스 목록, 기사/정책문 출처 메모
- `validation/`: 백테스트 규칙, 라벨링 기준, 검증 로그
- `notes/`: 자유 메모, 아이디어 스케치

현재 시작 문서:
- `plans/01_pilot_usdkrw_research_plan_20260415.md`
- `plans/02_market_state_engine_phase_roadmap_20260415.docs`
- `plans/03_market_state_scenario_schema_v1_20260415.docs`
- `validation/01_historical_validation_cases_20260415.md`

Standalone runner:
- `scripts/run_market_state_pipeline.py`
- `scripts/market_state_engine.py`
- `scripts/generate_phase4_review_dashboard.py` — Phase 4 설명 레이어 검토용 HTML 대시보드
- `scripts/validate_phase4_outputs.py` — Phase 4 산출물 구조/범위/coverage 자동 검증
- `scripts/run_event_overlay_pipeline.py` — Phase 5 뉴스/정책 이벤트 오버레이 fixture 실행기
- `scripts/event_overlay_engine.py` — Phase 5 이벤트 구조화/집계/HTML 대시보드 엔진
- `scripts/run_final_market_state_pipeline.py` — Phase 6 정형 + 비정형 최종 병합 실행기
- `scripts/final_market_state_engine.py` — Phase 6 최종 점수/최종 confidence 병합 엔진
- `scripts/run_historical_validation.py` — 역사 케이스 기반 검증 로그 생성기
- `scripts/run_intraday_nowcast_pipeline.py` — 1시간봉 기반 한국장/원화/반도체 장중 nowcast 수집·요약
- `scripts/intraday_nowcast_engine.py` — intraday nowcast feature/vector 생성 엔진

Primary outputs:
- `outputs/raw/raw_market_state_daily_<data_version>.csv`
- `outputs/processed/scenario_state_daily_<run_id>.csv`
- `outputs/processed/market_factor_daily_<run_id>.csv`
- `outputs/reports/daily_market_state_summary_<run_id>.md`
- `outputs/reports/scenario_snapshot_metadata_<run_id>.json`
- `outputs/reports/phase4_review_dashboard_<run_id>.html`

Phase 5 event overlay outputs:
- `outputs/events/event_overlay_article_<run_id>.csv`
- `outputs/events/event_overlay_daily_<run_id>.csv`
- `outputs/reports/event_overlay_review_<run_id>.md`
- `outputs/reports/phase5_event_overlay_dashboard_<run_id>.html`

Phase 6 final merge outputs:
- `outputs/final/final_market_state_daily_<run_id>.csv`
- `outputs/final/scenario_confidence_<run_id>.csv`
- `outputs/final/top_active_scenarios_<run_id>.json`
- `outputs/reports/final_market_state_summary_<run_id>.md`

Historical validation outputs:
- `outputs/validation/historical_validation_cases_<run_id>.csv`
- `outputs/reports/historical_validation_review_<run_id>.md`

Intraday nowcast outputs:
- `outputs/raw/raw_intraday_market_state_1h_<data_version>.csv`
- `outputs/processed/intraday_ticker_feature_1h_<run_id>.csv`
- `outputs/processed/intraday_nowcast_signal_1h_<run_id>.csv`
- `outputs/nowcast_vectors/current_intraday_nowcast_1h_<run_id>.csv`
- `outputs/reports/intraday_nowcast_dashboard_1h_<run_id>.html`

Current Phase 4 signal shape:
- 장세분류는 기존 14개 proxy에서 **27개 시장 proxy + 70개 자산 breadth synthetic signal**로 확장했다.
- 추가 지표는 개별 항목을 모두 노출하지 않고 `Growth/Risk`, `Rates`, `Credit`, `Inflation/Commodity`, `USD/KRW`, `Korea`, `Global Breadth`, `Defensive Rotation`의 8개 팩터로 압축한다.
- 70개 자산 유니버스는 장세를 단독 결정하지 않고, 상승 확산도/추세 확산도/breadth로 시나리오 판단을 보조한다.
- FRED/BOK/KRX 같은 공식 데이터는 추후 API key/원천 파일이 확보되면 같은 팩터 레이어에 연결한다.

Intraday nowcast shape:
- 일봉 Phase 4는 **전일 확정 글로벌 장세**로 유지한다.
- 1시간봉 nowcast는 **오늘 한국장/원화/반도체 반응**을 `PROVISIONAL` 성격으로 빠르게 감지한다.
- 기본 티커는 `^KS200`, `005930.KS`, `000660.KS`, 주요 한국 대형주, `KRW=X`, `EWY`, `SOXX`, `QQQ`, `SPY`, `TLT`이다.
- 산출 nowcast는 `한국장 장중 위험선호`, `한국 반도체 장중 부담`, `원화약세 장중 압력`, `한국장 방어주 상대강세`, `글로벌 위험회피 한국 전이` 5개다.

Phase 5 event overlay shape:
- Phase 5는 뉴스/정책문을 시장 판단자로 쓰지 않고 **정형 Phase 4 점수의 보조 오버레이**로만 사용한다.
- 초기 입력은 `inputs/event_overlay_sample_20260507.csv` 같은 검토된 fixture로 시작한다.
- 기사 단위 `event_overlay_article`은 `event_type`, `region`, `direction`, `severity`, `novelty`, `scenario_links`, `evidence_span`, `extract_confidence`, `needs_review`를 가진다.
- 일별 `event_overlay_daily`는 scenario별 `event_overlay_score`, `overlay_confidence`, `event_count`, `evidence_summary`를 가진다.
- `evidence_span`이 없거나 추론만으로 연결된 이벤트는 `needs_review=Y`로 분리해 final score에 과신 반영하지 않는다.

Phase 6 final merge shape:
- Phase 6는 Phase 4 `structured_score/confidence`와 Phase 5 `event_overlay_score/overlay_confidence`를 날짜·시나리오 기준으로 병합한다.
- 기본 반영식은 `final_score = 0.85 * structured_score + 0.15 * event_overlay_score`다.
- 최종 산출물은 scenario별 `final_score`, `final_confidence`, `final_display_state`와 최신 기준 상위 활성 시나리오를 제공한다.
