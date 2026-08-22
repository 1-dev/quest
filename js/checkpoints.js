const CHECKPOINTS = [];
let DIGITS = [];

async function loadCheckpoints() {
  const res = await fetch(window.location.origin + "/api/checkpoints");
  const data = await res.json();
  CHECKPOINTS.length = 0;
  data.forEach(cp => { CHECKPOINTS[cp.id] = cp; });
  DIGITS = data.map(cp => cp.digit);
}
