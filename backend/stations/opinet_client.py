import os
import json
import urllib.parse
import urllib.request
import pyproj

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
            katec_proj = "+proj=tmerc +lat_0=38N +lon_0=128E +ellps=bessel +x_0=400000 +y_0=600000 +k=0.9999 +units=m +towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43"
            wgs84_proj = "+proj=latlong +datum=WGS84 +ellps=WGS84"
            transformer = pyproj.Transformer.from_crs(katec_proj, wgs84_proj, always_xy=True)
            lon, lat = transformer.transform(float(x), float(y))
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

    def fetch_price_rows(self):
        """Fetch Opinet fuel price rows.

        강남역 주변 반경 5km 이내의 휘발유(B027) 및 경유(D047) 주유소 및 가격 수집
        """
        base_x = 314871.8
        base_y = 544012.0
        
        all_collected_rows = []
        
        for prodcd in ["B027", "D047"]:
            try:
                payload = self._get_json(
                    "aroundAll.do",
                    {
                        "x": str(base_x),
                        "y": str(base_y),
                        "radius": "5000",
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
