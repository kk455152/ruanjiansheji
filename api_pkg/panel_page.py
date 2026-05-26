import json
from collections import deque

from flask import render_template_string, request

from . import api_bp
from .common import mysql_all, mongo_db, now_str, json_safe

RECENT_REQUESTS = deque(maxlen=60)


@api_bp.before_app_request
def capture_recent_requests():
    path = request.path or ""
    if path.startswith("/api/panel/db"):
        return
    if path.startswith("/static") or path == "/favicon.ico":
        return

    try:
        RECENT_REQUESTS.appendleft({
            "time": now_str(),
            "method": request.method,
            "path": path,
            "query": dict(request.args) if request.args else {},
            "ip": request.headers.get("X-Forwarded-For", request.remote_addr or "-"),
        })
    except Exception:
        pass


def _cell_text(v):
    v = json_safe(v)
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return str(v)


def get_mysql_snapshot(limit_rows=8):
    tables = []
    try:
        raw = mysql_all("SHOW TABLES")
        names = sorted([list(x.values())[0] for x in raw])
    except Exception:
        names = []

    for name in names:
        try:
            count_row = mysql_all(f"SELECT COUNT(*) AS c FROM `{name}`")
            row_count = int(count_row[0]["c"]) if count_row else 0

            rows = mysql_all(f"SELECT * FROM `{name}` ORDER BY 1 DESC LIMIT {limit_rows}")
            if not rows:
                rows = mysql_all(f"SELECT * FROM `{name}` LIMIT {limit_rows}")

            if rows:
                columns = list(rows[0].keys())
            else:
                col_rows = mysql_all(f"SHOW COLUMNS FROM `{name}`")
                columns = [r.get("Field", "") for r in col_rows]

            display_rows = []
            for row in rows:
                display_rows.append({col: _cell_text(row.get(col)) for col in columns})

            tables.append({
                "name": name,
                "count": row_count,
                "columns": columns,
                "rows": display_rows,
            })
        except Exception as e:
            tables.append({
                "name": name,
                "count": "?",
                "columns": ["error"],
                "rows": [{"error": str(e)}],
            })
    return tables


def get_mongo_snapshot(limit_rows=8):
    collections = []
    try:
        db = mongo_db()
    except Exception:
        db = None

    if db is None:
        return collections

    try:
        names = sorted(db.list_collection_names())
    except Exception:
        names = []

    for name in names:
        try:
            col = db[name]
            count = col.count_documents({})
            docs = list(col.find({}, limit=limit_rows).sort([("_id", -1)]))

            columns = []
            for doc in docs:
                for k in doc.keys():
                    if k not in columns:
                        columns.append(k)

            display_rows = []
            for doc in docs:
                safe_doc = json_safe(doc)
                display_rows.append({col_name: _cell_text(safe_doc.get(col_name)) for col_name in columns})

            collections.append({
                "name": name,
                "count": count,
                "columns": columns,
                "rows": display_rows,
            })
        except Exception as e:
            collections.append({
                "name": name,
                "count": "?",
                "columns": ["error"],
                "rows": [{"error": str(e)}],
            })
    return collections


HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>C 后端联调数据库看板（紧凑表格版）</title>
  <style>
    :root{
      --bg:#fff6fa;
      --panel:#fffafd;
      --line:#f0d6e0;
      --line2:#f7e8ee;
      --text:#4b2b36;
      --sub:#8d6472;
      --title:#bb4e75;
      --shadow:0 8px 24px rgba(183,84,120,.08);
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
      background:var(--bg);
      color:var(--text);
    }
    .wrap{
      width:min(1500px,96vw);
      margin:14px auto;
    }
    .top{
      background:#fff1f6;
      border:1px solid var(--line);
      border-radius:16px;
      box-shadow:var(--shadow);
      padding:14px 18px;
      margin-bottom:14px;
    }
    h1{
      margin:0 0 6px;
      font-size:24px;
      color:var(--title);
      line-height:1.2;
    }
    .desc{
      color:var(--sub);
      font-size:13px;
      line-height:1.5;
    }
    .mini-bar{
      display:flex;
      flex-wrap:wrap;
      gap:10px 16px;
      margin-top:8px;
      font-size:12px;
      color:#7f5d69;
    }
    .btn{
      display:inline-block;
      margin-top:8px;
      padding:6px 12px;
      border-radius:999px;
      background:#e982a5;
      color:#fff;
      text-decoration:none;
      font-size:12px;
    }

    .block{
      background:var(--panel);
      border:1px solid var(--line);
      border-radius:16px;
      box-shadow:var(--shadow);
      margin-bottom:14px;
      overflow:hidden;
    }
    .block-hd{
      padding:12px 16px;
      border-bottom:1px solid var(--line2);
      font-size:18px;
      font-weight:700;
      color:#55313d;
      background:#fff3f8;
    }
    .block-bd{
      padding:12px;
    }

    .log-table-wrap,.table-wrap{
      overflow:auto;
      border:1px solid var(--line2);
      border-radius:10px;
      background:#fff;
    }

    table{
      width:100%;
      border-collapse:collapse;
      font-size:12px;
      table-layout:auto;
    }
    th,td{
      border-bottom:1px solid #f7e8ee;
      border-right:1px solid #f9eef2;
      padding:6px 8px;
      text-align:left;
      white-space:nowrap;
      vertical-align:top;
      max-width:260px;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    th{
      position:sticky;
      top:0;
      background:#fff6fa;
      color:#6f4957;
      z-index:1;
    }
    tr:hover td{
      background:#fff8fb;
    }

    .two-col{
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:14px;
    }

    details.item{
      border:1px solid var(--line2);
      border-radius:12px;
      background:#fff;
      margin-bottom:10px;
      overflow:hidden;
    }
    details.item > summary{
      list-style:none;
      cursor:pointer;
      padding:10px 12px;
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      background:#fff8fb;
      color:#4f2d38;
      font-size:14px;
      font-weight:700;
      border-bottom:1px solid #f7e8ee;
    }
    details.item > summary::-webkit-details-marker{display:none;}
    .meta{
      font-size:12px;
      color:#8a6572;
      font-weight:400;
      white-space:nowrap;
    }
    .empty{
      padding:10px 12px;
      color:#94707c;
      font-size:12px;
    }
    .table-box{
      padding:8px;
    }
    .tip{
      font-size:12px;
      color:#8b6875;
      margin-bottom:8px;
    }

    @media (max-width: 980px){
      .two-col{grid-template-columns:1fr;}
      th,td{max-width:180px}
    }
  </style>
  <script>
    setTimeout(function(){ location.reload(); }, 10000);
  </script>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <h1>C 后端联调数据库看板</h1>
      <div class="desc">
        浅粉色紧凑表格版。上面保留最近请求日志，下面直接展示 MySQL 表 / MongoDB 集合的真实数据。
        每张表默认显示最近 8 行，页面每 10 秒自动刷新一次。
      </div>
      <div class="mini-bar">
        <div>快照时间：{{ snapshot_time }}</div>
        <div>最近请求数：{{ request_logs|length }}</div>
        <div>MySQL 表：{{ mysql_tables|length }}</div>
        <div>MongoDB 集合：{{ mongo_tables|length }}</div>
      </div>
      <a class="btn" href="javascript:location.reload()">立即刷新</a>
    </div>

    <div class="block">
      <div class="block-hd">实时请求日志</div>
      <div class="block-bd">
        <div class="tip">这里只显示最近请求，面板自己的自动刷新请求不会被记进来。</div>
        <div class="log-table-wrap">
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
              {% if request_logs %}
                {% for item in request_logs %}
                <tr>
                  <td>{{ item.time }}</td>
                  <td>{{ item.method }}</td>
                  <td>{{ item.path }}</td>
                  <td>{{ item.query }}</td>
                  <td>{{ item.ip }}</td>
                </tr>
                {% endfor %}
              {% else %}
                <tr><td colspan="5">暂无后端请求日志。请求 /api/... 后这里会出现。</td></tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="two-col">
      <div class="block">
        <div class="block-hd">MySQL 表</div>
        <div class="block-bd">
          {% for t in mysql_tables %}
          <details class="item" open>
            <summary>
              <span>{{ t.name }}</span>
              <span class="meta">{{ t.count }} 行 · {{ t.columns|length }} 列</span>
            </summary>
            <div class="table-box">
              {% if t.columns %}
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {% for c in t.columns %}
                      <th>{{ c }}</th>
                      {% endfor %}
                    </tr>
                  </thead>
                  <tbody>
                    {% if t.rows %}
                      {% for row in t.rows %}
                      <tr>
                        {% for c in t.columns %}
                        <td title="{{ row.get(c, '') }}">{{ row.get(c, '') }}</td>
                        {% endfor %}
                      </tr>
                      {% endfor %}
                    {% else %}
                      <tr><td colspan="{{ t.columns|length }}">空表</td></tr>
                    {% endif %}
                  </tbody>
                </table>
              </div>
              {% else %}
              <div class="empty">无字段信息</div>
              {% endif %}
            </div>
          </details>
          {% endfor %}
        </div>
      </div>

      <div class="block">
        <div class="block-hd">MongoDB 集合</div>
        <div class="block-bd">
          {% for t in mongo_tables %}
          <details class="item" open>
            <summary>
              <span>{{ t.name }}</span>
              <span class="meta">{{ t.count }} 条 · {{ t.columns|length }} 字段</span>
            </summary>
            <div class="table-box">
              {% if t.columns %}
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {% for c in t.columns %}
                      <th>{{ c }}</th>
                      {% endfor %}
                    </tr>
                  </thead>
                  <tbody>
                    {% if t.rows %}
                      {% for row in t.rows %}
                      <tr>
                        {% for c in t.columns %}
                        <td title="{{ row.get(c, '') }}">{{ row.get(c, '') }}</td>
                        {% endfor %}
                      </tr>
                      {% endfor %}
                    {% else %}
                      <tr><td colspan="{{ t.columns|length }}">空集合</td></tr>
                    {% endif %}
                  </tbody>
                </table>
              </div>
              {% else %}
              <div class="empty">无字段信息</div>
              {% endif %}
            </div>
          </details>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""


@api_bp.get("/panel/db")
def panel_db():
    request_logs = list(RECENT_REQUESTS)[:20]
    mysql_tables = get_mysql_snapshot(limit_rows=8)
    mongo_tables = get_mongo_snapshot(limit_rows=8)
    return render_template_string(
        HTML,
        snapshot_time=now_str(),
        request_logs=request_logs,
        mysql_tables=mysql_tables,
        mongo_tables=mongo_tables,
    )
