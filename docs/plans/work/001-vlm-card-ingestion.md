# VLM Card Ingestion

> Replace Selenium regex parsing with VLM multimodal API

**Status**: Active
**Created**: 2026-06-24
**Owner**: backend agent

## Goal
기존 정규식 기반의 취약한 텍스트 파싱 로직을 GMS VLM(GPT-4o) 멀티모달 캡처 분석으로 완전히 대체하여, UI 변경 시에도 견고하게 카드 혜택을 추출합니다.

## Context
설계 문서 참고: `docs/plans/designs/002-vlm-card-ingestion.md`

## Constraints
- **비용 최적화**: 매 크롤링마다 무조건 VLM에 전송하지 않고 Diff-check 수행.
- **예외 처리**: VLM 포맷 에러 및 비현실적 할인값(`benefit_safety.py`) 차단.

## Tasks

| # | Task | Agent | Priority | Status | Dependencies |
|---|------|-------|----------|--------|--------------|
| 1 | GMS Client 멀티모달 지원 추가 (`gms_client.py`) | backend | P0 | DONE | — |
| 2 | Selenium 크롤링 캡처 파이프라인 개편 (`selenium_ingestion.py`) | backend | P0 | DONE | 1 |
| 3 | 비용 최적화 (Diff-Check) 로직 추가 | backend | P1 | DONE | 2 |
| 4 | VLM 환각 예외 처리 및 검증 연동 | qa | P1 | DONE | 2 |

## Done When
- [x] `gms_client.py`에 `normalize_multimodal` 함수가 추가되고 정상 호출됨.
- [ ] 정규식 로직 없이 Base64 스크린샷으로 `CardBenefitTier`가 올바르게 추출 및 DB 저장됨.
- [x] 중복 크롤링 시 VLM 토큰 API가 호출되지 않음(Diff-check 동작 확인).
- [x] 비정상적인 응답일 때 `ERROR` 처리됨.

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-24 | Base64 캡처 전송 방식으로 확정 | UI Breakage 근본 해결 및 VLM 역량 극대화 |
| 2026-06-24 | Diff-Check 로직 필수화 | VLM API 토큰 비용(FinOps) 방어 목적 |

## Progress Notes

- [2026-06-24] Plan created
