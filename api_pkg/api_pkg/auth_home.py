from . import api_bp
from .common import (
    body_json,
    create_or_get_wechat_user,
    create_token,
    current_user_id,
    current_user_profile,
    device_list,
    get_device,
    get_song,
    history_rows,
    ok,
    plain,
    now_str,
)


@api_bp.get("/_health")
def health():
    return ok("api routes loaded", {"time": now_str(), "mode": "mysql-mongo-real-with-visible-fallback"})


@api_bp.post("/auth/wechat-login")
def wechat_login():
    body = body_json()
    code = str(body.get("code", "")).strip()
    encrypted_data = body.get("encryptedData")
    iv = body.get("iv")

    if not code:
        return ok("请求参数错误", {"field": "code", "reason": "微信登录 code 不能为空"}, 400)

    if not encrypted_data or not iv:
        return ok("请求参数错误", {"field": "encryptedData/iv", "reason": "encryptedData 和 iv 不能为空"}, 400)

    nickname = body.get("nickname") or body.get("nickName") or "【兜底数据】微信用户"
    avatar = body.get("avatar") or body.get("avatarUrl") or ""

    user_id, nickname = create_or_get_wechat_user(code, nickname=nickname)
    token = create_token(user_id)

    has_device = len(device_list(user_id)) > 0

    return plain(
        {
            "token": token,
            "userId": int(user_id),
            "nickname": nickname,
            "avatar": avatar,
            "hasDevice": bool(has_device),
        }
    )


@api_bp.get("/home/overview")
def home_overview():
    user_id = current_user_id()
    device = get_device(user_id=user_id)
    song = get_song()

    return plain(
        {
            "device": {
                "deviceId": device["deviceId"],
                "name": device["deviceName"],
                "model": device["modelName"],
                "online": device["online"],
                "battery": device["battery"],
            },
            "playing": {
                "songId": song["songId"],
                "songName": song["songName"],
                "artist": song["artist"],
                "source": song["source"],
                "isPlaying": bool(song.get("isPlaying", True)),
            },
            "historyCount": len(history_rows(user_id=user_id, limit=200)),
        }
    )


# ### DB_PANEL_REBUILD_COMPACT_20260514
# 浅粉色后端联调数据库看板：直接挂在 /api/panel/db，不需要 static，不需要额外数据接口
from collections import deque as _panel_deque

_PANEL_RECENT_REQUESTS = _panel_deque(maxlen=80)


@api_bp.before_app_request
def _panel_capture_requests_compact():
    try:
        path = request.path or ""
        if path in ("/api/panel/db", "/favicon.ico"):
            return
        if path.startswith("/static"):
            return
        _PANEL_RECENT_REQUESTS.appendleft({
            "time": now_str(),
            "method": request.method,
            "path": path,
            "query": dict(request.args) if request.args else {},
            "ip": request.headers.get("X-Forwarded-For", request.remote_addr or "-"),
        })
    except Exception:
        pass


def _panel_text(v):
    try:
        v = json_safe(v)
    except Exception:
        pass

    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        try:
            import json
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return str(v)


def _panel_mysql_tables(limit=8):
    tables = []
    try:
        raw = mysql_all("SHOW TABLES")
        names = sorted([list(x.values())[0] for x in raw])
    except Exception:
        names = []

    for name in names:
        try:
            c = mysql_all(f"SELECT COUNT(*) AS c FROM ")
            count = int(c[0]["c"]) if c else 0

            rows = mysql_all(f"SELECT * FROM  ORDER BY 1 DESC LIMIT {int(limit)}")
            if not rows:
                rows = mysql_all(f"SELECT * FROM  LIMIT {int(limit)}")

            if rows:
                cols = list(rows[0].keys())
            else:
                col_rows = mysql_all(f"SHOW COLUMNS FROM ")
                cols = [r.get("Field", "") for r in col_rows]

            display_rows = []
            for row in rows:
                display_rows.append({col: _panel_text(row.get(col)) for col in cols})

            tables.append({
                "name": name,
                "count": count,
                "cols": cols,
                "rows": display_rows,
            })
        except Exception as exc:
            tables.append({
                "name": name,
                "count": "?",
                "cols": ["error"],
                "rows": [{"error": str(exc)}],
            })
    return tables


def _panel_mongo_tables(limit=8):
    tables = []
    try:
        db = mongo_db()
    except Exception:
        db = None

    if db is None:
        return tables

    try:
        names = sorted(db.list_collection_names())
    except Exception:
        names = []

    for name in names:
        try:
            col = db[name]
            count = col.count_documents({})
            docs = list(col.find({}, limit=int(limit)).sort([("_id", -1)]))

            cols = []
            for doc in docs:
                for k in doc.keys():
                    if k not in cols:
                        cols.append(k)

            rows = []
            for doc in docs:
                safe_doc = json_safe(doc)
                rows.append({c: _panel_text(safe_doc.get(c)) for c in cols})

            tables.append({
                "name": name,
                "count": count,
                "cols": cols,
                "rows": rows,
            })
        except Exception as exc:
            tables.append({
                "name": name,
                "count": "?",
                "cols": ["error"],
                "rows": [{"error": str(exc)}],
            })
    return tables


@api_bp.get("/panel/db")
def panel_db_compact_page():
    from flask import render_template_string

    html = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>C 后端联调数据库看板</title>
<style>
:root{
  --bg:#fff6fa;
  --top:#fff0f6;
  --card:#fffafd;
  --line:#efd4de;
  --line2:#f8e8ef;
  --text:#4b2b36;
  --sub:#8a6370;
  --main:#bb4e75;
}
*{box-sizing:border-box}
body{
  margin:0;
  background:var(--bg);
  color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
}
.wrap{width:min(1580px,97vw);margin:12px auto}
.top{
  background:var(--top);
  border:1px solid var(--line);
  border-radius:16px;
  padding:12px 16px;
  margin-bottom:12px;
  box-shadow:0 8px 24px rgba(188,76,118,.08);
}
h1{margin:0 0 4px;font-size:24px;color:var(--main)}
.desc{font-size:13px;color:var(--sub)}
.meta{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:8px;color:#7b5966;font-size:12px}
.btn{
  display:inline-block;
  margin-top:10px;
  border-radius:999px;
  background:#e982a5;
  color:white;
  padding:7px 13px;
  text-decoration:none;
  font-size:12px;
}
.block{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:16px;
  overflow:hidden;
  margin-bottom:12px;
  box-shadow:0 8px 24px rgba(188,76,118,.06);
}
.block-title{
  padding:10px 14px;
  background:var(--top);
  border-bottom:1px solid var(--line2);
  font-size:17px;
  font-weight:700;
}
.inner{padding:10px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.tablewrap{
  overflow:auto;
  border:1px solid var(--line2);
  border-radius:10px;
  background:white;
  max-height:340px;
}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{
  border-right:1px solid #faedf2;
  border-bottom:1px solid #faedf2;
  padding:5px 7px;
  white-space:nowrap;
  max-width:230px;
  overflow:hidden;
  text-overflow:ellipsis;
  vertical-align:top;
}
th{
  position:sticky;
  top:0;
  background:#fff2f7;
  color:#674351;
  z-index:1;
}
tr:hover td{background:#fff8fb}
details{
  background:#fff;
  border:1px solid var(--line2);
  border-radius:12px;
  margin-bottom:8px;
  overflow:hidden;
}
summary{
  list-style:none;
  cursor:pointer;
  padding:8px 10px;
  background:#fff7fb;
  font-size:13px;
  font-weight:700;
  display:flex;
  justify-content:space-between;
  gap:8px;
}
summary::-webkit-details-marker{display:none}
.count{color:var(--sub);font-weight:400;font-size:12px;white-space:nowrap}
.small{color:var(--sub);font-size:12px;margin-bottom:7px}
.empty{color:var(--sub);font-size:12px;padding:10px}
@media(max-width:980px){.two{grid-template-columns:1fr}th,td{max-width:160px}}
</style>
<script>setTimeout(function(){location.reload()},10000);</script>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1>C 后端联调数据库看板</h1>
    <div class="desc">浅粉色紧凑表格版：上方显示实时请求日志，下方直接展示 MySQL 表和 MongoDB 集合真实数据。每 10 秒自动刷新。</div>
    <div class="meta">
      <span>快照时间：{{ snapshot_time }}</span>
      <span>请求日志：{{ logs|length }}</span>
      <span>MySQL 表：{{ mysql|length }}</span>
      <span>MongoDB 集合：{{ mongo|length }}</span>
    </div>
    <a class="btn" href="">立即刷新</a>
  </div>

  <div class="block">
    <div class="block-title">实时请求日志</div>
    <div class="inner">
      <div class="small">请求 /api/... 后这里会出现。</div>
      <div class="tablewrap">
        <table>
          <thead><tr><th>时间</th><th>方法</th><th>路径</th><th>Query</th><th>IP</th></tr></thead>
          <tbody>
          {% if logs %}
            {% for x in logs %}
            <tr><td>{{x.time}}</td><td>{{x.method}}</td><td>{{x.path}}</td><td>{{x.query}}</td><td>{{x.ip}}</td></tr>
            {% endfor %}
          {% else %}
            <tr><td colspan="5">暂无后端请求日志。请求 /api/... 后这里会出现。</td></tr>
          {% endif %}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="two">
    <div class="block">
      <div class="block-title">MySQL 表</div>
      <div class="inner">
      {% for t in mysql %}
        <details open>
          <summary><span>{{t.name}}</span><span class="count">{{t.count}} 行 · {{t.cols|length}} 字段</span></summary>
          {% if t.cols %}
          <div class="tablewrap">
            <table>
              <thead><tr>{% for c in t.cols %}<th>{{c}}</th>{% endfor %}</tr></thead>
              <tbody>
              {% if t.rows %}
                {% for r in t.rows %}
                <tr>{% for c in t.cols %}<td title="{{r.get(c,'')}}">{{r.get(c,'')}}</td>{% endfor %}</tr>
                {% endfor %}
              {% else %}
                <tr><td colspan="{{t.cols|length}}">空表</td></tr>
              {% endif %}
              </tbody>
            </table>
          </div>
          {% else %}
            <div class="empty">无字段信息</div>
          {% endif %}
        </details>
      {% endfor %}
      </div>
    </div>

    <div class="block">
      <div class="block-title">MongoDB 集合</div>
      <div class="inner">
      {% if mongo %}
        {% for t in mongo %}
          <details open>
            <summary><span>{{t.name}}</span><span class="count">{{t.count}} 条 · {{t.cols|length}} 字段</span></summary>
            {% if t.cols %}
            <div class="tablewrap">
              <table>
                <thead><tr>{% for c in t.cols %}<th>{{c}}</th>{% endfor %}</tr></thead>
                <tbody>
                {% if t.rows %}
                  {% for r in t.rows %}
                    <tr>{% for c in t.cols %}<td title="{{r.get(c,'')}}">{{r.get(c,'')}}</td>{% endfor %}</tr>
                  {% endfor %}
                {% else %}
                  <tr><td colspan="{{t.cols|length}}">空集合</td></tr>
                {% endif %}
                </tbody>
              </table>
            </div>
            {% else %}
              <div class="empty">无字段信息</div>
            {% endif %}
          </details>
        {% endfor %}
      {% else %}
        <div class="empty">未连接到 MongoDB 或暂无集合。</div>
      {% endif %}
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""
    return render_template_string(
        html,
        snapshot_time=now_str(),
        logs=list(_PANEL_RECENT_REQUESTS)[:25],
        mysql=_panel_mysql_tables(8),
        mongo=_panel_mongo_tables(8),
    )
