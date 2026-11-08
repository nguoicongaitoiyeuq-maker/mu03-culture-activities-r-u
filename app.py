from datetime import datetime, timezone
import base64
from io import BytesIO
import json
import logging
import os
import csv
import sqlite3
import shutil
import tempfile
import threading
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request as UrlRequest, urlopen
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from starlette.background import BackgroundTask
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = Path(__file__).parent
BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
LOCAL_DB_PATH = ROOT / "mu03_ru.sqlite3"
CONFIGURED_DATA_PATH = os.getenv("MU03_DATA_PATH", "").strip()
DB_PATH = Path(CONFIGURED_DATA_PATH or LOCAL_DB_PATH).expanduser()
DEFAULT_FAMILIES = ["Gen 4", "Gen 5", "HTIW", "Grinder", "D&F", "Nailer", "Sub Line", "ALL MU03"]
DEFAULT_LEADER = "Le Thanh Dat 1 (VN.MIL-PT-PRO-TOOL)"
ROLE_RANK = {"MEMBER": 1, "AREA_LEADER": 2, "SHIFT_LEADER": 3, "ADMIN": 4}
SHIFT_CONFIRM_STATUSES = {"READ", "LINE SHARING COMPLETED", "NO LINE - COMPLETED"}
CULTURE_GROUP_OWNER = "thanhdat.le2@ttigroup.com.vn"
CULTURE_GROUP_NAME = "Core Teams"
LEGACY_CULTURE_GROUP_NAME = "Ban Văn Hóa"
CORE_TEAM_OWNER_EMAILS = ("khachieu.nguyen01@ttigroup.com.vn", "hongthai.vu@ttigroup.com.vn")
SHAREPOINT_HOST = os.getenv("MU03_SHAREPOINT_HOST", "ttigroup.sharepoint.com").strip()
SHAREPOINT_SITE_PATH = os.getenv("MU03_SHAREPOINT_SITE_PATH", "/sites/MU03CultureActivities").strip()
SHAREPOINT_LIST_NAME = os.getenv("MU03_SHAREPOINT_LIST_NAME", "MU03 Ticket Database").strip()
MU03_FLOW_HTTP_URL = os.getenv("MU03_FLOW_HTTP_URL", "").strip()
MU03_UPDATE_FLOW_HTTP_URL = os.getenv("MU03_UPDATE_FLOW_HTTP_URL", "").strip()
MU03_READ_FLOW_HTTP_URL = os.getenv("MU03_READ_FLOW_HTTP_URL", "").strip()
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
    ("hongthai.vu@ttigroup.com.vn", "Vũ Hồng Thái", "Production Manager", "SHIFT_LEADER", ""),
    ("khachieu.nguyen01@ttigroup.com.vn", "Brian Nguyễn Khắc Hiểu", "Senior Manufacturing Manager", "SHIFT_LEADER", ""),
]
ASSETS = {"1.jpg": "image/jpeg", "4.webp": "image/webp", "6.jpg": "image/jpeg", "8.jpg": "image/jpeg", "10.jpg": "image/jpeg", "12.png": "image/png", "13.png": "image/png", "15.png": "image/png", "16.jpg": "image/jpeg", "17.webp": "image/webp", "snaptik.vn_7616226358024310033.mp4": "video/mp4"}
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
LOGGER = logging.getLogger("mu03")
SCHEMA_LOCK = threading.Lock()
SCHEMA_READY = False
DIRECTORY = {}


def prepare_db_path():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH == LOCAL_DB_PATH or DB_PATH.exists() or not LOCAL_DB_PATH.exists():
        return
    shutil.copy2(LOCAL_DB_PATH, DB_PATH)


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
    prepare_db_path()
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
                add_column(conn, "tickets", "reviewed_by", "TEXT NOT NULL DEFAULT ''")
                add_column(conn, "tickets", "reviewed_at", "TEXT")
                add_column(conn, "tickets", "work_shift", "TEXT NOT NULL DEFAULT ''")
                add_column(conn, "tickets", "sharepoint_item_id", "TEXT NOT NULL DEFAULT ''")
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


def business_today():
    return datetime.now(BANGKOK_TZ).date().isoformat()


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
    conn.execute("UPDATE families SET name=? WHERE owner=? AND name=?", (CULTURE_GROUP_NAME, CULTURE_GROUP_OWNER, LEGACY_CULTURE_GROUP_NAME))
    conn.execute("UPDATE family_members SET family_name=? WHERE family_owner=? AND family_name=?", (CULTURE_GROUP_NAME, CULTURE_GROUP_OWNER, LEGACY_CULTURE_GROUP_NAME))
    conn.execute("UPDATE tickets SET family=? WHERE family=?", (CULTURE_GROUP_NAME, LEGACY_CULTURE_GROUP_NAME))
    conn.execute("UPDATE tickets SET target_family=? WHERE target_family=?", (CULTURE_GROUP_NAME, LEGACY_CULTURE_GROUP_NAME))
    conn.execute("INSERT OR IGNORE INTO families(owner,name,created_at) VALUES(?,?,?)", (CULTURE_GROUP_OWNER, CULTURE_GROUP_NAME, now_iso()))
    for email, display_name, title, role, managed_by in CULTURE_GROUP_MEMBERS:
        conn.execute(
            "INSERT OR REPLACE INTO family_members(family_owner,family_name,email,display_name,title,role,managed_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (CULTURE_GROUP_OWNER, CULTURE_GROUP_NAME, email, display_name, title, role, managed_by, now_iso()),
        )
    placeholders = ",".join("?" for _ in CORE_TEAM_OWNER_EMAILS)
    conn.execute(f"UPDATE family_members SET role='ADMIN', managed_by='' WHERE family_owner=? AND family_name=? AND lower(email) IN ({placeholders})", (CULTURE_GROUP_OWNER, CULTURE_GROUP_NAME, *CORE_TEAM_OWNER_EMAILS))
    conn.execute(f"UPDATE family_members SET role='MEMBER', managed_by='' WHERE family_owner=? AND family_name=? AND lower(email) NOT IN ({placeholders})", (CULTURE_GROUP_OWNER, CULTURE_GROUP_NAME, *CORE_TEAM_OWNER_EMAILS))
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
    if conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND lower(email)=lower(?) LIMIT 1", (CULTURE_GROUP_OWNER, CULTURE_GROUP_NAME, user)).fetchone():
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
    if str(row["shift_leader"] or "").strip().lower() == user.lower():
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


def media_preview_data(media):
    media_name = str(media.get("name") or "").lower()
    media_type = str(media.get("type") or "").lower()
    if not (media_type in ("image/heic", "image/heif") or media_name.endswith((".heic", ".heif", ".heics", ".heix"))):
        return ""
    data = str(media.get("data") or "")
    if not data.startswith("data:") or "," not in data:
        return ""
    try:
        from PIL import Image
        from pillow_heif import register_heif_opener
        register_heif_opener()
        source = Image.open(BytesIO(base64.b64decode(data.split(",", 1)[1]))).convert("RGB")
        output = BytesIO()
        source.save(output, format="PNG")
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return ""


def ticket_json(row, conn=None, user=None):
    item = dict(row)
    item["media"] = json.loads(item.pop("media_json") or "[]")
    for media in item["media"]:
        preview = media_preview_data(media)
        if preview:
            media["preview_data"] = preview
    item["recipients"] = json.loads(item.pop("recipient_emails", "[]") or "[]")
    item["can_update_today"] = item.get("day") == business_today()
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
                is_shift = str(item.get("shift_leader") or "").lower() == user.lower() or (bool(target_row["managed_by"]) and target_row["managed_by"].lower() == user.lower())
            elif target_row and target_row["role"] == "SHIFT_LEADER":
                is_shift = is_target
                is_area = False
            else:
                is_shift = conn.execute("SELECT 1 FROM family_members WHERE lower(email)=lower(?) AND role='SHIFT_LEADER'", (user,)).fetchone() is not None
                is_area = conn.execute("SELECT 1 FROM family_members WHERE lower(email)=lower(?) AND role='AREA_LEADER'", (user,)).fetchone() is not None
        else:
            is_shift = str(item.get("shift_leader") or "").lower() == user.lower() or conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND lower(email)=lower(?) AND role='SHIFT_LEADER'", (item["family_owner"], item["family"], user)).fetchone() is not None
            is_area = conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND lower(email)=lower(?) AND role='AREA_LEADER'", (item["family_owner"], item["family"], user)).fetchone() is not None
        item["can_review"] = False
        item["can_confirm"] = is_shift and item["status"] in SHIFT_CONFIRM_STATUSES
        item["can_manage"] = is_target and is_area
        if item["family"] == "ALL MU03" and target_email and target_row and target_row["role"] == "AREA_LEADER":
            item["can_review"] = item["status"] == "READ" and bool(item.get("read_at")) and bool(target_row["managed_by"]) and target_row["managed_by"].lower() == user.lower()
            item["can_confirm"] = is_shift and item["status"] in SHIFT_CONFIRM_STATUSES
            item["can_manage"] = is_target
        elif is_target and is_shift:
            item["can_review"] = item["status"] == "READ" and bool(item.get("read_at"))
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


def sync_ticket_side_effects(ticket, status):
    notify_power_automate_update(ticket)
    sharepoint_update_ticket(ticket)
    if status:
        notify_teams(ticket, f"Ticket status changed to {status}")


def schedule_ticket_side_effects(ticket, status):
    threading.Thread(
        target=sync_ticket_side_effects,
        args=(ticket, status),
        daemon=True,
        name="mu03-ticket-sync",
    ).start()


def notify_power_automate(ticket):
    if not MU03_FLOW_HTTP_URL:
        return
    payload = {
        "id": ticket.get("id", ""),
        "title": ticket.get("title", ""),
        "family": ticket.get("target_family") or ticket.get("family", ""),
        "content": ticket.get("content", ""),
        "owner": ticket.get("owner", ""),
        "leader": ticket.get("leader", ""),
        "status": ticket.get("status", ""),
        "shift": ticket.get("work_shift", ""),
        "line": ticket.get("line_id", ""),
        "ticketUrl": f"{os.getenv('MU03_APP_URL', 'https://mu03-r-u-3423969507737722.2.azure.databricksapps.com')}/?ticket={quote(ticket.get('id', ''))}",
        "mediaJson": json.dumps(ticket.get("media") or [], ensure_ascii=False),
    }
    try:
        request = UrlRequest(MU03_FLOW_HTTP_URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=8):
            pass
    except Exception:
        pass


def notify_power_automate_update(ticket):
    if not MU03_UPDATE_FLOW_HTTP_URL:
        return
    payload = {
        "id": ticket.get("id", ""),
        "status": ticket.get("status", ""),
        "line": ticket.get("line_id", ""),
        "shift": ticket.get("work_shift", ""),
        "content": ticket.get("content", ""),
        "mediaJson": json.dumps(ticket.get("media") or [], ensure_ascii=False),
        # The HTTP trigger requires a date-shaped string. The flow converts
        # this sentinel to null unless the ticket is actually CLOSED.
        "closedAt": ticket.get("closed_at") or "1900-01-01T00:00:00Z",
        "ticketUrl": f"{os.getenv('MU03_APP_URL', 'https://mu03-r-u-3423969507737722.2.azure.databricksapps.com')}/?ticket={quote(ticket.get('id', ''))}",
    }
    try:
        request = UrlRequest(MU03_UPDATE_FLOW_HTTP_URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=8):
            pass
    except Exception as error:
        LOGGER.warning("Power Automate update failed for %s: %s", ticket.get("id", ""), error)


def sharepoint_token():
    return os.getenv("MS_GRAPH_ACCESS_TOKEN", "").strip()


def sharepoint_graph_request(method, path, payload=None):
    token = sharepoint_token()
    if not token:
        return None
    url = "https://graph.microsoft.com/v1.0" + path
    data = json.dumps(payload).encode() if payload is not None else None
    request = UrlRequest(url, data=data, headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}, method=method)
    try:
        with urlopen(request, timeout=12) as response:
            raw = response.read()
            return json.loads(raw.decode()) if raw else {}
    except Exception:
        return None


def sharepoint_context():
    if not sharepoint_token():
        return None
    site = sharepoint_graph_request("GET", f"/sites/{SHAREPOINT_HOST}:{SHAREPOINT_SITE_PATH}")
    if not site or not site.get("id"):
        return None
    lists = sharepoint_graph_request("GET", f"/sites/{quote(site['id'], safe='')}/lists?$filter=displayName eq '{SHAREPOINT_LIST_NAME}'")
    entries = (lists or {}).get("value") or []
    if not entries:
        return None
    return site["id"], entries[0]["id"]


def sharepoint_fields(ticket):
    return {
        "Title": ticket.get("title", ""),
        "TicketId": ticket.get("id", ""),
        "Status": ticket.get("status", ""),
        "Family": ticket.get("target_family") or ticket.get("family", ""),
        "OwnerEmail": ticket.get("owner", ""),
        "LeaderEmail": ticket.get("leader", ""),
        "Shift": ticket.get("work_shift", ""),
        "Line": ticket.get("line_id", ""),
        "TicketUrl": f"{os.getenv('MU03_APP_URL', 'https://mu03-r-u-3423969507737722.2.azure.databricksapps.com')}/?ticket={quote(ticket.get('id', ''))}",
        "Content": ticket.get("content", ""),
        "MediaJson": json.dumps([{key: media.get(key, "") for key in ("name", "type", "uploaded_on")} for media in (ticket.get("media") or [])], ensure_ascii=False),
        "SentAt": ticket.get("sent_at", ""),
        "ClosedAt": ticket.get("closed_at") or None,
    }


def sharepoint_create_ticket(ticket):
    context = sharepoint_context()
    if not context:
        return ""
    site_id, list_id = context
    item = sharepoint_graph_request("POST", f"/sites/{quote(site_id, safe='')}/lists/{quote(list_id, safe='')}/items", {"fields": sharepoint_fields(ticket)})
    item_id = str((item or {}).get("id") or "")
    if not item_id:
        return ""
    for media in ticket.get("media") or []:
        data = str(media.get("data") or "")
        if not data.startswith("data:") or "," not in data:
            continue
        try:
            encoded = data.split(",", 1)[1]
            sharepoint_graph_request("POST", f"/sites/{quote(site_id, safe='')}/lists/{quote(list_id, safe='')}/items/{quote(item_id, safe='')}/attachments", {"name": media.get("name") or "evidence", "contentBytes": encoded})
        except Exception:
            pass
    return item_id


def sharepoint_update_ticket(ticket):
    context = sharepoint_context()
    item_id = str(ticket.get("sharepoint_item_id") or "")
    if not context or not item_id:
        return
    site_id, list_id = context
    sharepoint_graph_request("PATCH", f"/sites/{quote(site_id, safe='')}/lists/{quote(list_id, safe='')}/items/{quote(item_id, safe='')}/fields", sharepoint_fields(ticket))


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
        role in ("SHIFT_LEADER", "ADMIN")
        or user in {member[0] for member in CULTURE_GROUP_MEMBERS}
        or conn.execute("SELECT 1 FROM family_members WHERE lower(email)=lower(?) AND role='SHIFT_LEADER' LIMIT 1", (user,)).fetchone() is not None
        or conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND lower(email)=lower(?) LIMIT 1", (CULTURE_GROUP_OWNER, CULTURE_GROUP_NAME, user)).fetchone() is not None
    )
    conn.close()
    profile = directory_lookup(request, user)
    return {"user": user, "display_name": profile["display_name"], "today": business_today(), "role": role, "can_create_ticket": user in {member[0] for member in CULTURE_GROUP_MEMBERS}, "can_view_cfm": can_view_cfm, "can_view_data": user in {member[0] for member in CULTURE_GROUP_MEMBERS}, "teams_configured": bool(os.getenv("MU03_TEAMS_WEBHOOK_URL")), "sharepoint_configured": bool(sharepoint_token()), "directory_configured": bool(os.getenv("MS_GRAPH_ACCESS_TOKEN"))}


@app.get("/api/directory/lookup")
def lookup_directory(email: str, request: Request):
    if "@" not in email:
        raise HTTPException(400, "A company email is required")
    return directory_lookup(request, email)


def read_sharepoint_tickets():
    if not MU03_READ_FLOW_HTTP_URL:
        return None
    try:
        request = UrlRequest(MU03_READ_FLOW_HTTP_URL, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    entries = payload if isinstance(payload, list) else (payload.get("value") or payload.get("items") or [])
    result = []
    for entry in entries:
        fields = entry.get("fields") or entry
        media_value = fields.get("MediaJson") or "[]"
        try:
            media = json.loads(media_value) if isinstance(media_value, str) else (media_value or [])
        except (TypeError, ValueError):
            media = []
        sent_at = fields.get("SentAt") or fields.get("Created") or entry.get("createdDateTime") or ""
        result.append({
            "id": fields.get("TicketId") or entry.get("id", ""),
            "owner": fields.get("OwnerEmail", ""),
            "day": str(sent_at)[:10],
            "title": fields.get("Title", ""),
            "family": fields.get("Family", ""),
            "target_family": fields.get("Family", ""),
            "content": fields.get("Content", ""),
            "leader": fields.get("LeaderEmail", ""),
            "status": fields.get("Status", ""),
            "line_id": fields.get("Line", ""),
            "work_shift": fields.get("Shift", ""),
            "sent_at": sent_at,
            "closed_at": fields.get("ClosedAt") or None,
            "media": media,
            "recipients": [fields.get("LeaderEmail", "")] if fields.get("LeaderEmail") else [],
            "sharepoint_item_id": str(entry.get("id", "")),
        })
    return result


def sync_sharepoint_cache(conn, shared):
    shared_ids = {str(item.get("id") or "") for item in shared}
    for item in shared:
        media = item.get("media") or []
        existing = conn.execute("SELECT media_json FROM tickets WHERE id=?", (item.get("id", ""),)).fetchone()
        if existing and media:
            try:
                cached_media = json.loads(existing["media_json"] or "[]")
                cached_by_name = {str(entry.get("name")): entry for entry in cached_media if entry.get("data")}
                media = [{**entry, "data": entry.get("data") or cached_by_name.get(str(entry.get("name")), {}).get("data", "")} for entry in media]
            except (TypeError, ValueError):
                pass
        ticket = {
            "id": item.get("id", ""), "owner": item.get("owner", ""), "day": item.get("day", ""),
            "title": item.get("title", ""), "family": item.get("family", ""), "content": item.get("content", ""),
            "cause": "General", "department": item.get("owner", ""), "leader": item.get("leader", ""),
            "status": item.get("status", ""), "line_id": item.get("line_id", ""), "note": "",
            "media_json": json.dumps(media, ensure_ascii=False), "sent_at": item.get("sent_at", ""),
            "read_at": None, "closed_at": item.get("closed_at"), "family_owner": CULTURE_GROUP_OWNER,
            "shift_leader": item.get("shift_leader", ""), "area_leader": item.get("area_leader") or item.get("leader", ""),
            "recipient_emails": json.dumps(item.get("recipients") or [], ensure_ascii=False), "target_email": item.get("target_email") or item.get("leader", ""),
            "target_family": item.get("target_family") or item.get("family", ""), "work_shift": item.get("work_shift", ""),
            "sharepoint_item_id": item.get("sharepoint_item_id", ""),
        }
        if conn.execute("SELECT 1 FROM tickets WHERE id=?", (ticket["id"],)).fetchone():
            conn.execute("UPDATE tickets SET owner=:owner,day=:day,title=:title,family=:family,content=:content,leader=:leader,status=:status,line_id=:line_id,media_json=:media_json,sent_at=:sent_at,closed_at=:closed_at,family_owner=:family_owner,shift_leader=:shift_leader,area_leader=:area_leader,recipient_emails=:recipient_emails,target_email=:target_email,target_family=:target_family,work_shift=:work_shift,sharepoint_item_id=:sharepoint_item_id WHERE id=:id", ticket)
        else:
            conn.execute("INSERT INTO tickets (id,owner,day,title,family,content,cause,department,leader,status,line_id,note,media_json,sent_at,read_at,closed_at,family_owner,shift_leader,area_leader,recipient_emails,target_email,target_family,work_shift,sharepoint_item_id) VALUES (:id,:owner,:day,:title,:family,:content,:cause,:department,:leader,:status,:line_id,:note,:media_json,:sent_at,:read_at,:closed_at,:family_owner,:shift_leader,:area_leader,:recipient_emails,:target_email,:target_family,:work_shift,:sharepoint_item_id)", ticket)
    if shared_ids:
        placeholders = ",".join("?" for _ in shared_ids)
        conn.execute(f"DELETE FROM tickets WHERE id NOT IN ({placeholders})", tuple(shared_ids))
    else:
        conn.execute("DELETE FROM tickets")
    conn.commit()


@app.get("/api/tickets")
def list_tickets(request: Request, day: str = "all"):
    user = user_email(request)
    shared = read_sharepoint_tickets()
    if shared is not None:
        cache = db()
        sync_sharepoint_cache(cache, shared)
        cache.close()
    conn = db()
    query = "SELECT * FROM tickets WHERE (owner=? OR lower(shift_leader)=lower(?) OR EXISTS (SELECT 1 FROM family_members m WHERE m.family_owner=tickets.family_owner AND m.family_name=tickets.family AND lower(m.email)=lower(?) AND m.role='SHIFT_LEADER') OR (target_email<>'' AND (lower(target_email)=lower(?) OR EXISTS (SELECT 1 FROM family_members m WHERE m.family_owner=tickets.family_owner AND lower(m.email)=lower(tickets.target_email) AND m.role='AREA_LEADER' AND lower(m.managed_by)=lower(?) AND (tickets.target_family='' OR m.family_name=tickets.target_family)))) OR (target_email='' AND (family='ALL MU03' OR EXISTS (SELECT 1 FROM family_members m WHERE m.family_owner=tickets.family_owner AND m.family_name=tickets.family AND lower(m.email)=lower(?)))))"
    args = [user, user, user, user, user, user]
    if day != "all":
        query += " AND day=?"
        args.append(day)
    rows = conn.execute(query + " ORDER BY sent_at DESC", args).fetchall()
    result = [ticket_json(row, conn, user) for row in rows]
    conn.close()
    return result


@app.get("/api/dashboard/tickets")
def dashboard_ticket_feed(request: Request):
    shared = read_sharepoint_tickets()
    if shared is not None:
        return shared
    conn = db()
    rows = conn.execute("SELECT * FROM tickets ORDER BY sent_at DESC").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["media"] = json.loads(item.pop("media_json") or "[]")
        item["recipients"] = json.loads(item.pop("recipient_emails", "[]") or "[]")
        result.append(item)
    conn.close()
    return result


def remove_export(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def excel_image_from_media(media):
    data = str(media.get("data") or "")
    if not data.startswith("data:") or "," not in data:
        return None
    try:
        raw = base64.b64decode(data.split(",", 1)[1])
        try:
            return ExcelImage(BytesIO(raw))
        except Exception:
            from PIL import Image
            if str(media.get("name") or "").lower().endswith((".heic", ".heif", ".heics", ".heix")):
                from pillow_heif import register_heif_opener
                register_heif_opener()
            source = Image.open(BytesIO(raw)).convert("RGB")
            output = BytesIO()
            source.save(output, format="PNG")
            output.seek(0)
            return ExcelImage(output)
    except Exception:
        return None


@app.get("/api/tickets/export")
def export_tickets(request: Request, day: str = "all"):
    user = user_email(request)
    conn = db()
    query = "SELECT * FROM tickets WHERE (owner=? OR lower(shift_leader)=lower(?) OR (target_email<>'' AND (lower(target_email)=lower(?) OR EXISTS (SELECT 1 FROM family_members m WHERE m.family_owner=tickets.family_owner AND lower(m.email)=lower(tickets.target_email) AND m.role='AREA_LEADER' AND lower(m.managed_by)=lower(?) AND (tickets.target_family='' OR m.family_name=tickets.target_family)))) OR (target_email='' AND (family='ALL MU03' OR EXISTS (SELECT 1 FROM family_members m WHERE m.family_owner=tickets.family_owner AND m.family_name=tickets.family AND lower(m.email)=lower(?)))))"
    args = [user, user, user, user, user]
    if day != "all":
        query += " AND day=?"
        args.append(day)
    rows = conn.execute(query + " ORDER BY sent_at DESC", args).fetchall()
    items = [ticket_json(row, conn, user) for row in rows]
    conn.close()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ticket Data"
    evidence = workbook.create_sheet("Evidence")
    headers = ["Ticket ID", "Sent Date", "Closed Date", "Status", "Group", "Title", "Sender", "Leader", "Line", "Work Shift", "Content", "Media Files"]
    sheet.append(headers)
    evidence.append(["Ticket ID", "Group", "File", "Type", "Preview"])
    header_fill = PatternFill("solid", fgColor="8B0B1A")
    header_font = Font(color="FFFFFF", bold=True)
    for target in (sheet, evidence):
        for cell in target[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        target.freeze_panes = "A2"
        target.auto_filter.ref = target.dimensions
    widths = [24, 14, 14, 28, 18, 28, 34, 34, 14, 14, 72, 34]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[chr(64 + index)].width = width
    for index, width in enumerate([24, 18, 34, 14, 24], 1):
        evidence.column_dimensions[chr(64 + index)].width = width
    evidence_row = 2
    for item in items:
        media = item.get("media") or []
        media_names = ", ".join(str(entry.get("name", "")) for entry in media)
        sheet.append([item.get("id", ""), item.get("day", ""), str(item.get("closed_at") or ""), item.get("status", ""), item.get("target_family") or item.get("family", ""), item.get("title", ""), item.get("owner", ""), item.get("leader", ""), item.get("line_id", ""), item.get("work_shift", ""), item.get("content", ""), media_names])
        row_number = sheet.max_row
        sheet.cell(row_number, 11).alignment = Alignment(wrap_text=True, vertical="top")
        for entry in media:
            evidence.append([item.get("id", ""), item.get("target_family") or item.get("family", ""), entry.get("name", ""), entry.get("type", ""), ""])
            evidence_row = evidence.max_row
            evidence.cell(evidence_row, 1).alignment = Alignment(vertical="top")
            image = excel_image_from_media(entry)
            if image:
                image.width = 180
                image.height = 110
                evidence.add_image(image, f"E{evidence_row}")
                evidence.row_dimensions[evidence_row].height = 86
            else:
                evidence.cell(evidence_row, 5).value = "Preview unavailable; open the ticket to view the original media."
    sheet.auto_filter.ref = sheet.dimensions
    evidence.auto_filter.ref = evidence.dimensions
    export_path = os.path.join(tempfile.gettempdir(), f"mu03-ticket-data-{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx")
    workbook.save(export_path)
    return FileResponse(export_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=os.path.basename(export_path), background=BackgroundTask(remove_export, export_path))


@app.post("/api/tickets")
async def create_ticket(request: Request):
    payload = await request.json()
    user = user_email(request)
    if user not in {member[0] for member in CULTURE_GROUP_MEMBERS}:
        raise HTTPException(403, "Only Core Teams members can create tickets")
    if any(not str(payload.get(key, "")).strip() for key in ("title", "family", "content")):
        raise HTTPException(400, "Title, family and content are required")
    work_shift = ""
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
        targets = [row for row in members if row["role"] == "AREA_LEADER"]
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
        target_family = target["family_name"] if family_name == "ALL MU03" and target and target["role"] == "AREA_LEADER" else (family_name if target and target["role"] == "AREA_LEADER" else "")
        item = {"id": "R&U-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + os.urandom(2).hex(), "owner": user, "day": business_today(), "title": str(payload["title"]).strip(), "family": family_name, "content": str(payload["content"]).strip(), "cause": str(payload.get("cause", "General")), "department": user, "leader": target_email or (areas[0] if areas else DEFAULT_LEADER), "status": "WAITING FOR LEADER READ", "line_id": "", "note": "", "media_json": json.dumps(payload.get("media", [])), "sent_at": now_iso(), "read_at": None, "closed_at": None, "family_owner": family_owner, "shift_leader": target["managed_by"].strip().lower() if target and target["role"] == "AREA_LEADER" else (shifts[0] if shifts else ""), "area_leader": target_email if target and target["role"] == "AREA_LEADER" else (areas[0] if areas else ""), "recipient_emails": json.dumps([target_email] if target_email else recipients), "target_email": target_email, "target_family": target_family, "work_shift": work_shift, "sharepoint_item_id": ""}
        conn.execute("""INSERT INTO tickets (id,owner,day,title,family,content,cause,department,leader,status,line_id,note,media_json,sent_at,read_at,closed_at,family_owner,shift_leader,area_leader,recipient_emails,target_email,target_family,work_shift,sharepoint_item_id) VALUES (:id,:owner,:day,:title,:family,:content,:cause,:department,:leader,:status,:line_id,:note,:media_json,:sent_at,:read_at,:closed_at,:family_owner,:shift_leader,:area_leader,:recipient_emails,:target_email,:target_family,:work_shift,:sharepoint_item_id)""", item)
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (item["id"],)).fetchone()
        results.append(ticket_json(row, conn, user))
    conn.commit()
    conn.close()
    for result in results:
        sharepoint_id = sharepoint_create_ticket(result)
        if sharepoint_id:
            result["sharepoint_item_id"] = sharepoint_id
            mirror = db()
            mirror.execute("UPDATE tickets SET sharepoint_item_id=? WHERE id=?", (sharepoint_id, result["id"]))
            mirror.commit()
            mirror.close()
        notify_power_automate(result)
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
    if payload.get("reviewed") is True and not current.get("can_review"):
        conn.close()
        raise HTTPException(403, "Shift Leader review is required before confirmation")
    if status in ("LINE SHARING COMPLETED", "NO LINE - COMPLETED") and not current.get("can_manage"):
        conn.close()
        raise HTTPException(403, "Only the area leader can manage this ticket")
    if status in ("LINE SHARING COMPLETED", "NO LINE - COMPLETED") and row["day"] != business_today():
        conn.close()
        raise HTTPException(409, "Only tickets from today can be updated")
    if status in ("LINE SHARING COMPLETED", "NO LINE - COMPLETED") and str(payload.get("work_shift", "")).strip().lower() not in ("day", "night"):
        conn.close()
        raise HTTPException(400, "Select Day or Night shift")
    if status == "LINE SHARING COMPLETED":
        if not str(payload.get("line_id", "")).strip():
            conn.close()
            raise HTTPException(400, "Line ID is required")
        if not payload.get("media"):
            conn.close()
            raise HTTPException(400, "Sharing image or video is required")
    if status == "LINE SHARING COMPLETED" and any(media.get("uploaded_on") != business_today() for media in payload.get("media", []) if isinstance(media, dict)):
        conn.close()
        raise HTTPException(409, "Only images or videos from today can be submitted")
    if status == "CLOSED" and not current.get("can_confirm"):
        conn.close()
        raise HTTPException(403, "Only the assigned shift leader can close this ticket")
    fields = {key: payload[key] for key in ("status", "line_id", "note", "work_shift") if key in payload}
    if payload.get("reviewed") is True:
        fields["reviewed_by"] = user
        fields["reviewed_at"] = now_iso()
    if "media" in payload:
        fields["media_json"] = json.dumps(payload["media"])
    if status == "READ":
        fields["read_at"] = now_iso()
        fields["reviewed_by"] = ""
        fields["reviewed_at"] = None
    if status == "CLOSED":
        fields["closed_at"] = now_iso()
    if fields:
        clause = ", ".join(f"{key}=?" for key in fields)
        conn.execute(f"UPDATE tickets SET {clause} WHERE id=?", (*fields.values(), ticket_id))
        conn.commit()
    updated = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    result = ticket_json(updated, conn, user)
    conn.close()
    # Keep external systems off the request path while ensuring the sync thread starts
    # before the response is returned to the browser.
    schedule_ticket_side_effects(result, status)
    return result


@app.get("/api/families")
def list_families(request: Request):
    user = user_email(request)
    conn = db()
    ensure_families(conn, user)
    is_culture_member = conn.execute("SELECT 1 FROM family_members WHERE family_owner=? AND family_name=? AND lower(email)=lower(?) LIMIT 1", (CULTURE_GROUP_OWNER, CULTURE_GROUP_NAME, user)).fetchone()
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
