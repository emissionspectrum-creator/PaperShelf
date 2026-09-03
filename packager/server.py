#!/usr/bin/env python3
"""本機打包器伺服器：只做檔案 I/O 與 git 指令代理，不含出題/審題等判斷邏輯。

執行：python3 packager/server.py，然後開啟 http://localhost:8420
"""
import json
import mimetypes
import subprocess
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
SOURCE_IMAGES_DIR = ROOT / "source-images"
DOCS_DIR = ROOT / "docs"
EXAMS_DIR = DOCS_DIR / "exams"
MANIFEST_PATH = ROOT / "manifest.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
TW_TZ = timezone(timedelta(hours=8))


def load_manifest():
    if not MANIFEST_PATH.exists():
        return {"exams": []}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(data):
    MANIFEST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_images():
    if not SOURCE_IMAGES_DIR.exists():
        return []
    return sorted(
        str(p.relative_to(SOURCE_IMAGES_DIR))
        for p in SOURCE_IMAGES_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def escape_html(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_index_html(manifest):
    exams = sorted(manifest.get("exams", []), key=lambda e: e.get("addedAt", ""), reverse=True)
    grades = sorted({e["grade"] for e in exams})
    subjects = sorted({e["subject"] for e in exams})

    def option(v):
        return f'<option value="{escape_html(v)}">{escape_html(v)}</option>'

    items = "\n".join(
        f'      <li data-grade="{escape_html(e["grade"])}" data-subject="{escape_html(e["subject"])}">'
        f'<a href="{escape_html(e["file"])}">{escape_html(e["grade"])} {escape_html(e["subject"])}'
        f'{" · " + escape_html(e["scope"]) if e.get("scope") else ""}</a></li>'
        for e in exams
    )

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>考卷列表</title>
<style>
  html, body {{ margin: 0; padding: 0; background: #f5f4f0; font-family: system-ui, sans-serif; }}
  main {{ max-width: 640px; margin: 0 auto; padding: 1.5rem; }}
  .filters {{ display: flex; gap: 0.5rem; margin-bottom: 1rem; }}
  select {{ font-size: 1rem; padding: 0.3rem; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ margin-bottom: 0.5rem; }}
  a {{ display: block; padding: 0.75rem 1rem; background: #fff; border-radius: 6px; text-decoration: none; color: #222; }}
</style>
</head>
<body>
<main>
  <h1>考卷列表</h1>
  <div class="filters">
    <select id="grade-filter"><option value="">全部年級</option>{"".join(option(g) for g in grades)}</select>
    <select id="subject-filter"><option value="">全部科目</option>{"".join(option(s) for s in subjects)}</select>
  </div>
  <ul id="exam-list">
{items}
  </ul>
</main>
<script>
  const gradeSel = document.getElementById('grade-filter');
  const subjectSel = document.getElementById('subject-filter');
  const items = Array.from(document.querySelectorAll('#exam-list li'));
  function applyFilter() {{
    const g = gradeSel.value, s = subjectSel.value;
    items.forEach(li => {{
      const show = (!g || li.dataset.grade === g) && (!s || li.dataset.subject === s);
      li.style.display = show ? '' : 'none';
    }});
  }}
  gradeSel.addEventListener('change', applyFilter);
  subjectSel.addEventListener('change', applyFilter);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type=None):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or (mimetypes.guess_type(str(path))[0] or "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("", "/"):
            return self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")

        if path == "/api/images":
            return self._send_json({"images": list_images()})

        if path == "/api/manifest":
            return self._send_json(load_manifest())

        if path.startswith("/api/image/"):
            rel = unquote(path[len("/api/image/"):])
            target = (SOURCE_IMAGES_DIR / rel).resolve()
            base = SOURCE_IMAGES_DIR.resolve()
            if base not in target.parents:
                return self._send_json({"error": "invalid path"}, 400)
            if not target.exists():
                return self._send_json({"error": "not found"}, 404)
            return self._send_file(target)

        if path.startswith("/static/"):
            rel = unquote(path[len("/static/"):])
            target = (STATIC_DIR / rel).resolve()
            base = STATIC_DIR.resolve()
            if base not in target.parents:
                return self._send_json({"error": "invalid path"}, 400)
            if not target.exists():
                return self._send_json({"error": "not found"}, 404)
            return self._send_file(target)

        return self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._read_json_body()
        except Exception as e:
            return self._send_json({"error": f"bad json: {e}"}, 400)

        if path == "/api/exam":
            return self._handle_save_exam(body)
        if path == "/api/manifest":
            return self._handle_manifest(body)
        if path == "/api/index":
            return self._handle_render_index()
        if path == "/api/publish":
            return self._handle_publish(body)

        return self._send_json({"error": "not found"}, 404)

    def _handle_save_exam(self, body):
        exam_id = body.get("id", "")
        html = body.get("html", "")
        if not exam_id or not html:
            return self._send_json({"error": "id and html required"}, 400)
        safe_id = "".join(c for c in exam_id if c not in '/\\:*?"<>|')
        if safe_id != exam_id:
            return self._send_json({"error": "invalid id"}, 400)
        EXAMS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = EXAMS_DIR / f"{safe_id}.html"
        out_path.write_text(html, encoding="utf-8")
        return self._send_json({"ok": True, "file": str(out_path.relative_to(ROOT))})

    def _handle_manifest(self, body):
        action = body.get("action")
        manifest = load_manifest()

        if action == "add":
            required = ["id", "grade", "subject", "seq"]
            if any(k not in body for k in required):
                return self._send_json({"error": f"missing fields, need {required}"}, 400)
            entry = {
                "id": body["id"],
                "grade": body["grade"],
                "subject": body["subject"],
                "seq": body["seq"],
                "scope": body.get("scope", ""),
                "addedAt": datetime.now(TW_TZ).isoformat(),
                "file": f"exams/{body['id']}.html",
            }
            manifest["exams"] = [e for e in manifest["exams"] if e["id"] != entry["id"]]
            manifest["exams"].append(entry)
            save_manifest(manifest)
            return self._send_json({"ok": True, "manifest": manifest})

        if action == "delete":
            exam_id = body.get("id")
            if not exam_id:
                return self._send_json({"error": "id required"}, 400)
            manifest["exams"] = [e for e in manifest["exams"] if e["id"] != exam_id]
            save_manifest(manifest)
            exam_file = EXAMS_DIR / f"{exam_id}.html"
            if exam_file.exists():
                exam_file.unlink()
            return self._send_json({"ok": True, "manifest": manifest})

        return self._send_json({"error": "unknown action"}, 400)

    def _handle_render_index(self):
        manifest = load_manifest()
        html = render_index_html(manifest)
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
        return self._send_json({"ok": True})

    def _handle_publish(self, body):
        message = body.get("message") or "更新考卷"
        add = subprocess.run(["git", "add", "-A"], cwd=ROOT, capture_output=True, text=True)
        if add.returncode != 0:
            return self._send_json({"ok": False, "stage": "add", "output": add.stdout + add.stderr}, 500)

        commit = subprocess.run(["git", "commit", "-m", message], cwd=ROOT, capture_output=True, text=True)
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            return self._send_json({"ok": False, "stage": "commit", "output": commit.stdout + commit.stderr}, 500)

        push = subprocess.run(["git", "push"], cwd=ROOT, capture_output=True, text=True)
        if push.returncode != 0:
            return self._send_json({"ok": False, "stage": "push", "output": push.stdout + push.stderr}, 500)

        return self._send_json({"ok": True, "output": commit.stdout + push.stdout})

    def log_message(self, format, *args):
        pass


def main():
    port = 8420
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"PaperShelf 打包器：http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
