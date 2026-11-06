from datetime import datetime, timezone
import json
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

ROOT = Path(__file__).parent
DB_PATH = Path(os.getenv("MU03_DATA_PATH", str(ROOT / "mu03_ru.sqlite3")))
ASSETS = {
    "1.jpg": "image/jpeg", "4.webp": "image/webp", "6.jpg": "image/jpeg",
    "snaptik.vn_7616226358024310033.mp4": "video/mp4",
}
DEFAULT_FAMILIES = ["Gen 4", "Gen 5", "HTIW", "Grinder", "D&F", "Nailer", "Sub Line"]
DEFAULT_LEADER = "Le Thanh Dat 1 (VN.MIL-PT-PRO-TOOL)"

app = FastAPI(title="MU03 Production Communication")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, day TEXT NOT NULL, title TEXT NOT NULL,
        family TEXT NOT NULL, content TEXT NOT NULL, cause TEXT, department TEXT,
        leader TEXT NOT NULL DEFAULT 'Le Thanh Dat 1 (VN.MIL-PT-PRO-TOOL)', status TEXT NOT NULL,
        line_id TEXT, note TEXT, media_json TEXT NOT NULL, sent_at TEXT NOT NULL,
        read_at TEXT, closed_at TEXT
    )""")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tickets)")}
    if "leader" not in columns:
        conn.execute("ALTER TABLE tickets ADD COLUMN leader TEXT NOT NULL DEFAULT 'Le Thanh Dat 1 (VN.MIL-PT-PRO-TOOL)'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_owner_day ON tickets(owner, day)")
    conn.execute("""CREATE TABLE IF NOT EXISTS families (
        owner TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(owner, name)
    )""")
    conn.commit()
    return conn


def owner(request: Request):
    for key in ("x-forwarded-email", "x-user-email", "x-databricks-user-name", "x-forwarded-user"):
        value = request.headers.get(key)
        if value:
            return value.strip()
    return "authenticated-user"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ticket_json(row):
    item = dict(row)
    item["media"] = json.loads(item.pop("media_json") or "[]")
    if not str(item.get("leader") or "").strip() or item["leader"] == "Leader Inbox":
        item["leader"] = DEFAULT_LEADER
    return item


def ensure_families(conn, user):
    for name in DEFAULT_FAMILIES:
        conn.execute("INSERT OR IGNORE INTO families(owner,name,created_at) VALUES(?,?,?)", (user, name, now_iso()))
    conn.commit()


@app.get("/", include_in_schema=False)
def home():
    index = ROOT / "index.html"
    return HTMLResponse(index.read_text(encoding="utf-8"))


@app.get("/js/{name}", include_in_schema=False)
def javascript(name: str):
    if not name.endswith(".js") or "/" in name or "\\" in name:
        raise HTTPException(404, "Script not found")
    path = (ROOT / "js" / name).resolve()
    if not path.exists() or ROOT.resolve() not in path.parents:
        raise HTTPException(404, "Script not found")
    return FileResponse(path, media_type="application/javascript")


@app.get("/asset/{name}", include_in_schema=False)
def asset(name: str):
    if name not in ASSETS:
        raise HTTPException(404, "Asset not found")
    path = (ROOT / name).resolve()
    if not path.exists() or ROOT.resolve() not in path.parents:
        raise HTTPException(404, "Asset not found")
    return FileResponse(path, media_type=ASSETS[name])


@app.get("/api/session")
def session(request: Request):
    user = owner(request)
    conn = db()
    ensure_families(conn, user)
    conn.close()
    return {"user": user, "today": datetime.now().date().isoformat()}


@app.get("/api/tickets")
def list_tickets(request: Request, day: str = "all"):
    conn = db()
    user = owner(request)
    query = "SELECT * FROM tickets WHERE owner=?"
    args = [user]
    if day != "all":
        query += " AND day=?"
        args.append(day)
    rows = conn.execute(query + " ORDER BY sent_at DESC", args).fetchall()
    conn.close()
    return [ticket_json(row) for row in rows]


@app.post("/api/tickets")
async def create_ticket(request: Request):
    payload = await request.json()
    required = ("title", "family", "content")
    if any(not str(payload.get(key, "")).strip() for key in required):
        raise HTTPException(400, "Title, family and content are required")
    stamp = now_iso()
    item = {
        "id": "R&U-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + os.urandom(2).hex(),
        "owner": owner(request), "day": datetime.now().date().isoformat(),
        "title": str(payload["title"]).strip(), "family": str(payload["family"]).strip(),
        "content": str(payload["content"]).strip(), "cause": str(payload.get("cause", "General")),
        "department": str(payload.get("department") or owner(request)),
        "leader": str(payload.get("leader") or DEFAULT_LEADER).strip(),
        "status": "WAITING FOR LEADER READ", "line_id": "", "note": "",
        "media_json": json.dumps(payload.get("media", [])), "sent_at": stamp,
        "read_at": None, "closed_at": None,
    }
    conn = db()
    conn.execute("""INSERT INTO tickets
        (id,owner,day,title,family,content,cause,department,leader,status,line_id,note,media_json,sent_at,read_at,closed_at)
        VALUES (:id,:owner,:day,:title,:family,:content,:cause,:department,:leader,:status,:line_id,:note,:media_json,:sent_at,:read_at,:closed_at)""", item)
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (item["id"],)).fetchone()
    conn.close()
    return ticket_json(row)


@app.patch("/api/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, request: Request):
    payload = await request.json()
    fields = {key: payload[key] for key in ("status", "line_id", "note") if key in payload}
    if "media" in payload:
        fields["media_json"] = json.dumps(payload["media"])
    if payload.get("status") == "READ":
        fields["read_at"] = now_iso()
    if payload.get("status") == "CLOSED":
        fields["closed_at"] = now_iso()
    conn = db()
    row = conn.execute("SELECT * FROM tickets WHERE id=? AND owner=?", (ticket_id, owner(request))).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Ticket not found")
    if fields:
        clause = ", ".join(f"{key}=?" for key in fields)
        conn.execute(f"UPDATE tickets SET {clause} WHERE id=? AND owner=?", (*fields.values(), ticket_id, owner(request)))
        conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    conn.close()
    return ticket_json(row)


@app.get("/api/families")
def list_families(request: Request):
    conn = db()
    ensure_families(conn, owner(request))
    rows = conn.execute("SELECT name FROM families WHERE owner=? ORDER BY created_at", (owner(request),)).fetchall()
    conn.close()
    return [row["name"] for row in rows]


@app.post("/api/families")
async def add_family(request: Request):
    payload = await request.json()
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "Family name is required")
    conn = db()
    conn.execute("INSERT OR IGNORE INTO families(owner,name,created_at) VALUES(?,?,?)", (owner(request), name, now_iso()))
    conn.commit()
    conn.close()
    return {"name": name}


@app.delete("/api/families/{name}")
def delete_family(name: str, request: Request):
    conn = db()
    conn.execute("DELETE FROM families WHERE owner=? AND name=?", (owner(request), name))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok", "app": "mu03-ru"}
