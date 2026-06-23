# 구현 계획서: LLM 주도 주유 할인 혜택 구간 추출

## 1. 목표

현재 구조는 앱이 키워드 기반으로 먼저 청크를 만들고, LLM/GMS는 그 청크를 정규화하는 방식이다. 사용자가 원하는 방향은 다르다. **Selenium이 크롤링한 카드 원문을 LLM이 직접 읽고, 본인이 `주유 할인 혜택` 구간만 식별한 뒤, 그 구간의 데이터만 추출해 저장/추천에 반영하는 구조**로 바꾼다.

## 2. 현재 코드 근거

- Selenium 수집 진입점: `PJT/backend/cards/management/commands/ingest_card_search_ai.py:61`
- GMS normalizer 선택: `PJT/backend/cards/management/commands/ingest_card_search_ai.py:48`
- GMS 호출: `PJT/backend/cards/gms_client.py:89`
- 현재 GMS 프롬프트: `PJT/backend/cards/gms_client.py:136`
- 현재 청크 생성: `PJT/backend/cards/ai_chunks.py:55`
- 현재 키워드 줄 선택: `PJT/backend/cards/ai_chunks.py:77`
- 현재 저장 함수: `PJT/backend/cards/ai_normalization.py:124`
- 현재 `CardBenefitTier` 생성은 LLM 결과가 아니라 `_derive_tier_data(raw_text, candidate)` 기반: `PJT/backend/cards/ai_normalization.py:131`
- 추천 할인 계산은 `CardBenefitTier` 기반: `PJT/backend/stations/services.py:299`, `PJT/backend/stations/services.py:332`

## 3. 핵심 문제

1. `ai_chunks.py:55`의 `fuel_benefit` 청크는 앱이 이미 주유 관련 줄을 골라낸 결과다. 즉 LLM이 직접 구간을 자르는 구조가 아니다.
2. `ai_chunks.py:77`은 키워드가 있는 줄의 앞뒤 1줄만 선택하므로 `주유` 제목 아래 여러 줄로 이어지는 할인/브랜드/한도 섹션을 안정적으로 잡기 어렵다.
3. `gms_client.py:136`의 프롬프트는 `fuel_sections`, `start_line`, `end_line`처럼 “LLM이 직접 선택한 구간”을 요구하지 않는다.
4. `ai_normalization.py:124`는 LLM 결과를 `normalized_data`에는 저장하지만, 실제 추천에 쓰이는 `CardBenefitTier`는 `ai_normalization.py:131`에서 로컬 파서/후보값으로 다시 만든다.

## 4. 목표 아키텍처

### 현재 흐름

```text
Selenium crawl -> ScrapedCardCandidate -> RawCardDocument -> app keyword chunks -> GMS prompt -> normalized_data 저장 -> CardBenefitTier는 로컬 파서 기반 생성 -> 추천 계산
```

### 목표 흐름

```text
Selenium crawl -> ScrapedCardCandidate -> RawCardDocument -> line-numbered raw document -> GMS prompt: LLM이 직접 주유 혜택 구간 선택 -> LLM output: fuel_sections + benefits + quality -> validator -> CardCatalog.normalized_data 저장 -> valid LLM benefit -> CardBenefitTier 저장 -> 추천 계산
```

## 5. LLM 응답 스키마

LLM/GMS 응답은 다음 구조를 강제한다.

```json
{
  "card": {"name": "카드명", "issuer": "카드사"},
  "fuel_sections": [
    {
      "section_title": "주유",
      "start_line": 12,
      "end_line": 18,
      "evidence_text": "주유\n최대 1만원 할인\nSK에너지·GS칼텍스",
      "reason": "주유 제목과 할인/브랜드 조건이 같은 혜택 블록임"
    }
  ],
  "benefits": [
    {
      "category": "fuel",
      "fuel_type": "ALL",
      "discount_type": "fixed_amount",
      "discount_value": "10000",
      "brand_scope": "SK,GS",
      "min_payment_amount": null,
      "max_discount_amount": 10000,
      "monthly_discount_limit": 10000,
      "evidence_section_index": 0,
      "evidence_text": "주유\n최대 1만원 할인\nSK에너지·GS칼텍스"
    }
  ],
  "quality": {"extraction_confidence": "0.86", "verification_status": "unverified", "warnings": []}
}
```

핵심은 `fuel_sections`다. LLM이 할인값만 내는 것이 아니라 **어느 원문 라인을 주유 혜택 구간으로 판단했는지**를 같이 반환해야 한다.

## 6. 구현 단계

### Step 1. 라인 번호 기반 원문 입력 추가

대상 파일:

- 신규 권장: `PJT/backend/cards/llm_fuel_extraction.py`
- 또는 기존: `PJT/backend/cards/ai_chunks.py`

작업:

- `build_line_numbered_document(raw_text)` 추가
- 원문을 의미 기반으로 자르지 않고 다음처럼 변환

```text
[001] KB국민 마이핏카드
[002] 주유
[003] 최대 1만원 할인
[004] SK에너지·GS칼텍스
[005] 통신
[006] 최대 1만원 할인
```

완료 기준:

- GMS 경로에서 `build_chunks()`가 아니라 line-numbered raw document를 기본 입력으로 사용한다.
- 너무 긴 원문은 잘림 여부를 `quality.warnings` 또는 `input_truncated`에 남긴다.

### Step 2. GMS 프롬프트 교체

대상 파일:

- `PJT/backend/cards/gms_client.py:136`

작업:

- `build_gms_normalization_prompt()`가 `build_chunks(document.raw_text)` 대신 line-numbered raw document를 사용하게 한다.
- 한국어 지시를 추가한다.

필수 프롬프트 규칙:

```text
카드 혜택 원문에서 주유/충전/주유소/LPG/전기차 충전 혜택 구간만 직접 찾아라.
앱이 미리 잘라 준 청크를 기준으로 판단하지 말고, line-numbered raw_text에서 fuel_sections를 먼저 선택하라.
'주유' 같은 짧은 제목 줄 뒤의 할인/한도/브랜드 줄은 다음 혜택 제목이 나오기 전까지 같은 주유 혜택 구간일 수 있다.
일반 가맹점/통신/커피/영화 혜택은 주유 구간의 조건이 아니라면 fuel benefit으로 추출하지 마라.
evidence_text는 선택한 라인 범위에서 그대로 복사하라.
```

완료 기준:

- 프롬프트가 `fuel_sections`, `start_line`, `end_line`, `category=fuel`, `evidence_section_index`를 요구한다.
- 한국어 예시가 포함된다.

### Step 3. LLM 응답 검증기 추가

대상 파일:

- 신규 권장: `PJT/backend/cards/llm_fuel_extraction.py`
- 연동: `PJT/backend/cards/gms_client.py`

작업:

- `validate_llm_fuel_payload(document, llm_payload)` 추가
- 검증 규칙:
  - `benefits[*].category == "fuel"`
  - `evidence_section_index`가 실제 `fuel_sections`를 가리킴
  - `start_line/end_line`이 원문 라인 범위 안에 있음
  - `evidence_text`가 선택 라인 범위에 포함됨
  - `discount_type`이 기존 `CardPolicy.DiscountType`과 호환됨
  - `discount_value > 0`인 경우에만 추천 티어 후보가 됨

완료 기준:

- LLM이 원문에 없는 혜택을 만들어내면 `quality.warnings`에 기록되고 `CardBenefitTier` 생성은 차단된다.

### Step 4. 저장 경로를 LLM benefit 우선으로 변경

대상 파일:

- `PJT/backend/cards/ai_normalization.py:124`

작업:

- `extract_valid_fuel_tier_data(normalized_payload, raw_text)` 추가
- `save_ai_normalized_candidate()`에서 `ai_normalization.py:131`의 로컬 파서 우선 구조를 바꾼다.
- 우선순위:
  1. 검증된 LLM `benefits`
  2. LLM 결과 없음/검증 실패 시 기존 `_derive_tier_data()` fallback
  3. fallback 사용 시 `quality.warnings`에 기록

완료 기준:

- LLM이 추출한 주유 할인 데이터가 실제 `CardBenefitTier`에 저장된다.
- `normalized_data.benefits`와 `CardBenefitTier` 할인값이 불일치하지 않는다.

### Step 5. Selenium 파서와 역할 분리

대상 파일:

- `PJT/backend/cards/selenium_ingestion.py:355`
- `PJT/backend/cards/selenium_ingestion.py:381`
- `PJT/backend/cards/selenium_ingestion.py:398`

작업:

- GMS/LLM ingestion 경로에서는 Selenium 파서가 채운 `candidate.discount_value`를 최종 진실로 취급하지 않는다.
- Selenium 파서는 URL, 카드명, 이미지, 원문 수집 보조 역할로 둔다.
- 최종 주유 할인 티어는 validated LLM benefit이 우선한다.

완료 기준:

- 후보값과 LLM값이 충돌하면 검증된 LLM값이 우선된다.
- LLM 검증 실패 때만 기존 후보/로컬 파서를 fallback으로 쓴다.

### Step 6. 회귀 테스트 추가

대상 파일:

- `PJT/backend/cards/tests_ai_normalization.py`
- 필요 시 `PJT/backend/cards/tests_ingestion.py`
- 필요 시 추천 통합 테스트 파일

필수 테스트:

1. `주유` 제목 아래 할인/브랜드가 이어지는 케이스
   - 기대: LLM mock의 `fuel_sections`가 주유 블록만 선택하고 `CardBenefitTier.discount_value == 10000`
2. 일반 가맹점 할인 혼동 방지
   - 입력: `국내외 가맹점 1% 할인` + `주유 리터당 60원 할인`
   - 기대: 1%가 아니라 리터당 60원이 저장됨
3. 근거 없는 LLM 응답 거부
   - LLM이 원문에 없는 `리터당 200원`을 반환
   - 기대: warning 기록, 티어 생성 차단 또는 fallback만 사용
4. 추천 반영 검증
   - 검증된 LLM benefit으로 생성된 `CardBenefitTier`가 `stations/services.py:332`의 할인 계산에 반영됨

## 7. 검증 명령

기본 테스트:

```powershell
cd PJT\backend
..\.venv\Scripts\python.exe manage.py test cards.tests_ai_normalization cards.tests_ingestion -v 2
```

추천 통합 테스트 추가 후:

```powershell
cd PJT\backend
..\.venv\Scripts\python.exe manage.py test stations.tests_additions -v 2
```

실제 GMS 호출은 크레딧/API 키가 필요하므로 기본 검증에서는 mock만 사용한다. 실제 호출은 별도 승인 후 제한적으로 실행한다.

```powershell
cd PJT\backend
..\.venv\Scripts\python.exe manage.py ingest_card_search_ai --normalizer=gms --detail --limit=1 --scroll-count=1 --dry-run
```

## 8. 리스크와 대응

| 리스크 | 영향 | 대응 |
|---|---:|---|
| 원문이 너무 김 | LLM이 필요한 주유 구간을 못 볼 수 있음 | line-numbered packer에서 잘림 여부 기록, detail text 우선 포함 |
| LLM이 일반 혜택을 주유로 오분류 | 할인 과대 계산 | `category=fuel`, evidence line, 주유 키워드/브랜드 근거 검증 |
| LLM 환각 | 잘못된 티어 저장 | evidence_text 원문 포함 검증 실패 시 티어 저장 차단 |
| LLM 결과가 저장만 되고 추천에 미반영 | 사용자 체감 변화 없음 | `CardBenefitTier` 저장 경로를 LLM benefit 우선으로 변경 |
| 기존 로컬 파서와 충돌 | 데이터 불일치 | validated LLM 우선, fallback 사용 시 warning 기록 |

## 9. 완료 기준

- GMS 프롬프트가 line-numbered raw document를 기준으로 LLM 직접 구간 선택을 요구한다.
- LLM 응답에 `fuel_sections`가 포함된다.
- `benefits`가 `fuel_sections`의 근거와 연결된다.
- 검증된 LLM benefit이 `CardBenefitTier`에 저장된다.
- 추천 계산에서 해당 `CardBenefitTier`가 실제 할인액 계산에 사용된다.
- mock GMS 테스트가 통과한다.
- 기존 `cards.tests_ai_normalization`, `cards.tests_ingestion` 회귀 테스트가 통과한다.
- 실제 GMS 호출은 승인된 경우에만 제한 dry-run으로 검증한다.

## 10. ADR

### Decision

GMS/LLM 경로에서는 앱이 키워드 기반으로 주유 구간을 미리 확정하지 않는다. LLM이 라인 번호가 붙은 크롤링 원문에서 직접 주유 할인 혜택 구간을 선택하고, 검증된 결과만 `CardBenefitTier`에 반영한다.

### Drivers

- 사용자 요구가 “LLM이 본인이 직접 주유 할인 혜택 부분만 잘라서 가져오는 방식”이기 때문이다.
- `ai_chunks.py:77`의 앞뒤 1줄 방식은 카드 혜택 섹션 구조를 충분히 반영하지 못한다.
- `ai_normalization.py:131`은 현재 LLM benefit을 추천 티어에 직접 반영하지 않는다.

### Alternatives considered

1. 현재 키워드 청크 개선: 구현은 작지만 앱이 구간 선택을 계속 주도하므로 기각.
2. 로컬 정규식 파서 강화: 비용은 낮지만 표현 다양성을 따라가기 어려워 fallback으로만 유지.
3. LLM 직접 구간 선택 + 검증 후 저장: 사용자 의도와 가장 잘 맞고 환각 위험은 validator로 줄일 수 있어 채택.

### Consequences

- 프롬프트와 schema 테스트가 중요해진다.
- evidence 검증 실패 시 추천 티어 저장을 막아야 한다.
- 운영 전 mock 테스트와 제한된 GMS dry-run이 필요하다.

### Follow-ups

- 구현 후 실제 GMS dry-run 1~3건으로 응답 품질을 확인한다.
- `verification_status=unverified` 기본 정책은 유지한다.
- 이후 관리자 검수 화면에서 `fuel_sections.evidence_text`를 보여주면 데이터 신뢰도를 높일 수 있다.
