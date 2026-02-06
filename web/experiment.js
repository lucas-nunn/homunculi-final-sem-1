/*
 * Lexical Decision Task with Visual Masking (web version)
 *
 * Within-subject 2x2 factorial design:
 *   IV1: Lexicality (word vs pseudoword)
 *   IV2: Presentation duration (40 ms vs 200 ms)
 *   DVs: Accuracy and Reaction Time
 *
 * Trial structure:
 *   1. Fixation cross  (500 ms)
 *   2. Target string   (40 or 200 ms)
 *   3. Mask            (150 ms)
 *   4. Response window  (up to 2000 ms)
 *   5. Feedback        (500 ms)
 *
 * Timing uses requestAnimationFrame for frame-accurate presentation.
 */

import { db } from "./firebase-config.js";
import {
  collection,
  addDoc,
  doc,
  updateDoc,
  serverTimestamp,
  increment,
} from "https://www.gstatic.com/firebasejs/11.3.0/firebase-firestore.js";

let sessionDocId = null;

// =========================================================================
// Configuration
// =========================================================================
const CONFIG = {
  // stimuli
  words: [
    "river",
    "window",
    "sugar",
    "forest",
    "jacket",
    "island",
    "kitten",
    "cheese",
    "hammer",
    "candle",
  ],
  pseudowords: [
    "tible",
    "hause",
    "gardon",
    "flomer",
    "desern",
    "strean",
    "perlun",
    "morle",
    "stome",
    "waper",
  ],

  // practice stimuli (separate from main set)
  practiceItems: [
    { stimulus: "finger", lexicality: "word" },
    { stimulus: "church", lexicality: "word" },
    { stimulus: "carrot", lexicality: "word" },
    { stimulus: "hamen", lexicality: "pseudoword" },
    { stimulus: "pamer", lexicality: "pseudoword" },
    { stimulus: "waten", lexicality: "pseudoword" },
  ],

  // timing in ms
  durations: [40, 200], // stimulus presentation durations
  fixationDuration: 500,
  maskDuration: 150,
  responseTimeout: 2000,
  feedbackDuration: 500,

  // design
  nReps: 1, // repetitions of the full stimulus set
  maxSameLexInRow: 3, // randomisation constraint

  // response keys
  keyWord: "f",
  keyNonword: "j",
};

// =========================================================================
// Trial generation
// =========================================================================

/** Generate a mask string matched to stimulus length. */
function generateMask(stimulus) {
  return "#".repeat(stimulus.length);
}

/** Shuffle array in place (Fisher-Yates). */
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/** Check that no more than maxRun trials of the same lexicality appear in a row. */
function checkLexConstraint(trials, maxRun) {
  let count = 1;
  for (let i = 1; i < trials.length; i++) {
    if (trials[i].lexicality === trials[i - 1].lexicality) {
      count++;
      if (count > maxRun) return false;
    } else {
      count = 1;
    }
  }
  return true;
}

/** Build the main trial list: each stimulus x each duration x uReps, shuffled with constraint. */
function generateTrials() {
  const trials = [];
  for (let rep = 0; rep < CONFIG.nReps; rep++) {
    for (const dur of CONFIG.durations) {
      for (const word of CONFIG.words) {
        trials.push({ stimulus: word, lexicality: "word", duration: dur });
      }
      for (const pw of CONFIG.pseudowords) {
        trials.push({ stimulus: pw, lexicality: "pseudoword", duration: dur });
      }
    }
  }

  // shuffle with constraint (try up to 1000 times)
  for (let attempt = 0; attempt < 1000; attempt++) {
    shuffle(trials);
    if (checkLexConstraint(trials, CONFIG.maxSameLexInRow)) break;
  }

  // add trial numbers
  trials.forEach((t, i) => {
    t.trialNumber = i;
  });
  return trials;
}

/** Build practice trials: half short duration, half long duration. */
function generatePracticeTrials() {
  const items = [...CONFIG.practiceItems];
  const half = Math.ceil(items.length / 2);
  const trials = items.map((item, i) => ({
    ...item,
    duration:
      i < half
        ? CONFIG.durations[0]
        : CONFIG.durations[CONFIG.durations.length - 1],
  }));
  shuffle(trials);
  return trials;
}

// =========================================================================
// Touch device detection
// =========================================================================
const isTouchDevice = "ontouchstart" in window || navigator.maxTouchPoints > 0;
if (isTouchDevice) {
  document.body.classList.add("touch");
}

// =========================================================================
// DOM helpers
// =========================================================================
const screens = {
  welcome: document.getElementById("screen-welcome"),
  practiceIntro: document.getElementById("screen-practice-intro"),
  practiceDone: document.getElementById("screen-practice-done"),
  break: document.getElementById("screen-break"),
  trial: document.getElementById("screen-trial"),
  end: document.getElementById("screen-end"),
};
const trialContent = document.getElementById("trial-content");

function showScreen(name) {
  Object.values(screens).forEach((s) => s.classList.remove("active"));
  screens[name].classList.add("active");
}

// =========================================================================
// Timing helpers (requestAnimationFrame-based)
// =========================================================================

/**
 * Show content in the trial area for a given duration using rAF.
 * Returns a promise that resolves with the timestamp when the phase ended.
 */
function showForDuration(html, durationMs) {
  return new Promise((resolve) => {
    let startTime = null;
    trialContent.innerHTML = html;

    function frame(timestamp) {
      if (startTime === null) startTime = timestamp;
      if (timestamp - startTime >= durationMs) {
        resolve(timestamp);
        return;
      }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  });
}

/**
 * Wait for a key response (F or J) or a mobile button tap, with a timeout.
 * Returns { key, rt } or { key: null, rt: null } on timeout.
 */
function waitForResponse(promptHtml, timeoutMs) {
  return new Promise((resolve) => {
    trialContent.innerHTML = promptHtml;
    document.body.classList.add("awaiting-response");
    const startTime = performance.now();
    let resolved = false;

    function cleanup() {
      document.body.classList.remove("awaiting-response");
      document.removeEventListener("keydown", onKey);
      btnWord.removeEventListener("pointerup", onTapWord);
      btnNonword.removeEventListener("pointerup", onTapNonword);
      clearTimeout(timer);
    }

    function respond(key) {
      if (resolved) return;
      resolved = true;
      cleanup();
      resolve({ key, rt: performance.now() - startTime });
    }

    // keyboard
    function onKey(e) {
      const k = e.key.toLowerCase();
      if (k === CONFIG.keyWord) respond(CONFIG.keyWord);
      else if (k === CONFIG.keyNonword) respond(CONFIG.keyNonword);
    }
    document.addEventListener("keydown", onKey);

    // mobile buttons
    const btnWord = document.getElementById("btn-word");
    const btnNonword = document.getElementById("btn-nonword");
    function onTapWord(e) {
      e.preventDefault();
      respond(CONFIG.keyWord);
    }
    function onTapNonword(e) {
      e.preventDefault();
      respond(CONFIG.keyNonword);
    }
    btnWord.addEventListener("pointerup", onTapWord);
    btnNonword.addEventListener("pointerup", onTapNonword);

    // timeout
    const timer = setTimeout(() => {
      if (resolved) return;
      resolved = true;
      cleanup();
      resolve({ key: null, rt: null });
    }, timeoutMs);
  });
}

/**
 * Wait until the participant presses F or J, or taps a .btn-continue
 * (used for instruction screens).
 */
function waitForAnyResponseKey() {
  return new Promise((resolve) => {
    let resolved = false;

    function done() {
      if (resolved) return;
      resolved = true;
      document.removeEventListener("keydown", onKey);
      continueButtons.forEach((btn) =>
        btn.removeEventListener("pointerup", onTap),
      );
      resolve();
    }

    // keyboard
    function onKey(e) {
      const k = e.key.toLowerCase();
      if (k === CONFIG.keyWord || k === CONFIG.keyNonword) done();
    }
    document.addEventListener("keydown", onKey);

    // mobile continue buttons (only the visible one will be tappable)
    const continueButtons = document.querySelectorAll(".btn-continue");
    function onTap(e) {
      e.preventDefault();
      done();
    }
    continueButtons.forEach((btn) => btn.addEventListener("pointerup", onTap));
  });
}

// =========================================================================
// Run a single trial
// =========================================================================

/**
 * Run one trial and return the result object.
 * The trial sequence: fixation -> stimulus -> mask -> response -> feedback.
 */
async function runTrial(trialInfo) {
  showScreen("trial");

  // 1. Fixation cross
  await showForDuration(
    '<span class="fixation">+</span>',
    CONFIG.fixationDuration,
  );

  // 2. Stimulus
  await showForDuration(
    `<span class="stimulus">${trialInfo.stimulus.toUpperCase()}</span>`,
    trialInfo.duration,
  );

  // 3. Mask
  const mask = generateMask(trialInfo.stimulus);
  await showForDuration(
    `<span class="mask">${mask}</span>`,
    CONFIG.maskDuration,
  );

  // 4. Response
  const { key, rt } = await waitForResponse(
    `<span class="prompt">${CONFIG.keyWord.toUpperCase()} = WORD &nbsp;&nbsp;&nbsp; ${CONFIG.keyNonword.toUpperCase()} = NOT A WORD</span>`,
    CONFIG.responseTimeout,
  );

  // score
  const timedOut = key === null;
  const expected =
    trialInfo.lexicality === "word" ? CONFIG.keyWord : CONFIG.keyNonword;
  const correct = !timedOut && key === expected;

  // 5. Feedback
  let fbText;
  if (timedOut) fbText = "Too slow!";
  else if (correct) fbText = "Correct!";
  else fbText = "Incorrect.";
  await showForDuration(
    `<span class="feedback">${fbText}</span>`,
    CONFIG.feedbackDuration,
  );

  return {
    stimulus: trialInfo.stimulus,
    lexicality: trialInfo.lexicality,
    duration: trialInfo.duration,
    response: timedOut ? "" : key === CONFIG.keyWord ? 1 : 0,
    RT: timedOut ? "" : (rt / 1000).toFixed(6), // convert ms to seconds
    accuracy: correct ? 1 : 0,
  };
}

// =========================================================================
// CSV export
// =========================================================================

function toCSV(rows, columns) {
  const header = columns.join(",");
  const lines = rows.map((row) => columns.map((c) => row[c] ?? "").join(","));
  return header + "\n" + lines.join("\n") + "\n";
}

function downloadCSV(csv, filename) {
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// =========================================================================
// Read parameters from the welcome form and apply to CONFIG
// =========================================================================

function applyFormParameters() {
  CONFIG.nReps = parseInt(document.getElementById("param-reps").value) || 1;
  CONFIG.fixationDuration =
    parseInt(document.getElementById("param-fix-dur").value) || 500;
  CONFIG.maskDuration =
    parseInt(document.getElementById("param-mask-dur").value) || 150;
  CONFIG.responseTimeout =
    parseInt(document.getElementById("param-timeout").value) || 2000;
  CONFIG.feedbackDuration =
    parseInt(document.getElementById("param-fb-dur").value) || 500;

  if (document.getElementById("param-swap").checked) {
    CONFIG.keyWord = "j";
    CONFIG.keyNonword = "f";
  }
}

// =========================================================================
// Firestore helpers
// =========================================================================

async function createSession(username, totalTrials) {
  const docRef = await addDoc(collection(db, "sessions"), {
    username,
    status: "in_progress",
    totalTrials,
    completedTrials: 0,
    startedAt: serverTimestamp(),
    completedAt: null,
  });
  return docRef.id;
}

async function saveTrialToFirestore(username, result) {
  await addDoc(collection(db, "trials"), {
    sessionId: sessionDocId,
    username,
    trialNumber: result.trialNumber,
    stimulus: result.stimulus,
    lexicality: result.lexicality,
    duration: result.duration,
    response: result.response,
    RT: result.RT,
    accuracy: result.accuracy,
    timestamp: serverTimestamp(),
  });
  await updateDoc(doc(db, "sessions", sessionDocId), {
    completedTrials: increment(1),
  });
}

async function completeSession() {
  await updateDoc(doc(db, "sessions", sessionDocId), {
    status: "completed",
    completedAt: serverTimestamp(),
  });
}

// =========================================================================
// Summary statistics for end screen
// =========================================================================

function computeSummary(results) {
  const durations = [...new Set(results.map((r) => r.duration))].sort(
    (a, b) => a - b,
  );

  // helper: compute mean accuracy and mean correct RT for a subset
  function stats(subset) {
    const n = subset.length;
    if (n === 0) return { acc: 0, rt: null, n: 0 };
    const acc = subset.reduce((s, r) => s + r.accuracy, 0) / n;
    const correct = subset.filter((r) => r.accuracy === 1 && r.RT !== "");
    const rt =
      correct.length > 0
        ? correct.reduce((s, r) => s + parseFloat(r.RT), 0) / correct.length
        : null;
    return { acc, rt, n };
  }

  // 2x2: lexicality x duration
  const cells = {};
  for (const lex of ["word", "pseudoword"]) {
    cells[lex] = {};
    for (const dur of durations) {
      cells[lex][dur] = stats(
        results.filter((r) => r.lexicality === lex && r.duration === dur),
      );
    }
  }

  // marginals by lexicality
  const byLex = {};
  for (const lex of ["word", "pseudoword"]) {
    byLex[lex] = stats(results.filter((r) => r.lexicality === lex));
  }

  // marginals by duration
  const byDur = {};
  for (const dur of durations) {
    byDur[dur] = stats(results.filter((r) => r.duration === dur));
  }

  return { durations, cells, byLex, byDur };
}

function populateSummary(results) {
  const { durations, cells, byLex, byDur } = computeSummary(results);
  const nCorrect = results.filter((r) => r.accuracy === 1).length;
  const fmt = (v) => (v !== null ? v.toFixed(3) : "—");
  const pct = (v) => (v * 100).toFixed(0) + "%";

  // overall
  document.getElementById("end-overall").textContent =
    `You completed ${results.length} trials with ${nCorrect}/${results.length} correct (${pct(nCorrect / results.length)}).`;

  // 2x2 table headers
  document.getElementById("th-acc-dur0").textContent = durations[0] + " ms";
  document.getElementById("th-acc-dur1").textContent = durations[1] + " ms";
  document.getElementById("th-rt-dur0").textContent = durations[0] + " ms";
  document.getElementById("th-rt-dur1").textContent = durations[1] + " ms";

  // 2x2 cells
  document.getElementById("acc-word-dur0").textContent = pct(
    cells.word[durations[0]].acc,
  );
  document.getElementById("acc-word-dur1").textContent = pct(
    cells.word[durations[1]].acc,
  );
  document.getElementById("acc-pw-dur0").textContent = pct(
    cells.pseudoword[durations[0]].acc,
  );
  document.getElementById("acc-pw-dur1").textContent = pct(
    cells.pseudoword[durations[1]].acc,
  );
  document.getElementById("rt-word-dur0").textContent = fmt(
    cells.word[durations[0]].rt,
  );
  document.getElementById("rt-word-dur1").textContent = fmt(
    cells.word[durations[1]].rt,
  );
  document.getElementById("rt-pw-dur0").textContent = fmt(
    cells.pseudoword[durations[0]].rt,
  );
  document.getElementById("rt-pw-dur1").textContent = fmt(
    cells.pseudoword[durations[1]].rt,
  );

  // by lexicality
  document.getElementById("lex-acc-word").textContent = pct(byLex.word.acc);
  document.getElementById("lex-acc-pw").textContent = pct(byLex.pseudoword.acc);
  document.getElementById("lex-rt-word").textContent = fmt(byLex.word.rt);
  document.getElementById("lex-rt-pw").textContent = fmt(byLex.pseudoword.rt);

  // by duration
  document.getElementById("dur-label-0").textContent = durations[0] + " ms";
  document.getElementById("dur-label-1").textContent = durations[1] + " ms";
  document.getElementById("dur-acc-0").textContent = pct(
    byDur[durations[0]].acc,
  );
  document.getElementById("dur-acc-1").textContent = pct(
    byDur[durations[1]].acc,
  );
  document.getElementById("dur-rt-0").textContent = fmt(byDur[durations[0]].rt);
  document.getElementById("dur-rt-1").textContent = fmt(byDur[durations[1]].rt);
}

// =========================================================================
// Main experiment flow
// =========================================================================

async function runExperiment() {
  applyFormParameters();
  const subjId = document.getElementById("subject-id").value.trim();
  if (!subjId) {
    alert("Please enter a username.");
    return;
  }
  const includePractice = document.getElementById("param-practice").checked;
  const devMode = document.getElementById("param-dev-mode").checked;
  const results = [];

  // Create Firestore session
  const totalTrials = devMode
    ? 10
    : CONFIG.nReps *
      (CONFIG.words.length + CONFIG.pseudowords.length) *
      CONFIG.durations.length;

  try {
    sessionDocId = await createSession(subjId, totalTrials);
  } catch (err) {
    console.error("Failed to create Firestore session:", err);
  }

  // --- Practice (optional) ---
  if (includePractice) {
    showScreen("practiceIntro");
    await waitForAnyResponseKey();

    const practiceTrials = generatePracticeTrials();
    for (const pt of practiceTrials) {
      await runTrial(pt); // results discarded
    }

    showScreen("practiceDone");
    await waitForAnyResponseKey();
  }

  // --- Main trials ---
  let trials = generateTrials();
  if (devMode) {
    trials = trials.slice(0, 10);
  }
  const midpoint = Math.floor(trials.length / 2);

  for (let i = 0; i < trials.length; i++) {
    // midpoint break (only when nReps > 1)
    if (CONFIG.nReps > 1 && i === midpoint) {
      showScreen("break");
      await waitForAnyResponseKey();
    }

    const result = await runTrial(trials[i]);
    result.trialNumber = i;
    result.subject = subjId;
    results.push(result);

    // Fire-and-forget write to Firestore (don't block next trial)
    if (sessionDocId) {
      saveTrialToFirestore(subjId, result).catch((err) =>
        console.error("Firestore write failed for trial", i, err),
      );
    }
  }

  // Mark session complete
  if (sessionDocId) {
    completeSession().catch((err) =>
      console.error("Failed to mark session complete:", err),
    );
  }

  // --- End screen with summary ---
  populateSummary(results);
  showScreen("end");

  // wire up download button
  const columns = [
    "subject",
    "trialNumber",
    "stimulus",
    "lexicality",
    "duration",
    "response",
    "RT",
    "accuracy",
  ];
  const csv = toCSV(results, columns);
  document.getElementById("btn-download").addEventListener("click", () => {
    downloadCSV(
      csv,
      `${subjId.replace(/[^a-zA-Z0-9_-]/g, "_")}_trial_responses.csv`,
    );
  });
}

// =========================================================================
// Start
// =========================================================================
document.getElementById("btn-start").addEventListener("click", () => {
  runExperiment();
});
