# Historical Validation Cases (2026-04-15)

## 1. 목적
이 문서는 `일별 시나리오 taxonomy`와 분리된 `역사적 검증 케이스 라이브러리`다.

여기서 정리하는 케이스는 매일 분류하는 시나리오가 아니라,
시나리오 엔진이 과거 주요 위기 구간을 얼마나 타당하게 포착하는지 검증하기 위한 기준 사례다.

즉, `GFC`, `COVID`, `러-우 전쟁`은 시나리오 이름이 아니라
`검증 케이스`로 관리한다.

---

## 2. 운영 원칙
- 역사적 검증 케이스는 시나리오 taxonomy에 직접 넣지 않는다.
- 각 케이스는 하나 이상의 시나리오와 매핑된다.
- 검증 목적은 `라벨 타당성`, `전환 속도`, `과민반응 여부` 확인이다.
- 기간은 연구 목적에 따라 세부 조정할 수 있으나, 기준 기간은 문서에 고정해 둔다.

---

## 3. 핵심 검증 케이스

| 케이스 | 기준 기간 | 주된 검증 시나리오 | 설명 |
| --- | --- | --- | --- |
| `GFC (글로벌 금융위기)` | `2007.10 ~ 2009.03` | `Acute Global Stress / Liquidity Crunch` | 전례 없는 유동성 경색과 광범위한 자산 동반 급락 구간 |
| `COVID / Pandemic Shock` | `2020.02.19 ~ 2020.04.15` | `Acute Global Stress / Liquidity Crunch` | 한 달 내 상관관계 급수렴이 나타난 단기·초고강도 위기 |
| `2022 Global Rate Shock` | `2021.11 ~ 2022.10` | `Higher-for-Longer / Long-Rate Shock` | 예상보다 강한 긴축과 장기금리 급등으로 채권·성장주 동반 압박 |
| `Russia-Ukraine / War-Energy Shock` | `2022.02 ~ 2022.10` | `Stagflation / Reinflation / Energy Shock` | 전쟁과 유가 급등이 결합된 스태그플레이션형 충격 |
| `China Slowdown / Property Stress` | `2023.01 ~ 2024.12` | `China / Trade Fragmentation Shock` | 중국 성장둔화와 부동산 스트레스가 아시아 자산에 전이된 구간 |

---

## 4. 팬데믹 계열 보조 케이스
팬데믹은 COVID만 고정하지 않고 보조 케이스를 추가할 수 있다.

| 케이스 | 성격 | 활용 목적 |
| --- | --- | --- |
| `MERS` | 한국 지역성 보건 충격 | 국내 자산과 KRW 민감도 확인 |
| `Influenza / Pandemic Scare` | 글로벌 위험회피 이벤트 | 단기 위험회피 반응 확인 |

이 보조 케이스는 `Acute Global Stress / Liquidity Crunch`의 하위 검증 재료로 사용한다.

---

## 5. 검증 방식
각 케이스마다 아래를 점검한다.

1. 해당 기간에 맞는 시나리오 점수가 실제로 상승했는가
2. `WATCH -> ACTIVE -> STRESS` 전환이 자연스럽게 나타났는가
3. 사건 발생 후 너무 늦게 반응하지 않았는가
4. 관련 없는 시나리오까지 과도하게 튀지 않았는가

---

## 6. 문서 사용법
- 시나리오 정의는 `plans/` 문서에서 관리한다.
- 역사적 검증은 이 문서와 `validation/` 문서에서 관리한다.
- stress template은 향후 별도 문서로 분리한다.
