import sqlite3
import os
import json
import random
import string
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "quest.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT UNIQUE NOT NULL,
            numbers TEXT DEFAULT '',
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS game_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numbers TEXT NOT NULL,
            assigned_to INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            FOREIGN KEY (assigned_to) REFERENCES participants(id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            order_json TEXT NOT NULL,
            started_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            finished_at TEXT,
            FOREIGN KEY (participant_id) REFERENCES participants(id)
        );

        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            checkpoint_id INTEGER NOT NULL,
            scanned_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            UNIQUE(session_id, checkpoint_id)
        );

        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            time_ms INTEGER NOT NULL,
            time_formatted TEXT NOT NULL,
            password TEXT NOT NULL,
            numbers TEXT DEFAULT '',
            route TEXT DEFAULT '',
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)
    conn.close()


def _generate_token():
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


def _shuffle(arr):
    a = list(arr)
    random.shuffle(a)
    return a


# ---- Participants ----

def add_participant(nickname, numbers=""):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO participants (nickname, numbers) VALUES (?, ?)",
            (nickname.strip().lower(), numbers),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_participants():
    conn = get_db()
    rows = conn.execute("SELECT * FROM participants ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def import_participants(sets):
    conn = get_db()
    conn.execute("DELETE FROM participants")
    for name, nums in sets:
        conn.execute(
            "INSERT INTO participants (nickname, numbers) VALUES (?, ?)",
            (name, ", ".join(str(n) for n in nums)),
        )
    conn.commit()
    conn.close()


def clear_participants():
    conn = get_db()
    conn.execute("DELETE FROM participants")
    conn.commit()
    conn.close()


def generate_game(num_participants):
    """Generate N number sets from 1-21, store in game pool."""
    conn = get_db()
    conn.execute("DELETE FROM participants")
    conn.execute("DELETE FROM game_pool")
    conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM checkpoints")
    conn.execute("DELETE FROM results")

    all_numbers = list(range(1, 22))
    random.shuffle(all_numbers)

    per_player = 21 // num_participants
    remainder = 21 % num_participants
    sets = []
    idx = 0
    for i in range(num_participants):
        count = per_player + (1 if i < remainder else 0)
        nums = sorted(all_numbers[idx:idx + count])
        sets.append(nums)
        idx += count

    for nums in sets:
        nums_str = ", ".join(str(n) for n in nums)
        conn.execute("INSERT INTO game_pool (numbers) VALUES (?)", (nums_str,))

    conn.commit()
    conn.close()
    return [{"slot": i + 1, "numbers": sets[i]} for i in range(num_participants)]


def update_participant_nickname(old_nickname, new_nickname):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE participants SET nickname = ? WHERE nickname = ?",
            (new_nickname.strip(), old_nickname),
        )
        conn.commit()
        ok = conn.total_changes > 0
    except sqlite3.IntegrityError:
        ok = False
    finally:
        conn.close()
    return ok


def get_game_pool():
    conn = get_db()
    rows = conn.execute(
        """SELECT gp.id, gp.numbers, gp.assigned_to, p.nickname
           FROM game_pool gp
           LEFT JOIN participants p ON gp.assigned_to = p.id
           ORDER BY gp.id"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pool_status():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM game_pool").fetchone()["c"]
    taken = conn.execute("SELECT COUNT(*) as c FROM game_pool WHERE assigned_to IS NOT NULL").fetchone()["c"]
    conn.close()
    return {"total": total, "taken": taken, "available": total - taken}


# ---- Sessions ----

def create_session(nickname):
    conn = get_db()

    # Find an unassigned slot in the game pool
    slot = conn.execute(
        "SELECT id, numbers FROM game_pool WHERE assigned_to IS NULL LIMIT 1"
    ).fetchone()
    if not slot:
        conn.close()
        return None

    # Create or get participant
    participant = conn.execute(
        "SELECT id FROM participants WHERE nickname = ?", (nickname.strip().lower(),)
    ).fetchone()

    if participant:
        participant_id = participant["id"]
    else:
        conn.execute(
            "INSERT INTO participants (nickname, numbers) VALUES (?, ?)",
            (nickname.strip().lower(), slot["numbers"]),
        )
        participant_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Mark pool slot as assigned
    conn.execute(
        "UPDATE game_pool SET assigned_to = ? WHERE id = ?",
        (participant_id, slot["id"]),
    )

    order = _shuffle(list(range(8)))
    salt = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    token = _generate_token()

    conn.execute(
        "INSERT INTO sessions (participant_id, token, salt, order_json) VALUES (?, ?, ?, ?)",
        (participant_id, token, salt, json.dumps(order)),
    )
    conn.commit()
    session = conn.execute(
        "SELECT * FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    conn.close()
    return dict(session) if session else None


def get_session(token):
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    conn.close()
    return dict(session) if session else None


def finish_session(token):
    conn = get_db()
    conn.execute(
        "UPDATE sessions SET finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE token = ?",
        (token,),
    )
    conn.commit()
    conn.close()


# ---- Checkpoints ----

def scan_checkpoint(token, checkpoint_id):
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    if not session:
        conn.close()
        return {"ok": False, "error": "invalid_token"}

    if session["finished_at"]:
        conn.close()
        return {"ok": False, "error": "session_finished"}

    order = json.loads(session["order_json"])
    completed = [
        r["checkpoint_id"]
        for r in conn.execute(
            "SELECT checkpoint_id FROM checkpoints WHERE session_id = ?",
            (session["id"],),
        ).fetchall()
    ]

    expected_index = len(completed)
    if expected_index >= 8:
        conn.close()
        return {"ok": False, "error": "all_done"}

    expected_cp = order[expected_index]
    if checkpoint_id != expected_cp:
        conn.close()
        return {"ok": False, "error": "wrong_order", "expected": expected_cp, "current_index": expected_index}

    conn.execute(
        "INSERT INTO checkpoints (session_id, checkpoint_id) VALUES (?, ?)",
        (session["id"], checkpoint_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "digit": [4, 2, 1, 3, 0, 5, 6, 7][checkpoint_id], "step": expected_index + 1}


def get_session_progress(token):
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    if not session:
        conn.close()
        return None

    completed = [
        r["checkpoint_id"]
        for r in conn.execute(
            "SELECT checkpoint_id FROM checkpoints WHERE session_id = ? ORDER BY scanned_at",
            (session["id"],),
        ).fetchall()
    ]
    conn.close()

    participant = get_db().execute(
        "SELECT p.* FROM participants p JOIN sessions s ON p.id = s.participant_id WHERE s.token = ?",
        (token,),
    ).fetchone()

    return {
        "session": dict(session),
        "order": json.loads(session["order_json"]),
        "completed": completed,
        "current_index": len(completed),
        "nickname": dict(participant)["nickname"] if participant else "",
        "numbers": dict(participant)["numbers"] if participant else "",
    }


# ---- Results ----

def save_result(token, time_ms, password):
    conn = get_db()
    session = conn.execute(
        "SELECT s.*, p.nickname, p.numbers FROM sessions s JOIN participants p ON p.id = s.participant_id WHERE s.token = ?",
        (token,),
    ).fetchone()
    if not session:
        conn.close()
        return None

    s = dict(session)
    order = json.loads(s["order_json"])

    conn.execute(
        """INSERT INTO results (session_id, nickname, time_ms, time_formatted, password, numbers, route)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            s["id"],
            s["nickname"],
            time_ms,
            _format_time(time_ms),
            password,
            s["numbers"],
            json.dumps(order),
        ),
    )
    conn.commit()
    conn.close()
    return True


def get_results():
    conn = get_db()
    rows = conn.execute("SELECT * FROM results ORDER BY time_ms ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_results():
    conn = get_db()
    conn.execute("DELETE FROM results")
    conn.commit()
    conn.close()


def delete_session_by_participant_id(participant_id):
    conn = get_db()
    conn.execute("DELETE FROM checkpoints WHERE session_id IN (SELECT id FROM sessions WHERE participant_id = ?)", (participant_id,))
    conn.execute("DELETE FROM sessions WHERE participant_id = ?", (participant_id,))
    conn.execute("DELETE FROM participants WHERE id = ?", (participant_id,))
    conn.commit()
    conn.close()


def resume_session(nickname):
    conn = get_db()
    participant = conn.execute(
        "SELECT id FROM participants WHERE nickname = ?", (nickname.strip().lower(),)
    ).fetchone()
    if not participant:
        conn.close()
        return None
    session = conn.execute(
        "SELECT * FROM sessions WHERE participant_id = ? ORDER BY id DESC LIMIT 1",
        (participant["id"],),
    ).fetchone()
    conn.close()
    return dict(session) if session else None


# ---- Helpers ----

def _format_time(ms):
    total_sec = ms // 1000
    m = total_sec // 60
    s = total_sec % 60
    cs = (ms % 1000) // 10
    return f"{m:02d}:{s:02d}.{cs:02d}"
