import json
import secrets
from datetime import datetime

from flask import request

from . import api_bp
from .common import (
    body_json,
    create_or_get_wechat_user,
    current_user_id,
    mysql_exec,
    now_str,
    ok,
)


FEEDBACK_TYPE_TITLES = {
    "suggestion": "\u529f\u80fd\u5efa\u8bae",
    "bug": "\u95ee\u9898\u53cd\u9988",
    "experience": "\u4f53\u9a8c\u5410\u69fd",
    "other": "\u5176\u4ed6\u53cd\u9988",
}


def _clean_text(value, limit):
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _feedback_no():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3).upper()
    return f"FB{timestamp}{suffix}"


def _feedback_type(value):
    feedback_type = _clean_text(value, 50)
    if feedback_type in FEEDBACK_TYPE_TITLES:
        return feedback_type
    return "other"


def _rating(value):
    try:
        rating = int(value or 0)
    except (TypeError, ValueError):
        return None
    return rating if 1 <= rating <= 5 else None


def _device_info(body):
    device_info = body.get("deviceInfo")
    extra = {
        "nickname": _clean_text(body.get("nickname"), 100),
        "avatarUrl": _clean_text(body.get("avatarUrl"), 512),
    }
    extra = {key: value for key, value in extra.items() if value}

    if isinstance(device_info, dict):
        payload = dict(device_info)
        payload.update(extra)
        text = json.dumps(payload, ensure_ascii=False)
    elif device_info:
        text = str(device_info)
        if extra:
            text = json.dumps({"deviceInfo": text, **extra}, ensure_ascii=False)
    elif extra:
        text = json.dumps(extra, ensure_ascii=False)
    else:
        text = ""

    return _clean_text(text, 1000)


def _user_id(body):
    auth = _clean_text(request.headers.get("Authorization"), 255)
    if auth:
        user_id = int(current_user_id())
        _sync_user_profile(user_id, body)
        return user_id

    code = _clean_text(body.get("loginCode") or body.get("code"), 80)
    if code:
        user_id, _ = create_or_get_wechat_user(code, nickname=_clean_text(body.get("nickname"), 100) or None)
        _sync_user_profile(user_id, body)
        return int(user_id)

    user_id = int(current_user_id())
    _sync_user_profile(user_id, body)
    return user_id


def _sync_user_profile(user_id, body):
    nickname = _clean_text(body.get("nickname"), 100)
    avatar = _clean_text(body.get("avatarUrl") or body.get("avatar"), 512)
    if not nickname and not avatar:
        return

    mysql_exec(
        """
        UPDATE `user`
        SET nickname=COALESCE(NULLIF(%s, ''), nickname),
            avatar=COALESCE(NULLIF(%s, ''), avatar),
            updated_at=NOW()
        WHERE user_id=%s
        """,
        (nickname, avatar, user_id),
    )


def _clear_admin_feedback_cache():
    try:
        from admin_routes import clear_admin_cache

        clear_admin_cache()
    except Exception:
        pass


@api_bp.post("/feedback/submit")
def submit_feedback():
    body = body_json()
    content = _clean_text(body.get("content"), 500)
    if len(content) < 5:
        return ok("feedback content must be at least 5 characters", {"field": "content"}, 400)

    feedback_type = _feedback_type(body.get("type") or body.get("feedbackType"))
    star_rating = _rating(body.get("rating") if "rating" in body else body.get("starRating"))
    feedback_no = _feedback_no()
    submitted_at = now_str()
    priority = "high" if feedback_type == "bug" or (star_rating is not None and star_rating <= 2) else "normal"

    inserted_id = mysql_exec(
        """
        INSERT INTO user_feedback
        (feedback_no, user_id, feedback_type, title, content, contact, device_info,
         status, priority, star_rating, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            feedback_no,
            _user_id(body),
            feedback_type,
            FEEDBACK_TYPE_TITLES[feedback_type],
            content,
            _clean_text(body.get("contact"), 100),
            _device_info(body),
            "pending",
            priority,
            star_rating,
            submitted_at,
            submitted_at,
        ),
        fetch_last_id=True,
    )

    if not inserted_id:
        return ok("feedback submit failed", {"feedbackId": feedback_no}, 500)

    _clear_admin_feedback_cache()
    return ok(
        "feedback submitted",
        {
            "feedbackId": feedback_no,
            "status": "pending",
            "submittedAt": submitted_at,
        },
    )
