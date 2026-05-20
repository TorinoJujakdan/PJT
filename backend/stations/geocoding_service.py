import os
import urllib.request
import urllib.parse
import json

PRESETS = [
    { "name": "서울시청", "address": "서울특별시 중구 세종대로 110", "latitude": 37.5665, "longitude": 126.9780 },
    { "name": "강남역", "address": "서울특별시 강남구 강남대로 396", "latitude": 37.4979, "longitude": 127.0276 },
    { "name": "판교역 / 테크노밸리", "address": "경기도 성남시 분당구 판교역로 150", "latitude": 37.3948, "longitude": 127.1112 },
    { "name": "대전시청", "address": "대전광역시 서구 둔산로 100", "latitude": 36.3504, "longitude": 127.3848 },
    { "name": "부산역", "address": "부산광역시 동구 중앙대로 206", "latitude": 35.1152, "longitude": 129.0422 },
    { "name": "홍대입구역", "address": "서울특별시 마포구 양화로 160", "latitude": 37.5575, "longitude": 126.9244 },
    { "name": "신촌역", "address": "서울특별시 마포구 신촌로 90", "latitude": 37.5552, "longitude": 126.9369 },
    { "name": "건대입구역", "address": "서울특별시 광진구 아차산로 272", "latitude": 37.5404, "longitude": 127.0692 },
    { "name": "명동역", "address": "서울특별시 중구 퇴계로 126", "latitude": 37.5609, "longitude": 126.9863 },
    { "name": "여의도역", "address": "서울특별시 영등포구 여의도동 3", "latitude": 37.5216, "longitude": 126.9242 },
    { "name": "잠실역", "address": "서울특별시 송파구 올림픽로 265", "latitude": 37.5133, "longitude": 127.1001 },
    { "name": "삼성역", "address": "서울특별시 강남구 테헤란로 538", "latitude": 37.5088, "longitude": 127.0631 },
    { "name": "신도림역", "address": "서울특별시 구로구 새말로 117-21", "latitude": 37.5089, "longitude": 126.8913 },
    { "name": "혜화역 (대학로)", "address": "서울특별시 종로구 대학로 120", "latitude": 37.5822, "longitude": 127.0019 },
    { "name": "종로3가역", "address": "서울특별시 종로구 돈화문로 30", "latitude": 37.5704, "longitude": 126.9922 },
    { "name": "광화문역 (세종문화회관)", "address": "서울특별시 종로구 세종대로 172", "latitude": 37.5716, "longitude": 126.9765 },
    { "name": "이태원역", "address": "서울특별시 용산구 이태원로 177", "latitude": 37.5345, "longitude": 126.9946 },
    { "name": "인천역", "address": "인천광역시 중구 제물량로 269", "latitude": 37.4764, "longitude": 126.6171 },
    { "name": "부평역", "address": "인천광역시 부평구 광장로 16", "latitude": 37.4895, "longitude": 126.7248 },
    { "name": "수원역", "address": "경기도 수원시 팔달구 덕영대로 924", "latitude": 37.2662, "longitude": 127.0001 },
    { "name": "분당 정자역", "address": "경기도 성남시 분당구 성남대로 333", "latitude": 37.3674, "longitude": 127.1082 },
    { "name": "일산시청", "address": "경기도 고양시 덕양구 고양시청로 10", "latitude": 37.6584, "longitude": 126.8320 },
    { "name": "의정부역", "address": "경기도 의정부시 평화로 525", "latitude": 37.7396, "longitude": 127.0423 },
    { "name": "춘천시청", "address": "강원특별자치도 춘천시 시청길 11", "latitude": 37.8813, "longitude": 127.7298 },
    { "name": "청주시청", "address": "충청북도 청주시 상당구 상당로 155", "latitude": 36.6424, "longitude": 127.4890 },
    { "name": "천안역", "address": "충청남도 천안시 동남구 대흥로 239", "latitude": 36.8100, "longitude": 127.1462 },
    { "name": "대구역", "address": "대구광역시 북구 태평로 161", "latitude": 35.8767, "longitude": 128.5971 },
    { "name": "동대구역", "address": "대구광역시 동구 동대구로 550", "latitude": 35.8822, "longitude": 128.6293 },
    { "name": "경북대 대구캠퍼스", "address": "대구광역시 북구 대학로 80", "latitude": 35.8906, "longitude": 128.6121 },
    { "name": "울산시청", "address": "울산광역시 남구 중앙로 201", "latitude": 35.5396, "longitude": 129.3115 },
    { "name": "창원시청", "address": "경상남도 창원시 성산구 중앙대로 151", "latitude": 35.2281, "longitude": 128.6811 },
    { "name": "광주시청", "address": "광주광역시 서구 내방로 111", "latitude": 35.1601, "longitude": 126.8514 },
    { "name": "전주시청", "address": "전북특별자치도 전주시 완산구 노송광장로 10", "latitude": 35.8242, "longitude": 127.1480 },
    { "name": "목포역", "address": "전라남도 목포시 영산로 98", "latitude": 34.7912, "longitude": 126.3865 },
    { "name": "여수시청", "address": "전라남도 여수시 시청로 1", "latitude": 34.7604, "longitude": 127.6622 },
    { "name": "제주도청", "address": "제주특별자치도 제주시 문송길 5", "latitude": 33.4890, "longitude": 126.4983 },
    { "name": "서귀포시청", "address": "제주특별자치도 서귀포시 중앙로 105", "latitude": 33.2541, "longitude": 126.5601 }
]

def geocode_query_fallback(query: str):
    """Fallback geocoding matching local presets (string search)."""
    normalized_query = query.replace(" ", "").lower()
    results = []
    for preset in PRESETS:
        normalized_name = preset["name"].replace(" ", "").lower()
        normalized_address = preset["address"].replace(" ", "").lower()
        if normalized_query in normalized_name or normalized_query in normalized_address:
            results.append(preset)
    return results

def geocode_query(query: str):
    """Query location coordinates from Naver Map API with a resilient fallback."""
    if not query or not query.strip():
        return []

    client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        # Fallback if API keys are not provided (resilient local dev)
        return geocode_query_fallback(query)

    try:
        url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query=" + urllib.parse.quote(query)
        req = urllib.request.Request(url)
        req.add_header("X-NCP-APIGW-API-KEY-ID", client_id)
        req.add_header("X-NCP-APIGW-API-KEY", client_secret)

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                addresses = data.get("addresses", [])
                results = []
                for addr in addresses:
                    results.append({
                        "name": addr.get("roadAddress") or addr.get("jibunAddress") or query,
                        "address": addr.get("roadAddress") or addr.get("jibunAddress") or "",
                        "latitude": float(addr.get("y")),
                        "longitude": float(addr.get("x")),
                    })
                return results
    except Exception:
        # Fallback to local search if external API request fails
        pass

    return geocode_query_fallback(query)
