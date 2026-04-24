import os
import threading
import urllib.parse
import webbrowser

import requests
import urllib3
from flask import Flask, jsonify, render_template, request

from song_info_provider import (
    get_binaryify_base_url,
    get_gdstudio_search_url,
    get_provider_timeout,
    get_real_ip,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__, template_folder="templates")

GUI_HOST = os.environ.get("GUI_HOST", "127.0.0.1")
GUI_PORT = int(os.environ.get("GUI_PORT", "5080"))
GUI_OPEN_BROWSER = os.environ.get("GUI_OPEN_BROWSER", "true").lower() in ("1", "true", "yes", "on")
SEARCH_LIMIT = int(os.environ.get("GUI_SEARCH_LIMIT", "8"))


def build_http_session():
    session = requests.Session()
    session.trust_env = False
    session.headers.update(
        {
            "User-Agent": "smart-speaker-gui/1.0",
            "Accept": "application/json,text/plain,*/*",
        }
    )
    return session


def normalize_binaryify_song(song):
    album = song.get("al") or {}
    artists = [artist.get("name") for artist in song.get("ar", []) if artist.get("name")]
    return {
        "song_id": str(song.get("id", "")),
        "name": song.get("name", ""),
        "artists": artists,
        "album": album.get("name", ""),
        "cover_url": album.get("picUrl", ""),
        "provider": "binaryify",
    }


def normalize_gdstudio_song(song):
    return {
        "song_id": str(song.get("id") or song.get("url_id") or ""),
        "name": song.get("name", ""),
        "artists": song.get("artist") or [],
        "album": song.get("album", ""),
        "cover_url": "",
        "provider": "gdstudio_fallback",
    }


def search_binaryify(keyword, limit):
    session = build_http_session()
    response = session.get(
        f"{get_binaryify_base_url()}/cloudsearch",
        params={
            "keywords": keyword,
            "limit": limit,
            "type": 1,
            "realIP": get_real_ip(),
        },
        timeout=get_provider_timeout(),
        verify=False,
    )
    response.raise_for_status()
    payload = response.json()
    songs = ((payload or {}).get("result") or {}).get("songs") or []
    return [normalize_binaryify_song(song) for song in songs]


def search_gdstudio(keyword, limit):
    session = build_http_session()
    response = session.get(
        get_gdstudio_search_url(),
        params={
            "types": "search",
            "source": "netease",
            "count": limit,
            "name": keyword,
        },
        timeout=get_provider_timeout(),
        verify=False,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []
    return [normalize_gdstudio_song(song) for song in payload]


def search_songs(keyword, limit):
    errors = []

    try:
        songs = search_binaryify(keyword, limit)
        if songs:
            return songs, "binaryify", errors
        errors.append("binaryify returned no songs")
    except Exception as exc:
        errors.append(f"binaryify: {exc}")

    try:
        songs = search_gdstudio(keyword, limit)
        if songs:
            return songs, "gdstudio_fallback", errors
        errors.append("gdstudio returned no songs")
    except Exception as exc:
        errors.append(f"gdstudio: {exc}")

    raise RuntimeError("; ".join(errors) or "No song source succeeded")


def fetch_binaryify_play_url(song_id):
    session = build_http_session()
    endpoints = (
        ("/song/url/v1", {"id": song_id, "level": "standard", "realIP": get_real_ip()}),
        ("/song/url", {"id": song_id, "realIP": get_real_ip()}),
    )

    last_error = None
    for path, params in endpoints:
        try:
            response = session.get(
                f"{get_binaryify_base_url()}{path}",
                params=params,
                timeout=get_provider_timeout(),
                verify=False,
            )
            response.raise_for_status()
            payload = response.json()
            data = (payload or {}).get("data") or []
            if data and data[0].get("url"):
                return data[0]["url"]
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise RuntimeError(f"binaryify play url failed: {last_error}")
    raise RuntimeError("binaryify play url returned empty data")


def fetch_gdstudio_play_url(song_id):
    session = build_http_session()
    response = session.get(
        get_gdstudio_search_url(),
        params={
            "types": "url",
            "source": "netease",
            "id": song_id,
        },
        timeout=get_provider_timeout(),
        verify=False,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("url"):
        return payload["url"]
    raise RuntimeError("gdstudio play url returned empty data")


def fetch_gdstudio_cover_url(song_id):
    session = build_http_session()
    response = session.get(
        get_gdstudio_search_url(),
        params={
            "types": "pic",
            "source": "netease",
            "id": song_id,
        },
        timeout=get_provider_timeout(),
        verify=False,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("url", "")


def fetch_playback_payload(song_id, provider, fallback_cover_url):
    if provider == "binaryify":
        return {
            "play_url": fetch_binaryify_play_url(song_id),
            "cover_url": fallback_cover_url,
        }

    play_url = fetch_gdstudio_play_url(song_id)
    cover_url = fallback_cover_url or fetch_gdstudio_cover_url(song_id)
    return {
        "play_url": play_url,
        "cover_url": cover_url,
    }


@app.route("/")
def index():
    return render_template("song_player.html")


@app.route("/api/search")
def api_search():
    keyword = (request.args.get("q") or "").strip()
    if not keyword:
        return jsonify({"ok": False, "message": "Missing search keyword"}), 400

    limit = request.args.get("limit", type=int) or SEARCH_LIMIT

    try:
        songs, provider, warnings = search_songs(keyword, limit)
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 502

    return jsonify(
        {
            "ok": True,
            "keyword": keyword,
            "provider": provider,
            "warnings": warnings,
            "songs": songs,
        }
    )


@app.route("/api/play")
def api_play():
    song_id = (request.args.get("song_id") or "").strip()
    provider = (request.args.get("provider") or "").strip() or "binaryify"
    cover_url = (request.args.get("cover_url") or "").strip()

    if not song_id:
        return jsonify({"ok": False, "message": "Missing song_id"}), 400

    try:
        payload = fetch_playback_payload(song_id, provider, cover_url)
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 502

    return jsonify({"ok": True, **payload})


@app.route("/api/source")
def api_source():
    return jsonify(
        {
            "ok": True,
            "binaryify_base_url": get_binaryify_base_url(),
            "gdstudio_base_url": get_gdstudio_search_url(),
        }
    )


def open_browser_later():
    url = f"http://{GUI_HOST}:{GUI_PORT}/"
    webbrowser.open(url)


def main():
    if GUI_OPEN_BROWSER:
        threading.Timer(1.0, open_browser_later).start()
    print(f"[gui] music player available at http://{GUI_HOST}:{GUI_PORT}/", flush=True)
    app.run(host=GUI_HOST, port=GUI_PORT, debug=False)


if __name__ == "__main__":
    main()
