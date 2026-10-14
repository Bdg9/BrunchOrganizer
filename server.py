#!/usr/bin/env python3
"""Serveur du brunch : sert static/index.html et garde la liste dans data.json.

Usage : python3 server.py [port]      (port 8080 par défaut, écoute sur 127.0.0.1)
Variables : HOST (défaut 127.0.0.1), PORT, DATA_FILE.
"""
import json, os, re, secrets, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA_FILE = Path(os.environ.get("DATA_FILE", ROOT / "data.json"))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8080"))

MAX_ITEMS, MAX_SIGNUPS, MAX_BODY = 200, 1000, 2048
LOCK = threading.Lock()


def load():
    try:
        return json.loads(DATA_FILE.read_text("utf-8"))
    except (FileNotFoundError, ValueError):
        return {"items": [], "signups": []}


def save(state):
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), "utf-8")
    os.replace(tmp, DATA_FILE)


def clean(value, limit):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value[:limit]


class Handler(BaseHTTPRequestHandler):
    server_version = "Brunch/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return None
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/state":
            with LOCK:
                return self.send_json(200, load())
        if path in ("/", "/index.html"):
            body = (STATIC / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return self.wfile.write(body)
        self.send_json(404, {"error": "introuvable"})

    def do_POST(self):
        data = self.read_json()
        if data is None:
            return self.send_json(400, {"error": "requête invalide"})
        path = self.path.split("?", 1)[0]
        with LOCK:
            state = load()
            if path == "/api/items":
                name = clean(data.get("name"), 40)
                if not name:
                    return self.send_json(400, {"error": "nom vide"})
                if len(state["items"]) >= MAX_ITEMS:
                    return self.send_json(409, {"error": "liste pleine"})
                if any(i["name"].lower() == name.lower() for i in state["items"]):
                    return self.send_json(409, {"error": "déjà sur la liste"})
                state["items"].append({"id": secrets.token_hex(6), "name": name, "createdAt": int(time.time() * 1000)})
            elif path == "/api/signups":
                who = clean(data.get("who"), 24)
                item_id = str(data.get("itemId") or "")
                if not who or not any(i["id"] == item_id for i in state["items"]):
                    return self.send_json(400, {"error": "données invalides"})
                if len(state["signups"]) >= MAX_SIGNUPS:
                    return self.send_json(409, {"error": "liste pleine"})
                if any(s["itemId"] == item_id and s["who"].lower() == who.lower() for s in state["signups"]):
                    return self.send_json(200, state)
                state["signups"].append({"id": secrets.token_hex(6), "itemId": item_id, "who": who, "createdAt": int(time.time() * 1000)})
            else:
                return self.send_json(404, {"error": "introuvable"})
            save(state)
            self.send_json(200, state)

    def do_DELETE(self):
        m = re.fullmatch(r"/api/(items|signups)/([0-9a-f]{12})", self.path.split("?", 1)[0])
        if not m:
            return self.send_json(404, {"error": "introuvable"})
        kind, ident = m.groups()
        with LOCK:
            state = load()
            state[kind] = [x for x in state[kind] if x["id"] != ident]
            if kind == "items":
                state["signups"] = [s for s in state["signups"] if s["itemId"] != ident]
            save(state)
            self.send_json(200, state)


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print("Brunch sur http://%s:%d  (données : %s)" % (HOST, PORT, DATA_FILE))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
