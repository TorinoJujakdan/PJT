from importlib import import_module
from itertools import product
from unittest.mock import patch

from django.test import SimpleTestCase


class NaverMapsAuthTests(SimpleTestCase):
    STATES = ("absent", "id_only", "secret_only", "complete")
    FAMILIES = (
        ("NAVER_GEOCODING_CLIENT_ID", "NAVER_GEOCODING_CLIENT_SECRET"),
        ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"),
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
        auth = import_module("stations.naver_maps_auth")

        for states in product(self.STATES, repeat=len(self.FAMILIES)):
            with self.subTest(states=states):
                with patch.dict(
                    "os.environ",
                    self.environment_for(states),
                    clear=True,
                ):
                    credentials = auth.get_naver_maps_credentials()

                self.assertEqual(credentials, self.expected_for(states))

    def test_prefers_geocoding_credentials(self):
        auth = import_module("stations.naver_maps_auth")

        with patch.dict(
            "os.environ",
            {
                "NAVER_GEOCODING_CLIENT_ID": "maps-id",
                "NAVER_GEOCODING_CLIENT_SECRET": "maps-secret",
                "NAVER_CLIENT_ID": "legacy-id",
                "NAVER_CLIENT_SECRET": "legacy-secret",
            },
            clear=True,
        ):
            credentials = auth.get_naver_maps_credentials()

        self.assertEqual(credentials, ("maps-id", "maps-secret"))

    def test_falls_back_to_legacy_maps_credentials(self):
        auth = import_module("stations.naver_maps_auth")

        with patch.dict(
            "os.environ",
            {
                "NAVER_CLIENT_ID": "legacy-id",
                "NAVER_CLIENT_SECRET": "legacy-secret",
            },
            clear=True,
        ):
            credentials = auth.get_naver_maps_credentials()

        self.assertEqual(credentials, ("legacy-id", "legacy-secret"))

    def test_geocoding_and_directions_share_maps_auth_helper(self):
        auth = import_module("stations.naver_maps_auth")
        geocoding = import_module("stations.naver_geocoding_client")
        directions = import_module("stations.naver_directions_client")

        self.assertIs(
            geocoding.get_naver_maps_credentials,
            auth.get_naver_maps_credentials,
        )
        self.assertIs(
            directions.get_naver_maps_credentials,
            auth.get_naver_maps_credentials,
        )
