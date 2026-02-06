/*
 * Live Dashboard for the Lexical Decision Task
 *
 * Listens to Firestore collections (sessions + trials) and recomputes
 * summary statistics in real time, mirroring the analysis pipeline in
 * analysis.py.
 */

import { db } from "./firebase-config.js";
import {
  collection,
  onSnapshot,
  query,
  orderBy,
} from "https://www.gstatic.com/firebasejs/11.3.0/firebase-firestore.js";

// =========================================================================
// State
// =========================================================================
let allSessions = [];
let allTrials = [];
let accChart = null;
let rtChart = null;

// =========================================================================
// Firestore listeners
// =========================================================================

const sessionsQuery = query(
  collection(db, "sessions"),
  orderBy("startedAt", "desc"),
);

const trialsQuery = query(
  collection(db, "trials"),
  orderBy("timestamp", "asc"),
);

onSnapshot(sessionsQuery, (snapshot) => {
  allSessions = snapshot.docs.map((d) => ({ id: d.id, ...d.data() }));
  updateParticipantList(allTrials);
  updateStatusLine();
});

let recomputeTimer = null;
onSnapshot(trialsQuery, (snapshot) => {
  allTrials = snapshot.docs.map((d) => ({ id: d.id, ...d.data() }));
  // Debounce recomputation (many trials can arrive in quick succession)
  clearTimeout(recomputeTimer);
  recomputeTimer = setTimeout(recomputeAll, 500);
  updateStatusLine();
});

// =========================================================================
// Status line
// =========================================================================

function updateStatusLine() {
  const el = document.getElementById("status-line");
  const nSessions = allSessions.length;
  const nTrials = allTrials.length;
  el.textContent = `Connected \u2014 ${nSessions} session(s), ${nTrials} trial(s) received.`;
}

// =========================================================================
// Participant list
// =========================================================================

function updateParticipantList(trials) {
  const inProgress = allSessions.filter(
    (s) => s.status === "in_progress",
  ).length;
  const completed = allSessions.filter(
    (s) => s.status === "completed",
  ).length;

  document.getElementById("count-in-progress").textContent = inProgress;
  document.getElementById("count-completed").textContent = completed;
  document.getElementById("count-trials").textContent = trials.length;

  // Compute per-participant accuracy from trial data
  const trialsByUser = groupBy(trials, "username");
  const ranked = allSessions
    .map((s) => {
      const userTrials = trialsByUser[s.username] || [];
      const n = userTrials.length;
      const acc =
        n > 0 ? userTrials.reduce((sum, t) => sum + t.accuracy, 0) / n : null;
      return { ...s, acc, nTrials: n };
    })
    .sort((a, b) => {
      // Completed participants first, then by accuracy descending
      if (a.status === "completed" && b.status !== "completed") return -1;
      if (a.status !== "completed" && b.status === "completed") return 1;
      if (a.acc === null && b.acc === null) return 0;
      if (a.acc === null) return 1;
      if (b.acc === null) return -1;
      return b.acc - a.acc;
    });

  const tbody = document.getElementById("participant-tbody");
  tbody.innerHTML = ranked
    .map((s, i) => {
      const dotClass =
        s.status === "completed" ? "dot-done" : "dot-progress";
      const statusLabel = s.status === "completed" ? "done" : "running";
      const accText =
        s.acc !== null ? (s.acc * 100).toFixed(0) + "%" : "--";
      return `<tr>
      <td>${i + 1}</td>
      <td>${escapeHtml(s.username)}</td>
      <td><span class="status-cell"><span class="dot ${dotClass}"></span> ${statusLabel}</span></td>
      <td>${accText}</td>
    </tr>`;
    })
    .join("");
}

// =========================================================================
// Recompute all statistics (mirrors analysis.py)
// =========================================================================

function recomputeAll() {
  if (allTrials.length === 0) return;

  // 1. Trial-level exclusions (matching analysis.py)
  const clean = allTrials.filter((t) => {
    if (t.RT === "" || t.RT === null || t.RT === undefined) return false;
    const rt = parseFloat(t.RT);
    if (isNaN(rt)) return false;
    if (rt < 0.2) return false; // RT < 200 ms
    if (rt > 2.0) return false; // RT > 2000 ms
    return true;
  });

  // 2. Grand means by lexicality x duration
  const conditions = [
    { lex: "word", dur: 40 },
    { lex: "word", dur: 200 },
    { lex: "pseudoword", dur: 40 },
    { lex: "pseudoword", dur: 200 },
  ];

  const grandStats = {};
  for (const { lex, dur } of conditions) {
    const subset = clean.filter(
      (t) => t.lexicality === lex && t.duration === dur,
    );
    const n = subset.length;
    const acc =
      n > 0 ? subset.reduce((s, t) => s + t.accuracy, 0) / n : null;
    const correct = subset.filter((t) => t.accuracy === 1);
    const meanRT =
      correct.length > 0
        ? correct.reduce((s, t) => s + parseFloat(t.RT), 0) / correct.length
        : null;
    grandStats[`${lex}-${dur}`] = { acc, meanRT, n };
  }

  // 3. Update participant ranking and charts
  updateParticipantList(allTrials);
  updateCharts(grandStats);
}

// =========================================================================
// Charts (Chart.js)
// =========================================================================

function updateCharts(stats) {
  const labels = ["40 ms", "200 ms"];
  const wordAcc = [stats["word-40"].acc, stats["word-200"].acc];
  const pwAcc = [stats["pseudoword-40"].acc, stats["pseudoword-200"].acc];
  const wordRT = [stats["word-40"].meanRT, stats["word-200"].meanRT];
  const pwRT = [stats["pseudoword-40"].meanRT, stats["pseudoword-200"].meanRT];

  // Accuracy chart
  if (accChart) {
    accChart.data.datasets[0].data = wordAcc;
    accChart.data.datasets[1].data = pwAcc;
    accChart.update();
  } else {
    accChart = new Chart(document.getElementById("chart-accuracy"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Word",
            data: wordAcc,
            backgroundColor: "#4ade80",
          },
          {
            label: "Pseudoword",
            data: pwAcc,
            backgroundColor: "#f87171",
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: "Accuracy by Lexicality and Duration",
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 1,
            title: {
              display: true,
              text: "Accuracy (proportion correct)",
            },
          },
          x: {
            title: { display: true, text: "Presentation Duration" },
          },
        },
      },
    });
  }

  // RT chart
  if (rtChart) {
    rtChart.data.datasets[0].data = wordRT;
    rtChart.data.datasets[1].data = pwRT;
    rtChart.update();
  } else {
    rtChart = new Chart(document.getElementById("chart-rt"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Word",
            data: wordRT,
            backgroundColor: "#4ade80",
          },
          {
            label: "Pseudoword",
            data: pwRT,
            backgroundColor: "#f87171",
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: "Reaction Time by Lexicality and Duration",
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Mean Correct RT (s)" },
          },
          x: {
            title: { display: true, text: "Presentation Duration" },
          },
        },
      },
    });
  }
}

// =========================================================================
// Utilities
// =========================================================================

function groupBy(arr, key) {
  return arr.reduce((groups, item) => {
    (groups[item[key]] = groups[item[key]] || []).push(item);
    return groups;
  }, {});
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
