from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class VehicleProfileResetMigrationTests(TransactionTestCase):
    reset_sequences = True

    migrate_from = [
        ("cards", "0003_cardingestiontask"),
        (
            "stations",
            "0002_rename_stations_fu_fuel_ty_e56c8c_idx_stations_fu_fuel_ty_788131_idx_and_more",
        ),
        ("vehicles", "0004_vehicleprofile_vehicles_one_default_per_user"),
    ]
    migrate_to = [
        ("cards", "0003_cardingestiontask"),
        (
            "stations",
            "0002_rename_stations_fu_fuel_ty_e56c8c_idx_stations_fu_fuel_ty_788131_idx_and_more",
        ),
        ("vehicles", "0005_reset_profiles_expand_vehicle_types"),
    ]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps

        user = old_apps.get_model("auth", "User").objects.create(username="migration-user")
        old_apps.get_model("vehicles", "VehicleProfile").objects.create(
            user_id=user.id,
            name="Legacy vehicle",
            vehicle_type="compact",
            fuel_type="gasoline",
            fuel_efficiency_kmpl="12.0",
            is_default=True,
        )
        self.assertEqual(old_apps.get_model("vehicles", "VehicleProfile").objects.count(), 1)
        station = old_apps.get_model("stations", "GasStation").objects.create(
            external_station_id="migration-station",
            name="Migration Station",
            brand="OTHER",
            address="Seoul",
            latitude="37.5000000",
            longitude="127.0000000",
        )
        old_apps.get_model("stations", "FuelPrice").objects.create(
            station_id=station.id,
            fuel_type="gasoline",
            price_per_liter=1700,
            source="opinet",
            collected_at=timezone.now(),
        )
        old_apps.get_model("cards", "CardPolicy").objects.create(
            owner_id=user.id,
            card_name="Migration Card",
            issuer_name="Issuer",
            discount_type="per_liter",
            discount_value="80.00",
        )
        old_apps.get_model("cards", "CardCatalog").objects.create(card_name="Catalog Card")

        self.preserved_counts = {
            "users": old_apps.get_model("auth", "User").objects.count(),
            "stations": old_apps.get_model("stations", "GasStation").objects.count(),
            "prices": old_apps.get_model("stations", "FuelPrice").objects.count(),
            "policies": old_apps.get_model("cards", "CardPolicy").objects.count(),
            "catalog": old_apps.get_model("cards", "CardCatalog").objects.count(),
        }

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.migrate_to)
        super().tearDown()

    def test_reset_deletes_only_vehicle_profiles(self):
        self.assertEqual(self.apps.get_model("vehicles", "VehicleProfile").objects.count(), 0)
        self.assertEqual(
            self.apps.get_model("auth", "User").objects.count(),
            self.preserved_counts["users"],
        )
        self.assertEqual(
            self.apps.get_model("stations", "GasStation").objects.count(),
            self.preserved_counts["stations"],
        )
        self.assertEqual(
            self.apps.get_model("stations", "FuelPrice").objects.count(),
            self.preserved_counts["prices"],
        )
        self.assertEqual(
            self.apps.get_model("cards", "CardPolicy").objects.count(),
            self.preserved_counts["policies"],
        )
        self.assertEqual(
            self.apps.get_model("cards", "CardCatalog").objects.count(),
            self.preserved_counts["catalog"],
        )

    def test_vehicle_type_choices_are_the_nine_canonical_values(self):
        field = self.apps.get_model("vehicles", "VehicleProfile")._meta.get_field("vehicle_type")

        self.assertEqual(
            tuple(value for value, _label in field.choices),
            (
                "sedan",
                "suv",
                "rv_mpv",
                "sports_coupe",
                "hatchback",
                "wagon",
                "convertible",
                "pickup",
                "micro_city",
            ),
        )
