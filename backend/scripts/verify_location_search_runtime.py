import argparse
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request


QUERIES = {
    "롯데월드타워": "naver_local_search",
    "코엑스": "naver_local_search",
    "서울역": "naver_local_search",
    "스타벅스 강남": "naver_local_search",
    "강남구": "naver_geocode",
}
CREDENTIAL_KEYS = (
    "NAVER_GEOCODING_CLIENT_ID",
    "NAVER_GEOCODING_CLIENT_SECRET",
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "NAVER_LOCAL_CLIENT_ID",
    "NAVER_LOCAL_CLIENT_SECRET",
    "NAVER_SEARCH_CLIENT_ID",
    "NAVER_SEARCH_CLIENT_SECRET",
    "NAVER_OPENAPI_CLIENT_ID",
    "NAVER_OPENAPI_CLIENT_SECRET",
)


def request_query(base_url, query):
    separator = "&" if "?" in base_url else "?"
    url = f"{base_url}{separator}{urllib.parse.urlencode({'query': query})}"
    with urllib.request.urlopen(url, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return response.status, payload


def sanitize(query, transport, status, payload):
    meta = payload["meta"]
    return {
        "query": query,
        "transport": transport,
        "http_status": status,
        "count": len(payload["results"]),
        "source": meta["source"],
        **{
            key: meta[key]
            for key in (
                "status",
                "reason",
                "fallback_from",
                "fallback_reason",
                "fallback_source",
                "fallback_status",
                "fallback_count",
            )
            if key in meta
        },
        "result_names": [item["name"] for item in payload["results"]],
    }


def assert_payload(query, expected_source, status, payload):
    if status != 200:
        raise AssertionError(f"{query}: expected HTTP 200, got {status}")
    if set(payload) != {"results", "meta"}:
        raise AssertionError(f"{query}: unexpected top-level schema")
    if payload["meta"].get("source") != expected_source:
        raise AssertionError(
            f"{query}: expected {expected_source}, "
            f"got {payload['meta'].get('source')}"
        )
    if not payload["results"]:
        raise AssertionError(f"{query}: expected at least one result")


def assert_schema_parity(query, payloads):
    result_key_sets = {
        tuple(sorted(item.keys()))
        for payload in payloads
        for item in payload["results"]
    }
    if not result_key_sets:
        raise AssertionError(f"{query}: no normalized results")
    for payload in payloads:
        if "source" not in payload["meta"] or "status" not in payload["meta"]:
            raise AssertionError(f"{query}: incomplete metadata")


def assert_redacted(serialized):
    for key in CREDENTIAL_KEYS:
        value = os.getenv(key, "").strip()
        if value and value in serialized:
            raise AssertionError(f"credential value leaked into output: {key}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--django-url", required=True)
    parser.add_argument("--fastapi-url", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    records = []
    for query, expected_source in QUERIES.items():
        payloads = []
        for transport, url in (
            ("django", args.django_url),
            ("fastapi", args.fastapi_url),
        ):
            status, payload = request_query(url, query)
            assert_payload(query, expected_source, status, payload)
            payloads.append(payload)
            records.append(sanitize(query, transport, status, payload))
        assert_schema_parity(query, payloads)

    serialized = json.dumps(
        records,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    assert_redacted(serialized)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"location search runtime verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
