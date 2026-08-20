const QuestApp = (() => {
  const STORAGE_KEY = "quest21_state";
  const LEADERBOARD_KEY = "quest21_leaderboard";
  const DIGITS_CORRECT = [4, 2, 1, 3, 0];

  /* ---- state ---- */

  function getState() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || null; } catch { return null; }
  }

  function setState(s) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  }

  function resetQuest() {
    localStorage.removeItem(STORAGE_KEY);
  }

  /* ---- shuffle ---- */

  function shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  /* ---- token helpers (deterministic, no backend) ---- */

  function _hash(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
      h = ((h << 5) - h + str.charCodeAt(i)) | 0;
    }
    return h;
  }

  function makeToken(checkpointId, sessionSalt) {
    return (
      String(checkpointId) +
      "-" +
      Math.abs(_hash(checkpointId + ":" + sessionSalt)).toString(36)
    );
  }

  function validateToken(token, state) {
    if (!token || !state || !state.order || !state.salt) return false;
    if (typeof token !== "string") return false;
    const dash = token.indexOf("-");
    if (dash < 1) return false;
    const cpId = parseInt(token.slice(0, dash));
    if (isNaN(cpId) || cpId < 0 || cpId > 4) return false;
    return token === makeToken(cpId, state.salt);
  }

  function tokenToCheckpointId(token) {
    return parseInt(token.split("-")[0]);
  }

  /* ---- quest lifecycle ---- */

  function startQuest(nickname) {
    const order = shuffle([0, 1, 2, 3, 4]);
    const salt = Math.random().toString(36).slice(2, 10);
    const state = {
      nickname: nickname.trim(),
      startTime: Date.now(),
      order,
      salt,
      currentIndex: 0,
      collectedDigits: [],
      completedCheckpoints: [],
    };
    setState(state);
    return state;
  }

  function completeCheckpoint(checkpointId) {
    const state = getState();
    if (!state) return null;
    const seqIndex = state.order.indexOf(checkpointId);
    if (seqIndex !== state.currentIndex) return null;
    if (state.completedCheckpoints.includes(checkpointId)) return null;

    state.completedCheckpoints.push(checkpointId);
    state.collectedDigits.push(DIGITS_CORRECT[checkpointId]);
    state.currentIndex++;
    setState(state);
    return state;
  }

  function assemblePassword(state) {
    if (!state || state.collectedDigits.length < 5) return null;
    const pw = ["", "", "", "", ""];
    state.order.forEach((cpId, seqIdx) => {
      pw[cpId] = String(state.collectedDigits[seqIdx]);
    });
    return pw.join("");
  }

  /* ---- time ---- */

  function getTime() {
    const s = getState();
    if (!s || !s.startTime) return 0;
    return Date.now() - s.startTime;
  }

  function formatTime(ms) {
    const t = Math.floor(ms / 1000);
    const m = Math.floor(t / 60);
    const s = t % 60;
    const cs = Math.floor((ms % 1000) / 10);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(cs).padStart(2, "0")}`;
  }

  /* ---- finish ---- */

  function finishQuest() {
    const state = getState();
    if (!state || !state.startTime) return null;
    const time = Date.now() - state.startTime;
    const password = assemblePassword(state);
    const entry = {
      name: state.nickname,
      time,
      timeFormatted: formatTime(time),
      password,
      date: new Date().toISOString(),
    };
    const lb = getLeaderboard();
    lb.push(entry);
    lb.sort((a, b) => a.time - b.time);
    if (lb.length > 50) lb.length = 50;
    localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(lb));
    localStorage.removeItem(STORAGE_KEY);
    return entry;
  }

  function getLeaderboard() {
    try { return JSON.parse(localStorage.getItem(LEADERBOARD_KEY)) || []; } catch { return []; }
  }

  /* ---- UI renders ---- */

  function renderProgress(current, total) {
    const el = document.getElementById("progress");
    if (!el) return;
    total = total || 5;
    let steps = "";
    for (let i = 0; i < total; i++) {
      const cls = i < current ? "completed" : i === current ? "active" : "";
      steps += `<div class="progress-step ${cls}">${i < current ? "✓" : i + 1}</div>`;
    }
    const pct = total === 0 ? 0 : (current / total) * 100;
    el.innerHTML = `
      <div class="progress-label"><span>Прогресс</span><span>${current} / ${total}</span></div>
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div class="progress-steps">${steps}</div>`;
  }

  let _timerRAF = null;
  function startTimerDisplay() {
    const el = document.getElementById("quest-timer");
    if (!el) return;
    (function tick() {
      const s = getState();
      if (!s || !s.startTime) return;
      el.innerHTML = `<div class="timer-label">Время</div><div>${formatTime(Date.now() - s.startTime)}</div>`;
      _timerRAF = requestAnimationFrame(tick);
    })();
  }

  function stopTimerDisplay() {
    if (_timerRAF) cancelAnimationFrame(_timerRAF);
  }

  function renderPasswordDisplay(digits) {
    const el = document.getElementById("password-display");
    if (!el) return;
    let html = "";
    for (let i = 0; i < 5; i++) {
      const filled = digits[i] !== undefined && digits[i] !== "";
      const val = filled ? String(digits[i]) : "?";
      html += `<div class="password-digit ${filled ? "filled" : ""}">${val}</div>`;
    }
    el.innerHTML = html;
  }

  function renderLeaderboard(highlightName) {
    const el = document.getElementById("leaderboard");
    if (!el) return;
    const lb = getLeaderboard();
    if (!lb.length) {
      el.innerHTML = '<p class="text-dim text-center" style="padding:2rem">Пока нет результатов.</p>';
      return;
    }
    const medals = ["🥇", "🥈", "🥉"];
    el.innerHTML = lb.slice(0, 10).map((e, i) => {
      const rc = i === 0 ? "gold" : i === 1 ? "silver" : i === 2 ? "bronze" : "";
      const hl = e.name === highlightName ? " highlight" : "";
      return `<div class="leaderboard-row${hl}">
        <div class="leaderboard-rank ${rc}">${medals[i] || `#${i + 1}`}</div>
        <div class="leaderboard-name">${esc(e.name)}</div>
        <div class="leaderboard-time">${e.timeFormatted}</div>
      </div>`;
    }).join("");
  }

  function esc(t) { const d = document.createElement("div"); d.textContent = t; return d.innerHTML; }

  function confetti() {
    const c = document.getElementById("confetti-canvas");
    if (!c) return;
    const ctx = c.getContext("2d");
    c.width = innerWidth;
    c.height = innerHeight;
    const colors = ["#00ff9c", "#00d4ff", "#ffd700", "#ff4757", "#ff9f43", "#c678dd"];
    const pieces = Array.from({ length: 100 }, () => ({
      x: Math.random() * c.width,
      y: Math.random() * c.height - c.height,
      w: Math.random() * 8 + 4,
      h: Math.random() * 6 + 3,
      color: colors[Math.floor(Math.random() * colors.length)],
      speed: Math.random() * 3 + 2,
      angle: Math.random() * 360,
      spin: (Math.random() - 0.5) * 10,
      drift: (Math.random() - 0.5) * 2,
    }));
    let f = 0;
    (function anim() {
      ctx.clearRect(0, 0, c.width, c.height);
      for (const p of pieces) {
        p.y += p.speed; p.x += p.drift; p.angle += p.spin;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.angle * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      }
      if (++f < 300) requestAnimationFrame(anim);
      else ctx.clearRect(0, 0, c.width, c.height);
    })();
  }

  /* ---- init guard ---- */

  function currentPageId() {
    const f = location.pathname.split("/").pop() || "start.html";
    return f.replace(".html", "") || "start";
  }

  function initGuard() {
    const page = currentPageId();
    if (page === "start" || page === "index" || page === "") {
      resetQuest();
      return;
    }
    if (page === "run" || page === "finish") {
      const s = getState();
      if (!s || !s.startTime) { location.href = "start.html"; return; }
      if (page === "run") startTimerDisplay();
    }
  }

  /* ---- public ---- */

  return {
    init: initGuard,
    startQuest,
    completeCheckpoint,
    assemblePassword,
    makeToken,
    validateToken,
    tokenToCheckpointId,
    getTime,
    formatTime,
    finishQuest,
    getLeaderboard,
    resetQuest,
    renderProgress,
    startTimerDisplay,
    stopTimerDisplay,
    renderPasswordDisplay,
    renderLeaderboard,
    confetti,
    getState,
    currentPageId,
    DIGITS_CORRECT,
  };
})();

document.addEventListener("DOMContentLoaded", () => QuestApp.init());
