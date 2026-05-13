import html
import json
import os
from collections import deque
from datetime import datetime, date, time, timedelta
from time import perf_counter

from flask import jsonify, request, g

from api_pkg.common import mysql_all, mongo_db


REQUEST_LOGS = deque(maxlen=200)
LOG_FILE = "/www/wwwroot/mysite/runtime/c_observe_request_logs.jsonl"


def bj_now(fmt="%Y-%m-%d %H:%M:%S"):
    return (datetime.utcnow() + timedelta(hours=8)).strftime(fmt)


def safe_text(v, max_len=180):
    if v is None:
        s = "null"
    elif isinstance(v, (datetime, date, time, timedelta)):
        s = str(v)
    elif isinstance(v, (dict, list, tuple)):
        s = json.dumps(v, ensure_ascii=False, default=str)
    else:
        s = str(v)
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return html.escape(s)


def save_log(item):
    REQUEST_LOGS.append(item)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def read_logs(limit=120):
    logs = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        for line in lines:
            try:
                logs.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    if not logs:
        logs = list(REQUEST_LOGS)[-limit:]
    return logs[-limit:]


def mysql_tables():
    try:
        rows = mysql_all("SHOW TABLES")
        return [str(list(r.values())[0]) for r in rows]
    except Exception:
        return []


def mysql_columns(table):
    try:
        rows = mysql_all("SHOW COLUMNS FROM `{}`".format(table))
        return [r.get("Field") for r in rows if r.get("Field")]
    except Exception:
        return []


def mysql_count(table):
    try:
        rows = mysql_all("SELECT COUNT(*) AS c FROM `{}`".format(table))
        return int(rows[0].get("c") or 0) if rows else 0
    except Exception:
        return 0


def mysql_rows(table, cols, limit=8):
    try:
        if cols:
            return mysql_all("SELECT * FROM `{}` ORDER BY `{}` DESC LIMIT {}".format(table, cols[0], int(limit)))
        return mysql_all("SELECT * FROM `{}` LIMIT {}".format(table, int(limit)))
    except Exception:
        try:
            return mysql_all("SELECT * FROM `{}` LIMIT {}".format(table, int(limit)))
        except Exception:
            return []


def mongo_cols():
    db = mongo_db()
    if db is None:
        return []
    try:
        return sorted(db.list_collection_names())
    except Exception:
        return []


def mongo_count(name):
    db = mongo_db()
    if db is None:
        return 0
    try:
        return db[name].count_documents({})
    except Exception:
        return 0


def mongo_rows(name, limit=8):
    db = mongo_db()
    if db is None:
        return []
    try:
        return list(db[name].find({}).sort("_id", -1).limit(int(limit)))
    except Exception:
        try:
            return list(db[name].find({}).limit(int(limit)))
        except Exception:
            return []


def columns_from_rows(rows):
    cols = []
    seen = set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)
    return cols


def render_log_card():
    logs = read_logs(120)
    if logs:
        lines = []
        for item in logs[-80:]:
            line = "{}  {}  {}  {}  {}ms".format(
                item.get("time", ""),
                item.get("method", ""),
                item.get("status", ""),
                item.get("path", ""),
                item.get("cost_ms", ""),
            )
            lines.append(line)
        text = "\n".join(lines)
    else:
        text = "暂无请求日志。刷新本页面或请求 /api/_health 后这里会出现。"

    return """
<section class="card">
  <div class="card-head">
    <div>
      <h2>实时请求日志</h2>
      <p>滚动日志屏幕，刷新后保留最近请求记录。</p>
    </div>
    <span class="tag">已展开</span>
  </div>
  <pre class="log-screen">{}</pre>
</section>
""".format(html.escape(text))


def render_table_card(kind, name, total, cols, rows):
    if not cols:
        cols = columns_from_rows(rows)
    if not cols:
        cols = ["数据"]

    th = "".join("<th>{}</th>".format(safe_text(c, 80)) for c in cols)

    if rows:
        trs = []
        for r in rows:
            tds = []
            for c in cols:
                val = r.get(c) if isinstance(r, dict) else ""
                tds.append("<td>{}</td>".format(safe_text(val, 180)))
            trs.append("<tr>{}</tr>".format("".join(tds)))
        tbody = "\n".join(trs)
    else:
        tbody = '<tr><td colspan="{}" class="empty">暂无数据</td></tr>'.format(len(cols))

    return """
<section class="card">
  <div class="card-head">
    <div>
      <h2>{}：{}</h2>
      <p>{} 条记录 · {} 字段 · 当前展示 {} 条</p>
    </div>
    <span class="tag">已展开</span>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr>{}</tr></thead>
      <tbody>{}</tbody>
    </table>
  </div>
</section>
""".format(
        safe_text(kind, 40),
        safe_text(name, 80),
        total,
        len(cols),
        len(rows or []),
        th,
        tbody,
    )


def render_page():
    cards = [render_log_card()]

    for t in mysql_tables():
        cols = mysql_columns(t)
        rows = mysql_rows(t, cols, 8)
        cards.append(render_table_card("MySQL 表", t, mysql_count(t), cols, rows))

    for c in mongo_cols():
        rows = mongo_rows(c, 8)
        cols = columns_from_rows(rows)
        cards.append(render_table_card("MongoDB 集合", c, mongo_count(c), cols, rows))

    body = "\n".join(cards)

    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="5">
<title>C 后端联调数据库看板</title>
<style>
:root{
  --bg:#fff7fb;
  --card:#ffffff;
  --line:#f3cfe0;
  --line2:#f8e3ed;
  --text:#3f2532;
  --muted:#9a667c;
  --strong:#5a2d42;
  --tag:#fff0f7;
}
*{box-sizing:border-box}
body{
  margin:0;
  background:linear-gradient(180deg,#fff7fb,#ffffff);
  color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",Arial,sans-serif;
  font-size:13px;
}
header{
  position:sticky;
  top:0;
  z-index:10;
  background:rgba(255,247,251,.96);
  border-bottom:1px solid var(--line2);
  padding:12px 16px;
}
.header-inner{
  max-width:1180px;
  margin:0 auto;
}
h1{
  margin:0;
  font-size:22px;
  color:var(--strong);
}
.sub{
  margin-top:5px;
  color:var(--muted);
  font-size:12px;
}
main{
  max-width:1180px;
  margin:14px auto 40px;
  padding:0 12px;
}
.card{
  width:100%;
  background:var(--card);
  border:1px solid var(--line);
  border-radius:16px;
  margin-bottom:14px;
  overflow:hidden;
  box-shadow:0 4px 16px rgba(126,58,89,.06);
}
.card-head{
  display:flex;
  justify-content:space-between;
  gap:10px;
  align-items:center;
  padding:10px 12px;
  background:#fff3f8;
  border-bottom:1px solid var(--line2);
}
.card h2{
  margin:0;
  font-size:15px;
  color:var(--strong);
}
.card p{
  margin:4px 0 0;
  color:var(--muted);
  font-size:12px;
}
.tag{
  padding:3px 8px;
  border:1px solid var(--line);
  border-radius:999px;
  background:var(--tag);
  color:#a45375;
  font-size:12px;
}
.table-wrap{
  width:100%;
  overflow:auto;
  max-height:460px;
}
table{
  width:100%;
  border-collapse:collapse;
  table-layout:fixed;
  font-size:12px;
}
th,td{
  border-bottom:1px solid var(--line2);
  border-right:1px solid #faedf3;
  padding:6px;
  vertical-align:top;
  word-break:break-word;
  overflow-wrap:anywhere;
  line-height:1.35;
}
th{
  position:sticky;
  top:0;
  background:#fffafd;
  color:#70495d;
  text-align:left;
  z-index:1;
}
.empty{
  color:var(--muted);
  padding:16px;
}
.log-screen{
  margin:0;
  padding:12px;
  height:260px;
  overflow:auto;
  white-space:pre-wrap;
  word-break:break-word;
  background:#2d1f29;
  color:#fff7fb;
  font-family:Consolas,Menlo,Monaco,"Courier New",monospace;
  font-size:12px;
  line-height:1.55;
}
</style>
</head>
<body>
<header>
  <div class="header-inner">
    <h1>C 后端联调数据库看板</h1>
    <div class="sub">单列展示 MySQL 表 / MongoDB 集合，默认全部展开。页面自动刷新：5 秒。北京时间：""" + bj_now() + """</div>
  </div>
</header>
<main>
""" + body + """
</main>
</body>
</html>"""


def register_c_observe_routes(app):
    @app.before_request
    def c_observe_before():
        if request.path.startswith("/api/") or request.path == "/c-observe":
            g.c_observe_start = perf_counter()

    @app.after_request
    def c_observe_after(response):
        if request.path.startswith("/api/") or request.path == "/c-observe":
            try:
                start = getattr(g, "c_observe_start", perf_counter())
                item = {
                    "time": bj_now("%H:%M:%S"),
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "cost_ms": int((perf_counter() - start) * 1000),
                }
                save_log(item)
            except Exception:
                pass
        return response

    def c_observe():
        return render_page()

    def api_c_observe():
        return jsonify({
            "code": 200,
            "message": "ok",
            "data": {
                "mysqlTables": mysql_tables(),
                "mongoCollections": mongo_cols(),
            }
        })

    if "c_observe" not in app.view_functions:
        app.add_url_rule("/c-observe", "c_observe", c_observe, methods=["GET"])
    if "api_c_observe" not in app.view_functions:
        app.add_url_rule("/api/c-observe", "api_c_observe", api_c_observe, methods=["GET"])
