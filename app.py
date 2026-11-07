from datetime import datetime, timezone
import json
import os
import csv
import sqlite3
import threading
from pathlib import Path
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

ROOT = Path(__file__).parent
DB_PATH = Path(os.getenv("MU03_DATA_PATH", str(ROOT / "mu03_ru.sqlite3")))
DEFAULT_FAMILIES = ["Gen 4", "Gen 5", "HTIW", "Grinder", "D&F", "Nailer", "Sub Line", "ALL MU03"]
DEFAULT_LEADER = "Le Thanh Dat 1 (VN.MIL-PT-PRO-TOOL)"
ROLE_RANK = {"MEMBER": 1, "AREA_LEADER": 2, "SHIFT_LEADER": 3, "ADMIN": 4}
CULTURE_GROUP_OWNER = "thanhdat.le2@ttigroup.com.vn"
CULTURE_GROUP_MEMBERS = [
    ("thanhphat.duong@ttigroup.com.vn", "Dương Thành Phát", "Assistant Production Manager", "MEMBER", ""),
    ("trunghieu.ho@ttigroup.com.vn", "Hồ Trung Hiếu", "Production Supervisor", "MEMBER", ""),
    ("thebao.vo@ttigroup.com.vn", "Võ Thế Bảo", "Production Supervisor", "MEMBER", ""),
    ("son.le@ttigroup.com.vn", "Lê Trần Thái Linh Sơn", "Production Supervisor", "MEMBER", ""),
    ("catnhan.le@ttigroup.com.vn", "Lê Cát Nhàn", "Production Supervisor", "MEMBER", ""),
    ("tuannhu.le01@ttigroup.com.vn", "Lê Tuấn Nhu", "Senior Production Supervisor", "MEMBER", ""),
    ("minhquan.pham1@ttigroup.com.vn", "Phạm Minh Quân", "Senior Production Supervisor", "MEMBER", ""),
    ("hailam.hoang@ttigroup.com.vn", "Hoàng Hải Lâm", "Senior Production Supervisor", "MEMBER", ""),
    ("thanhdat.le2@ttigroup.com.vn", "Lê Thành Đạt", "Acting Line Leader", "AREA_LEADER", ""),
]
ASSETS = {"1.jpg": "image/jpeg", "4.webp": "image/webp", "6.jpg": "image/jpeg", "8.jpg": "image/jpeg", "10.jpg": "image/jpeg", "12.png": "image/png", "13.png": "image/png", "15.png": "image/png", "snaptik.vn_7616226358024310033.mp4": "video/mp4"}
HTIW_LEADERS = [
    ("vandai.dang@ttigroup.com.vn", "Đặng Văn Đại", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("ngochieu.dang@ttigroup.com.vn", "Đặng Ngọc Hiếu", "Production Line Leader", "AREA_LEADER", "vandai.dang@ttigroup.com.vn"),
    ("tanphat.cao@ttigroup.com.vn", "Cao Tấn Phát", "Acting Line Leader", "AREA_LEADER", "vandai.dang@ttigroup.com.vn"),
    ("namtri.vo@ttigroup.com.vn", "Võ Nam Trí", "Acting Line Leader", "AREA_LEADER", "vandai.dang@ttigroup.com.vn"),
    ("vankien.vo@ttigroup.com.vn", "Võ Văn Kiên", "Junior Production Line Leader", "AREA_LEADER", "vandai.dang@ttigroup.com.vn"),
    ("quochai.pham@ttigroup.com.vn", "Phạm Quốc Hải", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("viettrinh.vo@ttigroup.com.vn", "Võ Thị Việt Trinh", "Production Line Leader", "AREA_LEADER", "quochai.pham@ttigroup.com.vn"),
    ("vandam.nguyen@ttigroup.com.vn", "Nguyễn Văn Đảm", "Production Line Leader", "AREA_LEADER", "quochai.pham@ttigroup.com.vn"),
    ("minhduong.hua@ttigroup.com.vn", "Hứa Minh Đương", "Production Line Leader", "AREA_LEADER", "quochai.pham@ttigroup.com.vn"),
    ("ngocthi.nguyen@ttigroup.com.vn", "Nguyễn Ngọc Thi", "Acting Line Leader", "AREA_LEADER", "quochai.pham@ttigroup.com.vn"),
]
GEN4_LEADERS = [
    ("huuthiep.nguyen@ttigroup.com.vn", "Nguyễn Hữu Thiệp", "Senior Production Shift Leader", "SHIFT_LEADER", ""),
    ("phuongthao.le@ttigroup.com.vn", "Lê Phương Thảo", "Production Line Leader", "AREA_LEADER", "huuthiep.nguyen@ttigroup.com.vn"),
    ("huutai.truong@ttigroup.com.vn", "Trương Hữu Tài", "Production Line Leader", "AREA_LEADER", "huuthiep.nguyen@ttigroup.com.vn"),
    ("vanluong.tran@ttigroup.com.vn", "Trần Văn Lương", "Acting Line Leader", "AREA_LEADER", "huuthiep.nguyen@ttigroup.com.vn"),
    ("kimchung.truong@ttigroup.com.vn", "Trương Kim Chung", "Senior Production Shift Leader", "SHIFT_LEADER", ""),
    ("quocdat.nguyen@ttigroup.com.vn", "Nguyễn Quốc Đạt", "Production Line Leader", "AREA_LEADER", "kimchung.truong@ttigroup.com.vn"),
    ("khanhhoa.vo@ttigroup.com.vn", "Võ Khánh Hòa", "Production Line Leader", "AREA_LEADER", "kimchung.truong@ttigroup.com.vn"),
    ("minhtam.nguyen@ttigroup.com.vn", "Nguyễn Minh Tâm", "Production Line Leader", "AREA_LEADER", "kimchung.truong@ttigroup.com.vn"),
    ("anh.nguyen1@ttigroup.com.vn", "Nguyễn Hoàng Anh", "Production Line Leader", "AREA_LEADER", "kimchung.truong@ttigroup.com.vn"),
]
GEN5_LEADERS = [
    ("minhtai.ngo@ttigroup.com.vn", "Ngô Minh Tài", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("huutho.truong@ttigroup.com.vn", "Trương Hữu Thọ", "Senior Production Line Leader", "AREA_LEADER", "minhtai.ngo@ttigroup.com.vn"),
    ("duyngau.ho@ttigroup.com.vn", "Hồ Duy Ngâu", "Production Line Leader", "AREA_LEADER", "minhtai.ngo@ttigroup.com.vn"),
    ("kiet.nguyen1@ttigroup.com.vn", "Nguyễn Quốc Kiệt", "Production Line Leader", "AREA_LEADER", "minhtai.ngo@ttigroup.com.vn"),
    ("vantro.pham@ttigroup.com.vn", "Phạm Văn Trổ", "Production Line Leader", "AREA_LEADER", "minhtai.ngo@ttigroup.com.vn"),
    ("trianhkhoa.ho01@ttigroup.com.vn", "Hồ Trị Anh Khoa", "Production Line Leader", "AREA_LEADER", "minhtai.ngo@ttigroup.com.vn"),
    ("thetrinh.le@ttigroup.com.vn", "Lê Thế Trinh", "Production Line Leader", "AREA_LEADER", "minhtai.ngo@ttigroup.com.vn"),
    ("hieu.nguyen7@ttigroup.com.vn", "Nguyễn Thanh Hiếu", "Acting Line Leader", "AREA_LEADER", "minhtai.ngo@ttigroup.com.vn"),
    ("hiepthai.duong@ttigroup.com.vn", "Dương Hiệp Thái", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("thanhtao.chau@ttigroup.com.vn", "Châu Thanh Tạo", "Senior Production Line Leader", "AREA_LEADER", "hiepthai.duong@ttigroup.com.vn"),
    ("duytrai.nguyen02@ttigroup.com.vn", "Nguyễn Trần Duy Trải", "Production Line Leader", "AREA_LEADER", "hiepthai.duong@ttigroup.com.vn"),
    ("vanhung.le1@ttigroup.com.vn", "Lê Văn Hùng", "Production Line Leader", "AREA_LEADER", "hiepthai.duong@ttigroup.com.vn"),
    ("hoangvu.luu@ttigroup.com.vn", "Lưu Hoàng Vũ", "Production Line Leader", "AREA_LEADER", "hiepthai.duong@ttigroup.com.vn"),
    ("phuong.nguyen7@ttigroup.com.vn", "Nguyễn Như Duy Phương", "Acting Line Leader", "AREA_LEADER", "hiepthai.duong@ttigroup.com.vn"),
    ("vankhang.vo@ttigroup.com.vn", "Võ Văn Khang", "Acting Line Leader", "AREA_LEADER", "hiepthai.duong@ttigroup.com.vn"),
]
GRINDER_LEADERS = [
    ("vanteo.nguyen07@ttigroup.com.vn", "Nguyễn Văn Tèo", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("vanhau.nong01@ttigroup.com.vn", "Nông Văn Hậu", "Production Line Leader", "AREA_LEADER", "vanteo.nguyen07@ttigroup.com.vn"),
    ("khacquoc.phan@ttigroup.com.vn", "Phan Khắc Quốc", "Production Line Leader", "AREA_LEADER", "vanteo.nguyen07@ttigroup.com.vn"),
    ("phuong.tran1@ttigroup.com.vn", "Trần Nguyễn Minh Phương", "Production Line Leader", "AREA_LEADER", "vanteo.nguyen07@ttigroup.com.vn"),
    ("vandat.nguyen@ttigroup.com.vn", "Nguyễn Văn Đạt", "Production Line Leader", "AREA_LEADER", "vanteo.nguyen07@ttigroup.com.vn"),
    ("quoccuong.duong@ttigroup.com.vn", "Dương Quốc Cường", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("vandanganh.vo@ttigroup.com.vn", "Võ Văn Đặng Anh", "Production Line Leader", "AREA_LEADER", "quoccuong.duong@ttigroup.com.vn"),
    ("hoangnho.dang@ttigroup.com.vn", "Đặng Hoàng Nhớ", "Production Line Leader", "AREA_LEADER", "quoccuong.duong@ttigroup.com.vn"),
    ("thanhnga.ly@ttigroup.com.vn", "Lý Thanh Nga", "Production Line Leader", "AREA_LEADER", "quoccuong.duong@ttigroup.com.vn"),
    ("thuhang.nguyen@ttigroup.com.vn", "Nguyễn Thu Hằng", "Acting Line Leader", "AREA_LEADER", "quoccuong.duong@ttigroup.com.vn"),
    ("nhung.nguyen4@ttigroup.com.vn", "Nguyễn Thị Hồng Nhung", "Acting Line Leader", "AREA_LEADER", "quoccuong.duong@ttigroup.com.vn"),
]
NAILER_LEADERS = [
    ("thithuhuong.phan01@ttigroup.com.vn", "Phan Thị Thu Hương", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("thihang.nguyen03@ttigroup.com.vn", "Nguyễn Thị Hằng", "Production Line Leader", "AREA_LEADER", "thithuhuong.phan01@ttigroup.com.vn"),
    ("thanhtam.duong@ttigroup.com.vn", "Dương Thanh Tâm", "Production Line Leader", "AREA_LEADER", "thithuhuong.phan01@ttigroup.com.vn"),
    ("minhkhoi.phan@ttigroup.com.vn", "Phan Minh Khôi", "Production Line Leader", "AREA_LEADER", "thithuhuong.phan01@ttigroup.com.vn"),
    ("tantrung.duong@ttigroup.com.vn", "Dương Tấn Trung", "Production Line Leader", "AREA_LEADER", "thithuhuong.phan01@ttigroup.com.vn"),
    ("nguyenbinh.cao@ttigroup.com.vn", "Cao Nguyễn Bình", "Acting Line Leader", "AREA_LEADER", "thithuhuong.phan01@ttigroup.com.vn"),
    ("vanloi.do@ttigroup.com.vn", "Đỗ Văn Lợi", "Acting Line Leader", "AREA_LEADER", "thithuhuong.phan01@ttigroup.com.vn"),
    ("hoa.dang@ttigroup.com.vn", "Đặng Thị Thanh Hòa", "Acting Line Leader", "AREA_LEADER", "thithuhuong.phan01@ttigroup.com.vn"),
    ("thisau.pham01@ttigroup.com.vn", "Phạm Thị Sáu", "Senior Production Line Leader", "AREA_LEADER", "thithuhuong.phan01@ttigroup.com.vn"),
    ("lamhuyenmai.huynh@ttigroup.com.vn", "Huỳnh Lâm Huyền Mai", "Senior Production Shift Leader", "SHIFT_LEADER", ""),
    ("chi.nguyen1@ttigroup.com.vn", "Nguyễn Thị Kim Chi", "Production Line Leader", "AREA_LEADER", "lamhuyenmai.huynh@ttigroup.com.vn"),
    ("dinhduc.tran@ttigroup.com.vn", "Trần Đình Đức", "Production Line Leader", "AREA_LEADER", "lamhuyenmai.huynh@ttigroup.com.vn"),
    ("truong.nguyen2@ttigroup.com.vn", "Nguyễn Nhật Trường", "Production Line Leader", "AREA_LEADER", "lamhuyenmai.huynh@ttigroup.com.vn"),
    ("huynhngoc.duong@ttigroup.com.vn", "Dương Huỳnh Ngọc", "Acting Line Leader", "AREA_LEADER", "lamhuyenmai.huynh@ttigroup.com.vn"),
]
DF_LEADERS = [
    ("lam.nguyen1@ttigroup.com.vn", "Nguyễn Thanh Lâm", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("ducdan.ho@ttigroup.com.vn", "Hồ Đức Dân", "Production Line Leader", "AREA_LEADER", "lam.nguyen1@ttigroup.com.vn"),
    ("vantuan.nguyen10@ttigroup.com.vn", "Nguyễn Văn Tuấn", "Senior Production Line Leader", "AREA_LEADER", "lam.nguyen1@ttigroup.com.vn"),
    ("thicamthom.tran01@ttigroup.com.vn", "Trần Thị Cẩm Thơm", "Production Line Leader", "AREA_LEADER", "lam.nguyen1@ttigroup.com.vn"),
    ("thanhdat.le4@ttigroup.com.vn", "Lê Thành Đạt", "Acting Line Leader", "AREA_LEADER", "lam.nguyen1@ttigroup.com.vn"),
    ("tanphat.pham2@ttigroup.com.vn", "Phạm Tấn Phát", "Acting Line Leader", "AREA_LEADER", "lam.nguyen1@ttigroup.com.vn"),
    ("thuy.nguyen6@ttigroup.com.vn", "Nguyễn Thị Thu Thủy", "Production Shift Leader", "SHIFT_LEADER", ""),
    ("hoaivinh.do@ttigroup.com.vn", "Đổ Hoài Vinh", "Production Line Leader", "AREA_LEADER", "thuy.nguyen6@ttigroup.com.vn"),
    ("tien.nguyen@ttigroup.com.vn", "Nguyễn Thị Cẩm Tiên", "Production Line Leader", "AREA_LEADER", "thuy.nguyen6@ttigroup.com.vn"),
    ("phuong.tran@ttigroup.com.vn", "Trần Thị Mỹ Phượng", "Production Line Leader", "AREA_LEADER", "thuy.nguyen6@ttigroup.com.vn"),
    ("vantien.tran03@ttigroup.com.vn", "Trần Văn Tiền", "Production Line Leader", "AREA_LEADER", "thuy.nguyen6@ttigroup.com.vn"),
    ("chihau.le@ttigroup.com.vn", "Lê Chí Hậu", "Acting Line Leader", "AREA_LEADER", "thuy.nguyen6@ttigroup.com.vn"),
    ("quangthang.le1@ttigroup.com.vn", "Lê Quang Thắng", "Acting Line Leader", "AREA_LEADER", "thuy.nguyen6@ttigroup.com.vn"),
]
SUBLINE_LEADERS = [
    ("danghai.le01@ttigroup.com.vn", "Lê Đăng Hải", "Senior Production Line Leader", "SHIFT_LEADER", ""),
    ("thingocyen.le@ttigroup.com.vn", "Lê Thị Ngọc Yến", "Senior Production Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
    ("thiphu.nguyen03@ttigroup.com.vn", "Nguyễn Thị Phú", "Production Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
    ("thingocgiau.vo@ttigroup.com.vn", "Võ Thị Ngọc Giàu", "Production Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
    ("thimyuyen.huynh@ttigroup.com.vn", "Huỳnh Thị Mỹ Uyên", "Acting Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
    ("thithu.nguyen2@ttigroup.com.vn", "Nguyễn Thị Thu", "Acting Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
    ("trungkien.tran2@ttigroup.com.vn", "Trần Trung Kiên", "Acting Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
    ("vanthun.la@ttigroup.com.vn", "La Văn Thun", "Acting Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
    ("thiquynhnhu.bui@ttigroup.com.vn", "Bùi Thị Quỳnh Như", "Acting Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
    ("tranvuduy.hoang@ttigroup.com.vn", "Hoàng Trần Vũ Duy", "Acting Line Leader", "AREA_LEADER", "danghai.le01@ttigroup.com.vn"),
]
app = FastAPI(title="MU03 Production Communication")
SCHEMA_LOCK = threading.Lock()
SCHEMA_READY = False
DIRECTORY = {}


def load_directory():
    global DIRECTORY
    if DIRECTORY:
        return DIRECTORY
    path = ROOT / "company_directory.csv"
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as source:
            DIRECTORY = {row["email"].strip().lower(): row for row in csv.DictReader(source) if row.get("email")}
    return DIRECTORY


def add_column(conn, table, column, definition):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def db():
    global SCHEMA_READY
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=20000")
    if not SCHEMA_READY:
        with SCHEMA_LOCK:
            if not SCHEMA_READY:
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                except sqlite3.OperationalError:
                    pass
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
                add_column(conn, "tickets", "target_email", "TEXT NOT NULL DEFAULT ''")
                add_column(conn, "tickets", "target_family", "TEXT NOT NULL DEFAULT ''")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_owner_day ON tickets(owner, day)")
                conn.execute("""CREATE TABLE IF NOT EXISTS families (
                    owner TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL,
                    teams_webhook_url TEXT NOT NULL DEFAULT '', PRIMARY KEY(owner, name)
                )""")
                add_column(conn, "families", "teams_webhook_url", "TEXT NOT NULL DEFAULT ''")
                conn.execute("""CREATE TABLE IF NOT EXISTS family_members (
                    family_owner TEXT NOT NULL, family_name TEXT NOT NULL, email TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '', title TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'MEMBER', managed_by TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                    PRIMARY KEY(family_owner, family_name, email)
                )""")
                add_column(conn, "family_members", "display_name", "TEXT NOT NULL DEFAULT ''")
                add_column(conn, "family_members", "title", "TEXT NOT NULL DEFAULT ''")
                add_column(conn, "family_members", "managed_by", "TEXT NOT NULL DEFAULT ''")
                conn.execute("UPDATE family_members SET role='AREA_LEADER' WHERE role='MEMBER'")
                conn.commit()
                SCHEMA_READY = True
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


def directory_lookup(request, email):
    email = email.strip().lower()
    record = load_directory().get(email)
    if record:
        return {"email": email, "display_name": record["display_name"], "teams_name": record["display_name"], "title": record["title"], "employee_code": record["employee_code"], "source": "company-directory"}
    token = os.getenv("MS_GRAPH_ACCESS_TOKEN", "").strip()
    if token:
        try:
            url = "https://graph.microsoft.com/v1.0/users/" + email + "?$select=displayName,mail,userPrincipalName"
            graph_request = UrlRequest(url, headers={"Authorization": f"Bearer {token}"})
            with urlopen(graph_request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
            name = data.get("displayName") or email
            return {"email": data.get("mail") or data.get("userPrincipalName") or email, "display_name": name, "teams_name": name, "source": "microsoft-graph"}
        except Exception:
            pass
    for key in ("x-forwarded-user-name", "x-user-name", "x-databricks-display-name"):
        value = request.headers.get(key)
        if value and "@" not in value and email == user_email(request):
            return {"email": email, "display_name": value.strip(), "teams_name": value.strip(), "source": "login-header"}
    return {"email": email, "display_name": email, "teams_name": email, "source": "email-fallback"}


def ensure_families(conn, user):
    conn.execute("INSERT OR IGNORE INTO families(owner,name,created_at) VALUES(?,?,?)", (CULTURE_GROUP_OWNER, "Ban Văn Hóa", now_iso()))
    for email, display_name, title, role, managed_by in CULTURE_GROUP_MEMBERS:
        conn.execute(
            "INSERT OR REPLACE INTO family_members(family_owner,family_name,email,display_name,title,role,managed_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (CULTURE_GROUP_OWNER, "Ban Văn Hóa", email, display_name, title, role, managed_by, now_iso()),
        )
    for name in DEFAULT_FAMILIES:
        conn.execute("INSERT OR IGNORE INTO families(owner,name,created_at) VALUES(?,?,?)", (CULTURE_GROUP_OWNER, name, now_iso()))
    conn.commit()
    has_own = conn.execute("SELECT 1 FROM families WHERE owner=? LIMIT 1", (user,)).fetchone()
    is_member = conn.execute("SELECT 1 FROM family_members WHERE email=? LIMIT 1", (user,)).fetchone()
    if not has_own and not is_member:
        for name in DEFAULT_FAMILIES:
            conn.execute("INSERT OR IGNORE INTO families(owner,name,created_at) VALUES(?,?,?)", (user, name, now_iso()))
        conn.commit()
    for family_name, members in (
        ("HTIW", HTIW_LEADERS),
        ("Gen 4", GEN4_LEADERS),
        ("Gen 5", GEN5_LEADERS),
        ("Grinder", GRINDER_LEADERS),
        ("Nailer", NAILER_LEADERS),
        ("D&F", DF_LEADERS),
        ("Sub Line", SUBLINE_LEADERS),
    ):
        for owner in dict.fromkeys((user, CULTURE_GROUP_OWNER)):
            if family_row(conn, owner, family_name):
                for email, display_name, title, role, managed_by in members:
                    conn.execute(
                        "INSERT OR REPLACE INTO family_members(family_owner,family_name,email,display_name,title,role,managed_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
                        (owner, family_name, email, display_name, title, role, managed_by, now_iso()),
                    )
    conn.commit()


def family_row(conn, owner, name):
    return conn.execute("SELECT * FROM families WHERE owner=? AND name=?", (owner, name)).fetchone()


def member_rows(conn, owner, name):
    return conn.execute("SELECT email, display_name, title, role, managed_by FROM family_members WHERE family_owner=? AND family_name=? ORDER BY role DESC, email", (owner, name)).fetchall()


def family_access(conn, user, name):
    if name == "ALL MU03":
        row = conn.execute("SELECT * FROM families WHERE name=? ORDER BY created_at LIMIT 1", (name,)).fetchone()
        return (row, "ALL") if row else (None, None)
    if conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name='Ban Văn Hóa' AND lower(email)=lower(?) LIMIT 1", (CULTURE_GROUP_OWNER, user)).fetchone():
        shared = family_row(conn, CULTURE_GROUP_OWNER, name)
        if shared:
            return shared, "VIEWER"
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
    target_email = str(row["target_email"] or "").strip()
    if target_email:
        if target_email.lower() == user.lower():
            return True
        target_family = str(row["target_family"] or "").strip()
        return conn.execute("""SELECT 1 FROM family_members m
            WHERE m.family_owner=? AND lower(m.email)=lower(?) AND m.role='AREA_LEADER'
              AND lower(m.managed_by)=lower(?) AND (?='' OR m.family_name=?) LIMIT 1""",
            (row["family_owner"], target_email, user, target_family, target_family)).fetchone() is not None
    if row["family"] == "ALL MU03":
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
        target_email = str(item.get("target_email") or "").strip().lower()
        is_target = not target_email or target_email == user.lower()
        if item["family"] == "ALL MU03":
            target_family = str(item.get("target_family") or "").strip()
            target_row = conn.execute("""SELECT role, managed_by FROM family_members
                WHERE family_owner=? AND lower(email)=lower(?) AND role IN ('AREA_LEADER','SHIFT_LEADER')
                  AND (?='' OR family_name=?) ORDER BY role DESC LIMIT 1""",
                (item["family_owner"], target_email, target_family, target_family)).fetchone() if target_email else None
            if target_row and target_row["role"] == "AREA_LEADER":
                is_area = is_target
                is_shift = bool(target_row["managed_by"]) and target_row["managed_by"].lower() == user.lower()
            elif target_row and target_row["role"] == "SHIFT_LEADER":
                is_shift = is_target
                is_area = False
            else:
                is_shift = conn.execute("SELECT 1 FROM family_members WHERE email=? AND role='SHIFT_LEADER'", (user,)).fetchone() is not None
                is_area = conn.execute("SELECT 1 FROM family_members WHERE email=? AND role='AREA_LEADER'", (user,)).fetchone() is not None
        else:
            is_shift = conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND email=? AND role='SHIFT_LEADER'", (item["family_owner"], item["family"], user)).fetchone() is not None
            is_area = conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND email=? AND role='AREA_LEADER'", (item["family_owner"], item["family"], user)).fetchone() is not None
        item["can_confirm"] = is_target and is_shift
        item["can_manage"] = is_target and is_area
        if item["family"] == "ALL MU03" and target_email and target_row and target_row["role"] == "AREA_LEADER":
            item["can_confirm"] = bool(target_row["managed_by"]) and target_row["managed_by"].lower() == user.lower()
            item["can_manage"] = is_target
        item["role"] = role
    return item


def notify_teams(ticket, event):
    webhook = os.getenv("MU03_TEAMS_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    app_url = os.getenv("MU03_APP_URL", "https://r-u-4482605715640778.18.azure.databricksapps.com")
    ticket_url = f"{app_url}/?ticket={ticket['id']}"
    card = {"@type": "MessageCard", "@context": "http://schema.org/extensions", "summary": f"MU03 R&U: {event}", "themeColor": "C1121F", "sections": [{"activityTitle": f"MU03 R&U: {event}", "facts": [{"name": "Ticket", "value": ticket["id"]}, {"name": "Family", "value": ticket["family"]}, {"name": "Sender", "value": ticket["owner"]}, {"name": "Shift leader", "value": ticket.get("shift_leader") or "Not configured"}, {"name": "Area leader", "value": ticket.get("area_leader") or "Not configured"}], "text": f"{ticket['title']}\nStatus: {ticket['status']}\nOpen: {ticket_url}"}], "potentialAction": [{"@type": "OpenUri", "name": "Open ticket", "targets": [{"os": "default", "uri": ticket_url}]}]}
    message = {"event": event, "ticket_id": ticket["id"], "family": ticket["family"], "title": ticket["title"], "status": ticket["status"], "sender_email": ticket["owner"], "recipient_emails": ticket.get("recipients", []), "shift_leader_email": ticket.get("shift_leader", ""), "area_leader_email": ticket.get("area_leader", ""), "ticket_url": ticket_url, "message_card": card}
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
    can_view_cfm = (
        role == "SHIFT_LEADER"
        or user in {member[0] for member in CULTURE_GROUP_MEMBERS}
        or conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name='Ban Văn Hóa' AND lower(email)=lower(?) LIMIT 1", (CULTURE_GROUP_OWNER, user)).fetchone() is not None
    )
    conn.close()
    profile = directory_lookup(request, user)
    return {"user": user, "display_name": profile["display_name"], "today": datetime.now().date().isoformat(), "role": role, "can_create_ticket": user in {member[0] for member in CULTURE_GROUP_MEMBERS}, "can_view_cfm": can_view_cfm, "teams_configured": bool(os.getenv("MU03_TEAMS_WEBHOOK_URL")), "directory_configured": bool(os.getenv("MS_GRAPH_ACCESS_TOKEN"))}


@app.get("/api/directory/lookup")
def lookup_directory(email: str, request: Request):
    if "@" not in email:
        raise HTTPException(400, "A company email is required")
    return directory_lookup(request, email)


@app.get("/api/tickets")
def list_tickets(request: Request, day: str = "all"):
    user = user_email(request)
    conn = db()
    query = "SELECT * FROM tickets WHERE (owner=? OR (target_email<>'' AND (lower(target_email)=lower(?) OR EXISTS (SELECT 1 FROM family_members m WHERE m.family_owner=tickets.family_owner AND lower(m.email)=lower(tickets.target_email) AND m.role='AREA_LEADER' AND lower(m.managed_by)=lower(?) AND (tickets.target_family='' OR m.family_name=tickets.target_family)))) OR (target_email='' AND (family='ALL MU03' OR EXISTS (SELECT 1 FROM family_members m WHERE m.family_owner=tickets.family_owner AND m.family_name=tickets.family AND lower(m.email)=lower(?)))))"
    args = [user, user, user, user]
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
    if user not in {member[0] for member in CULTURE_GROUP_MEMBERS}:
        raise HTTPException(403, "Only the Ban Văn Hóa members can create tickets")
    if any(not str(payload.get(key, "")).strip() for key in ("title", "family", "content")):
        raise HTTPException(400, "Title, family and content are required")
    conn = db()
    access, _ = family_access(conn, user, str(payload["family"]).strip())
    if not access:
        conn.close()
        raise HTTPException(403, "You are not assigned to this family")
    family_owner, family_name = access["owner"], access["name"]
    if family_name == "ALL MU03":
        broadcast_families = [name for name in DEFAULT_FAMILIES if name != "ALL MU03"]
        placeholders = ",".join("?" for _ in broadcast_families)
        broadcast_rows = conn.execute(
            f"SELECT DISTINCT family_name, email, display_name, title, role, managed_by FROM family_members WHERE family_owner=? AND family_name IN ({placeholders}) AND role='AREA_LEADER' ORDER BY email",
            (CULTURE_GROUP_OWNER, *broadcast_families),
        ).fetchall()
        targets = []
        seen = set()
        for row in broadcast_rows:
            email = row["email"].strip().lower()
            if email not in seen:
                seen.add(email)
                targets.append(row)
        family_owner = CULTURE_GROUP_OWNER
    else:
        members = member_rows(conn, family_owner, family_name)
        targets = [None]
        members = list(members)
    shifts = [row["email"] for row in members if row["role"] == "SHIFT_LEADER"] if family_name != "ALL MU03" else []
    areas = [row["email"] for row in members if row["role"] == "AREA_LEADER"] if family_name != "ALL MU03" else []
    recipients = [row["email"] for row in members] if family_name != "ALL MU03" else []
    if not targets:
        conn.close()
        raise HTTPException(400, "No leaders are configured for ALL MU03")
    results = []
    for target in targets:
        target_email = target["email"].strip().lower() if target else ""
        item = {"id": "R&U-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + os.urandom(2).hex(), "owner": user, "day": datetime.now().date().isoformat(), "title": str(payload["title"]).strip(), "family": family_name, "content": str(payload["content"]).strip(), "cause": str(payload.get("cause", "General")), "department": user, "leader": target_email or (areas[0] if areas else DEFAULT_LEADER), "status": "WAITING FOR LEADER READ", "line_id": "", "note": "", "media_json": json.dumps(payload.get("media", [])), "sent_at": now_iso(), "read_at": None, "closed_at": None, "family_owner": family_owner, "shift_leader": target["managed_by"].strip().lower() if target and target["role"] == "AREA_LEADER" else (shifts[0] if shifts else ""), "area_leader": target_email if target and target["role"] == "AREA_LEADER" else (areas[0] if areas else ""), "recipient_emails": json.dumps([target_email] if target_email else recipients), "target_email": target_email, "target_family": target["family_name"] if target and target["role"] == "AREA_LEADER" else ""}
        conn.execute("""INSERT INTO tickets (id,owner,day,title,family,content,cause,department,leader,status,line_id,note,media_json,sent_at,read_at,closed_at,family_owner,shift_leader,area_leader,recipient_emails,target_email,target_family) VALUES (:id,:owner,:day,:title,:family,:content,:cause,:department,:leader,:status,:line_id,:note,:media_json,:sent_at,:read_at,:closed_at,:family_owner,:shift_leader,:area_leader,:recipient_emails,:target_email,:target_family)""", item)
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (item["id"],)).fetchone()
        results.append(ticket_json(row, conn, user))
    conn.commit()
    conn.close()
    for result in results:
        notify_teams(result, "New ticket")
    return results[0] if len(results) == 1 else {"broadcast": True, "count": len(results), "tickets": results}


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
    if status == "READ" and not current.get("can_manage"):
        conn.close()
        raise HTTPException(403, "Only the assigned area leader can mark this ticket READ")
    if status in ("SHIFT LEADER CONFIRMED", "SHIFT LEADER REJECTED") and not current.get("can_confirm"):
        conn.close()
        raise HTTPException(403, "Only the assigned shift leader can confirm this ticket")
    if status in ("SHIFT LEADER CONFIRMED", "SHIFT LEADER REJECTED") and (row["status"] != "READ" or not row["read_at"]):
        conn.close()
        raise HTTPException(409, "The assigned leader must read and update this ticket first")
    if status in ("LINE SHARING COMPLETED", "NO LINE - COMPLETED") and not current.get("can_manage"):
        conn.close()
        raise HTTPException(403, "Only the area leader can manage this ticket")
    if status == "LINE SHARING COMPLETED":
        if not str(payload.get("line_id", "")).strip():
            conn.close()
            raise HTTPException(400, "Line ID is required")
        if not payload.get("media"):
            conn.close()
            raise HTTPException(400, "Sharing image or video is required")
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
    is_culture_member = conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name='Ban Văn Hóa' AND lower(email)=lower(?) LIMIT 1", (CULTURE_GROUP_OWNER, user)).fetchone()
    if is_culture_member:
        rows = conn.execute("SELECT DISTINCT name FROM families WHERE owner=? ORDER BY created_at", (CULTURE_GROUP_OWNER,)).fetchall()
    else:
        rows = conn.execute("""SELECT DISTINCT f.name FROM families f LEFT JOIN family_members m
            ON m.family_owner=f.owner AND m.family_name=f.name
            WHERE f.owner=? OR lower(m.email)=lower(?) ORDER BY f.created_at""", (user, user)).fetchall()
    result = [row["name"] for row in rows]
    if "ALL MU03" not in result:
        result.append("ALL MU03")
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
    result = []
    for row in member_rows(conn, access["owner"], name):
        item = dict(row)
        profile = directory_lookup(request, item["email"])
        if not item.get("display_name") or item["display_name"].lower() == item["email"].lower():
            item["display_name"] = profile["display_name"]
        if not item.get("title"):
            item["title"] = profile.get("title", "")
        result.append(item)
    conn.close()
    return result


@app.post("/api/families/{name}/members")
async def add_member(name: str, request: Request):
    user = user_email(request)
    payload = await request.json()
    email = str(payload.get("email", "")).strip().lower()
    profile = directory_lookup(request, email)
    display_name = str(payload.get("display_name") or profile["display_name"]).strip()
    title = str(payload.get("title") or profile.get("title") or "").strip()
    role = str(payload.get("role", "MEMBER")).strip().upper()
    managed_by = str(payload.get("managed_by", "")).strip().lower()
    if "@" not in email or role not in ("AREA_LEADER", "SHIFT_LEADER"):
        raise HTTPException(400, "A company email and valid role are required")
    conn = db()
    if not family_row(conn, user, name):
        conn.close()
        raise HTTPException(403, "Only the family owner can manage members")
    if role == "AREA_LEADER":
        if not managed_by or not conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND lower(email)=lower(?) AND role='SHIFT_LEADER'", (user, name, managed_by)).fetchone():
            conn.close()
            raise HTTPException(400, "Select a shift leader for this area leader")
    else:
        managed_by = ""
    conn.execute("INSERT OR REPLACE INTO family_members(family_owner,family_name,email,display_name,title,role,managed_by,created_at) VALUES(?,?,?,?,?,?,?,?)", (user, name, email, display_name, title, role, managed_by, now_iso()))
    conn.commit()
    conn.close()
    return {"email": email, "display_name": display_name, "title": title, "teams_name": profile["teams_name"], "role": role, "managed_by": managed_by}


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
