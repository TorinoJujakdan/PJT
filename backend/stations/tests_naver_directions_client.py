from importlib import import_module

from django.test import SimpleTestCase


class NaverDirectionsClientTests(SimpleTestCase):
    def test_owns_directions_url(self):
        client = import_module("stations.naver_directions_client")

        self.assertEqual(
            client.DIRECTIONS_URL,
            "https://maps.apigw.ntruss.com/map-direction/v1/driving",
        )

    def test_route_path_keeps_only_valid_coordinate_points(self):
        client = import_module("stations.naver_directions_client")

        normalized = client._normalize_route_path(
            [
                [127.039, 37.501],
                ["invalid"],
                [181, 37.502],
                [127.041, 37.503],
            ]
        )

        self.assertEqual(
            normalized,
            [
                {"latitude": 37.501, "longitude": 127.039},
                {"latitude": 37.503, "longitude": 127.041},
            ],
        )
