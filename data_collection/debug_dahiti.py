"""Debug DAHITI API: xem raw response"""
import os, sys, json, requests
from pathlib import Path

ENV_PATH = Path(__file__).parent.parent / ".env"
for line in ENV_PATH.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

API_KEY = os.environ.get("DAHITI_API_KEY", "")
print(f"Key: {API_KEY[:8]}...{API_KEY[-4:]}\n")

BASE_URL = "https://dahiti.dgfi.tum.de/api/v2/"

def test(endpoint, args):
    args["api_key"] = API_KEY
    print(f"POST {BASE_URL}{endpoint}")
    print(f"Args: {args}")
    r = requests.post(BASE_URL + endpoint, json=args, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type','')}")
    print(f"Raw response (500 chars):\n{r.text[:500]}")
    print()

# Test 1: get-nearest-target
test("get-nearest-target/", {"latitude": 10.804, "longitude": 105.234})

# Test 2: list-targets voi bbox nho
test("list-targets/", {
    "min_latitude": 10.0, "max_latitude": 11.5,
    "min_longitude": 104.5, "max_longitude": 106.0
})
