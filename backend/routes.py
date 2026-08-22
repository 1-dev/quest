from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from . import db

router = APIRouter()


# ---- Models ----

class CheckpointRequest(BaseModel):
    id: int
    digit: int
    title: str
    location: str
    code_comment: str = ""
    code_line: str = ""
    riddle: str
    emoji: str = "📍"

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

    existing = db.resume_session(nickname)
    if existing:
        return {
            "ok": True,
            "token": existing["token"],
            "order": __import__("json").loads(existing["order_json"]),
        }

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

    if len(completed) < 8:
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


# ---- Admin: delete session ----

class DeleteSessionRequest(BaseModel):
    participant_id: int


@router.post("/api/admin/delete-session")
def delete_session(req: DeleteSessionRequest):
    db.delete_session_by_participant_id(req.participant_id)
    return {"ok": True}


@router.get("/api/admin/sessions")
def get_sessions():
    sessions = db.get_db().execute(
        """SELECT s.id, s.token, s.started_at, s.finished_at, s.order_json,
                  p.id as participant_id, p.nickname, p.numbers
           FROM sessions s
           JOIN participants p ON p.id = s.participant_id
           ORDER BY s.id"""
    ).fetchall()
    db.get_db().close()
    return [dict(r) for r in sessions]


# ---- Checkpoints Config ----

@router.get("/api/checkpoints")
def get_checkpoints():
    return db.get_checkpoints()


@router.post("/api/checkpoints/save")
def save_checkpoint(req: CheckpointRequest):
    db.save_checkpoint(req.dict())
    return {"ok": True}


@router.delete("/api/checkpoints/{cp_id}")
def delete_checkpoint(cp_id: int):
    db.delete_checkpoint(cp_id)
    return {"ok": True}


@router.get("/api/checkpoints/{cp_id}/qr")
def generate_qr(cp_id: int, base_url: str = "https://quest.1-dev.ru"):
    cp = db.get_checkpoint(cp_id)
    if not cp:
        raise HTTPException(404, "Checkpoint not found")
    try:
        import qrcode
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise HTTPException(500, "qrcode/pillow not installed")

    url = f"{base_url.rstrip('/')}/start.html?cp={cp['id']}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="white").convert("RGB")

    # Draw S21 logo in center
    w, h = img.size
    logo_size = min(w, h) // 6
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    r = logo_size // 2 + 3
    box_half = r * 2
    draw.rounded_rectangle([cx - box_half, cy - box_half, cx + box_half, cy + box_half], radius=box_half // 3, fill="white", outline="#00ff41", width=2)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", logo_size - 4)
    except Exception:
        font = ImageFont.load_default()
    text = "S21"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 1), text, fill="#00ff41", font=font)

    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png")
