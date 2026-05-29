import os
import json
import urllib.parse
import urllib.request
import pyproj
from django.utils import timezone

from stations.models import FuelPrice, GasStation


class OpinetConfigurationError(RuntimeError):
    pass


class OpinetMappingError(ValueError):
    pass


OPINET_PRODUCT_TO_FUEL_TYPE = {
    "B027": FuelPrice.FuelType.GASOLINE,
    "D047": FuelPrice.FuelType.DIESEL,
    "B034": FuelPrice.FuelType.PREMIUM_GASOLINE,
    "K015": FuelPrice.FuelType.LPG,
}
FUEL_TYPE_TO_OPINET_PRODUCT = {
    fuel_type: product_code
    for product_code, fuel_type in OPINET_PRODUCT_TO_FUEL_TYPE.items()
}

OPINET_MAX_RADIUS_KM = 5.0
KATEC_PROJ = "+proj=tmerc +lat_0=38N +lon_0=128E +ellps=bessel +x_0=400000 +y_0=600000 +k=0.9999 +units=m +towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43"
WGS84_PROJ = "+proj=latlong +datum=WGS84 +ellps=WGS84"
KATEC_TO_WGS84_TRANSFORMER = pyproj.Transformer.from_crs(KATEC_PROJ, WGS84_PROJ, always_xy=True)
WGS84_TO_KATEC_TRANSFORMER = pyproj.Transformer.from_crs(WGS84_PROJ, KATEC_PROJ, always_xy=True)

OPINET_BRAND_TO_STATION_BRAND = {
    "SKE": GasStation.Brand.SK,
    "GSC": GasStation.Brand.GS,
    "HDO": GasStation.Brand.HD_HYUNDAI,
    "SOL": GasStation.Brand.S_OIL,
}


def _first_present(row, *keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def map_opinet_product_code(prodcd):
    try:
        return OPINET_PRODUCT_TO_FUEL_TYPE[prodcd]
    except KeyError as exc:
        raise OpinetMappingError(f"Unsupported Opinet product code: {prodcd}") from exc


def map_opinet_brand_code(poll_div_cd):
    return OPINET_BRAND_TO_STATION_BRAND.get(poll_div_cd, GasStation.Brand.OTHER)


def katec_to_wgs84(x, y):
    lon, lat = KATEC_TO_WGS84_TRANSFORMER.transform(float(x), float(y))
    return lat, lon


def wgs84_to_katec(latitude, longitude):
    x, y = WGS84_TO_KATEC_TRANSFORMER.transform(float(longitude), float(latitude))
    return x, y


def normalize_opinet_radius_meters(radius_km):
    radius = float(radius_km or OPINET_MAX_RADIUS_KM)
    radius = max(1.0, min(radius, OPINET_MAX_RADIUS_KM))
    return int(radius * 1000)


def opinet_product_codes_for_fuel_type(fuel_type=None):
    if not fuel_type:
        return ["B027", "D047", "B034", "K015"]
    try:
        return [FUEL_TYPE_TO_OPINET_PRODUCT[fuel_type]]
    except KeyError as exc:
        raise OpinetMappingError(f"Unsupported SmartFuel fuel type: {fuel_type}") from exc


def normalize_opinet_price_row(row, default_product_code=None):
    product_code = _first_present(row, "PRODCD") or default_product_code
    price = _first_present(row, "PRICE", "OIL_PRICE")
    if not product_code:
        raise OpinetMappingError("Opinet price row is missing PRODCD.")
    if price in (None, ""):
        raise OpinetMappingError("Opinet price row is missing PRICE.")

    try:
        price_per_liter = int(float(price))
    except (TypeError, ValueError) as exc:
        raise OpinetMappingError(f"Invalid Opinet price: {price}") from exc

    return {
        "fuel_type": map_opinet_product_code(product_code),
        "price_per_liter": price_per_liter,
        "trade_date": _first_present(row, "TRADE_DT"),
        "trade_time": _first_present(row, "TRADE_TM"),
        "source": FuelPrice.Source.OPINET,
    }


def normalize_opinet_station_row(row):
    station_id = _first_present(row, "UNI_ID")
    if not station_id:
        raise OpinetMappingError("Opinet station row is missing UNI_ID.")

    x = _first_present(row, "GIS_X_COOR")
    y = _first_present(row, "GIS_Y_COOR")
    lat, lon = None, None
    if x and y:
        try:
            lat, lon = katec_to_wgs84(x, y)
        except (ValueError, TypeError, Exception):
            pass

    res = {
        "external_station_id": station_id,
        "name": _first_present(row, "OS_NM") or "",
        "brand": map_opinet_brand_code(_first_present(row, "POLL_DIV_CD", "POLL_DIV_CO")),
        "address": _first_present(row, "NEW_ADR", "VAN_ADR") or "",
        "katec_x": x,
        "katec_y": y,
        "lpg_yn": _first_present(row, "LPG_YN"),
    }
    if lat is not None and lon is not None:
        res["latitude"] = lat
        res["longitude"] = lon
    return res


class OpinetClient:
    BASE_URL = "https://www.opinet.co.kr/api"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPINET_API_KEY", "").strip()
        if not self.api_key:
            raise OpinetConfigurationError("OPINET_API_KEY is required for Opinet synchronization.")

    def _get_json(self, endpoint, params=None):
        query = urllib.parse.urlencode(
            {
                "out": "json",
                "code": self.api_key,
                **(params or {}),
            }
        )
        url = f"{self.BASE_URL}/{endpoint}?{query}"
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_average_price_rows(self):
        payload = self._get_json("avgAllPrice.do")
        rows = payload.get("RESULT", {}).get("OIL", [])
        if isinstance(rows, dict):
            return [rows]
        return rows or []

    def fetch_price_rows(self, latitude=None, longitude=None, radius_km=OPINET_MAX_RADIUS_KM, fuel_type=None):
        """Fetch Opinet fuel price rows around a user-selected WGS84 location."""
        if latitude is None or longitude is None:
            return []

        x, y = wgs84_to_katec(latitude, longitude)
        radius_meters = normalize_opinet_radius_meters(radius_km)

        all_collected_rows = []

        for prodcd in opinet_product_codes_for_fuel_type(fuel_type):
            try:
                payload = self._get_json(
                    "aroundAll.do",
                    {
                        "x": f"{x:.1f}",
                        "y": f"{y:.1f}",
                        "radius": str(radius_meters),
                        "prodcd": prodcd,
                        "sort": "1",
                    }
                )
                rows = payload.get("RESULT", {}).get("OIL", [])
                if isinstance(rows, dict):
                    rows = [rows]
                elif not rows:
                    rows = []
                
                for r in rows:
                    if "PRODCD" not in r:
                        r["PRODCD"] = prodcd
                    all_collected_rows.append(r)
            except Exception:
                pass
                
        return all_collected_rows


def save_opinet_price_rows(rows, collected_at=None):
    collected_at = collected_at or timezone.now()
    station_count = 0
    price_count = 0
    skipped_count = 0

    for row in rows:
        try:
            station_data = normalize_opinet_station_row(row)
            external_id = station_data.pop("external_station_id")
            if "latitude" not in station_data or "longitude" not in station_data:
                raise OpinetMappingError("Opinet station row is missing usable WGS84 coordinates.")

            allowed_fields = {"name", "brand", "address", "latitude", "longitude", "is_self"}
            defaults = {key: value for key, value in station_data.items() if key in allowed_fields}
            if not defaults.get("address"):
                defaults["address"] = "주소 정보 없음"

            _station, created = GasStation.objects.update_or_create(
                external_station_id=external_id,
                defaults=defaults,
            )
            if created:
                station_count += 1

            price_data = normalize_opinet_price_row(row)
            FuelPrice.objects.create(
                station=_station,
                fuel_type=price_data["fuel_type"],
                price_per_liter=price_data["price_per_liter"],
                source=FuelPrice.Source.OPINET,
                collected_at=collected_at,
            )
            price_count += 1
        except (OpinetMappingError, ValueError):
            skipped_count += 1

    return {
        "stations_created": station_count,
        "prices_created": price_count,
        "rows_skipped": skipped_count,
    }
