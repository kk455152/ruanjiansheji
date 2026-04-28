import os
import threading
import urllib.parse
import webbrowser

from flask import Flask, jsonify, render_template

from song_info_provider import fetch_song_info

app = Flask(__name__, template_folder="templates")

GUI_HOST = os.environ.get("GUI_HOST", "127.0.0.1")
GUI_PORT = int(os.environ.get("GUI_PORT", "5080"))
GUI_WAKE_KEYWORD = os.environ.get("GUI_WAKE_KEYWORD", "稻香").strip() or "稻香"


def build_song_context(keyword):
    payload = fetch_song_info(keyword)
    song = payload["song"]
    song_id = str(song.get("song_id") or "")
    if not song_id:
        raise RuntimeError("Song source returned empty song_id")

    return {
        "keyword": keyword,
        "provider": payload.get("provider", ""),
        "provider_url": payload.get("provider_url", ""),
        "song_id": song_id,
        "song_name": song.get("name", keyword),
        "artists": " / ".join(song.get("artists") or []) or "未知歌手",
        "album": song.get("album", ""),
        "cover_url": song.get("cover_url", ""),
        "app_uri": f"orpheus://song/{song_id}/?autoplay=1",
        "app_uri_fallback": f"orpheus://song/{song_id}",
        "web_url": f"https://music.163.com/#/song?id={song_id}",
    }


def try_open_app_uri(song_context):
    if os.name != "nt":
        return False

    for candidate in (
        song_context["app_uri"],
        song_context["app_uri_fallback"],
        "orpheus://",
    ):
        try:
            os.startfile(candidate)  # type: ignore[attr-defined]
            return True
        except OSError:
            continue
        except Exception:
            continue
    return False


def open_browser_later():
    webbrowser.open(f"http://{GUI_HOST}:{GUI_PORT}/")


@app.route("/")
def index():
    return render_template("cloudmusic_launcher.html", **app.config["SONG_CONTEXT"])


@app.route("/api/context")
def api_context():
    return jsonify({"ok": True, **app.config["SONG_CONTEXT"]})


def main():
    song_context = build_song_context(GUI_WAKE_KEYWORD)
    app.config["SONG_CONTEXT"] = song_context

    launched = try_open_app_uri(song_context)
    if launched:
        print(
            f"[gui] 已尝试唤起网易云客户端: {song_context['song_name']} "
            f"({song_context['song_id']})",
            flush=True,
        )
        return

    print("[gui] 本机未直接唤起网易云客户端，正在打开本地引导页。", flush=True)
    threading.Timer(0.8, open_browser_later).start()
    app.run(host=GUI_HOST, port=GUI_PORT, debug=False)


if __name__ == "__main__":
    main()
