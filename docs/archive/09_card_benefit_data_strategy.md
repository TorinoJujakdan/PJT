# SmartFuel Card Benefit Data Strategy

## 1. Purpose

This document defines the card-benefit requirements added before Slice 4.

The goal is to support both:

- user-entered card benefits
- card benefit discovery through controlled Selenium ingestion from user-approved public domains

without breaking the existing project structure.

## 2. Added Requirements

### 2.1 Manual Card Benefit Input

Users can directly enter their own card benefit policy.

Required fields:

- card name
- issuer name
- discount type
- discount value
- brand scope

Optional fields:

- minimum payment amount
- maximum discount amount
- monthly discount limit
- monthly remaining discount
- card image URL
- source URL
- user memo

Manual policies are treated as valid user-owned policies, but the response must expose that the policy source is `manual`.

### 2.2 Selenium-Based Card Benefit Discovery

SmartFuel may use Selenium to discover card benefit candidates from public domains explicitly provided by the user and allowlisted by the backend.

The first user-approved source is:

```text
https://card-search.naver.com/list?companyCode=&brandNames=&benefitCategoryIds=1&sortMethod=ri&isRefetch=true&bizType=CPC
```

Allowed approach:

- Treat `card-search.naver.com` as the first user-approved default domain.
- Use `CARD_INGESTION_ALLOWED_DOMAINS` for any additional backend allowlist entries.
- Use Selenium only in a separate ingestion worker or management command, not during recommendation requests.
- Store source URL, title, summary, image URL, and collected time.
- Let the user confirm or edit the discovered benefit before it becomes an active user card.

Disallowed approach:

- Do not scrape private pages or bypass access controls.
- Do not bypass CAPTCHA, anti-bot controls, login walls, or payment authentication.
- Do not store card numbers, CVC, resident registration numbers, or payment credentials.
- Do not silently activate an unverified discovered benefit.

Selenium ingestion data is discovery data, not authoritative financial advice.

### 2.3 Card Physical Image Display

The frontend should show a card image when available.

Image priority:

1. user-provided image URL
2. issuer-provided image URL
3. Selenium-discovered public image URL
4. default local card placeholder

Each image should keep its source metadata.

For production, prefer issuer-owned image URLs or locally licensed assets.

### 2.4 Recommendation Reason Enhancement

Slice 4 recommendation reason must explain:

- base fuel price
- travel cost
- selected card
- discount type
- discount amount
- final effective total cost
- why the selected station wins over cheaper or closer alternatives

Example:

```text
GS 할인카드가 리터당 80원을 할인해 주고, 왕복 이동 비용을 포함해도 최종 예상 비용이 가장 낮습니다.
```

## 3. Impact Analysis

| Area | Impact |
|---|---|
| Slice 1 nearby station search | No change |
| Slice 2 fuel-price-only recommendation | No change |
| Slice 3 travel-cost recommendation | No change |
| Slice 4 card discount | Must support manual and discovered card policies |
| API contract | Card policy schema and card discovery endpoint required |
| ERD | Card source and image metadata required |
| Use Case | Card entry, discovery, image display, and confirmation required |
| QA | Manual input, Selenium discovery, card image fallback, and reason quality scenarios required |

## 4. Data Source Confidence

Card policy records should expose:

```text
source_type = manual | selenium | naver_search | issuer | admin_seed
verification_status = unverified | user_confirmed | admin_verified
```

Recommendation can use:

- `manual` policies created by the user
- `user_confirmed` discovered policies
- `admin_verified` seeded policies

Recommendation must not silently use `unverified` Selenium-discovered policies.

## 5. Implementation Order

Before Slice 4 implementation:

1. Update card API contract.
2. Update card ERD.
3. Update card use cases.
4. Add QA scenarios.

During Slice 4 implementation:

1. Implement manual card policy model/API.
2. Implement card image fields.
3. Implement Selenium discovery as a separate service boundary.
4. Require user confirmation before using discovered benefits.
5. Apply confirmed card policies to recommendation ranking.

## 6. Selenium Ingestion Note

SmartFuel should treat Selenium as an external ingestion dependency behind a service boundary:

```text
backend/cards/selenium_ingestion.py
```

The application should continue to work when no allowed ingestion domain is configured by falling back to manual card input.
