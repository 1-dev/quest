from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import db

router = APIRouter()


# ---- Models ----

class StartRequest(BaseModel):
    nickname: str


class ScanRequest(BaseModel):
    token: str
    checkpoint_id: int


class FinishRequest(BaseModel):
    token: str
    time_ms: int
    password: str


class GenerateGameRequest(BaseModel):
    num_participants: int


# ---- Game ----

@router.post("/api/game/generate")
def generate_game(req: GenerateGameRequest):
    if req.num_participants < 1 or req.num_participants > 21:
        raise HTTPException(400, "Количество участников: 1-21")
    sets = db.generate_game(req.num_participants)
    return {"ok": True, "slots": sets}


@router.get("/api/game/pool")
def get_pool():
    return db.get_game_pool()


@router.get("/api/game/status")
def get_pool_status():
    return db.get_pool_status()


@router.post("/api/game/clear")
def clear_game():
    conn = db.get_db()
    conn.execute("DELETE FROM participants")
    conn.execute("DELETE FROM game_pool")
    conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM checkpoints")
    conn.execute("DELETE FROM results")
    conn.commit()
    conn.close()
    return {"ok": True}


# ---- Quest flow ----

@router.post("/api/start")
def start_quest(req: StartRequest):
    nickname = req.nickname.strip()
    if not nickname:
        raise HTTPException(400, "Nickname required")

    session = db.create_session(nickname)
    if not session:
        raise HTTPException(400, "Нет свободных слотов. Игра заполнена.")
    return {
        "ok": True,
        "token": session["token"],
        "order": __import__("json").loads(session["order_json"]),
    }


@router.post("/api/scan")
def scan_checkpoint(req: ScanRequest):
    result = db.scan_checkpoint(req.token, req.checkpoint_id)
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return result


@router.get("/api/progress")
def get_progress(token: str):
    data = db.get_session_progress(token)
    if not data:
        raise HTTPException(404, "Session not found")
    return data


@router.post("/api/finish")
def finish_quest(req: FinishRequest):
    session = db.get_session(req.token)
    if not session:
        raise HTTPException(404, "Session not found")

    completed = db.get_db().execute(
        "SELECT checkpoint_id FROM checkpoints WHERE session_id = ?",
        (session["id"],),
    ).fetchall()

    if len(completed) < 5:
        raise HTTPException(400, "Not all checkpoints completed")

    db.finish_session(req.token)
    db.save_result(req.token, req.time_ms, req.password)
    return {"ok": True}


# ---- Results ----

@router.get("/api/results")
def get_results():
    return db.get_results()


@router.post("/api/results/clear")
def clear_results():
    db.clear_results()
    return {"ok": True}
