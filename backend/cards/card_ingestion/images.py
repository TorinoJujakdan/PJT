from __future__ import annotations

import hashlib
import mimetypes
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.core.files.base import ContentFile

from .domain import MAX_CARD_IMAGE_BYTES, ALLOWED_IMAGE_CONTENT_TYPES

class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def build_card_image_filename(candidate, image_url, content_type=""):
    parsed = urlparse(image_url or "")
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = mimetypes.guess_extension(content_type or "") or ".img"
    digest_source = f"{candidate.source_url}|{image_url}|{candidate.card_name}".encode("utf-8", errors="ignore")
    digest = hashlib.sha256(digest_source).hexdigest()[:16]
    return f"card-{digest}{suffix}"


def is_safe_url(url):
    import socket
    import ipaddress
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_multicast or ip_obj.is_unspecified:
                return False
        return True
    except (socket.gaierror, ValueError):
        return False


def fetch_remote_image(image_url, timeout=8, max_bytes=MAX_CARD_IMAGE_BYTES):
    parsed = urlparse(image_url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, ""

    if not is_safe_url(image_url):
        return None, ""

    request = Request(
        image_url,
        headers={"User-Agent": "SmartFuelCardIngestion/1.0 (+https://card-search.naver.com)"},
    )
    try:
        opener = build_opener(NoRedirectHandler)
        with opener.open(request, timeout=timeout) as response:
            content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                return None, content_type
            
            start_time = time.time()
            content = bytearray()
            while True:
                if time.time() - start_time > timeout:
                    return None, ""
                chunk = response.read(8192)
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > max_bytes:
                    break
            content = bytes(content)
    except (HTTPError, URLError, TimeoutError, OSError):
        return None, ""

    if not content or len(content) > max_bytes:
        return None, content_type
    return content, content_type


def persist_catalog_card_image(catalog_card, candidate, fetch_image=fetch_remote_image):
    """Download the public card artwork and store the DB-backed FileField path.

    The original image URL is retained as provenance only; recommendation/UI code can
    use card_image_file instead of hot-linking the remote image.
    """
    image_url = (candidate.card_image_url or "").strip()
    if not image_url:
        return False

    catalog_card.card_image_original_url = image_url[:200]
    if catalog_card.card_image_file and catalog_card.card_image_url == image_url:
        return False

    content, content_type = fetch_image(image_url)
    if not content:
        return False

    filename = build_card_image_filename(candidate, image_url, content_type)
    catalog_card.card_image_file.save(filename, ContentFile(content), save=False)
    return True


