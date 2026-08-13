import json
from pathlib import Path

from django.test import SimpleTestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "docs/api_contracts/locations_geocode.json"
BLUEPRINT_PATH = PROJECT_ROOT / "docs/02_api_blueprint.json"

EXPECTED_REQUIRED = [
    {"source", "status", "count"},
    {"source", "status", "count", "fallback_from", "fallback_reason"},
    {"source", "status", "count", "fallback_from", "fallback_reason"},
    {
        "source",
        "status",
        "reason",
        "fallback_source",
        "fallback_status",
        "fallback_reason",
    },
    {
        "source",
        "status",
        "count",
        "fallback_source",
        "fallback_status",
        "fallback_reason",
    },
    {
        "source",
        "status",
        "count",
        "fallback_source",
        "fallback_status",
        "fallback_count",
    },
    {
        "source",
        "status",
        "reason",
        "fallback_source",
        "fallback_status",
        "fallback_count",
    },
]


class LocationSearchDocsTests(SimpleTestCase):
    def test_contract_defines_exact_metadata_variants_a_through_g(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        meta_schema = contract["responses"]["200"]["properties"]["meta"]
        variants = meta_schema["oneOf"]

        self.assertEqual(len(variants), 7)
        self.assertEqual(
            [variant["title"].split(" ", 1)[0] for variant in variants],
            list("ABCDEFG"),
        )
        for variant, expected_required in zip(
            variants,
            EXPECTED_REQUIRED,
        ):
            self.assertFalse(variant["additionalProperties"])
            self.assertEqual(set(variant["required"]), expected_required)
            self.assertEqual(
                set(variant["properties"]),
                expected_required,
            )
        self.assertEqual(
            contract["responses"]["400"]["properties"]["message"]["example"],
            "검색어(query) 파라미터가 누락되었습니다.",
        )

    def test_blueprint_defines_count_and_matching_variants(self):
        blueprint = json.loads(BLUEPRINT_PATH.read_text(encoding="utf-8"))
        endpoint = next(
            item
            for item in blueprint["endpoints"]
            if item["path"] == "/stations/geocode/"
        )
        meta = endpoint["responses"]["200"]["properties"]["meta"]
        variants = meta["metadataVariants"]

        self.assertIn("count", meta["properties"])
        self.assertEqual([item["case"] for item in variants], list("ABCDEFG"))
        self.assertEqual(
            [set(item["required"]) for item in variants],
            EXPECTED_REQUIRED,
        )
