import sqlite3
from datetime import datetime, timezone
from .config import DB_PATH

def now(): return datetime.now(timezone.utc).isoformat()
def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance INTEGER NOT NULL DEFAULT 0,
          premium INTEGER NOT NULL DEFAULT 0, daily_used INTEGER NOT NULL DEFAULT 0, daily_date TEXT,
          referred_by INTEGER, referral_awarded INTEGER NOT NULL DEFAULT 0, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS jobs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, mode TEXT, src_name TEXT, out_name TEXT,
          created_at TEXT, status TEXT
        );
        ''')

def ensure_user(uid, username=None, first_name=None, referred_by=None):
    today=datetime.now(timezone.utc).date().isoformat()
    with connect() as c:
        row=c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
        if not row:
            c.execute("INSERT INTO users(id,username,first_name,daily_date,referred_by,created_at) VALUES(?,?,?,?,?,?)",(uid,username,first_name,today,referred_by,now()))
        else:
            c.execute("UPDATE users SET username=?, first_name=? WHERE id=?",(username,first_name,uid))

def get_user(uid):
    ensure_user(uid)
    with connect() as c: return c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()

def consume(uid):
    with connect() as c:
        r=c.execute("SELECT balance,premium,daily_used,daily_date FROM users WHERE id=?",(uid,)).fetchone()
        today=datetime.now(timezone.utc).date().isoformat()
        used=0 if r['daily_date']!=today else r['daily_used']
        if r['premium'] or r['balance']>0:
            if r['balance']>0 and not r['premium']:
                c.execute("UPDATE users SET balance=balance-1 WHERE id=?",(uid,))
            return True, ('premium' if r['premium'] else 'balance'), used
        if used < 3:
            c.execute("UPDATE users SET daily_used=?,daily_date=? WHERE id=?",(used+1,today,uid))
            return True,'daily',used+1
        return False,'limit',used

def add_balance(uid,n):
    with connect() as c: c.execute("UPDATE users SET balance=balance+? WHERE id=?",(n,uid))

def mark_referral(uid):
    with connect() as c:
        u=c.execute("SELECT referred_by,referral_awarded FROM users WHERE id=?",(uid,)).fetchone()
        if not u or not u['referred_by'] or u['referral_awarded']: return None
        ref=u['referred_by']
        c.execute("UPDATE users SET referral_awarded=1 WHERE id=?",(uid,))
        return ref

def set_premium(uid,val):
    with connect() as c: c.execute("UPDATE users SET premium=? WHERE id=?",(1 if val else 0,uid))

def stats():
    with connect() as c:
        return c.execute("SELECT COUNT(*) users, COALESCE(SUM(premium),0) premium, COALESCE(SUM(balance),0) balance FROM users").fetchone()
