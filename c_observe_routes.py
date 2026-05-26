import json
import os
import time
from datetime import datetime

from flask import Blueprint, Response, g, jsonify, request

c_observe_bp = Blueprint("c_observe", __name__)

RUNTIME_DIR = "/www/wwwroot/mysite/runtime"
LOG_FILE = os.path.join(RUNTIME_DIR, "c_observe_requests.jsonl")
SNAPSHOT_FILE = os.path.join(RUNTIME_DIR, "c_observe_snapshot.json")


def ensure_runtime():
    os.makedirs(RUNTIME_DIR, exist_ok=True)


def read_snapshot():
    if not os.path.exists(SNAPSHOT_FILE):
        return {
            "updated_at": "暂无快照",
            "mysql": [],
            "mongo": []
        }

    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {
            "updated_at": "快照读取失败",
            "mysql": [
                {
                    "name": "snapshot_error",
                    "count": 0,
                    "columns": ["error"],
                    "rows": [{"error": str(exc)}],
                }
            ],
            "mongo": [],
        }


def append_log(item):
    ensure_runtime()
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def read_logs(limit=30):
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
    except Exception:
        return []

    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            pass

    return list(reversed(out))


@c_observe_bp.before_app_request
def observe_before():
    if request.path.startswith("/c-observe"):
        return

    g.c_observe_start = time.time()


@c_observe_bp.after_app_request
def observe_after(response):
    if request.path.startswith("/c-observe"):
        return response

    if not (
        request.path.startswith("/api")
        or request.path.startswith("/device")
        or request.path.startswith("/auth")
        or request.path.startswith("/stats")
    ):
        return response

    cost_ms = 0
    if hasattr(g, "c_observe_start"):
        cost_ms = int((time.time() - g.c_observe_start) * 1000)

    body = None
    try:
        if request.is_json:
            body = request.get_json(silent=True)
        elif request.form:
            body = request.form.to_dict()
        elif request.data:
            body = request.data.decode("utf-8", errors="replace")[:500]
    except Exception:
        body = None

    resp_text = ""
    try:
        resp_text = response.get_data(as_text=True)[:500]
    except Exception:
        resp_text = ""

    append_log({
        "time": datetime.now().strftime("%H:%M:%S"),
        "method": request.method,
        "path": request.path,
        "query": request.query_string.decode("utf-8", errors="replace"),
        "status": response.status_code,
        "cost_ms": cost_ms,
        "body": body,
        "response": resp_text,
    })

    return response


@c_observe_bp.route("/c-observe")
def c_observe_page():
    html = r'''
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>C 后端联调数据库看板</title>
<style>
body{
  margin:0;
  font-family:Arial,"Microsoft YaHei",sans-serif;
  background:#fff9fc;
  color:#4d3443;
}
header{
  background:#fff7fb;
  border-bottom:1px solid #f8dce9;
  padding:16px 22px;
  position:sticky;
  top:0;
  z-index:20;
}
h1{margin:0;font-size:23px;color:#4d2941}
.sub{margin-top:5px;font-size:13px;color:#8a6578}
.wrap{padding:14px;max-width:1180px;margin:0 auto}
.panel{
  background:#fff;
  border:1px solid #f8dce9;
  border-radius:18px;
  box-shadow:0 6px 18px rgba(234,145,184,.10);
  overflow:hidden;
  margin-bottom:16px;
}
.panel h2{
  margin:0;
  padding:13px 16px;
  background:#fff7fb;
  border-bottom:1px solid #f8dce9;
  color:#4d2941;
  font-size:18px;
}
.body{padding:12px}
.request{
  border:1px solid #f8dce9;
  border-left:5px solid #f3bad4;
  border-radius:12px;
  padding:8px;
  background:#fffdfd;
  margin-bottom:8px;
}
.request.ok{border-left-color:#a7d9b2}
.request.err{border-left-color:#ef8aa4}
.tag{
  display:inline-block;
  padding:2px 8px;
  border-radius:999px;
  background:#fff3f8;
  color:#70495d;
  font-size:12px;
  margin-right:5px;
}
pre{
  margin:7px 0 0;
  white-space:pre-wrap;
  word-break:break-word;
  background:#fff9fc;
  border:1px solid #f8dce9;
  color:#564251;
  border-radius:8px;
  padding:7px;
  font-size:12px;
  max-height:90px;
  overflow:auto;
}
.db-grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
}
.group-title{
  color:#60364e;
  font-size:18px;
  font-weight:bold;
  margin:0 0 10px;
}
.card{
  border:1px solid #f8dce9;
  border-radius:16px;
  background:#fff;
  margin-bottom:10px;
  overflow:hidden;
}
.card-head{
  padding:10px 12px;
  background:#fffdfd;
  cursor:pointer;
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
}
.card-head:hover{background:#fff7fb}
.card.active .card-head{
  background:#fff3f8;
  border-bottom:1px solid #f8dce9;
}
.card-name{
  font-weight:bold;
  color:#4d2941;
  font-size:14px;
}
.card-meta{
  color:#9a6b80;
  font-size:12px;
  margin-top:4px;
}
.arrow{
  color:#b77a96;
  font-size:12px;
  white-space:nowrap;
}
.card-body{
  display:none;
}
.card.active .card-body{
  display:block;
}
.table-wrap{
  overflow:auto;
  max-height:300px;
}
table{
  width:100%;
  table-layout:fixed;
  border-collapse:collapse;
  font-size:12px;
}
th{
  position:sticky;
  top:0;
  background:#fffafd;
  color:#70495d;
  text-align:left;
  padding:6px;
  border-bottom:1px solid #f8dce9;
  white-space:normal;
  word-break:break-word;
  overflow-wrap:anywhere;
}
td{
  padding:6px;
  border-bottom:1px solid #fbedf3;
  max-width:110px;
  white-space:normal;
  overflow:hidden;
  word-break:break-word;
  overflow-wrap:anywhere;
  line-height:1.35;
}
tr:hover td{background:#fff9fc}
.empty{padding:14px;color:#9b7084}
@media(max-width:1100px){
  .db-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>
<header>
  <h1>C 后端联调数据库看板</h1>
  <div class="sub">点击卡片后原地展开表格；自动刷新。快照时间：<span id="snap">加载中</span>，页面刷新：<span id="last">加载中</span></div>
</header>

<div class="wrap">
  <section class="panel">
    <h2>实时请求日志</h2>
    <div class="body" id="requests"><div class="empty">加载中...</div></div>
  </section>

  <section class="panel">
    <h2>数据库卡片看板</h2>
    <div class="body db-grid">
      <div>
        <div class="group-title">MySQL 表</div>
        <div id="mysqlCards"></div>
      </div>
      <div>
        <div class="group-title">MongoDB 集合</div>
        <div id="mongoCards"></div>
      </div>
    </div>
  </section>
</div>

<script>
let openKeys = new Set();

function esc(v){
  if(v===null||v===undefined)return '';
  return String(v).replace(/[&<>"']/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
}
function short(v,n=36){
  let s=typeof v==='object'?JSON.stringify(v):String(v??'');
  return s.length>n?s.slice(0,n)+'...':s;
}
async function getJson(url){
  const r=await fetch(url,{cache:'no-store'});
  const text=await r.text();
  try{return JSON.parse(text)}
  catch(e){throw new Error(url+' 返回非 JSON：'+text.slice(0,100))}
}
function toggleCard(key){
  if(openKeys.has(key)) openKeys.delete(key);
  else openKeys.add(key);
  const el=document.querySelector(`[data-key="${key}"]`);
  if(el) el.classList.toggle('active', openKeys.has(key));
}
function renderTable(item){
  const cols=item.columns||[];
  const rows=item.rows||[];

  if(!cols.length){
    return '<div class="empty">暂无字段</div>';
  }

  if(!rows.length){
    return `<div class="table-wrap"><table><thead><tr>${cols.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead></table></div><div class="empty">暂无数据</div>`;
  }

  return `<div class="table-wrap">
    <table>
      <thead><tr>${cols.map(c=>`<th title="${esc(c)}">${esc(c)}</th>`).join('')}</tr></thead>
      <tbody>
        ${rows.map(r=>`<tr>${cols.map(c=>`<td title="${esc(String(r[c]??''))}">${esc(short(r[c],36))}</td>`).join('')}</tr>`).join('')}
      </tbody>
    </table>
  </div>`;
}
function renderCards(list, prefix){
  return list.map((x)=>{
    const key=prefix+':'+x.name;
    const active=openKeys.has(key);
    return `<div class="card ${active?'active':''}" data-key="${esc(key)}">
      <div class="card-head" onclick="toggleCard('${esc(key)}')">
        <div>
          <div class="card-name">${esc(x.name)}</div>
          <div class="card-meta">${esc(x.count)} 条记录 · ${(x.columns||[]).length} 个字段 · 显示 ${(x.rows||[]).length} 条</div>
        </div>
        <div class="arrow">${active?'收起 ▲':'展开 ▼'}</div>
      </div>
      <div class="card-body">${renderTable(x)}</div>
    </div>`;
  }).join('');
}
async function loadReq(){
  const box=document.getElementById('requests');
  try{
    const data=await getJson('/c-observe/api/requests');
    const logs=data.logs||[];
    if(!logs.length){
      box.innerHTML='<div class="empty">暂无后端请求日志。请求 /api/... 后这里会显示。</div>';
      return;
    }
    box.innerHTML=logs.slice(0,12).map(x=>{
      const ok=x.status>=200&&x.status<300;
      return `<div class="request ${ok?'ok':'err'}">
        <span class="tag">${esc(x.time)}</span>
        <span class="tag">${esc(x.method)}</span>
        <span class="tag">${esc(x.status)}</span>
        <b>${esc(x.path)}</b>
        <span class="tag">${esc(x.cost_ms)}ms</span>
        <pre>请求体：${esc(short(x.body,160))}
返回：${esc(short(x.response,160))}</pre>
      </div>`;
    }).join('');
  }catch(e){
    box.innerHTML='<div class="empty">请求日志加载失败：'+esc(e.message)+'</div>';
  }
}
async function loadDb(){
  try{
    const mysql=await getJson('/c-observe/api/mysql');
    document.getElementById('mysqlCards').innerHTML =
      renderCards(mysql.tables||[], 'mysql') || '<div class="empty">没有 MySQL 表</div>';
    document.getElementById('snap').innerText=mysql.updated_at||'未知';
  }catch(e){
    document.getElementById('mysqlCards').innerHTML =
      '<div class="empty">MySQL 加载失败：'+esc(e.message)+'</div>';
  }

  try{
    const mongo=await getJson('/c-observe/api/mongo');
    document.getElementById('mongoCards').innerHTML =
      renderCards(mongo.collections||[], 'mongo') || '<div class="empty">没有 MongoDB 集合</div>';
  }catch(e){
    document.getElementById('mongoCards').innerHTML =
      '<div class="empty">MongoDB 加载失败：'+esc(e.message)+'</div>';
  }
}
async function refresh(){
  await Promise.all([loadReq(), loadDb()]);
  document.getElementById('last').innerText=new Date().toLocaleTimeString();
}
refresh();
setInterval(refresh,2500);
</script>
</body>
</html>
'''
    return Response(html, mimetype="text/html")


@c_observe_bp.route("/c-observe/api/requests")
def c_observe_api_requests():
    return jsonify({"logs": read_logs(40)})


@c_observe_bp.route("/c-observe/api/mysql")
def c_observe_api_mysql():
    snap = read_snapshot()
    return jsonify({
        "updated_at": snap.get("updated_at"),
        "tables": snap.get("mysql", []),
    })


@c_observe_bp.route("/c-observe/api/mongo")
def c_observe_api_mongo():
    snap = read_snapshot()
    return jsonify({
        "updated_at": snap.get("updated_at"),
        "collections": snap.get("mongo", []),
    })


def register_c_observe_routes(app):
    if "c_observe" not in app.blueprints:
        app.register_blueprint(c_observe_bp)
