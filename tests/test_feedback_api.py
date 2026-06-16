import os
import sys

from flask import Flask


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api_pkg import api_bp  # noqa: E402
import api_pkg.feedback as feedback_module  # noqa: E402


def _client():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    return app.test_client()


def test_submit_feedback_writes_to_user_feedback(monkeypatch):
    calls = []

    def fake_mysql_exec(sql, params=(), fetch_last_id=False):
        calls.append({"sql": sql, "params": params, "fetch_last_id": fetch_last_id})
        return 123 if fetch_last_id else 1

    monkeypatch.setattr(feedback_module, "mysql_exec", fake_mysql_exec)
    monkeypatch.setattr(feedback_module, "create_or_get_wechat_user", lambda code, nickname=None: (42, nickname))
    monkeypatch.setattr(feedback_module, "_clear_admin_feedback_cache", lambda: None)

    response = _client().post(
        "/api/feedback/submit",
        json={
            "content": "button click has no response",
            "contact": "tester@example.com",
            "type": "bug",
            "rating": 0,
            "loginCode": "wx-test-code",
            "nickname": "Mini User",
            "deviceInfo": {"platform": "devtools"},
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    inserted = calls[-1]
    assert payload["data"]["feedbackId"].startswith("FB")
    assert payload["data"]["status"] == "pending"
    assert "INSERT INTO user_feedback" in inserted["sql"]
    assert inserted["fetch_last_id"] is True
    assert inserted["params"][1] == 42
    assert inserted["params"][2] == "bug"
    assert inserted["params"][5] == "tester@example.com"
    assert inserted["params"][8] == "high"
    assert inserted["params"][9] is None
    assert any("UPDATE `user`" in call["sql"] for call in calls)


def test_submit_feedback_rejects_short_content(monkeypatch):
    monkeypatch.setattr(feedback_module, "mysql_exec", lambda *args, **kwargs: 123)

    response = _client().post("/api/feedback/submit", json={"content": "bad"})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["data"]["field"] == "content"
