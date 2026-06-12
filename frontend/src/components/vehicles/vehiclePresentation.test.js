import assert from "node:assert/strict";
import test from "node:test";

import {
  VEHICLE_NAME_MAX_LENGTH,
  VEHICLE_TYPES,
  buildVehiclePayload,
  getVehiclePresentation,
  getVehicleSelectorLabel,
  normalizeVehicleName
} from "./vehiclePresentation.js";

test("vehicle type catalog exposes five distinct static silhouettes", () => {
  assert.deepEqual(VEHICLE_TYPES.map(({ value }) => value), [
    "compact",
    "sedan",
    "suv",
    "large_rv",
    "sports"
  ]);
  assert.equal(new Set(VEHICLE_TYPES.map(({ imageUrl }) => imageUrl)).size, 5);
});

test("unknown type falls back to sedan presentation", () => {
  assert.equal(getVehiclePresentation("unknown").value, "sedan");
});

test("vehicle name normalization trims and enforces the contract", () => {
  assert.equal(normalizeVehicleName("  우리 차  "), "우리 차");
  assert.throws(() => normalizeVehicleName("   "), /차량 이름/);
  assert.throws(() => normalizeVehicleName("가".repeat(VEHICLE_NAME_MAX_LENGTH + 1)), /40자/);
});

test("payload builder includes vehicle identity and fuel data", () => {
  assert.deepEqual(
    buildVehiclePayload({
      name: "  출퇴근차 ",
      vehicle_type: "suv",
      fuel_type: "diesel",
      fuel_efficiency_kmpl: "13.4",
      is_default: true
    }),
    {
      name: "출퇴근차",
      vehicle_type: "suv",
      fuel_type: "diesel",
      fuel_efficiency_kmpl: 13.4,
      is_default: true
    }
  );
});

test("selector label puts the saved name first", () => {
  assert.equal(
    getVehicleSelectorLabel({
      name: "출퇴근차",
      vehicle_type: "compact",
      fuel_efficiency_kmpl: "15.2",
      is_default: true
    }),
    "출퇴근차 · 소형차 · 15.2 km/L · 대표"
  );
});
