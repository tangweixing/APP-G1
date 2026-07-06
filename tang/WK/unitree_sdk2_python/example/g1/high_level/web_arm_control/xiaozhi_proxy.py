#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智控制台 (xiaozhi.me) 代理模块。

APP 不直接调 xiaozhi.me，由本模块转发：
  - token 由用户在 APP 里手动粘贴一次（从控制台 F12 复制 localStorage.token）
  - token 存本地文件 xiaozhi_auth.json（权限 600），APP 端拿不到 token
  - 所有转发带 Authorization: Bearer <token>

挂载在 web_arm_control/app.py 的 /api/agent/* 路由下。

为什么不用账号密码/手机号登录：
  - 账号密码登录要图形验证码（captcha session）
  - 手机号登录要阿里云滑块验证码（只能在浏览器跑，uni-app App 端跑不了）
  所以改成手动粘 token，最稳。
"""

import os
import json
import time
import threading
import logging

import requests

logger = logging.getLogger(__name__)

# ==================== 配置 ====================
XIAOZHI_BASE = "https://xiaozhi.me/api"
AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xiaozhi_auth.json")

# 默认智能体 ID（用户指定的控制台智能体）
DEFAULT_AGENT_ID = "1711120"

# 请求超时
TIMEOUT = 15

_token_lock = threading.Lock()


# ==================== token 存储 ====================
def _load_auth():
    """读取本地 {token, agent_id, saved_at}。"""
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"读取 xiaozhi_auth.json 失败: {e}")
    return {}


def _save_auth(token, agent_id=None):
    """保存 token + agent_id 到本地（权限 600）。"""
    old = _load_auth()
    with _token_lock:
        data = {
            "token": token,
            "agent_id": agent_id or old.get("agent_id") or DEFAULT_AGENT_ID,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            with open(AUTH_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.chmod(AUTH_FILE, 0o600)
        except Exception as e:
            logger.error(f"保存 xiaozhi_auth.json 失败: {e}")


def _clear_auth():
    """清空 token。"""
    try:
        if os.path.exists(AUTH_FILE):
            os.remove(AUTH_FILE)
    except Exception as e:
        logger.warning(f"删除 xiaozhi_auth.json 失败: {e}")


def _get_token():
    return _load_auth().get("token")


def save_token(token, agent_id=None):
    """用户手动粘贴 token 后调用。返回 (ok, message)。"""
    if not token or not isinstance(token, str):
        return False, "token 为空"
    token = token.strip()
    _save_auth(token, agent_id)
    return True, "token 已保存"


def get_agent_id():
    """当前选中的 agent_id（默认 1711120）。"""
    return _load_auth().get("agent_id") or DEFAULT_AGENT_ID


def set_agent_id(agent_id):
    """切换当前 agent_id。"""
    token = _get_token()
    if token:
        _save_auth(token, agent_id)


# ==================== 通用转发 ====================
def _xz_request(method, path, *, token=None, json_body=None, params=None):
    """发请求到 xiaozhi.me，返回 (ok, data_or_errmsg, status)。

    token=None 时不带 Authorization。
    """
    url = XIAOZHI_BASE + path
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.request(method, url, json=json_body, params=params,
                                headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        return False, f"网络错误: {e}", 0

    try:
        body = resp.json() if resp.content else {}
    except ValueError:
        body = {"raw": resp.text}

    if resp.status_code >= 200 and resp.status_code < 300:
        return True, body, resp.status_code
    msg = body.get("message") if isinstance(body, dict) else None
    # 401/403 通常意味着 token 失效或无权限
    if resp.status_code in (401, 403):
        return False, "token 无效或已过期，请重新粘贴", resp.status_code
    return False, msg or body or f"HTTP {resp.status_code}", resp.status_code


# ==================== 对外接口 ====================
def auth_status():
    """验证本地 token 是否有效（GET /api/user/identity-info）。"""
    token = _get_token()
    if not token:
        return True, {"logged_in": False}, 200
    ok, data, status = _xz_request("GET", "/user/identity-info", token=token)
    if not ok:
        return True, {"logged_in": False, "reason": "token 失效"}, 200
    return True, {"logged_in": True, "user": data, "agent_id": get_agent_id()}, 200


def logout():
    _clear_auth()
    return True, {"logged_out": True}, 200


def list_agents():
    """GET /api/agents，列智能体。"""
    token = _get_token()
    if not token:
        return False, "未登录", 401
    ok, data, status = _xz_request("GET", "/agents", token=token)
    if not ok:
        return False, data, status
    items = data.get("items") if isinstance(data, dict) and "items" in data else data
    return True, {"items": items}, status


def get_config():
    """GET /api/agents/{id}，读当前配置。"""
    token = _get_token()
    if not token:
        return False, "未登录", 401
    aid = get_agent_id()
    ok, data, status = _xz_request("GET", f"/agents/{aid}", token=token)
    if not ok:
        return False, data, status
    return True, data, status


def save_config(config):
    """POST /api/agents/{id}/config，改配置。config 是 dict。"""
    token = _get_token()
    if not token:
        return False, "未登录", 401
    aid = get_agent_id()
    ok, data, status = _xz_request("POST", f"/agents/{aid}/config", token=token, json_body=config)
    if not ok:
        return False, data, status
    return True, data, status


def list_voices():
    """音色列表。端点待确认，先试 /voices，404 再试其它。"""
    token = _get_token()
    if not token:
        return False, "未登录", 401
    for path in ["/voices", "/voice/list", "/tts/voices"]:
        ok, data, status = _xz_request("GET", path, token=token)
        if status != 404:
            if ok:
                items = data.get("items") if isinstance(data, dict) and "items" in data else data
                return True, {"items": items}, status
            return False, data, status
    return True, {"items": []}, 200


def optimize_character(character_text):
    """POST /api/agents/optimize-character，AI 优化人设。"""
    token = _get_token()
    if not token:
        return False, "未登录", 401
    ok, data, status = _xz_request(
        "POST", "/agents/optimize-character", token=token,
        json_body={"character": character_text},
    )
    if not ok:
        return False, data, status
    return True, data, status
