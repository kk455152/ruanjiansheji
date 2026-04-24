import os
from datetime import datetime, timezone

import requests

DEFAULT_BINARYIFY_BASE_URL = "https://netease-cloud-music-api-one-rouge.vercel.app"
DEFAULT_GDSTUDIO_SEARCH_URL = "https://music-api.gdstudio.xyz/api.php"
DEFAULT_PROVIDER_MODE = "auto"
DEFAULT_TIMEOUT = 10.0
DEFAULT_REAL_IP = "116.25.146.177"


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def get_provider_mode():
    return os.environ.get("SONG_INFO_PROVIDER_MODE", DEFAULT_PROVIDER_MODE).strip().lower()


def get_binaryify_base_url():
    return os.environ.get("SONG_INFO_PROVIDER_BASE_URL", DEFAULT_BINARYIFY_BASE_URL).rstrip("/")


def get_gdstudio_search_url():
    return os.environ.get("SONG_INFO_FALLBACK_URL", DEFAULT_GDSTUDIO_SEARCH_URL).rstrip("/")


def get_provider_timeout():
    return float(os.environ.get("SONG_INFO_PROVIDER_TIMEOUT", str(DEFAULT_TIMEOUT)))


def get_real_ip():
    return os.environ.get("SONG_INFO_PROVIDER_REAL_IP", DEFAULT_REAL_IP).strip()


def get_http_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "smart-speaker-song-info/1.0",
            "Accept": "application/json,text/plain,*/*",
        }
    )
    return session


def extract_keyword(value):
    if isinstance(value, str):
        keyword = value.strip()
    elif isinstance(value, dict):
        keyword = str(value.get("keyword", "")).strip()
    else:
        keyword = str(value).strip()

    if not keyword:
        raise ValueError("Song keyword is empty")
    return keyword


def normalize_song_payload(keyword, provider_name, provider_url, song_payload):
    return {
        "keyword": keyword,
        "provider": provider_name,
        "provider_url": provider_url,
        "fetched_at": utcnow_iso(),
        "song": song_payload,
    }


def fetch_binaryify_song_info(keyword):
    session = get_http_session()
    base_url = get_binaryify_base_url()
    timeout = get_provider_timeout()

    search_response = session.get(
        f"{base_url}/cloudsearch",
        params={
            "keywords": keyword,
            "limit": 1,
            "type": 1,
            "realIP": get_real_ip(),
        },
        timeout=timeout,
        verify=False,
    )
    search_response.raise_for_status()
    search_data = search_response.json()

    songs = ((search_data or {}).get("result") or {}).get("songs") or []
    if not songs:
        raise ValueError(f"Binaryify provider returned no songs for keyword: {keyword}")

    song_id = songs[0].get("id")
    detail_response = session.get(
        f"{base_url}/song/detail",
        params={"ids": song_id, "realIP": get_real_ip()},
        timeout=timeout,
        verify=False,
    )
    detail_response.raise_for_status()
    detail_data = detail_response.json()
    detail_list = (detail_data or {}).get("songs") or []
    detail_song = detail_list[0] if detail_list else songs[0]

    normalized_song = {
        "song_id": str(detail_song.get("id") or song_id),
        "name": detail_song.get("name") or songs[0].get("name"),
        "artists": [artist.get("name") for artist in detail_song.get("ar", []) if artist.get("name")],
        "album": ((detail_song.get("al") or {}).get("name")) or "",
        "duration_ms": detail_song.get("dt"),
        "cover_url": ((detail_song.get("al") or {}).get("picUrl")) or "",
        "raw": detail_song,
    }
    return normalize_song_payload(keyword, "binaryify", base_url, normalized_song)


def fetch_gdstudio_song_info(keyword):
    session = get_http_session()
    provider_url = get_gdstudio_search_url()
    timeout = get_provider_timeout()
    payload = []
    for _ in range(2):
        response = session.get(
            provider_url,
            params={
                "types": "search",
                "source": "netease",
                "count": 1,
                "name": keyword,
            },
            timeout=timeout,
            verify=False,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            break
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Fallback provider returned no songs for keyword: {keyword}")

    item = payload[0]
    normalized_song = {
        "song_id": str(item.get("id") or item.get("url_id") or ""),
        "name": item.get("name") or "",
        "artists": item.get("artist") or [],
        "album": item.get("album") or "",
        "duration_ms": None,
        "cover_url": item.get("pic_url") or item.get("pic") or "",
        "raw": item,
    }
    return normalize_song_payload(keyword, "gdstudio_fallback", provider_url, normalized_song)


def fetch_song_info(value):
    keyword = extract_keyword(value)
    mode = get_provider_mode()
    errors = []

    if mode in ("auto", "binaryify"):
        try:
            return fetch_binaryify_song_info(keyword)
        except Exception as exc:
            errors.append(f"binaryify: {exc}")
            if mode == "binaryify":
                raise

    if mode in ("auto", "fallback", "gdstudio"):
        try:
            return fetch_gdstudio_song_info(keyword)
        except Exception as exc:
            errors.append(f"fallback: {exc}")

    raise RuntimeError("; ".join(errors) or "No song provider succeeded")
