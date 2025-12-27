const textarea = document.getElementById("question");
const askBtn = document.getElementById("askBtn");
const responseEl = document.getElementById("response");
const loadingEl = document.getElementById("loading");
const statsEl = document.getElementById("stats");
const refreshStatsBtn = document.getElementById("refreshStats");

const MAX_LENGTH = 300;

function setLoading(isLoading) {
  askBtn.disabled = isLoading || !textarea.value.trim();
  loadingEl.classList.toggle("hidden", !isLoading);
}

function prettyPrint(obj) {
  return JSON.stringify(obj, null, 2);
}

async function sendQuestion() {
  const question = textarea.value.trim();
  if (!question || question.length > MAX_LENGTH) return;

  setLoading(true);
  responseEl.textContent = "{}";

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (!res.ok) {
      const text = await res.text();
      responseEl.textContent = prettyPrint({ error: text || "Request failed" });
    } else {
      const data = await res.json();
      responseEl.textContent = prettyPrint(data);
    }
  } catch (err) {
    responseEl.textContent = prettyPrint({ error: "Network error", detail: String(err) });
  } finally {
    setLoading(false);
  }
}

async function fetchStats() {
  try {
    const res = await fetch("/stats");
    if (!res.ok) {
      statsEl.textContent = prettyPrint({ error: "Failed to load stats" });
      return;
    }
    const data = await res.json();
    statsEl.textContent = prettyPrint(data);
  } catch (err) {
    statsEl.textContent = prettyPrint({ error: "Network error", detail: String(err) });
  }
}

askBtn.addEventListener("click", sendQuestion);

textarea.addEventListener("input", () => {
  if (textarea.value.length > MAX_LENGTH) {
    textarea.value = textarea.value.slice(0, MAX_LENGTH);
  }
  askBtn.disabled = !textarea.value.trim();
});

document.querySelectorAll(".example-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    textarea.value = btn.dataset.query;
    askBtn.disabled = false;
    textarea.focus();
  });
});

setLoading(false);
if (refreshStatsBtn) {
  refreshStatsBtn.addEventListener("click", fetchStats);
  fetchStats();
}
