import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  VEHICLE_NAME_MAX_LENGTH,
  VEHICLE_FUEL_LABELS,
  VEHICLE_FUEL_PRICE_UNITS,
  VEHICLE_TYPES,
  buildVehiclePayload,
  getVehicleFuelPriceUnit,
  getVehiclePresentation,
  getVehicleSelectorLabel,
  normalizeVehicleName
} from "./vehiclePresentation.js";

test("vehicle fuel labels are shared Korean presentation metadata", () => {
  assert.deepEqual(VEHICLE_FUEL_LABELS, {
    gasoline: "휘발유",
    diesel: "경유",
    lpg: "LPG",
    premium_gasoline: "고급 휘발유"
  });
});

test("vehicle fuel price units are shared across recommendation calculations", () => {
  assert.equal(getVehicleFuelPriceUnit("diesel"), VEHICLE_FUEL_PRICE_UNITS.diesel);
  assert.equal(getVehicleFuelPriceUnit("unknown"), VEHICLE_FUEL_PRICE_UNITS.gasoline);
});

test("vehicle type catalog exposes nine canonical distinct static silhouettes", () => {
  assert.deepEqual(VEHICLE_TYPES.map(({ value }) => value), [
    "sedan",
    "suv",
    "rv_mpv",
    "sports_coupe",
    "hatchback",
    "wagon",
    "convertible",
    "pickup",
    "micro_city"
  ]);
  assert.deepEqual(VEHICLE_TYPES.map(({ label }) => label), [
    "세단",
    "SUV",
    "RV / MPV",
    "쿠페",
    "해치백",
    "왜건",
    "로드스터",
    "픽업트럭",
    "경차"
  ]);
  assert.equal(new Set(VEHICLE_TYPES.map(({ imageUrl }) => imageUrl)).size, 9);
  assert.ok(VEHICLE_TYPES.every((type) => !Object.hasOwn(type, "description")));
});

test("vehicle artwork uses nine distinct PNG crops from the supplied design", async () => {
  const artwork = await Promise.all(
    VEHICLE_TYPES.map(async ({ imageUrl }) => ({
      imageUrl,
      source: await readFile(new URL(imageUrl))
    }))
  );

  for (const { imageUrl, source } of artwork) {
    assert.match(imageUrl, /\.png$/);
    assert.equal(source.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  }

  const hashes = artwork.map(({ source }) =>
    createHash("sha256").update(source).digest("hex")
  );
  assert.equal(new Set(hashes).size, VEHICLE_TYPES.length);
});

test("unknown type falls back to sedan presentation", () => {
  assert.equal(getVehiclePresentation("unknown").value, "sedan");
});

test("vehicle name normalization trims and enforces the contract", () => {
  assert.equal(normalizeVehicleName("  우리 차  "), "우리 차");
  assert.throws(() => normalizeVehicleName("   "), /차량 이름/);
  assert.throws(() => normalizeVehicleName("가".repeat(VEHICLE_NAME_MAX_LENGTH + 1)), /40자/);
});

test("payload builder includes editable vehicle data and excludes read-only state", () => {
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
      fuel_efficiency_kmpl: 13.4
    }
  );
});

test("selector label puts the saved name first", () => {
  assert.equal(
    getVehicleSelectorLabel({
      name: "출퇴근차",
      vehicle_type: "micro_city",
      fuel_efficiency_kmpl: "15.2",
      is_default: true
    }),
    "출퇴근차 · 경차 · 15.2 km/L · 대표"
  );
});
