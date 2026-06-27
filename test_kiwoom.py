# -*- coding: utf-8 -*-
# 키움 REST API 인증 테스트 (1단계)
# 하는 일: GitHub Secrets에 넣은 앱키/시크릿으로 키움에서 "토큰"을 받아본다.
# 성공하면 "인증 성공"만 출력. 키 값은 절대 화면에 안 찍음.

import os
import sys
import json
import urllib.request
import urllib.error

APP_KEY = os.environ.get("KIWOOM_APP_KEY", "")
SECRET_KEY = os.environ.get("KIWOOM_SECRET_KEY", "")

def mask(s):
    # 키가 들어왔는지 확인용 — 앞2자, 길이만. 값 자체는 안 보여줌.
    if not s:
        return "(비어있음)"
    return f"{s[:2]}***（길이 {len(s)}）"

print("=" * 50)
print("키움 인증 테스트 시작")
print("=" * 50)
print(f"APP_KEY 확인:    {mask(APP_KEY)}")
print(f"SECRET_KEY 확인: {mask(SECRET_KEY)}")
print()

if not APP_KEY or not SECRET_KEY:
    print("❌ 키가 안 들어왔어. GitHub Secrets 이름이 정확한지 확인:")
    print("   KIWOOM_APP_KEY / KIWOOM_SECRET_KEY")
    sys.exit(1)

URL = "https://api.kiwoom.com/oauth2/token"
payload = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "secretkey": SECRET_KEY,
}

print(f"요청 보내는 중 → {URL}")
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    URL, data=data,
    headers={"Content-Type": "application/json;charset=UTF-8"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    token = body.get("token", "")
    if token:
        print()
        print("✅✅✅ 인증 성공! 토큰을 받았어.")
        print(f"   토큰 앞부분: {token[:6]}... (길이 {len(token)})")
        print(f"   만료시각: {body.get('expires_dt','?')}")
        print(f"   토큰종류: {body.get('token_type','?')}")
        print()
        print("→ 1단계 통과! 키움 인증이 작동해.")
    else:
        print("⚠️ 응답은 왔는데 토큰이 없어. 응답 내용:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        sys.exit(1)
except urllib.error.HTTPError as e:
    print()
    print(f"❌ HTTP 에러: {e.code}")
    try:
        err = e.read().decode("utf-8")
        print("   응답:", err[:300])
    except Exception:
        pass
    print()
    print("자주 나는 원인:")
    print("  - 앱키/시크릿이 틀림 (재발급한 새 키 맞는지)")
    print("  - IP 등록 안 됨 (키움 포털에서 IP 등록 필요할 수 있음)")
    print("  - API 사용신청이 아직 승인 안 됨")
    sys.exit(1)
except Exception as e:
    print(f"❌ 기타 에러: {e}")
    sys.exit(1)
