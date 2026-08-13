from importlib import import_module
from itertools import product
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import SimpleTestCase


class NaverLocalSearchClientTests(SimpleTestCase):
    STATES = ("absent", "id_only", "secret_only", "complete")
    FAMILIES = (
        ("NAVER_LOCAL_CLIENT_ID", "NAVER_LOCAL_CLIENT_SECRET"),
        ("NAVER_SEARCH_CLIENT_ID", "NAVER_SEARCH_CLIENT_SECRET"),
        ("NAVER_OPENAPI_CLIENT_ID", "NAVER_OPENAPI_CLIENT_SECRET"),
    )

    def environment_for(self, states):
        environment = {}
        for index, ((id_key, secret_key), state) in enumerate(
            zip(self.FAMILIES, states),
        ):
            if state in {"id_only", "complete"}:
                environment[id_key] = f"id-{index}"
            if state in {"secret_only", "complete"}:
                environment[secret_key] = f"secret-{index}"
        return environment

    def expected_for(self, states):
        for index, state in enumerate(states):
            if state == "complete":
                return f"id-{index}", f"secret-{index}"
        return "", ""

    def test_exhaustive_same_family_pair_selection(self):
        client = import_module("stations.naver_local_search_client")

        for states in product(self.STATES, repeat=len(self.FAMILIES)):
            with self.subTest(states=states):
                with patch.dict(
                    "os.environ",
                    self.environment_for(states),
                    clear=True,
                ):
                    credentials = client.get_naver_local_credentials()

                self.assertEqual(credentials, self.expected_for(states))

    def test_normalizes_title_coordinates_and_category(self):
        client = import_module("stations.naver_local_search_client")
        provider_payload = {
            "items": [
                {
                    "title": "<b>COEX</b>",
                    "roadAddress": "Seoul Gangnam-gu Yeongdong-daero 513",
                    "address": "Seoul Gangnam-gu Samseong-dong 159",
                    "mapx": "1270591590",
                    "mapy": "375112994",
                    "category": "Culture, Art > Exhibition",
                }
            ]
        }

        with patch.object(
            client,
            "_request_naver_local_json",
            return_value=(provider_payload, None),
        ):
            payload = client.local_search_query_with_meta("COEX")

        result = payload["results"][0]
        self.assertEqual(result["name"], "COEX")
        self.assertEqual(result["latitude"], 37.5112994)
        self.assertEqual(result["longitude"], 127.059159)
        self.assertEqual(
            result["category"],
            "Culture, Art > Exhibition",
        )
        self.assertEqual(result["source"], "naver_local_search")

    def test_accepts_each_local_credential_family(self):
        client = import_module("stations.naver_local_search_client")

        for client_id_key, client_secret_key in self.FAMILIES:
            with self.subTest(client_id_key=client_id_key):
                with patch.dict(
                    "os.environ",
                    {
                        client_id_key: "local-id",
                        client_secret_key: "local-secret",
                    },
                    clear=True,
                ):
                    credentials = client.get_naver_local_credentials()

                self.assertEqual(credentials, ("local-id", "local-secret"))

    def test_rejects_cloud_maps_credentials_as_local_credentials(self):
        client = import_module("stations.naver_local_search_client")

        with (
            patch.dict(
                "os.environ",
                {
                    "NAVER_CLIENT_ID": "maps-id",
                    "NAVER_CLIENT_SECRET": "maps-secret",
                },
                clear=True,
            ),
            patch("urllib.request.urlopen") as urlopen,
        ):
            payload = client.local_search_query_with_meta("COEX")

        self.assertEqual(
            payload,
            {
                "results": [],
                "meta": {
                    "source": "naver_local_search",
                    "status": "unavailable",
                    "reason": "NAVER_LOCAL_KEY_MISSING",
                },
            },
        )
        urlopen.assert_not_called()

    def test_surfaces_http_401_for_invalid_local_credentials(self):
        client = import_module("stations.naver_local_search_client")
        http_error = HTTPError(
            url=client.LOCAL_SEARCH_URL,
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

        with (
            patch.dict(
                "os.environ",
                {
                    "NAVER_LOCAL_CLIENT_ID": "invalid-id",
                    "NAVER_LOCAL_CLIENT_SECRET": "invalid-secret",
                },
                clear=True,
            ),
            patch("urllib.request.urlopen", side_effect=http_error),
        ):
            payload = client.local_search_query_with_meta("COEX")

        self.assertEqual(payload["meta"]["reason"], "NAVER_LOCAL_HTTP_401")
