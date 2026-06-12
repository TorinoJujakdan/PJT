from importlib import import_module
from unittest.mock import patch

from django.test import SimpleTestCase


class NaverGeocodingClientTests(SimpleTestCase):
    def test_normalizes_successful_geocode_result(self):
        client = import_module("stations.naver_geocoding_client")
        provider_payload = {
            "addresses": [
                {
                    "roadAddress": "Seoul Gangnam-gu Teheran-ro 152",
                    "jibunAddress": "Seoul Gangnam-gu Yeoksam-dong 737",
                    "x": "127.0365",
                    "y": "37.5007",
                }
            ]
        }

        with patch.object(
            client,
            "_request_naver_json",
            return_value=(provider_payload, None),
        ):
            payload = client.geocode_query_with_meta("Teheran-ro 152")

        self.assertEqual(
            payload,
            {
                "results": [
                    {
                        "name": "Seoul Gangnam-gu Teheran-ro 152",
                        "address": "Seoul Gangnam-gu Teheran-ro 152",
                        "road_address": "Seoul Gangnam-gu Teheran-ro 152",
                        "jibun_address": "Seoul Gangnam-gu Yeoksam-dong 737",
                        "latitude": 37.5007,
                        "longitude": 127.0365,
                        "source": "naver_geocode",
                    }
                ],
                "meta": {
                    "source": "naver_geocode",
                    "status": "ok",
                    "count": 1,
                },
            },
        )

    def test_returns_exact_unavailable_reason(self):
        client = import_module("stations.naver_geocoding_client")

        with patch.object(
            client,
            "_request_naver_json",
            return_value=(None, "NAVER_GEOCODING_HTTP_401"),
        ):
            payload = client.geocode_query_with_meta("Gangnam")

        self.assertEqual(
            payload,
            {
                "results": [],
                "meta": {
                    "source": "naver_geocode",
                    "status": "unavailable",
                    "reason": "NAVER_GEOCODING_HTTP_401",
                },
            },
        )

    def test_reports_zero_when_no_addresses_normalize(self):
        client = import_module("stations.naver_geocoding_client")
        provider_payload = {
            "addresses": [
                {
                    "roadAddress": "Invalid coordinate",
                    "x": "not-a-number",
                    "y": "37.5007",
                }
            ]
        }

        with patch.object(
            client,
            "_request_naver_json",
            return_value=(provider_payload, None),
        ):
            payload = client.geocode_query_with_meta("Invalid coordinate")

        self.assertEqual(
            payload,
            {
                "results": [],
                "meta": {
                    "source": "naver_geocode",
                    "status": "ok",
                    "count": 0,
                },
            },
        )
