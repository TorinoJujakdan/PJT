export const VEHICLE_NAME_MAX_LENGTH = 40;

export const VEHICLE_FUEL_LABELS = Object.freeze({
  gasoline: "휘발유",
  diesel: "경유",
  lpg: "LPG",
  premium_gasoline: "고급 휘발유"
});

export const VEHICLE_FUEL_PRICE_UNITS = Object.freeze({
  gasoline: 1650,
  diesel: 1500,
  lpg: 1000,
  premium_gasoline: 1850
});

export function getVehicleFuelPriceUnit(type) {
  return VEHICLE_FUEL_PRICE_UNITS[type] ?? VEHICLE_FUEL_PRICE_UNITS.gasoline;
}

// These are direct pixel crops from the supplied car_design.png. Keeping them
// in this shared catalog guarantees that every vehicle surface uses the same
// original artwork without recreating or restyling the silhouettes.
export const VEHICLE_TYPES = Object.freeze([
  {
    value: "sedan",
    label: "세단",
    imageUrl: new URL("../../assets/vehicles/sedan.png", import.meta.url).href
  },
  {
    value: "suv",
    label: "SUV",
    imageUrl: new URL("../../assets/vehicles/suv.png", import.meta.url).href
  },
  {
    value: "rv_mpv",
    label: "RV / MPV",
    imageUrl: new URL("../../assets/vehicles/rv-mpv.png", import.meta.url).href
  },
  {
    value: "sports_coupe",
    label: "쿠페",
    imageUrl: new URL("../../assets/vehicles/sports-coupe.png", import.meta.url).href,
    imageClass: "vehicleImageFlipped"
  },
  {
    value: "hatchback",
    label: "해치백",
    imageUrl: new URL("../../assets/vehicles/hatchback.png", import.meta.url).href
  },
  {
    value: "wagon",
    label: "왜건",
    imageUrl: new URL("../../assets/vehicles/wagon.png", import.meta.url).href
  },
  {
    value: "convertible",
    label: "로드스터",
    imageUrl: new URL("../../assets/vehicles/convertible.png", import.meta.url).href
  },
  {
    value: "pickup",
    label: "픽업트럭",
    imageUrl: new URL("../../assets/vehicles/pickup.png", import.meta.url).href
  },
  {
    value: "micro_city",
    label: "경차",
    imageUrl: new URL("../../assets/vehicles/micro-city.png", import.meta.url).href
  }
]);

const sedanPresentation = VEHICLE_TYPES.find(({ value }) => value === "sedan");

export function getVehiclePresentation(vehicleType) {
  return VEHICLE_TYPES.find(({ value }) => value === vehicleType) || sedanPresentation;
}

export function normalizeVehicleName(value) {
  const name = String(value ?? "").trim();
  if (!name) {
    throw new Error("차량 이름을 입력해 주세요.");
  }
  if (name.length > VEHICLE_NAME_MAX_LENGTH) {
    throw new Error(`차량 이름은 ${VEHICLE_NAME_MAX_LENGTH}자 이하로 입력해 주세요.`);
  }
  return name;
}

export function buildVehiclePayload(source) {
  const presentation = VEHICLE_TYPES.find(({ value }) => value === source.vehicle_type);
  if (!presentation) {
    throw new Error("차량 유형을 선택해 주세요.");
  }

  const efficiency = Number(source.fuel_efficiency_kmpl);
  if (!Number.isFinite(efficiency) || efficiency < 1 || efficiency > 50) {
    throw new Error("연비는 1.0~50.0km/L 범위로 입력해 주세요.");
  }

  return {
    name: normalizeVehicleName(source.name),
    vehicle_type: presentation.value,
    fuel_type: source.fuel_type,
    fuel_efficiency_kmpl: efficiency
  };
}

export function getVehicleSelectorLabel(vehicle) {
  const type = getVehiclePresentation(vehicle?.vehicle_type);
  const efficiency = Number(vehicle?.fuel_efficiency_kmpl || 0).toFixed(1);
  return `${vehicle?.name || "이름 없는 차량"} · ${type.label} · ${efficiency} km/L${vehicle?.is_default ? " · 대표" : ""}`;
}
