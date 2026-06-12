import os


def get_naver_maps_credentials():
    for client_id_key, client_secret_key in (
        (
            "NAVER_GEOCODING_CLIENT_ID",
            "NAVER_GEOCODING_CLIENT_SECRET",
        ),
        ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"),
    ):
        client_id = os.getenv(client_id_key, "").strip()
        client_secret = os.getenv(client_secret_key, "").strip()
        if client_id and client_secret:
            return client_id, client_secret
    return "", ""
