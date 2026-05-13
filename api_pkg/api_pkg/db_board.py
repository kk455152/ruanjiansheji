import json
from collections import deque

from flask import render_template_string, request

from . import api_bp
from .common import mysql_all, mongo_db, now_str, json_safe

_REQUEST_LOGS = deque(maxlen=50)


@api_bp.before_app_request
def db_board_capture_request():
    try:
        path = request.path or ""
        if path in ("/api/db-board", "/favicon.ico"):
            return
        if path.startswith("/static"):
            return
        _REQUEST_LOGS.appendleft({
            "time": now_str(),
            "method": request.method,
            "path": path,
            "query": dict(request.args) if request.args else {},
            "ip": request.headers.get("X-Forwarded-For", request.remote_addr or "-"),
        })
    except Exception:
        pass


def cell(v):
    v = json_safe(v)
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return str(v)


def mysql_snapshot(limit=6):
    tables = []
    try:
        raw = mysql_all("SHOW TABLES")
        names = sorted([list(x.values())[0] for x in raw])
    except Exception:
        names = []

    for name in names:
        try:
            count_row = mysql_all(f"SELECT COUNT(*) AS c FROM `{name}`")
            count = int(count_row[0]["c"]) if count_row else 0

            rows = mysql_all(f"SELECT * FROM `{name}` ORDER BY 1 DESC LIMIT {limit}")
            if not rows:
                rows = mysql_all(f"SELECT * FROM `{name}` LIMIT {limit}")

            if rows:
                cols = list(rows[0].keys())
            else:
                col_rows = mysql_all(f"SHOW COLUMNS FROM `{name}`")
                cols = [r.get("Field", "") for r in col_rows]

            tables.append({
                "name": name,
                "count": count,
                "fieldCount": len(cols),
                "cols": cols,
                "rows": [{c: cell(row.get(c)) for c in cols} for row in rows],
            })
        except Exception as exc:
            tables.append({
                "name": name,
                "count": "?",
                "fieldCount": 1,
                "cols": ["error"],
                "rows": [{"error": str(exc)}],
            })
    return tables


def mongo_snapshot(limit=6):
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
            docs = list(col.find({}, limit=limit).sort([("_id", -1)]))

            cols = []
            for doc in docs:
                for k in doc.keys():
                    if k not in cols:
                        cols.append(k)

            rows = []
            for doc in docs:
                doc = json_safe(doc)
                rows.append({c: cell(doc.get(c)) for c in cols})

            tables.append({
                "name": name,
                "count": count,
                "fieldCount": len(cols),
                "cols": cols,
                "rows": rows,
            })
        except Exception as exc:
            tables.append({
                "name": name,
                "count": "?",
                "fieldCount": 1,
                "cols": ["error"],
                "rows": [{"error": str(exc)}],
            })
    return tables


HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>C 后端联调数据库看板</title>
<style>
:root{
  --bg:#fff7fb;
  --panel:#fffafd;
  --head:#fff0f6;
  --line:#f1d5df;
  --line2:#f8e8ef;
  --text:#4a2a36;
  --sub:#9a7180;
  --main:#412537;
}
*{box-sizing:border-box}
body{
  margin:0;
  background:var(--bg);
  color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
}
.wrap{
  width:min(1500px,96vw);
  margin:0 auto;
  padding:18px 0 28px;
}
h1{
  margin:0;
  font-size:28px;
  color:#3c2134;
  font-weight:800;
}
.top-desc{
  margin-top:4px;
  color:#a27685;
  font-size:14px;
  line-height:1.45;
}
.card{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:22px;
  overflow:hidden;
  margin-top:18px;
  box-shadow:0 10px 28px rgba(174,82,118,.08);
}
.card-title{
  background:var(--head);
  border-bottom:1px solid var(--line2);
  padding:14px 18px;
  font-size:21px;
  font-weight:800;
  color:#3f2436;
}
.card-body{
  padding:16px;
}
.empty{
  color:#9e7684;
  font-size:15px;
  padding:18px;
}
.columns{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:22px;
}
.section-title{
  font-size:20px;
  font-weight:800;
  margin:0 0 12px;
}
.table-card{
  background:white;
  border:1px solid var(--line);
  border-radius:16px;
  margin-bottom:10px;
  overflow:hidden;
}
summary{
  list-style:none;
  cursor:pointer;
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:10px 14px;
  background:#fff8fb;
}
summary::-webkit-details-marker{display:none}
.table-name{
  font-size:16px;
  font-weight:800;
  color:#4a2a36;
}
.table-meta{
  color:#a47786;
  font-size:13px;
  white-space:nowrap;
}
.table-wrap{
  overflow:auto;
  max-height:260px;
  border-top:1px solid var(--line2);
}
table{
  width:100%;
  border-collapse:collapse;
  font-size:12px;
}
th,td{
  border-right:1px solid #faedf2;
  border-bottom:1px solid #faedf2;
  padding:6px 8px;
  white-space:nowrap;
  max-width:220px;
  overflow:hidden;
  text-overflow:ellipsis;
  vertical-align:top;
}
th{
  position:sticky;
  top:0;
  background:#fff1f7;
  color:#6a4252;
  z-index:1;
}
tr:hover td{
  background:#fff8fb;
}
.log-wrap{
  overflow:auto;
  border:1px solid var(--line2);
  border-radius:14px;
  background:white;
  max-height:220px;
}
.btn{
  display:inline-block;
  margin-top:10px;
  padding:7px 14px;
  border-radius:999px;
  background:#e78aaa;
  color:white;
  text-decoration:none;
  font-size:13px;
}
@media(max-width:900px){
  .columns{grid-template-columns:1fr}
  .wrap{width:96vw}
  th,td{max-width:160px}
}
</style>
<script>
setTimeout(function(){ location.reload(); }, 8000);
</script>
</head>
<body>
<div class="wrap">
  <h1>C 后端联调数据库看板</h1>
  <div class="top-desc">
    卡片式查看 MySQL 表 / MongoDB 集合；自动刷新。
    快照时间：{{ snapshot_time }}，页面刷新：8 秒。
  </div>
  <a class="btn" href="">立即刷新</a>

  <div class="card">
    <div class="card-title">实时请求日志</div>
    <div class="card-body">
      <div class="log-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>方法</th>
              <th>路径</th>
              <th>Query</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
          {% if logs %}
            {% for x in logs %}
            <tr>
              <td>{{ x.time }}</td>
              <td>{{ x.method }}</td>
              <td>{{ x.path }}</td>
              <td>{{ x.query }}</td>
              <td>{{ x.ip }}</td>
            </tr>
            {% endfor %}
          {% else %}
            <tr>
              <td colspan="5" class="empty">暂无后端请求日志。请求 /api/... 后这里会出现。</td>
            </tr>
          {% endif %}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">数据库卡片看板</div>
    <div class="card-body">
      <div class="columns">
        <div>
          <div class="section-title">MySQL 表</div>
          {% for t in mysql %}
          <details class="table-card">
            <summary>
              <span class="table-name">{{ t.name }}</span>
              <span class="table-meta">{{ t.count }} 条 · {{ t.fieldCount }} 字段</span>
            </summary>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>{% for c in t.cols %}<th>{{ c }}</th>{% endfor %}</tr>
                </thead>
                <tbody>
                {% if t.rows %}
                  {% for r in t.rows %}
                  <tr>
                    {% for c in t.cols %}
                    <td title="{{ r.get(c, '') }}">{{ r.get(c, '') }}</td>
                    {% endfor %}
                  </tr>
                  {% endfor %}
                {% else %}
                  <tr><td colspan="{{ t.cols|length }}">空表</td></tr>
                {% endif %}
                </tbody>
              </table>
            </div>
          </details>
          {% endfor %}
        </div>

        <div>
          <div class="section-title">MongoDB 集合</div>
          {% if mongo %}
            {% for t in mongo %}
            <details class="table-card">
              <summary>
                <span class="table-name">{{ t.name }}</span>
                <span class="table-meta">{{ t.count }} 条 · {{ t.fieldCount }} 字段</span>
              </summary>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>{% for c in t.cols %}<th>{{ c }}</th>{% endfor %}</tr>
                  </thead>
                  <tbody>
                  {% if t.rows %}
                    {% for r in t.rows %}
                    <tr>
                      {% for c in t.cols %}
                      <td title="{{ r.get(c, '') }}">{{ r.get(c, '') }}</td>
                      {% endfor %}
                    </tr>
                    {% endfor %}
                  {% else %}
                    <tr><td colspan="{{ t.cols|length }}">空集合</td></tr>
                  {% endif %}
                  </tbody>
                </table>
              </div>
            </details>
            {% endfor %}
          {% else %}
            <div class="empty">MongoDB 暂无集合或未连接。</div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""


@api_bp.get("/db-board")
def db_board_page():
    return render_template_string(
        HTML,
        snapshot_time=now_str(),
        logs=list(_REQUEST_LOGS)[:20],
        mysql=mysql_snapshot(6),
        mongo=mongo_snapshot(6),
    )
