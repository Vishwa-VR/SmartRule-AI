(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const chatScroll = $("#chatScroll");
  const chatForm = $("#chatForm");
  const chatInput = $("#chatInput");
  const traceBody = $("#traceBody");
  const tracePanel = $("#tracePanel");
  const scrim = $("#scrim");
  const panelTitle = $("#panelTitle");
  const railLeft = $(".rail-left");

  // ---------------------------------------------------------------
  // Panel / tab switching
  // ---------------------------------------------------------------
  const PANEL_TITLES = {
    "panel-chat": "Chat",
    "panel-checklist": "Security checklist",
    "panel-kb": "Knowledge base",
    "panel-rules": "Rule base",
    "panel-history": "Conversation history",
  };

  function activatePanel(id) {
    $$(".panel").forEach(p => p.classList.toggle("active", p.id === id));
    $$(".tab").forEach(t => {
      const on = t.dataset.panel === id;
      t.classList.toggle("active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    panelTitle.textContent = PANEL_TITLES[id] || "SmartRuleAI";
    railLeft.classList.remove("open");
    scrim.classList.remove("show");

    if (id === "panel-kb") loadFacts();
    if (id === "panel-rules") loadRules();
    if (id === "panel-history") loadHistory();
  }

  $$(".tab").forEach(tab => {
    tab.addEventListener("click", () => activatePanel(tab.dataset.panel));
  });

  // Mobile menu drawer
  $("#menuToggle").addEventListener("click", () => {
    railLeft.classList.add("open");
    scrim.classList.add("show");
  });
  scrim.addEventListener("click", () => {
    railLeft.classList.remove("open");
    tracePanel.classList.remove("open");
    scrim.classList.remove("show");
  });

  // Mobile trace drawer
  $("#traceToggle").addEventListener("click", () => {
    tracePanel.classList.add("open");
    scrim.classList.add("show");
  });
  $("#traceClose").addEventListener("click", () => {
    tracePanel.classList.remove("open");
    scrim.classList.remove("show");
  });

  // ---------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  }

  function scrollChatToBottom() {
    chatScroll.scrollTop = chatScroll.scrollHeight;
  }

  function addBubble(sender, text, mood) {
    const wrap = document.createElement("div");
    wrap.className = `bubble ${sender}` + (mood ? ` mood-${mood}` : "");
    wrap.textContent = text;
    chatScroll.appendChild(wrap);
    scrollChatToBottom();
    return wrap;
  }

  function addTypingIndicator() {
    const el = document.createElement("div");
    el.className = "typing";
    el.innerHTML = "<span></span><span></span><span></span>";
    chatScroll.appendChild(el);
    scrollChatToBottom();
    return el;
  }

  // ---------------------------------------------------------------
  // Reasoning trace rendering
  // ---------------------------------------------------------------
  function renderTrace(trace) {
    traceBody.innerHTML = "";
    if (!trace || !trace.chain || !trace.chain.length) {
      traceBody.innerHTML = `<p class="trace-empty">No reasoning steps for that message. Try a topic like passwords, phishing, VPNs, or backups.</p>`;
      return;
    }
    trace.chain.forEach((step, i) => {
      const row = document.createElement("div");
      row.className = `trace-step ${step.polarity === "good" ? "good" : step.polarity === "risk" ? "risk" : ""}`;
      const ruleLine = step.rule
        ? `rule: ${escapeHtml(step.rule.name)}`
        : (step.is_initial ? "matched from your message" : "");
      row.innerHTML = `
        <div class="trace-num">${i + 1}</div>
        ${ruleLine ? `<div class="trace-rule">${ruleLine}</div>` : ""}
        <div class="trace-concept">${escapeHtml(step.label)}</div>
        <div class="trace-statement">${escapeHtml(step.statement)}</div>
      `;
      traceBody.appendChild(row);
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
  }

  // ---------------------------------------------------------------
  // Chat
  // ---------------------------------------------------------------
  async function sendMessage(message) {
    addBubble("user", message);
    chatInput.value = "";
    const typing = addTypingIndicator();

    try {
      const data = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      typing.remove();
      const bubble = addBubble("bot", data.response, data.mood);
      if (data.trace) {
        renderTrace(data.trace);
        const actions = document.createElement("div");
        actions.className = "bubble-actions";
        const btn = document.createElement("button");
        btn.className = "explain-link";
        btn.type = "button";
        btn.textContent = "Explain reasoning →";
        btn.addEventListener("click", () => {
          tracePanel.classList.add("open");
          scrim.classList.add("show");
        });
        actions.appendChild(btn);
        bubble.appendChild(actions);
      }
      refreshStats();
    } catch (err) {
      typing.remove();
      addBubble("bot", "Something went wrong reaching the reasoning engine. Please try again.");
    }
  }

  chatForm.addEventListener("submit", e => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;
    sendMessage(msg);
  });

  // ---------------------------------------------------------------
  // Greeting + quick chips + stats (loaded on startup)
  // ---------------------------------------------------------------
  function renderChips(list) {
    const box = $("#quickChips");
    box.innerHTML = "";
    list.forEach(q => {
      const chip = document.createElement("button");
      chip.className = "chip";
      chip.type = "button";
      chip.textContent = q;
      chip.addEventListener("click", () => sendMessage(q));
      box.appendChild(chip);
    });
  }

  function setStats(stats) {
    if (!stats) return;
    $("#statFacts").textContent = stats.facts ?? "–";
    $("#statRules").textContent = stats.rules ?? "–";
    $("#statDerived").textContent = stats.derived_facts ?? "–";
  }

  async function refreshStats() {
    try {
      const stats = await api("/api/stats");
      setStats(stats);
    } catch (_) { /* non-fatal */ }
  }

  async function loadGreeting() {
    try {
      const data = await api("/api/greeting");
      setStats(data.stats);
      renderChips(data.suggestions);
      const typing = addTypingIndicator();
      setTimeout(() => {
        typing.remove();
        addBubble("bot", `${data.emoji} ${data.greeting}`);
      }, 450);
    } catch (err) {
      addBubble("bot", "Hi! I'm SmartRuleAI. Ask me about passwords, phishing, VPNs, or backups.");
    }
  }

  $("#tipBtn").addEventListener("click", async () => {
    try {
      const data = await api("/api/tip");
      if (data.tip) {
        addBubble("bot", `💡 Tip — ${data.tip.statement}`);
        activatePanel("panel-chat");
      }
    } catch (_) {}
  });

  // ---------------------------------------------------------------
  // Knowledge base panel
  // ---------------------------------------------------------------
  let allFacts = [];

  async function loadFacts() {
    const data = await api("/api/facts");
    allFacts = data.facts;
    renderFacts(allFacts);
  }

  function renderFacts(facts) {
    const grid = $("#factGrid");
    grid.innerHTML = "";
    facts.forEach(f => {
      const card = document.createElement("div");
      card.className = `fact-card ${f.polarity}`;
      card.innerHTML = `
        <div class="fact-card-head">
          <span class="fact-concept">${escapeHtml(f.concept)}</span>
          ${f.is_base ? "" : `<button class="card-del" data-id="${f.id}" title="Delete">✕</button>`}
        </div>
        <div class="fact-statement">${escapeHtml(f.statement)}</div>
        <div class="fact-keywords">${escapeHtml(f.keywords)}</div>
      `;
      const del = card.querySelector(".card-del");
      if (del) del.addEventListener("click", async () => {
        await api(`/api/facts/${f.id}`, { method: "DELETE" });
        loadFacts();
        refreshStats();
      });
      grid.appendChild(card);
    });
  }

  $("#factSearch").addEventListener("input", e => {
    const q = e.target.value.toLowerCase();
    renderFacts(allFacts.filter(f =>
      f.concept.includes(q) || f.statement.toLowerCase().includes(q) || f.keywords.includes(q)
    ));
  });

  $("#addFactBtn").addEventListener("click", () => {
    $("#addFactForm").hidden = !$("#addFactForm").hidden;
  });

  $("#addFactForm").addEventListener("submit", async e => {
    e.preventDefault();
    try {
      await api("/api/facts", {
        method: "POST",
        body: JSON.stringify({
          concept: $("#factConcept").value,
          statement: $("#factStatement").value,
          keywords: $("#factKeywords").value,
          polarity: $("#factPolarity").value,
          category: "custom",
        }),
      });
      e.target.reset();
      e.target.hidden = true;
      loadFacts();
      refreshStats();
    } catch (err) {
      alert(err.message);
    }
  });

  // ---------------------------------------------------------------
  // Rule base panel
  // ---------------------------------------------------------------
  let allRules = [];

  async function loadRules() {
    const data = await api("/api/rules");
    allRules = data.rules;
    renderRules(allRules);
  }

  function renderRules(rules) {
    const list = $("#ruleList");
    list.innerHTML = "";
    rules.forEach(r => {
      const row = document.createElement("div");
      row.className = "rule-row";
      row.innerHTML = `
        <span class="rule-name">${escapeHtml(r.name)}</span>
        <span class="rule-chain">IF <b>${escapeHtml(r.if_concept)}</b> THEN <b>${escapeHtml(r.then_concept)}</b></span>
        <button class="card-del" data-id="${r.id}" title="Delete">✕</button>
      `;
      row.querySelector(".card-del").addEventListener("click", async () => {
        await api(`/api/rules/${r.id}`, { method: "DELETE" });
        loadRules();
        refreshStats();
      });
      list.appendChild(row);
    });
  }

  $("#ruleSearch").addEventListener("input", e => {
    const q = e.target.value.toLowerCase();
    renderRules(allRules.filter(r =>
      r.name.toLowerCase().includes(q) || r.if_concept.includes(q) || r.then_concept.includes(q)
    ));
  });

  $("#addRuleBtn").addEventListener("click", () => {
    $("#addRuleForm").hidden = !$("#addRuleForm").hidden;
  });

  $("#addRuleForm").addEventListener("submit", async e => {
    e.preventDefault();
    try {
      await api("/api/rules", {
        method: "POST",
        body: JSON.stringify({
          name: $("#ruleName").value,
          if_concept: $("#ruleIf").value,
          then_concept: $("#ruleThen").value,
          description: $("#ruleDesc").value,
        }),
      });
      e.target.reset();
      e.target.hidden = true;
      loadRules();
      refreshStats();
    } catch (err) {
      alert(err.message);
    }
  });

  // ---------------------------------------------------------------
  // History panel
  // ---------------------------------------------------------------
  async function loadHistory(q) {
    const data = await api(q ? `/api/history?q=${encodeURIComponent(q)}` : "/api/history");
    const list = $("#historyList");
    list.innerHTML = "";
    data.history.forEach(row => {
      const el = document.createElement("div");
      el.className = "history-row";
      el.innerHTML = `
        <span class="history-sender">${escapeHtml(row.sender)}</span>
        <span>${escapeHtml(row.message)}</span>
        <span class="history-time">${escapeHtml(row.timestamp)}</span>
      `;
      list.appendChild(el);
    });
  }

  $("#historySearch").addEventListener("input", e => loadHistory(e.target.value));
  $("#clearHistBtn").addEventListener("click", async () => {
    if (!confirm("Clear the entire conversation history? This can't be undone.")) return;
    await api("/api/history", { method: "DELETE" });
    loadHistory();
  });
  $("#exportBtn").addEventListener("click", async () => {
    const data = await api("/api/history");
    const text = data.history.map(r => `[${r.timestamp}] ${r.sender}: ${r.message}`).join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "smartruleai-history.txt";
    a.click();
  });

  // ---------------------------------------------------------------
  // Security checklist tool
  // ---------------------------------------------------------------
  const CHECKLIST_ITEMS = [
    { id: "password", q: "Do you use a strong, unique password on your main accounts?", yes: "strong_password", no: "weak_password" },
    { id: "twofactor", q: "Is two-factor authentication turned on?", yes: "two_factor_enabled", no: null },
    { id: "updates", q: "Do you keep your software and OS up to date?", yes: "software_updated", no: "outdated_software" },
    { id: "antivirus", q: "Do you run antivirus / endpoint protection?", yes: "antivirus_installed", no: null },
    { id: "wifi", q: "Do you avoid unprotected public Wi-Fi (or always use a VPN on it)?", yes: "vpn_used", no: "public_wifi_used" },
    { id: "backups", q: "Do you take regular backups of your important files?", yes: "regular_backups", no: "no_backups" },
    { id: "manager", q: "Do you use a password manager?", yes: "password_manager_used", no: null },
    { id: "training", q: "Could you confidently spot a phishing email?", yes: "security_awareness_training", no: null },
  ];

  const checklistAnswers = {};

  function renderChecklist() {
    const form = $("#checklistForm");
    form.innerHTML = "";
    CHECKLIST_ITEMS.forEach(item => {
      const row = document.createElement("div");
      row.className = "checklist-item";
      row.innerHTML = `
        <span class="checklist-q">${escapeHtml(item.q)}</span>
        <span class="checklist-toggle">
          <button type="button" data-val="yes">Yes</button>
          <button type="button" data-val="no">No</button>
        </span>
      `;
      const [yesBtn, noBtn] = row.querySelectorAll("button");
      yesBtn.addEventListener("click", () => {
        checklistAnswers[item.id] = item.yes;
        yesBtn.classList.add("selected-yes");
        noBtn.classList.remove("selected-no");
      });
      noBtn.addEventListener("click", () => {
        checklistAnswers[item.id] = item.no;
        noBtn.classList.add("selected-no");
        yesBtn.classList.remove("selected-yes");
      });
      form.appendChild(row);
    });
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "checklist-submit";
    submit.textContent = "Score my security";
    form.appendChild(submit);
  }
  renderChecklist();

  $("#checklistForm").addEventListener("submit", async e => {
    e.preventDefault();
    const answers = {};
    Object.keys(checklistAnswers).forEach(k => {
      if (checklistAnswers[k]) answers[k] = checklistAnswers[k];
    });
    if (!Object.keys(answers).length) {
      alert("Answer at least one question first.");
      return;
    }
    try {
      const data = await api("/api/checklist", {
        method: "POST",
        body: JSON.stringify({ answers }),
      });
      renderChecklistResult(data);
      renderTrace(data.trace);
      refreshStats();
    } catch (err) {
      alert(err.message);
    }
  });

  function renderChecklistResult(data) {
    const box = $("#checklistResult");
    box.hidden = false;
    const recoHtml = data.recommendations.length
      ? `<div class="reco-title">Where to focus first</div>` +
        data.recommendations.map(r => `<div class="reco-item">${escapeHtml(r.statement)}</div>`).join("")
      : `<div class="reco-title">No risk concepts were triggered — nice work.</div>`;
    box.innerHTML = `
      <div class="score-row">
        <div class="score-num">${data.score}%</div>
        <div>
          <div class="score-rating">${escapeHtml(data.rating)}</div>
          <div class="score-sub">${data.good_count} protective factor(s) vs ${data.risk_count} risk factor(s) reasoned about</div>
        </div>
      </div>
      ${recoHtml}
    `;
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------
  loadGreeting();
})();
