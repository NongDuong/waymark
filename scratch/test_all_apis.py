"""
Test script for all recently changed APIs.
Usage: python scratch/test_all_apis.py [base_url]
Default base_url: http://localhost:8000/v1
"""
import sys
import json
import uuid
import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/v1"
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m~\033[0m"

results = {"pass": 0, "fail": 0, "skip": 0}
token = None
test_user = {
    "email": f"test_{uuid.uuid4().hex[:8]}@waymark.test",
    "username": f"test_{uuid.uuid4().hex[:8]}",
    "password": "TestPass123",
    "display_name": "API Test User"
}
test_memory_id = None

def ok(name):
    results["pass"] += 1
    print(f"  {PASS} {name}")

def fail(name, reason=""):
    results["fail"] += 1
    print(f"  {FAIL} {name}" + (f" — {reason}" if reason else ""))

def skip(name, reason=""):
    results["skip"] += 1
    print(f"  {SKIP} {name}" + (f" ({reason})" if reason else ""))

def h(token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

# ─────────────────────────────────────────
print(f"\nTarget: {BASE_URL}\n")

# ─── 1. AUTH ─────────────────────────────
print("── 1. Auth ──────────────────────────────")

# Signup
r = requests.post(f"{BASE_URL}/auth/signup/email", json=test_user)
if r.status_code == 200:
    ok("POST /auth/signup/email")
else:
    fail("POST /auth/signup/email", f"{r.status_code} {r.text[:100]}")

# Login
r = requests.post(f"{BASE_URL}/auth/login/password",
    data={"username": test_user["username"], "password": test_user["password"]},
    headers={"Content-Type": "application/x-www-form-urlencoded"})
if r.status_code == 200:
    token = r.json()["access_token"]
    ok("POST /auth/login/password")
else:
    fail("POST /auth/login/password", f"{r.status_code} {r.text[:100]}")

# GET /auth/me
if token:
    r = requests.get(f"{BASE_URL}/auth/me", headers=h(token))
    if r.status_code == 200 and r.json().get("username") == test_user["username"]:
        ok("GET /auth/me")
    else:
        fail("GET /auth/me", f"{r.status_code}")

# Signup — validation: username too short
r = requests.post(f"{BASE_URL}/auth/signup/email", json={
    "email": "x@test.com", "username": "ab", "password": "123456"
})
if r.status_code == 422:
    ok("POST /auth/signup — username too short → 422")
else:
    fail("POST /auth/signup — username too short → 422", f"got {r.status_code}")

# Signup — validation: password too short
r = requests.post(f"{BASE_URL}/auth/signup/email", json={
    "email": "x@test.com", "username": "validuser", "password": "12345"
})
if r.status_code == 422:
    ok("POST /auth/signup — password too short → 422")
else:
    fail("POST /auth/signup — password too short → 422", f"got {r.status_code}")

# Forgot password
r = requests.post(f"{BASE_URL}/auth/forgot-password",
    json={"email": test_user["email"]})
if r.status_code == 200:
    ok("POST /auth/forgot-password")
else:
    fail("POST /auth/forgot-password", f"{r.status_code}")

# GET /auth/config
r = requests.get(f"{BASE_URL}/auth/config")
if r.status_code == 200:
    ok("GET /auth/config")
else:
    fail("GET /auth/config", f"{r.status_code}")

# ─── 2. PROFILE ──────────────────────────
print("\n── 2. Profile ───────────────────────────")

if token:
    r = requests.get(f"{BASE_URL}/me", headers=h(token))
    if r.status_code == 200 and "username" in r.json():
        ok("GET /me")
    else:
        fail("GET /me", f"{r.status_code}")

    r = requests.put(f"{BASE_URL}/me", headers=h(token),
        json={"display_name": "Test Updated"})
    if r.status_code == 200:
        ok("PUT /me")
    else:
        fail("PUT /me", f"{r.status_code}")

# ─── 3. MEMORIES ─────────────────────────
print("\n── 3. Memories ──────────────────────────")

if token:
    # Create memory (text only, no images)
    r = requests.post(f"{BASE_URL}/memories",
        headers={"Authorization": f"Bearer {token}"},
        data={"caption": "Test memory from API test", "lat": "21.0285", "lng": "105.8542", "privacy_level": "3"})
    if r.status_code == 200:
        test_memory_id = r.json().get("id")
        ok("POST /memories")
    else:
        fail("POST /memories", f"{r.status_code} {r.text[:150]}")

    # privacy_level invalid → 400
    r = requests.post(f"{BASE_URL}/memories",
        headers={"Authorization": f"Bearer {token}"},
        data={"caption": "test", "lat": "21.0", "lng": "105.0", "privacy_level": "99"})
    if r.status_code == 400:
        ok("POST /memories — invalid privacy_level → 400")
    else:
        fail("POST /memories — invalid privacy_level → 400", f"got {r.status_code}")

    # caption empty → 422
    r = requests.post(f"{BASE_URL}/memories",
        headers={"Authorization": f"Bearer {token}"},
        data={"caption": "", "lat": "21.0", "lng": "105.0"})
    if r.status_code in (400, 422):
        ok("POST /memories — empty caption → 400/422")
    else:
        fail("POST /memories — empty caption → 400/422", f"got {r.status_code}")

    if test_memory_id:
        r = requests.get(f"{BASE_URL}/memories/{test_memory_id}", headers=h(token))
        if r.status_code == 200:
            ok("GET /memories/{id}")
        else:
            fail("GET /memories/{id}", f"{r.status_code}")

# GET on-this-day
if token:
    r = requests.get(f"{BASE_URL}/memories/on-this-day", headers=h(token))
    if r.status_code == 200 and isinstance(r.json(), list):
        ok("GET /memories/on-this-day")
    else:
        fail("GET /memories/on-this-day", f"{r.status_code}")

# ─── 4. MAP ──────────────────────────────
print("\n── 4. Map ───────────────────────────────")

r = requests.get(f"{BASE_URL}/map/pins?lat=21.0285&lng=105.8542&radius=1000")
if r.status_code == 200 and isinstance(r.json(), list):
    ok("GET /map/pins (unauthenticated)")
else:
    fail("GET /map/pins (unauthenticated)", f"{r.status_code}")

if token:
    r = requests.get(f"{BASE_URL}/map/pins?lat=21.0285&lng=105.8542&radius=1000", headers=h(token))
    if r.status_code == 200:
        ok("GET /map/pins (authenticated)")
    else:
        fail("GET /map/pins (authenticated)", f"{r.status_code}")

# ─── 5. SOCIAL ───────────────────────────
print("\n── 5. Social ────────────────────────────")

if token and test_memory_id:
    # Like memory
    r = requests.post(f"{BASE_URL}/memories/{test_memory_id}/likes", headers=h(token))
    if r.status_code in (200, 201):
        ok("POST /memories/{id}/likes")
    else:
        fail("POST /memories/{id}/likes", f"{r.status_code}")

    # Get likes
    r = requests.get(f"{BASE_URL}/memories/{test_memory_id}/likes", headers=h(token))
    if r.status_code == 200 and isinstance(r.json(), list):
        ok("GET /memories/{id}/likes (batch load)")
    else:
        fail("GET /memories/{id}/likes", f"{r.status_code}")

    # Add comment
    r = requests.post(f"{BASE_URL}/memories/{test_memory_id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        data={"content": "Test comment from API test"})
    comment_id = None
    if r.status_code in (200, 201):
        comment_id = r.json().get("id")
        ok("POST /memories/{id}/comments")
    else:
        fail("POST /memories/{id}/comments", f"{r.status_code} {r.text[:100]}")

    # Get comments
    r = requests.get(f"{BASE_URL}/memories/{test_memory_id}/comments", headers=h(token))
    if r.status_code == 200 and isinstance(r.json(), list):
        ok("GET /memories/{id}/comments (batch load)")
    else:
        fail("GET /memories/{id}/comments", f"{r.status_code}")

    # Delete comment (soft delete)
    if comment_id:
        r = requests.delete(f"{BASE_URL}/comments/{comment_id}", headers=h(token))
        if r.status_code == 204:
            ok("DELETE /comments/{id} (soft delete)")
        else:
            fail("DELETE /comments/{id}", f"{r.status_code}")

# Notifications
if token:
    r = requests.get(f"{BASE_URL}/notifications?limit=10", headers=h(token))
    if r.status_code == 200 and isinstance(r.json(), list):
        ok("GET /notifications (batch load, cursor pagination)")
    else:
        fail("GET /notifications", f"{r.status_code}")

# Followers / Following / Friends (with pagination)
if token:
    for endpoint in ["/followers", "/following", "/friends"]:
        r = requests.get(f"{BASE_URL}{endpoint}?limit=10&offset=0", headers=h(token))
        if r.status_code == 200 and isinstance(r.json(), list):
            ok(f"GET {endpoint} (with limit/offset)")
        else:
            fail(f"GET {endpoint}", f"{r.status_code}")

# ─── 6. DISCOVERY ────────────────────────
print("\n── 6. Discovery ─────────────────────────")

if token:
    r = requests.get(f"{BASE_URL}/discovery/trending/nearby?lat=21.0285&lng=105.8542&radius=5000",
        headers=h(token))
    if r.status_code == 200 and isinstance(r.json(), list):
        ok("GET /discovery/trending/nearby (deleted_at filter + batch load)")
    else:
        fail("GET /discovery/trending/nearby", f"{r.status_code}")

# ─── 7. PROFILE MEMORIES ─────────────────
print("\n── 7. Profile memories (batch load) ────")

if token:
    me_id = None
    r = requests.get(f"{BASE_URL}/auth/me", headers=h(token))
    if r.status_code == 200:
        me_id = r.json().get("id")
    if me_id:
        r = requests.get(f"{BASE_URL}/users/{me_id}/memories?skip=0&limit=10", headers=h(token))
        if r.status_code == 200 and isinstance(r.json(), list):
            ok("GET /users/{id}/memories (batch load)")
        else:
            fail("GET /users/{id}/memories", f"{r.status_code}")

# ─── 8. CHAT ─────────────────────────────
print("\n── 8. Chat ──────────────────────────────")

if token:
    r = requests.get(f"{BASE_URL}/conversations", headers=h(token))
    if r.status_code == 200:
        ok("GET /conversations")
        convs = r.json()
        if convs:
            conv_id = convs[0].get("id")
            r2 = requests.get(f"{BASE_URL}/conversations/{conv_id}/messages?limit=30",
                headers=h(token))
            if r2.status_code == 200:
                ok("GET /conversations/{id}/messages (before_id pagination)")
            else:
                fail("GET /conversations/{id}/messages", f"{r2.status_code}")
        else:
            skip("GET /conversations/{id}/messages", "no conversations")
    else:
        fail("GET /conversations", f"{r.status_code}")

# ─── 9. LOGOUT ───────────────────────────
print("\n── 9. Logout ────────────────────────────")

if token:
    r = requests.post(f"{BASE_URL}/auth/logout", headers=h(token),
        json={"device_token": None})
    if r.status_code == 200:
        ok("POST /auth/logout")
    else:
        fail("POST /auth/logout", f"{r.status_code} {r.text[:100]}")

# ─── CLEANUP ─────────────────────────────
if token and test_memory_id:
    requests.delete(f"{BASE_URL}/memories/{test_memory_id}", headers=h(token))

# ─── SUMMARY ─────────────────────────────
total = results["pass"] + results["fail"] + results["skip"]
print(f"\n{'─'*45}")
print(f"  Passed: {results['pass']}/{total}  |  Failed: {results['fail']}  |  Skipped: {results['skip']}")
if results["fail"] == 0:
    print("  \033[92mAll tests passed — safe to deploy!\033[0m")
else:
    print("  \033[91mSome tests failed — check before deploying.\033[0m")
print(f"{'─'*45}\n")
