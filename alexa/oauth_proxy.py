import base64
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)
MAX_BODY_BYTES = 16 * 1024
LWA_TOKEN_URI = os.environ.get("LWA_TOKEN_URI", "https://api.amazon.com/auth/o2/token")
LWA_CLIENT_ID = os.environ.get("LWA_CLIENT_ID", "")

def _response(status, body, headers=None):
    return {"statusCode": status, "headers": headers or {"content-type": "application/json"}, "body": body}

def _client_id(event):
    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    auth = headers.get("authorization", "")
    if auth.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
            return decoded.split(":", 1)[0]
        except (ValueError, UnicodeError):
            return None
    try:
        payload = json.loads(event.get("body") or "{}")
        return payload.get("client_id")
    except (TypeError, ValueError):
        return None

def lambda_handler(event, context):
    if (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "")).upper() != "POST":
        return _response(405, json.dumps({"error": "method_not_allowed"}), {"content-type": "application/json", "allow": "POST"})
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except (ValueError, UnicodeError):
            return _response(400, json.dumps({"error": "invalid_request"}))
    if len(raw.encode("utf-8")) > MAX_BODY_BYTES:
        return _response(413, json.dumps({"error": "request_too_large"}))
    if LWA_CLIENT_ID and _client_id(event) != LWA_CLIENT_ID:
        return _response(401, json.dumps({"error": "invalid_client"}))
    headers = {str(k): v for k, v in (event.get("headers") or {}).items() if str(k).lower() in {"authorization", "content-type", "accept"}}
    request_id = (context or {}).aws_request_id if context else "unknown"
    try:
        response = urlopen(Request(LWA_TOKEN_URI, data=raw.encode("utf-8"), headers=headers, method="POST"), timeout=8)
        body = response.read().decode("utf-8")
        LOGGER.info("oauth_proxy request_id=%s upstream_status=%s", request_id, response.status)
        return _response(response.status, body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            code = json.loads(body).get("error")
        except (TypeError, ValueError):
            code = None
        LOGGER.warning("oauth_proxy request_id=%s upstream_status=%s error=%s", request_id, exc.code, code)
        return _response(exc.code, body)
    except (URLError, TimeoutError, OSError) as exc:
        LOGGER.error("oauth_proxy request_id=%s upstream_unavailable=%s", request_id, type(exc).__name__)
        return _response(502, json.dumps({"error": "temporarily_unavailable"}))
