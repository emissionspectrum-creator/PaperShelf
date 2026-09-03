const GRADES = ["國小一年級", "國小二年級", "國小三年級", "國小四年級", "國小五年級", "國小六年級"];
const SUBJECTS = ["國文", "數學"];

let images = [];
let manifest = { exams: [] };
let queue = []; // [{ path, dataUrl, scale }]

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function imageUrl(path) {
  return "/api/image/" + path.split("/").map(encodeURIComponent).join("/");
}

async function init() {
  const [imgRes, manRes] = await Promise.all([
    fetch("/api/images").then((r) => r.json()),
    fetch("/api/manifest").then((r) => r.json()),
  ]);
  images = imgRes.images;
  manifest = manRes;

  populateGradeSubject();
  renderImageList();
  renderExamList();
  updatePreview();
}

function populateGradeSubject() {
  const gradeSel = document.getElementById("grade");
  const subjectSel = document.getElementById("subject");
  GRADES.forEach((g) => {
    const o = document.createElement("option");
    o.value = g;
    o.textContent = g;
    gradeSel.appendChild(o);
  });
  SUBJECTS.forEach((s) => {
    const o = document.createElement("option");
    o.value = s;
    o.textContent = s;
    subjectSel.appendChild(o);
  });
  gradeSel.addEventListener("change", () => {
    suggestSeq();
    updatePreview();
  });
  subjectSel.addEventListener("change", () => {
    suggestSeq();
    updatePreview();
  });
  suggestSeq();
}

function suggestSeq() {
  const grade = document.getElementById("grade").value;
  const subject = document.getElementById("subject").value;
  const existing = manifest.exams
    .filter((e) => e.grade === grade && e.subject === subject)
    .map((e) => e.seq);
  document.getElementById("seq").value = existing.length ? Math.max(...existing) + 1 : 1;
}

function renderImageList() {
  const el = document.getElementById("image-list");
  el.innerHTML = "";
  images.forEach((path) => {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.textContent = path;
    const btn = document.createElement("button");
    btn.textContent = "加入";
    btn.onclick = () => addToQueue(path);
    li.append(span, btn);
    el.appendChild(li);
  });
}

async function addToQueue(path) {
  const res = await fetch(imageUrl(path));
  if (!res.ok) {
    alert("讀取圖片失敗：" + path);
    return;
  }
  const blob = await res.blob();
  const dataUrl = await blobToDataUrl(blob);
  queue.push({ path, dataUrl, scale: 100 });
  renderQueue();
  updatePreview();
}

function moveItem(i, delta) {
  const j = i + delta;
  if (j < 0 || j >= queue.length) return;
  [queue[i], queue[j]] = [queue[j], queue[i]];
  renderQueue();
  updatePreview();
}

function renderQueue() {
  const el = document.getElementById("queue-list");
  el.innerHTML = "";
  queue.forEach((q, i) => {
    const li = document.createElement("li");
    li.className = "queue-item";

    const label = document.createElement("div");
    label.className = "queue-item-path";
    label.textContent = `${i + 1}. ${q.path}`;
    li.appendChild(label);

    const controls = document.createElement("div");
    controls.className = "queue-item-controls";

    const up = document.createElement("button");
    up.textContent = "↑";
    up.disabled = i === 0;
    up.onclick = () => moveItem(i, -1);

    const down = document.createElement("button");
    down.textContent = "↓";
    down.disabled = i === queue.length - 1;
    down.onclick = () => moveItem(i, 1);

    const remove = document.createElement("button");
    remove.textContent = "移除";
    remove.onclick = () => {
      queue.splice(i, 1);
      renderQueue();
      updatePreview();
    };

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = 40;
    slider.max = 150;
    slider.value = q.scale;

    const scaleLabel = document.createElement("span");
    scaleLabel.textContent = q.scale + "%";

    slider.oninput = () => {
      q.scale = Number(slider.value);
      scaleLabel.textContent = q.scale + "%";
      updatePreview();
    };

    controls.append(up, down, remove, slider, scaleLabel);
    li.appendChild(controls);
    el.appendChild(li);
  });
}

function currentExamHtml() {
  const grade = document.getElementById("grade").value;
  const subject = document.getElementById("subject").value;
  return buildExamHtml({
    grade,
    subject,
    questions: queue.map((q) => ({ dataUrl: q.dataUrl, scale: q.scale })),
  });
}

function updatePreview() {
  document.getElementById("preview").srcdoc = currentExamHtml();
}

function renderExamList() {
  const el = document.getElementById("exam-list");
  el.innerHTML = "";
  manifest.exams
    .slice()
    .sort((a, b) => b.addedAt.localeCompare(a.addedAt))
    .forEach((e) => {
      const li = document.createElement("li");
      const span = document.createElement("span");
      span.textContent = `${e.grade} ${e.subject}${e.scope ? " · " + e.scope : ""}`;
      const del = document.createElement("button");
      del.textContent = "刪除";
      del.onclick = () => deleteExam(e.id);
      li.append(span, del);
      el.appendChild(li);
    });
}

async function deleteExam(id) {
  if (!confirm("確定刪除「" + id + "」？")) return;
  const res = await fetch("/api/manifest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "delete", id }),
  });
  const data = await res.json();
  if (!data.ok) {
    alert("刪除失敗");
    return;
  }
  manifest = data.manifest;
  await fetch("/api/index", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  renderExamList();
  suggestSeq();
}

async function save() {
  const grade = document.getElementById("grade").value;
  const subject = document.getElementById("subject").value;
  const seq = Number(document.getElementById("seq").value);
  const scope = document.getElementById("scope").value.trim();

  if (!grade || !subject || !seq || queue.length === 0) {
    alert("請選擇年級、科目、序號，並至少加入一題");
    return;
  }

  const id = `${grade}-${subject}-${String(seq).padStart(3, "0")}`;
  const html = currentExamHtml();

  const examRes = await fetch("/api/exam", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, html }),
  });
  if (!examRes.ok) {
    alert("存檔失敗：" + (await examRes.text()));
    return;
  }

  const manRes = await fetch("/api/manifest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "add", id, grade, subject, seq, scope }),
  });
  const manData = await manRes.json();
  if (!manData.ok) {
    alert("清單更新失敗：" + JSON.stringify(manData));
    return;
  }
  manifest = manData.manifest;

  await fetch("/api/index", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });

  renderExamList();
  suggestSeq();
  alert("已儲存：" + id);
}

async function publish() {
  const res = await fetch("/api/publish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: "更新考卷" }),
  });
  const data = await res.json();
  if (!data.ok) {
    alert("發布失敗（" + data.stage + "）：\n" + data.output);
    return;
  }
  alert("已發布：\n" + data.output);
}

document.getElementById("save-btn").addEventListener("click", save);
document.getElementById("publish-btn").addEventListener("click", publish);

init();
