/**
 * Google Apps Script — Volunteer Sprint Backend
 *
 * How to set up:
 * 1. Open Google Sheets → create new spreadsheet
 * 2. Extensions → Apps Script
 * 3. Paste this code
 * 4. Deploy → New deployment → Web app
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 5. Copy the deployment URL and paste into config.js
 */

const SHEET_NAME = "Results";

function doGet(e) {
  const sheet = getSheet();
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

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const sheet = getSheet();

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
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function getSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(["Name", "Time (ms)", "Time", "Password", "Numbers", "Date"]);
  }
  return sheet;
}
