from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from io import StringIO
from unittest.mock import Mock, patch

from .models import FuelPrice, GasStation
from .opinet_client import (
    OpinetClient,
    OpinetConfigurationError,
    OpinetMappingError,
    normalize_opinet_price_row,
    normalize_opinet_station_row,
)


class OpinetConfigurationTests(SimpleTestCase):
    def test_opinet_client_requires_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(OpinetConfigurationError):
                OpinetClient()

    def test_opinet_client_accepts_api_key(self):
        client = OpinetClient(api_key="test-key")

        self.assertEqual(client.api_key, "test-key")
        self.assertEqual(client.fetch_price_rows(), [])

    def test_opinet_client_fetches_average_price_rows(self):
        client = OpinetClient(api_key="test-key")

        with patch.object(
            client,
            "_get_json",
            return_value={"RESULT": {"OIL": [{"PRODCD": "B027", "PRICE": "1667.33"}]}},
        ):
            rows = client.fetch_average_price_rows()

        self.assertEqual(rows, [{"PRODCD": "B027", "PRICE": "1667.33"}])

    def test_opinet_client_normalizes_single_average_price_row(self):
        client = OpinetClient(api_key="test-key")

        with patch.object(
            client,
            "_get_json",
            return_value={"RESULT": {"OIL": {"PRODCD": "B027", "PRICE": "1667.33"}}},
        ):
            rows = client.fetch_average_price_rows()

        self.assertEqual(rows, [{"PRODCD": "B027", "PRICE": "1667.33"}])

    def test_sync_opinet_prices_requires_environment_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(CommandError):
                call_command("sync_opinet_prices", "--dry-run")

    def test_sync_opinet_prices_health_check_calls_average_price_endpoint(self):
        stdout = StringIO()
        with patch.dict("os.environ", {"OPINET_API_KEY": "test-key"}, clear=True):
            fetch_price_rows = Mock(return_value=[])
            with patch(
                "stations.management.commands.sync_opinet_prices.OpinetClient.fetch_price_rows",
                fetch_price_rows,
            ), patch(
                "stations.management.commands.sync_opinet_prices.OpinetClient.fetch_average_price_rows",
                Mock(return_value=[{"PRODCD": "B027"}]),
            ):
                call_command("sync_opinet_prices", "--health-check", stdout=stdout)

        self.assertIn("1 rows returned", stdout.getvalue())
        fetch_price_rows.assert_not_called()


class OpinetMappingTests(SimpleTestCase):
    def test_normalize_opinet_station_row_maps_uni_id_and_brand_with_coordinates(self):
        row = {
            "UNI_ID": "A0010207",
            "POLL_DIV_CD": "SKE",
            "OS_NM": "SK Sample",
            "NEW_ADR": "서울 강남구 역삼로 142",
            "GIS_X_COOR": "314871.80000",
            "GIS_Y_COOR": "544012.00000",
            "LPG_YN": "N",
        }

        mapped = normalize_opinet_station_row(row)

        self.assertEqual(mapped["external_station_id"], "A0010207")
        self.assertEqual(mapped["brand"], GasStation.Brand.SK)
        self.assertEqual(mapped["katec_x"], "314871.80000")
        self.assertEqual(mapped["katec_y"], "544012.00000")
        self.assertIn("latitude", mapped)
        self.assertIn("longitude", mapped)
        self.assertEqual(round(mapped["latitude"], 4), 37.4943)
        self.assertEqual(round(mapped["longitude"], 4), 127.0351)

    def test_normalize_opinet_station_row_accepts_documented_poll_div_co_typo(self):
        mapped = normalize_opinet_station_row(
            {"UNI_ID": "A0009907", "POLL_DIV_CO": "GSC", "OS_NM": "GS Sample"}
        )

        self.assertEqual(mapped["brand"], GasStation.Brand.GS)

    def test_normalize_opinet_price_row_maps_supported_product_codes(self):
        expectations = {
            "B027": FuelPrice.FuelType.GASOLINE,
            "D047": FuelPrice.FuelType.DIESEL,
            "B034": FuelPrice.FuelType.PREMIUM_GASOLINE,
            "K015": FuelPrice.FuelType.LPG,
        }

        for prodcd, fuel_type in expectations.items():
            with self.subTest(prodcd=prodcd):
                mapped = normalize_opinet_price_row({"PRODCD": prodcd, "PRICE": "1745"})
                self.assertEqual(mapped["fuel_type"], fuel_type)
                self.assertEqual(mapped["price_per_liter"], 1745)
                self.assertEqual(mapped["source"], FuelPrice.Source.OPINET)

    def test_normalize_opinet_price_row_rejects_unknown_product_code(self):
        with self.assertRaises(OpinetMappingError):
            normalize_opinet_price_row({"PRODCD": "C004", "PRICE": "1200"})
