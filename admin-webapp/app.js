const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const $ = (id) => document.getElementById(id);

async function api(path, { method = "GET", body } = {}) {
  const initData = (tg && tg.initData) || "";
  let url = `${API_BASE_URL}${path}`;
  const options = { method, headers: {} };

  if (method === "GET") {
    const sep = path.includes("?") ? "&" : "?";
    url += `${sep}initData=${encodeURIComponent(initData)}`;
  } else {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify({ ...body, initData });
  }

  const res = await fetch(url, options);
  return res.json();
}

function showPanel() {
  $("loading").classList.add("hidden");
  $("panel").classList.remove("hidden");
}

function showDenied() {
  $("loading").classList.add("hidden");
  $("denied").classList.remove("hidden");
}

async function loadStats() {
  const data = await api("/api/stats");
  if (data.ok) {
    $("stats").textContent = `Получателей: ${data.total_users}`;
  }
}

function statusLabel(status) {
  return { pending: "в очереди", running: "идёт", done: "готово", failed: "ошибка" }[status] || status;
}

async function loadHistory() {
  const data = await api("/api/broadcasts");
  if (!data.ok) return;
  const list = $("history-list");
  list.innerHTML = "";
  for (const b of data.broadcasts) {
    const li = document.createElement("li");
    const preview = b.text.length > 60 ? b.text.slice(0, 60) + "…" : b.text;
    li.textContent = `${statusLabel(b.status)} · ${b.sent}/${b.total} · ${preview}`;
    list.appendChild(li);
  }
}

async function pollBroadcast(id) {
  const data = await api(`/api/broadcast/${id}`);
  if (!data.ok) return;
  const b = data.broadcast;
  const pct = b.total ? Math.round(((b.sent + b.failed) / b.total) * 100) : 100;
  $("bar-fill").style.width = `${pct}%`;
  $("progress-text").textContent = `Отправлено: ${b.sent} · Ошибок: ${b.failed} · Всего: ${b.total}`;

  if (b.status === "done" || b.status === "failed") {
    $("send-btn").disabled = false;
    await loadStats();
    await loadHistory();
    return;
  }
  setTimeout(() => pollBroadcast(id), 1500);
}

$("broadcast-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("text").value.trim();
  if (!text) return;

  const button_text = $("button_text").value.trim() || undefined;
  const button_url = $("button_url").value.trim() || undefined;

  $("send-btn").disabled = true;
  $("progress").classList.remove("hidden");
  $("bar-fill").style.width = "0%";
  $("progress-text").textContent = "Запуск рассылки…";

  const data = await api("/api/broadcast", { method: "POST", body: { text, button_text, button_url } });

  if (!data.ok) {
    $("progress-text").textContent = "Ошибка: " + (data.error || "не удалось отправить");
    $("send-btn").disabled = false;
    return;
  }

  $("text").value = "";
  $("button_text").value = "";
  $("button_url").value = "";
  pollBroadcast(data.broadcast_id);
});

(async function init() {
  if (!tg || !tg.initData) {
    showDenied();
    return;
  }
  const auth = await api("/api/auth");
  if (!auth.ok) {
    showDenied();
    return;
  }
  showPanel();
  await loadStats();
  await loadHistory();
})();
