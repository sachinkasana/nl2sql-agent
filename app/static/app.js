(() => {
  const textarea = document.getElementById("question");
  const askBtn = document.getElementById("askBtn");
  const loadingEl = document.getElementById("loading");
  const statsEl = document.getElementById("stats");
  const refreshStatsBtn = document.getElementById("refreshStats");
  const answerText = document.getElementById("answerText");
  const latencyEl = document.getElementById("latency");
  const sqlCodeEl = document.getElementById("sqlCode");
  const copySqlBtn = document.getElementById("copySql");
  const tableContainer = document.getElementById("tableContainer");
  const warningsEl = document.getElementById("warnings");
  const themeToggle = document.getElementById("themeToggle");

  const MAX_LENGTH = 300;
  const THEME_KEY = "nl2sql-theme";

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
    themeToggle.textContent = theme === "dark" ? "☀️" : "🌙";
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || "light";
    setTheme(saved);
  }

  function setLoading(isLoading) {
    askBtn.disabled = isLoading || !textarea.value.trim();
    loadingEl.classList.toggle("hidden", !isLoading);
  }

  function prettyPrint(obj) {
    return JSON.stringify(obj, null, 2);
  }

  function renderWarnings(warnings) {
    if (warnings && warnings.length) {
      warningsEl.textContent = warnings.join(" • ");
    } else {
      warningsEl.textContent = "";
    }
  }

  function renderRows(rows) {
    if (!Array.isArray(rows)) {
      tableContainer.textContent = "No rows returned";
      return;
    }
    if (rows.length === 0) {
      tableContainer.textContent = "No rows returned";
      return;
    }
    const headers = Object.keys(rows[0]);
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    headers.forEach((h) => {
      const th = document.createElement("th");
      th.textContent = h;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      headers.forEach((h) => {
        const td = document.createElement("td");
        const val = row[h];
        td.textContent = val === null || val === undefined ? "" : String(val);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    tableContainer.innerHTML = "";
    tableContainer.appendChild(table);
  }

  function renderSQL(sql) {
    const cleanSql = sql || "";
    sqlCodeEl.textContent = cleanSql;
    if (window.Prism) {
      Prism.highlightElement(sqlCodeEl);
    }
    copySqlBtn.disabled = !cleanSql.trim();
  }

  async function copySql() {
    const sql = sqlCodeEl.textContent || "";
    if (!sql.trim()) return;
    try {
      await navigator.clipboard.writeText(sql);
      const original = copySqlBtn.textContent;
      copySqlBtn.textContent = "Copied ✓";
      setTimeout(() => (copySqlBtn.textContent = original), 1500);
    } catch {
      // ignore
    }
  }

  async function sendQuestion() {
    const question = textarea.value.trim();
    if (!question || question.length > MAX_LENGTH) return;

    setLoading(true);
    answerText.textContent = "";
    renderSQL("");
    tableContainer.textContent = "No rows returned";
    warningsEl.textContent = "";
    latencyEl.textContent = "";

    const start = performance.now();
    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const elapsed = Math.round(performance.now() - start);
      latencyEl.textContent = `Latency: ${elapsed} ms`;

      if (!res.ok) {
        const text = await res.text();
        answerText.textContent = "Error";
        renderSQL("");
        tableContainer.textContent = prettyPrint({ error: text || "Request failed" });
        return;
      }
      const data = await res.json();
      answerText.textContent = data.answer || "";
      renderSQL(data.sql || "");
      renderRows(data.rows);
      renderWarnings(data.warnings);
    } catch (err) {
      answerText.textContent = "Error";
      tableContainer.textContent = prettyPrint({ error: "Network error", detail: String(err) });
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

  function initExamples() {
    document.querySelectorAll(".example-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        textarea.value = btn.dataset.query;
        askBtn.disabled = false;
        textarea.focus();
      });
    });
  }

  function initInput() {
    textarea.addEventListener("input", () => {
      if (textarea.value.length > MAX_LENGTH) {
        textarea.value = textarea.value.slice(0, MAX_LENGTH);
      }
      askBtn.disabled = !textarea.value.trim();
    });
    askBtn.addEventListener("click", sendQuestion);
  }

  function initThemeToggle() {
    themeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      setTheme(current === "light" ? "dark" : "light");
    });
  }

  function initCopyButton() {
    copySqlBtn.addEventListener("click", copySql);
  }

  function initStats() {
    if (refreshStatsBtn) {
      refreshStatsBtn.addEventListener("click", fetchStats);
      fetchStats();
    }
  }

  // Init
  initTheme();
  setLoading(false);
  initExamples();
  initInput();
  initThemeToggle();
  initCopyButton();
  initStats();
})();
