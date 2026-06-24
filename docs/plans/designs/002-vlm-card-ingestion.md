# VLM Card Ingestion Design

## 1. 개요 (Architecture Overview)
기존의 정규식/텍스트 추출(Selenium) 기반 방식의 한계와 파싱의 복잡성을 개선하기 위해, VLM(Vision-Language Model)을 직접 도입하는 [Structural] 방식의 설계 문서입니다.
- **주요 변경점**: 대상 페이지의 카드 혜택 컴포넌트 전체를 스크린샷 캡처(Base64)하여 VLM(GPT-4o 등)으로 전송해 텍스트 파싱을 모델에게 전임합니다.
- **장점**: UI/DOM 구조가 변경되더라도 컴포넌트 화면만 확보되면 유지보수 없이 안정적인 추출이 가능합니다.

## 2. 주요 인터페이스 및 컨트랙트 (Key Interfaces & Contracts)

### GMS 멀티모달 API 요청 (Request)
기존 텍스트 청크(`chunks`) 대신 `image_url` 타입의 멀티모달 메시지를 GMS API로 전송합니다.
```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "다음 카드 혜택 캡처 화면에서 주유 혜택을 추출해 JSON으로 반환해줘." },
        { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
      ]
    }
  ]
}
```

### GMS 멀티모달 API 응답 (Response)
기존 정형화된 JSON 반환 규격(NormalizedPayload)과 호환되게 반환받습니다.
```json
{
  "card": { "name": "국민 에너지카드", "plate_image_detected": true },
  "benefits": [{ "fuel_type": "ALL", "discount_type": "PER_LITER", "discount_value": 150 }],
  "quality": { "verification_status": "UNVERIFIED", "extraction_confidence": 0.95 }
}
```

### GMSClient 수정 사항
`gms_client.py`에 다음 메서드를 추가하여 멀티모달 요청을 캡슐화합니다.
- `def normalize_multimodal(self, base64_image: str, context: dict) -> NormalizedPayload:`

## 3. 기존 코드 연동 지점 (Integration Points)

- **`selenium_ingestion.py` 파싱 로직 교체**: `parse_fuel_discount`, `parse_benefit_constraints` 등의 정규식 관련 함수들을 점진적으로 Deprecate 합니다. 대신 혜택 영역 DOM 요소를 타겟팅해 `screenshot_as_base64`로 이미지화하는 로직을 신설합니다.
- **`save_candidates` 파이프라인 통합**: 확보한 Base64 이미지를 `GMSClient.normalize_multimodal()` 에 넘겨 `CardCatalog` 및 `CardBenefitTier` DB 인스턴스로 변환/저장합니다.

## 4. 엣지 케이스 및 예외 처리 (Edge Cases)

- **렌더링 지연/초과 용량**: Selenium 명시적 대기(Explicit Wait)로 로딩 보장, Pillow 등을 활용한 이미지 리사이징(최대 폭 제한) 적용으로 토큰 한도 초과(413 Payload Too Large) 방지.
- **환각(Hallucination) 방어**: GMS가 반환한 JSON 스키마를 1차 검증하고, 기존 `benefit_safety.py`의 논리 검사(상식 밖의 할인금액 차단)를 통과하지 못하면 `ERROR` 상태 처리.
- **재시도 처리**: API Rate Limit(429) 대비 Exponential Backoff 적용.

## 5. 비용 및 성능 최적화 (FinOps / Blind Review 결의사항)

- **Diff-Check 캐싱 로직**: 매 크롤링마다 무조건 VLM에 전송하는 것은 큰 토큰 비용을 수반합니다. 기존 DB의 텍스트 Hash 혹은 `imageUrl`과 비교해 "새로운 카드"이거나 "변경 사항이 의심되는 카드"에 대해서만 Base64 캡처 후 VLM 판독을 수행하도록 방어 로직을 추가합니다.
- **DOM 타겟팅 캡처**: 페이지 전체 스크린샷 대신 혜택 영역 DOM 크기에 맞춰 최적화된 바운딩 박스(Bounding Box)를 스크린샷으로 캡처해 전송합니다.
