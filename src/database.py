from pathlib import Path
import sqlite3
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "travel_planner.db"

def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        destination TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        travelers INTEGER NOT NULL DEFAULT 1,
        trip_type TEXT NOT NULL DEFAULT 'Leisure',
        status TEXT NOT NULL DEFAULT 'Planning',
        currency TEXT NOT NULL DEFAULT 'USD',
        budget REAL NOT NULL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS itinerary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL,
        day_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT DEFAULT '',
        cost REAL NOT NULL DEFAULT 0,
        notes TEXT DEFAULT '',
        FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL,
        expense_date TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        paid INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS packing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL,
        item TEXT NOT NULL,
        category TEXT NOT NULL,
        packed INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL,
        document TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        notes TEXT DEFAULT '',
        FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

def execute(sql, params=(), fetch=False, many=False):
    conn = get_connection()
    cur = conn.cursor()
    if many:
        cur.executemany(sql, params)
    else:
        cur.execute(sql, params)
    rows = cur.fetchall() if fetch else None
    last_id = cur.lastrowid
    conn.commit()
    conn.close()
    return rows if fetch else last_id

def seed_demo():
    if execute("SELECT COUNT(*) AS n FROM trips", fetch=True)[0]["n"]:
        return
    trip_id = execute("""
        INSERT INTO trips(name,destination,start_date,end_date,travelers,trip_type,status,currency,budget,notes,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (
        "Coastal Explorer", "Goa, India", "2026-11-06", "2026-11-10", 3,
        "Leisure", "Planning", "INR", 65000,
        "Beach, heritage and local food trip.", datetime.now().isoformat(timespec="seconds")
    ))
    itinerary = [
        ("2026-11-06","09:00","11:00","Airport transfer & hotel check-in","Transport","Dabolim Airport",1200,"Pre-book cab."),
        ("2026-11-06","17:00","19:00","Sunset at Candolim Beach","Sightseeing","Candolim Beach",0,"Golden-hour photos."),
        ("2026-11-07","09:00","12:00","Old Goa Heritage Walk","Sightseeing","Old Goa",800,"Visit Basilica and churches."),
        ("2026-11-07","13:00","14:00","Local Goan Lunch","Food","Panaji",1800,"Try a local thali."),
        ("2026-11-08","08:00","16:00","South Goa Day Trip","Tour","Palolem",3500,"Reserve a private cab."),
    ]
    execute("""INSERT INTO itinerary(trip_id,day_date,start_time,end_time,title,category,location,cost,notes)
               VALUES(?,?,?,?,?,?,?,?,?)""", [(trip_id,*x) for x in itinerary], many=True)
    expenses = [
        ("2026-11-06","Transport","Airport transfer",1200,1),
        ("2026-11-07","Food","Lunch",1800,1),
        ("2026-11-08","Tours","Day trip",3500,0),
    ]
    execute("""INSERT INTO expenses(trip_id,expense_date,category,description,amount,paid)
               VALUES(?,?,?,?,?,?)""", [(trip_id,*x) for x in expenses], many=True)
    packing = [
        ("Passport / ID","Documents",1),("Phone charger","Electronics",0),
        ("Power bank","Electronics",0),("Comfortable shoes","Clothing",0),
        ("Sunscreen","Health",0),("Sunglasses","Accessories",1),
        ("Reusable bottle","Essentials",0),("Travel adapter","Electronics",0)
    ]
    execute("INSERT INTO packing(trip_id,item,category,packed) VALUES(?,?,?,?)",
            [(trip_id,*x) for x in packing], many=True)
    docs = [("Government ID","Ready",""),("Hotel confirmation","Ready",""),("Travel insurance","Pending","Check policy dates.")]
    execute("INSERT INTO documents(trip_id,document,status,notes) VALUES(?,?,?,?)",
            [(trip_id,*x) for x in docs], many=True)
