export const VEHICLE_NAME_MAX_LENGTH = 40;

export const VEHICLE_TYPES = Object.freeze([
  {
    value: "compact",
    label: "소형차",
    description: "도심 주행에 알맞은 작은 차체",
    imageUrl: new URL("../../assets/vehicles/compact.svg", import.meta.url).href
  },
  {
    value: "sedan",
    label: "세단",
    description: "균형 잡힌 기본 승용차 형태",
    imageUrl: new URL("../../assets/vehicles/sedan.svg", import.meta.url).href
  },
  {
    value: "suv",
    label: "SUV",
    description: "높은 차체와 넉넉한 적재 공간",
    imageUrl: new URL("../../assets/vehicles/suv.svg", import.meta.url).href
  },
  {
    value: "large_rv",
    label: "대형/RV",
    description: "카니발처럼 큰 다인승 차량",
    imageUrl: new URL("../../assets/vehicles/large-rv.svg", import.meta.url).href
  },
  {
    value: "sports",
    label: "스포츠카",
    description: "낮고 날렵한 고성능 차체",
    imageUrl: new URL("../../assets/vehicles/sports.svg", import.meta.url).href
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

  const payload = {
    name: normalizeVehicleName(source.name),
    vehicle_type: presentation.value,
    fuel_type: source.fuel_type,
    fuel_efficiency_kmpl: efficiency
  };

  if (typeof source.is_default === "boolean") {
    payload.is_default = source.is_default;
  }
  return payload;
}

export function getVehicleSelectorLabel(vehicle) {
  const type = getVehiclePresentation(vehicle?.vehicle_type);
  const efficiency = Number(vehicle?.fuel_efficiency_kmpl || 0).toFixed(1);
  return `${vehicle?.name || "이름 없는 차량"} · ${type.label} · ${efficiency} km/L${vehicle?.is_default ? " · 대표" : ""}`;
}
