const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const $ = (id) => document.getElementById(id);

async function api(path, { method = "GET", body } = {}) {
  const initData = (tg && tg.initData) || "";
  let url = path;
  const options = { method, headers: {} };

  if (method === "GET") {
    const sep = path.includes("?") ? "&" : "?";
    url += `${sep}initData=${encodeURIComponent(initData)}`;
  } else if (body instanceof FormData) {
    body.set("initData", initData);
    options.body = body;
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

function mediaLabel(kind) {
  return { photo: "[фото] ", animation: "[gif] ", video: "[видео] ", album: "[альбом] " }[kind] || "";
}

async function loadHistory() {
  const data = await api("/api/broadcasts");
  if (!data.ok) return;
  const list = $("history-list");
  list.innerHTML = "";
  for (const b of data.broadcasts) {
    const li = document.createElement("li");
    const preview = b.text.length > 60 ? b.text.slice(0, 60) + "…" : b.text;
    const excl = b.excluded_count ? ` · искл. ${b.excluded_count}` : "";
    li.textContent = `${statusLabel(b.status)} · ${b.sent}/${b.total}${excl} · ${mediaLabel(b.media_kind)}${preview}`;
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

// --- Форматирование текста (Telegram HTML): тулбар вставляет теги вокруг
// выделения, а перед отправкой всё, что не является нашим тегом, экранируется —
// так литеральные <, >, & в тексте админа не ломают разметку.
const ALLOWED_TAGS = ["b", "i", "u", "s", "tg-spoiler", "code"];
const SPLIT_RE = new RegExp(`(</?(?:${ALLOWED_TAGS.join("|")})>)`, "g");
const TAG_TEST_RE = new RegExp(`^</?(?:${ALLOWED_TAGS.join("|")})>$`);

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function toTelegramHtml(raw) {
  return raw
    .split(SPLIT_RE)
    .map((part) => (TAG_TEST_RE.test(part) ? part : escapeHtml(part)))
    .join("");
}

function wrapSelection(tag) {
  const el = $("text");
  const start = el.selectionStart;
  const end = el.selectionEnd;
  const value = el.value;
  const selected = value.slice(start, end);
  const before = `<${tag}>`;
  const after = `</${tag}>`;
  el.value = value.slice(0, start) + before + selected + after + value.slice(end);
  el.focus();
  el.selectionStart = start + before.length;
  el.selectionEnd = start + before.length + selected.length;
}

document.querySelectorAll("#toolbar button").forEach((btn) => {
  btn.addEventListener("click", () => wrapSelection(btn.dataset.tag));
});

// --- Медиа: фото/гифка/видео, один файл или альбом (2-10 фото/видео) ---
let selectedFiles = [];
const MAX_FILE_SIZE = 45 * 1024 * 1024;

function classifyFile(file) {
  if (file.type === "image/gif" || /\.gif$/i.test(file.name)) return "animation";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("image/")) return "photo";
  return null;
}

function updateMediaUI() {
  const container = $("media-preview");
  container.innerHTML = "";
  selectedFiles.forEach((file, idx) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    if (file.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      chip.appendChild(img);
    } else {
      const icon = document.createElement("span");
      icon.className = "chip-icon";
      icon.textContent = "🎬";
      chip.appendChild(icon);
    }
    const name = document.createElement("span");
    name.className = "chip-name";
    name.textContent = file.name;
    chip.appendChild(name);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "chip-remove";
    remove.textContent = "✕";
    remove.addEventListener("click", () => {
      selectedFiles.splice(idx, 1);
      updateMediaUI();
    });
    chip.appendChild(remove);
    container.appendChild(chip);
  });

  const isGroup = selectedFiles.length >= 2;
  $("media-hint").classList.toggle("hidden", !isGroup);
  $("button_text").disabled = isGroup;
  $("button_url").disabled = isGroup;
  if (isGroup) {
    $("button_text").value = "";
    $("button_url").value = "";
  }
}

$("media").addEventListener("change", (e) => {
  const picked = Array.from(e.target.files || []);
  e.target.value = "";

  const tooBig = picked.filter((f) => f.size > MAX_FILE_SIZE);
  if (tooBig.length) {
    alert("Слишком большой файл (>45MB): " + tooBig.map((f) => f.name).join(", "));
  }
  const unsupported = picked.filter((f) => !tooBig.includes(f) && !classifyFile(f));
  if (unsupported.length) {
    alert("Неподдерживаемый формат: " + unsupported.map((f) => f.name).join(", "));
  }

  const ok = picked.filter((f) => !tooBig.includes(f) && !unsupported.includes(f));
  selectedFiles = selectedFiles.concat(ok).slice(0, 10);
  updateMediaUI();
});

// --- Получатели: список с чекбоксами исключения и поиском ---
let allUsers = [];
const excludedIds = new Set();

function userLabel(u) {
  const name = [u.first_name, u.last_name].filter(Boolean).join(" ") || "Без имени";
  return u.username ? `${name} (@${u.username})` : name;
}

function updateUsersCount() {
  $("users-count").textContent = `${allUsers.length - excludedIds.size} из ${allUsers.length}`;
}

function renderUsers() {
  const filter = $("users-filter").value.trim().toLowerCase();
  const list = $("users-list");
  list.innerHTML = "";
  for (const u of allUsers) {
    const label = userLabel(u);
    if (filter && !label.toLowerCase().includes(filter)) continue;
    const row = document.createElement("label");
    row.className = "user-row";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = excludedIds.has(u.telegram_id);
    cb.addEventListener("change", () => {
      if (cb.checked) excludedIds.add(u.telegram_id);
      else excludedIds.delete(u.telegram_id);
      updateUsersCount();
    });
    row.appendChild(cb);
    const span = document.createElement("span");
    span.textContent = label;
    row.appendChild(span);
    list.appendChild(row);
  }
}

$("users-filter").addEventListener("input", renderUsers);

async function loadUsers() {
  const data = await api("/api/users");
  if (!data.ok) return;
  allUsers = data.users;
  renderUsers();
  updateUsersCount();
}

// --- Отправка ---
$("broadcast-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = toTelegramHtml($("text").value);

  if (!text.trim() && selectedFiles.length === 0) {
    alert("Добавьте текст или медиа.");
    return;
  }

  const isGroup = selectedFiles.length >= 2;
  const button_text = isGroup ? "" : $("button_text").value.trim();
  const button_url = isGroup ? "" : $("button_url").value.trim();

  const formData = new FormData();
  formData.set("text", text);
  if (button_text) formData.set("button_text", button_text);
  if (button_url) formData.set("button_url", button_url);
  if (excludedIds.size) formData.set("exclude_ids", JSON.stringify([...excludedIds]));
  for (const file of selectedFiles) formData.append("files", file);

  $("send-btn").disabled = true;
  $("progress").classList.remove("hidden");
  $("bar-fill").style.width = "0%";
  $("progress-text").textContent = "Запуск рассылки…";

  const data = await api("/api/broadcast", { method: "POST", body: formData });

  if (!data.ok) {
    $("progress-text").textContent = "Ошибка: " + (data.error || "не удалось отправить");
    $("send-btn").disabled = false;
    return;
  }

  $("text").value = "";
  $("button_text").value = "";
  $("button_url").value = "";
  selectedFiles = [];
  updateMediaUI();
  pollBroadcast(data.broadcast_id);
});

(async function init() {
  if (!tg || !tg.initData) {
    showDenied();
    return;
  }
  const auth = await api("/api/auth", { method: "POST", body: {} });
  if (!auth.ok) {
    showDenied();
    return;
  }
  showPanel();
  await loadStats();
  await loadHistory();
  await loadUsers();
})();
