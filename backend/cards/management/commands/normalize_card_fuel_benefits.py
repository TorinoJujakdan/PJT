from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import TypeAlias

from django.core.management.base import BaseCommand, CommandError

from cards.benefit_safety import has_fuel_context, is_suspicious_fuel_discount
from cards.brand_scope import normalize_brand_scope

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class TierAudit:
    pk: int | str | None
    original_brand_scope: str
    normalized_brand_scope: str
    brand_scope_inferred: bool
    brand_scope_reason: str
    suspicious_discount: bool
    discount_type: str
    discount_value: str

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "pk": self.pk,
            "original_brand_scope": self.original_brand_scope,
            "normalized_brand_scope": self.normalized_brand_scope,
            "brand_scope_inferred": self.brand_scope_inferred,
            "brand_scope_reason": self.brand_scope_reason,
            "suspicious_discount": self.suspicious_discount,
            "discount_type": self.discount_type,
            "discount_value": self.discount_value,
        }


class Command(BaseCommand):
    help = "Normalize card fuel benefit fixture brand scopes and report suspicious tiers without Gemini."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--fixture", required=True, help="Path to card_data.json fixture.")
        parser.add_argument("--report", required=True, help="Path to write JSON audit report.")
        parser.add_argument("--dry-run", action="store_true", help="Do not write normalized fixture changes.")
        parser.add_argument("--write", action="store_true", help="Write normalized brand_scope values back to fixture.")

    def handle(self, *args, **options) -> None:
        fixture_path = Path(str(options["fixture"]))
        report_path = Path(str(options["report"]))
        dry_run = bool(options["dry_run"])
        write_fixture = bool(options["write"])
        if dry_run and write_fixture:
            raise CommandError("Use either --dry-run or --write, not both.")
        if not fixture_path.exists():
            raise CommandError(f"Fixture does not exist: {fixture_path}")

        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise CommandError("Fixture must be a JSON list.")

        audits = self._audit_fixture(payload)
        report = self._build_report(audits)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        if write_fixture:
            fixture_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                "normalize_card_fuel_benefits "
                f"tiers={report['summary']['tiers']} "
                f"normalized={report['summary']['normalized_brand_scopes']} "
                f"suspicious={report['summary']['suspicious_tiers']}"
            )
        )

    def _audit_fixture(self, payload: list[JsonValue]) -> list[TierAudit]:
        audits: list[TierAudit] = []
        for entry in payload:
            if not isinstance(entry, dict) or entry.get("model") != "cards.cardbenefittier":
                continue
            fields = entry.get("fields")
            if not isinstance(fields, dict):
                continue
            original_scope = str(fields.get("brand_scope") or "")
            normalized = normalize_brand_scope(original_scope)
            discount_type = str(fields.get("discount_type") or "")
            discount_value = str(fields.get("discount_value") or "0")
            evidence_text = str(fields.get("raw_summary") or "")
            if not evidence_text and has_fuel_context(original_scope):
                evidence_text = original_scope
            if normalized.scope != original_scope:
                fields["brand_scope"] = normalized.scope
            audits.append(
                TierAudit(
                    pk=entry.get("pk") if isinstance(entry.get("pk"), (int, str)) else None,
                    original_brand_scope=original_scope,
                    normalized_brand_scope=normalized.scope,
                    brand_scope_inferred=normalized.inferred,
                    brand_scope_reason=normalized.reason,
                    suspicious_discount=is_suspicious_fuel_discount(discount_type, Decimal(discount_value), evidence_text),
                    discount_type=discount_type,
                    discount_value=discount_value,
                )
            )
        return audits

    def _build_report(self, audits: list[TierAudit]) -> dict[str, JsonValue]:
        changed = [audit for audit in audits if audit.original_brand_scope != audit.normalized_brand_scope]
        suspicious = [audit for audit in audits if audit.suspicious_discount]
        inferred = [audit for audit in audits if audit.brand_scope_inferred]
        return {
            "summary": {
                "tiers": len(audits),
                "normalized_brand_scopes": len(changed),
                "inferred_brand_scopes": len(inferred),
                "suspicious_tiers": len(suspicious),
            },
            "items": [audit.to_json() for audit in audits if audit in changed or audit in suspicious or audit in inferred],
        }
