/**
 * Google Apps Script — Volunteer Sprint Backend
 *
 * Setup:
 * 1. Google Sheets → Extensions → Apps Script → paste this code
 * 2. Deploy → New deployment → Web app (Execute as: Me, Access: Anyone)
 * 3. Copy URL → paste into js/config.js as API_URL
 *
 * Sheet tabs:
 *   "Results" — participant results (auto-created)
 *   "Numbers" — pre-generated number sets (upload from CSV)
 *     Columns: A=Participant, B=Numbers (comma-separated)
 */

const RESULTS_TAB = "Results";
const NUMBERS_TAB = "Numbers";

function doGet(e) {
  const action = e.parameter.action;

  if (action === "numbers") {
    return getNumbers(e.parameter.name);
  }

  return getResults();
}

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);

    if (body.action === "save_numbers") {
      return saveNumbers(body);
    }

    return saveResult(body);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/* ---- Results ---- */

function getResults() {
  const sheet = getOrCreateSheet(RESULTS_TAB);
  const data = sheet.getDataRange().getValues();
  const results = [];
  for (let i = 1; i < data.length; i++) {
    results.push({
      name: data[i][0],
      time: data[i][1],
      timeFormatted: data[i][2],
      password: data[i][3],
      numbers: data[i][4],
      date: data[i][5],
    });
  }
  results.sort((a, b) => a.time - b.time);
  return ContentService
    .createTextOutput(JSON.stringify(results))
    .setMimeType(ContentService.MimeType.JSON);
}

function saveResult(body) {
  const sheet = getOrCreateSheet(RESULTS_TAB);
  sheet.appendRow([
    body.name || "",
    body.time || 0,
    body.timeFormatted || "",
    body.password || "",
    body.numbers || "",
    body.date || new Date().toISOString(),
  ]);
  return ContentService
    .createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}

/* ---- Numbers ---- */

function getNumbers(name) {
  const sheet = getOrCreateSheet(NUMBERS_TAB);
  const data = sheet.getDataRange().getValues();

  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]).trim().toLowerCase() === String(name).trim().toLowerCase()) {
      const nums = String(data[i][1]).split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n));
      return ContentService
        .createTextOutput(JSON.stringify({ ok: true, numbers: nums, row: i + 1 }))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }

  return ContentService
    .createTextOutput(JSON.stringify({ ok: false, numbers: [] }))
    .setMimeType(ContentService.MimeType.JSON);
}

function saveNumbers(body) {
  const sheet = getOrCreateSheet(NUMBERS_TAB);
  // Clear old data (keep header)
  if (sheet.getLastRow() > 1) {
    sheet.deleteRows(2, sheet.getLastRow() - 1);
  }
  // Write new data
  for (const entry of body.sets) {
    sheet.appendRow([
      entry.name || "",
      (entry.numbers || []).join(", "),
    ]);
  }
  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, count: body.sets.length }))
    .setMimeType(ContentService.MimeType.JSON);
}

/* ---- Helpers ---- */

function getOrCreateSheet(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    if (name === RESULTS_TAB) {
      sheet.appendRow(["Name", "Time (ms)", "Time", "Password", "Numbers", "Date"]);
    } else if (name === NUMBERS_TAB) {
      sheet.appendRow(["Participant", "Numbers"]);
    }
  }
  return sheet;
}
