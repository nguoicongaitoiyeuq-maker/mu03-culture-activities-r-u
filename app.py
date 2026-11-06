from datetime import datetime, timezone
import json
import os
import sqlite3
from pathlib import Path
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

ROOT = Path(__file__).parent
DB_PATH = Path(os.getenv("MU03_DATA_PATH", str(ROOT / "mu03_ru.sqlite3")))
DEFAULT_FAMILIES = ["Gen 4", "Gen 5", "HTIW", "Grinder", "D&F", "Nailer", "Sub Line"]
DEFAULT_LEADER = "Le Thanh Dat 1 (VN.MIL-PT-PRO-TOOL)"
ROLE_RANK = {"MEMBER": 1, "AREA_LEADER": 2, "SHIFT_LEADER": 3, "ADMIN": 4}
ASSETS = {"1.jpg": "image/jpeg", "4.webp": "image/webp", "6.jpg": "image/jpeg", "snaptik.vn_7616226358024310033.mp4": "video/mp4"}
app = FastAPI(title="MU03 Production Communication")


def add_column(conn, table, column, definition):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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
    add_column(conn, "tickets", "family_owner", "TEXT NOT NULL DEFAULT ''")
    add_column(conn, "tickets", "shift_leader", "TEXT NOT NULL DEFAULT ''")
    add_column(conn, "tickets", "area_leader", "TEXT NOT NULL DEFAULT ''")
    add_column(conn, "tickets", "recipient_emails", "TEXT NOT NULL DEFAULT '[]'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_owner_day ON tickets(owner, day)")
    conn.execute("""CREATE TABLE IF NOT EXISTS families (
        owner TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL,
        teams_webhook_url TEXT NOT NULL DEFAULT '', PRIMARY KEY(owner, name)
    )""")
    add_column(conn, "families", "teams_webhook_url", "TEXT NOT NULL DEFAULT ''")
    conn.execute("""CREATE TABLE IF NOT EXISTS family_members (
        family_owner TEXT NOT NULL, family_name TEXT NOT NULL, email TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'MEMBER', created_at TEXT NOT NULL,
        PRIMARY KEY(family_owner, family_name, email)
    )""")
    conn.commit()
    return conn


def user_email(request: Request):
    for key in ("x-forwarded-email", "x-user-email", "x-databricks-user-name", "x-forwarded-user"):
        value = request.headers.get(key)
        if value and "@" in value:
            return value.strip().lower()
    for key in ("x-forwarded-email", "x-user-email", "x-databricks-user-name", "x-forwarded-user"):
        value = request.headers.get(key)
        if value:
            return value.strip().lower()
    return "authenticated-user"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_families(conn, user):
    has_own = conn.execute("SELECT 1 FROM families WHERE owner=? LIMIT 1", (user,)).fetchone()
    is_member = conn.execute("SELECT 1 FROM family_members WHERE email=? LIMIT 1", (user,)).fetchone()
    if not has_own and not is_member:
        for name in DEFAULT_FAMILIES:
            conn.execute("INSERT OR IGNORE INTO families(owner,name,created_at) VALUES(?,?,?)", (user, name, now_iso()))
        conn.commit()


def family_row(conn, owner, name):
    return conn.execute("SELECT * FROM families WHERE owner=? AND name=?", (owner, name)).fetchone()


def member_rows(conn, owner, name):
    return conn.execute("SELECT email, role FROM family_members WHERE family_owner=? AND family_name=? ORDER BY role DESC, email", (owner, name)).fetchall()


def family_access(conn, user, name):
    own = family_row(conn, user, name)
    if own:
        return own, "ADMIN"
    row = conn.execute("""SELECT f.*, m.role FROM families f JOIN family_members m
        ON m.family_owner=f.owner AND m.family_name=f.name
        WHERE f.name=? AND lower(m.email)=lower(?) ORDER BY m.role DESC LIMIT 1""", (name, user)).fetchone()
    return (row, row["role"] if row else None)


def highest_role(conn, user):
    roles = ["ADMIN"] if conn.execute("SELECT 1 FROM families WHERE owner=? LIMIT 1", (user,)).fetchone() else []
    roles += [row["role"] for row in conn.execute("SELECT role FROM family_members WHERE lower(email)=lower(?)", (user,)).fetchall()]
    return max(roles, key=lambda role: ROLE_RANK.get(role, 0), default="MEMBER")


def user_can_view(conn, row, user):
    if row["owner"] == user:
        return True
    return conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND lower(email)=lower(?) LIMIT 1", (row["family_owner"], row["family"], user)).fetchone() is not None


def ticket_json(row, conn=None, user=None):
    item = dict(row)
    item["media"] = json.loads(item.pop("media_json") or "[]")
    item["recipients"] = json.loads(item.pop("recipient_emails", "[]") or "[]")
    if not str(item.get("leader") or "").strip() or item["leader"] == "Leader Inbox":
        item["leader"] = item.get("area_leader") or DEFAULT_LEADER
    if conn and user:
        role = highest_role(conn, user)
        is_shift = conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND email=? AND role='SHIFT_LEADER'", (item["family_owner"], item["family"], user)).fetchone() is not None
        is_area = conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND email=? AND role='AREA_LEADER'", (item["family_owner"], item["family"], user)).fetchone() is not None
        item["can_confirm"] = is_shift
        item["can_manage"] = is_area
        item["role"] = role
    return item


def notify_teams(ticket, event):
    webhook = os.getenv("MU03_TEAMS_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    message = {"@type": "MessageCard", "@context": "http://schema.org/extensions", "summary": f"MU03 R&U: {event}", "themeColor": "C1121F", "sections": [{"activityTitle": f"MU03 R&U: {event}", "facts": [{"name": "Ticket", "value": ticket["id"]}, {"name": "Family", "value": ticket["family"]}, {"name": "Sender", "value": ticket["owner"]}, {"name": "Shift leader", "value": ticket.get("shift_leader") or "Not configured"}, {"name": "Area leader", "value": ticket.get("area_leader") or "Not configured"}], "text": f"{ticket['title']}\nStatus: {ticket['status']}"}]}
    try:
        request = UrlRequest(webhook, data=json.dumps(message).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=4):
            pass
    except Exception:
        pass


@app.get("/", include_in_schema=False)
def home():
    return HTMLResponse((ROOT / "index.html").read_text(encoding="utf-8"))


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
    user = user_email(request)
    conn = db()
    ensure_families(conn, user)
    role = highest_role(conn, user)
    conn.close()
    return {"user": user, "today": datetime.now().date().isoformat(), "role": role, "teams_configured": bool(os.getenv("MU03_TEAMS_WEBHOOK_URL"))}


@app.get("/api/tickets")
def list_tickets(request: Request, day: str = "all"):
    user = user_email(request)
    conn = db()
    query = "SELECT * FROM tickets WHERE (owner=? OR EXISTS (SELECT 1 FROM family_members m WHERE m.family_owner=tickets.family_owner AND m.family_name=tickets.family AND lower(m.email)=lower(?)))"
    args = [user, user]
    if day != "all":
        query += " AND day=?"
        args.append(day)
    rows = conn.execute(query + " ORDER BY sent_at DESC", args).fetchall()
    result = [ticket_json(row, conn, user) for row in rows]
    conn.close()
    return result


@app.post("/api/tickets")
async def create_ticket(request: Request):
    payload = await request.json()
    user = user_email(request)
    if any(not str(payload.get(key, "")).strip() for key in ("title", "family", "content")):
        raise HTTPException(400, "Title, family and content are required")
    conn = db()
    access, _ = family_access(conn, user, str(payload["family"]).strip())
    if not access:
        conn.close()
        raise HTTPException(403, "You are not assigned to this family")
    family_owner, family_name = access["owner"], access["name"]
    members = member_rows(conn, family_owner, family_name)
    shifts = [row["email"] for row in members if row["role"] == "SHIFT_LEADER"]
    areas = [row["email"] for row in members if row["role"] == "AREA_LEADER"]
    recipients = [row["email"] for row in members]
    item = {"id": "R&U-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + os.urandom(2).hex(), "owner": user, "day": datetime.now().date().isoformat(), "title": str(payload["title"]).strip(), "family": family_name, "content": str(payload["content"]).strip(), "cause": str(payload.get("cause", "General")), "department": user, "leader": areas[0] if areas else DEFAULT_LEADER, "status": "WAITING FOR SHIFT LEADER CONFIRMATION", "line_id": "", "note": "", "media_json": json.dumps(payload.get("media", [])), "sent_at": now_iso(), "read_at": None, "closed_at": None, "family_owner": family_owner, "shift_leader": shifts[0] if shifts else "", "area_leader": areas[0] if areas else "", "recipient_emails": json.dumps(recipients)}
    conn.execute("""INSERT INTO tickets (id,owner,day,title,family,content,cause,department,leader,status,line_id,note,media_json,sent_at,read_at,closed_at,family_owner,shift_leader,area_leader,recipient_emails) VALUES (:id,:owner,:day,:title,:family,:content,:cause,:department,:leader,:status,:line_id,:note,:media_json,:sent_at,:read_at,:closed_at,:family_owner,:shift_leader,:area_leader,:recipient_emails)""", item)
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (item["id"],)).fetchone()
    result = ticket_json(row, conn, user)
    conn.close()
    notify_teams(result, "New ticket")
    return result


@app.patch("/api/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, request: Request):
    payload = await request.json()
    user = user_email(request)
    conn = db()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not row or not user_can_view(conn, row, user):
        conn.close()
        raise HTTPException(404, "Ticket not found")
    current = ticket_json(row, conn, user)
    status = payload.get("status")
    if status in ("SHIFT LEADER CONFIRMED", "SHIFT LEADER REJECTED") and not current.get("can_confirm"):
        conn.close()
        raise HTTPException(403, "Only the assigned shift leader can confirm this ticket")
    if status in ("LINE SHARING COMPLETED", "NO LINE - COMPLETED") and not current.get("can_manage"):
        conn.close()
        raise HTTPException(403, "Only the area leader can manage this ticket")
    if status == "CLOSED" and not current.get("can_confirm"):
        conn.close()
        raise HTTPException(403, "Only the assigned shift leader can close this ticket")
    fields = {key: payload[key] for key in ("status", "line_id", "note") if key in payload}
    if "media" in payload:
        fields["media_json"] = json.dumps(payload["media"])
    if status == "READ":
        fields["read_at"] = now_iso()
    if status == "CLOSED":
        fields["closed_at"] = now_iso()
    if fields:
        clause = ", ".join(f"{key}=?" for key in fields)
        conn.execute(f"UPDATE tickets SET {clause} WHERE id=?", (*fields.values(), ticket_id))
        conn.commit()
    updated = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    result = ticket_json(updated, conn, user)
    conn.close()
    if status:
        notify_teams(result, f"Ticket status changed to {status}")
    return result


@app.get("/api/families")
def list_families(request: Request):
    user = user_email(request)
    conn = db()
    ensure_families(conn, user)
    rows = conn.execute("""SELECT DISTINCT f.name FROM families f LEFT JOIN family_members m
        ON m.family_owner=f.owner AND m.family_name=f.name
        WHERE f.owner=? OR lower(m.email)=lower(?) ORDER BY f.created_at""", (user, user)).fetchall()
    result = [row["name"] for row in rows]
    conn.close()
    return result


@app.post("/api/families")
async def add_family(request: Request):
    user = user_email(request)
    payload = await request.json()
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "Family name is required")
    conn = db()
    conn.execute("INSERT OR IGNORE INTO families(owner,name,created_at,teams_webhook_url) VALUES(?,?,?,?)", (user, name, now_iso(), str(payload.get("teams_webhook_url", "")).strip()))
    conn.commit()
    conn.close()
    return {"name": name}


@app.get("/api/families/{name}/members")
def list_members(name: str, request: Request):
    user = user_email(request)
    conn = db()
    access, _ = family_access(conn, user, name)
    if not access:
        conn.close()
        raise HTTPException(403, "Family not found")
    result = [dict(row) for row in member_rows(conn, access["owner"], name)]
    conn.close()
    return result


@app.post("/api/families/{name}/members")
async def add_member(name: str, request: Request):
    user = user_email(request)
    payload = await request.json()
    email = str(payload.get("email", "")).strip().lower()
    role = str(payload.get("role", "MEMBER")).strip().upper()
    if "@" not in email or role not in ("MEMBER", "AREA_LEADER", "SHIFT_LEADER"):
        raise HTTPException(400, "A company email and valid role are required")
    conn = db()
    if not family_row(conn, user, name):
        conn.close()
        raise HTTPException(403, "Only the family owner can manage members")
    conn.execute("INSERT OR REPLACE INTO family_members(family_owner,family_name,email,role,created_at) VALUES(?,?,?,?,?)", (user, name, email, role, now_iso()))
    conn.commit()
    conn.close()
    return {"email": email, "role": role}


@app.delete("/api/families/{name}/members/{email}")
def delete_member(name: str, email: str, request: Request):
    user = user_email(request)
    conn = db()
    if not family_row(conn, user, name):
        conn.close()
        raise HTTPException(403, "Only the family owner can manage members")
    conn.execute("DELETE FROM family_members WHERE family_owner=? AND family_name=? AND lower(email)=lower(?)", (user, name, email))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/families/{name}")
def delete_family(name: str, request: Request):
    user = user_email(request)
    conn = db()
    conn.execute("DELETE FROM family_members WHERE family_owner=? AND family_name=?", (user, name))
    conn.execute("DELETE FROM families WHERE owner=? AND name=?", (user, name))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok", "app": "mu03-ru"}
