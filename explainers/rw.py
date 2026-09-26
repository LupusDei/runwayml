"""Tiny stdlib client for the Runway API: submit, poll, download. Used by the elements video."""
import json, os, sys, time, urllib.request, urllib.error, base64, mimetypes

BASE = "https://api.dev.runwayml.com/v1"
KEY = os.environ["RUNWAYML_API_SECRET"]
HDR = {"Authorization": f"Bearer {KEY}", "X-Runway-Version": "2024-11-06", "Content-Type": "application/json"}

def _req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=HDR)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:800]}")

def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()

def submit(endpoint, body):
    return _req("POST", "/" + endpoint, body)["id"]

def wait(task_id, every=5, limit=1800):
    t0 = time.time()
    while True:
        t = _req("GET", f"/tasks/{task_id}")
        st = t.get("status")
        if st == "SUCCEEDED":
            return t
        if st in ("FAILED", "CANCELED"):
            raise RuntimeError(f"task {task_id} {st}: {t.get('failure')} {t.get('failureCode')}")
        if time.time() - t0 > limit:
            raise RuntimeError(f"task {task_id} timed out in {st}")
        time.sleep(every)

def fetch(url, dest):
    urllib.request.urlretrieve(url, dest)
    return dest

def run(endpoint, body, dest):
    tid = submit(endpoint, body)
    t = wait(tid)
    out = t["output"][0]
    fetch(out, dest)
    return tid, dest
