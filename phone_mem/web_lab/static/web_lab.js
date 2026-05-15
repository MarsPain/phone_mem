const json = (value) => JSON.stringify(value, null, 2);

const requestJson = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  const payload = await response.json();
  if (!response.ok && payload.error) {
    return payload;
  }
  return payload;
};

const setOutput = (id, value) => {
  document.getElementById(id).textContent = json(value);
};

let currentUser = null;

const updateAuthUI = () => {
  const loginForm = document.getElementById("login-form");
  const userInfo = document.getElementById("user-info");
  const userName = document.getElementById("user-name");
  if (currentUser) {
    loginForm.hidden = true;
    userInfo.hidden = false;
    userName.textContent = currentUser;
  } else {
    loginForm.hidden = false;
    userInfo.hidden = true;
    userName.textContent = "";
  }
};

const checkAuth = async () => {
  const payload = await requestJson("/api/me");
  if (payload.authenticated) {
    currentUser = payload.username;
  } else {
    currentUser = null;
  }
  updateAuthUI();
  return currentUser;
};

const login = async (username) => {
  const payload = await requestJson("/api/login", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
  if (payload.ok) {
    currentUser = username;
    updateAuthUI();
    clearChatLog();
    await refreshMemory();
    await refreshPhoneState();
    await refreshDebugger();
    addMessage("System", `Logged in as ${username}. Your memory is isolated.`, "system");
  } else {
    addMessage("Error", payload.error?.message || "Login failed", "error");
  }
};

const logout = async () => {
  await requestJson("/api/logout", { method: "POST" });
  currentUser = null;
  updateAuthUI();
  clearChatLog();
  addMessage("System", "Logged out. Please login to continue.", "system");
};

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("login-username");
  const username = input.value.trim();
  if (!username) return;
  input.value = "";
  await login(username);
});

document.getElementById("logout-btn").addEventListener("click", logout);

const refreshMemory = async () => {
  if (!currentUser) {
    setOutput("memory-output", { message: "Please login first." });
    return;
  }
  setOutput("memory-output", await requestJson("/api/memories"));
};

const refreshPhoneState = async () => {
  if (!currentUser) {
    setOutput("phone-state-output", { message: "Please login first." });
    return;
  }
  setOutput("phone-state-output", await requestJson("/api/phone-state"));
};

const latestTurn = (turnsPayload) => {
  const turns = turnsPayload.turns || [];
  return turns.length ? turns[turns.length - 1] : null;
};

const capturePayload = (turnsPayload, auditPayload) => {
  const turns = turnsPayload.turns || [];
  const latestCaptureTurn = [...turns].reverse().find((turn) => (turn.captured_event_ids || []).length);
  return {
    latest_captured_event_ids: latestCaptureTurn ? latestCaptureTurn.captured_event_ids : [],
    latest_capture_turn: latestCaptureTurn,
    audit_records: (auditPayload.audit_records || []).filter((record) =>
      (latestCaptureTurn?.captured_event_ids || []).some((eventId) =>
        (record.affected_event_ids || []).includes(eventId),
      ),
    ),
  };
};

const contextPayload = (turnsPayload) => {
  const turn = latestTurn(turnsPayload);
  const context = turn?.memory_context || null;
  return {
    latest_turn_index: turn?.index || null,
    evidence_event_ids: context?.evidence_event_ids || [],
    hot_memory_capsules: context?.hot_memory_capsules || [],
    omitted_memory: context?.omitted_memory || [],
    relation_paths: context?.relation_paths || [],
    safety_metadata: context?.safety_metadata || {},
    token_budget: context?.token_budget || {},
  };
};

const maintenancePayload = async () => ({
  reflect: await requestJson("/api/maintenance/reflect"),
  defrag: await requestJson("/api/maintenance/defrag"),
  schema_diff: await requestJson("/api/maintenance/schema-diff"),
});

const refreshDebugger = async () => {
  if (!currentUser) {
    const msg = { message: "Please login first." };
    setOutput("debug-panel-turns", msg);
    setOutput("debug-panel-capture", msg);
    setOutput("debug-panel-context", msg);
    setOutput("debug-panel-audit", msg);
    setOutput("debug-panel-metrics", msg);
    setOutput("debug-panel-maintenance", msg);
    return;
  }
  const turns = await requestJson("/api/turns");
  const audit = await requestJson("/api/audit");
  setOutput("debug-panel-turns", turns);
  setOutput("debug-panel-capture", capturePayload(turns, audit));
  setOutput("debug-panel-context", contextPayload(turns));
  setOutput("debug-panel-audit", audit);
  setOutput("debug-panel-metrics", await requestJson("/api/metrics"));
  setOutput("debug-panel-maintenance", await maintenancePayload());
};

const selectDebuggerTab = (selectedTab) => {
  document.querySelectorAll("[data-debug-tab]").forEach((tab) => {
    const isSelected = tab.dataset.debugTab === selectedTab;
    tab.classList.toggle("active", isSelected);
    tab.setAttribute("aria-selected", String(isSelected));
  });
  document.querySelectorAll(".debug-panel").forEach((panel) => {
    const isSelected = panel.id === `debug-panel-${selectedTab}`;
    panel.classList.toggle("active", isSelected);
    panel.hidden = !isSelected;
  });
};

const toggleDebuggerHelp = () => {
  const help = document.getElementById("debug-help");
  const toggle = document.getElementById("debug-help-toggle");
  const isExpanded = toggle.getAttribute("aria-expanded") === "true";
  help.hidden = isExpanded;
  toggle.setAttribute("aria-expanded", String(!isExpanded));
};

const addMessage = (role, text, className = "") => {
  const log = document.getElementById("chat-log");
  const node = document.createElement("div");
  node.className = `message ${className}`;
  const label = document.createElement("b");
  label.textContent = role;
  const body = document.createElement("div");
  body.textContent = text;
  node.append(label, body);
  log.append(node);
  log.scrollTop = log.scrollHeight;
};

const clearChatLog = () => {
  document.getElementById("chat-log").replaceChildren();
};

const refreshChat = async () => {
  if (!currentUser) {
    addMessage("Error", "Please login first.", "error");
    return;
  }
  const payload = await requestJson("/api/chat/refresh", { method: "POST" });
  if (payload.ok === false) {
    addMessage("Error", payload.error.message, "error");
    return;
  }
  clearChatLog();
  await refreshDebugger();
};

document.getElementById("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentUser) {
    addMessage("Error", "Please login first.", "error");
    return;
  }
  const input = document.getElementById("chat-message");
  const message = input.value.trim();
  if (!message) return;
  addMessage("User", message);
  input.value = "";
  const payload = await requestJson("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  if (payload.ok === false) {
    addMessage("Error", payload.error.message, "error");
  } else {
    addMessage("Assistant", payload.text);
  }
  await refreshMemory();
  await refreshDebugger();
});

document.getElementById("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentUser) {
    setOutput("memory-output", { message: "Please login first." });
    return;
  }
  const query = document.getElementById("search-query").value.trim();
  if (query) setOutput("memory-output", await requestJson(`/api/search?query=${encodeURIComponent(query)}`));
});

document.getElementById("preview-context").addEventListener("click", async () => {
  if (!currentUser) {
    setOutput("memory-output", { message: "Please login first." });
    return;
  }
  const query = document.getElementById("search-query").value.trim();
  if (query) setOutput("memory-output", await requestJson(`/api/context?query=${encodeURIComponent(query)}`));
});

document.getElementById("refresh-maintenance").addEventListener("click", async () => {
  if (!currentUser) {
    setOutput("memory-output", { message: "Please login first." });
    return;
  }
  const payload = await maintenancePayload();
  setOutput("memory-output", payload);
  setOutput("debug-panel-maintenance", payload);
});

document.querySelectorAll("[data-maintenance-report]").forEach((button) => {
  button.addEventListener("click", async () => {
    if (!currentUser) {
      setOutput("memory-output", { message: "Please login first." });
      return;
    }
    const report = button.dataset.maintenanceReport;
    const path = report === "schema-diff" ? "schema-diff" : report;
    setOutput("memory-output", await requestJson(`/api/maintenance/${path}`));
  });
});

document.getElementById("explain-event").addEventListener("click", async () => {
  if (!currentUser) {
    setOutput("memory-output", { message: "Please login first." });
    return;
  }
  const eventId = document.getElementById("event-id").value.trim();
  if (eventId) setOutput("memory-output", await requestJson(`/api/explain/${encodeURIComponent(eventId)}`));
});

document.getElementById("correct-event").addEventListener("click", async () => {
  if (!currentUser) {
    setOutput("memory-output", { message: "Please login first." });
    return;
  }
  const eventId = document.getElementById("event-id").value.trim();
  const replacementText = document.getElementById("replacement-text").value.trim();
  if (!eventId || !replacementText) return;
  const payload = await requestJson(`/api/correct/${encodeURIComponent(eventId)}`, {
    method: "POST",
    body: JSON.stringify({ replacement_text: replacementText }),
  });
  setOutput("memory-output", payload);
  await refreshMemory();
  await refreshDebugger();
});

document.getElementById("delete-event").addEventListener("click", async () => {
  if (!currentUser) {
    setOutput("memory-output", { message: "Please login first." });
    return;
  }
  const eventId = document.getElementById("event-id").value.trim();
  const reason = document.getElementById("delete-reason").value.trim();
  if (!eventId || !reason) return;
  const payload = await requestJson(`/api/delete/${encodeURIComponent(eventId)}`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
  setOutput("memory-output", payload);
  await refreshMemory();
  await refreshDebugger();
});

document.getElementById("refresh-memory").addEventListener("click", refreshMemory);
document.getElementById("refresh-phone-state").addEventListener("click", refreshPhoneState);
document.getElementById("refresh-debugger").addEventListener("click", refreshDebugger);
document.getElementById("refresh-chat").addEventListener("click", refreshChat);
document.getElementById("debug-help-toggle").addEventListener("click", toggleDebuggerHelp);
document.querySelectorAll("[data-debug-tab]").forEach((tab) => {
  tab.addEventListener("click", () => selectDebuggerTab(tab.dataset.debugTab));
});

(async () => {
  await checkAuth();
  if (currentUser) {
    refreshMemory();
    refreshPhoneState();
    refreshDebugger();
  } else {
    addMessage("System", "Welcome! Please enter a username to login. First login auto-registers.", "system");
  }
})();
