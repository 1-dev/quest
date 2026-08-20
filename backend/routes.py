from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import csv
import io

from . import db

router = APIRouter()

DIGITS = [4, 2, 1, 3, 0]


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


class ParticipantRequest(BaseModel):
    nickname: str
    numbers: str = ""


class GenerateGameRequest(BaseModel):
    num_participants: int


class RenameParticipantRequest(BaseModel):
    old_nickname: str
    new_nickname: str


# ---- Participant endpoints ----

@router.get("/api/participants")
def list_participants():
    return db.get_participants()


@router.post("/api/participants")
def add_participant(req: ParticipantRequest):
    ok = db.add_participant(req.nickname, req.numbers)
    if not ok:
        raise HTTPException(400, "Nickname already exists")
    return {"ok": True}


@router.delete("/api/participants/{nickname}")
def delete_participant(nickname: str):
    conn = db.get_db()
    conn.execute("DELETE FROM participants WHERE nickname = ?", (nickname,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/api/participants/clear")
def clear_participants():
    db.clear_participants()
    return {"ok": True}


@router.post("/api/participants/generate")
def generate_game(req: GenerateGameRequest):
    if req.num_participants < 1 or req.num_participants > 21:
        raise HTTPException(400, "Number of participants must be 1-21")
    sets = db.generate_game(req.num_participants)
    return {"ok": True, "participants": sets}


@router.put("/api/participants/rename")
def rename_participant(req: RenameParticipantRequest):
    ok = db.update_participant_nickname(req.old_nickname, req.new_nickname)
    if not ok:
        raise HTTPException(400, "Could not rename (nickname may already exist)")
    return {"ok": True}


@router.post("/api/participants/import")
async def import_participants_csv(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    sets = []
    for row in reader:
        if len(row) >= 2:
            name = row[0].strip()
            nums = [int(n.strip()) for n in row[1].split(",") if n.strip().isdigit()]
            sets.append((name, nums))
    db.import_participants(sets)
    return {"ok": True, "count": len(sets)}


# ---- Quest flow ----

@router.post("/api/start")
def start_quest(req: StartRequest):
    session = db.create_session(req.nickname)
    if not session:
        raise HTTPException(400, "Unknown participant. Register first.")
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
