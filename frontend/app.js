/* Al Basmah AI Media Studio - frontend (vanilla JS, no build step) */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

// ------------------------------------------------------------------ i18n
const EN = {
  brand: "Al Basmah", brand_sub: "AI media studio - Al Basmah Real Estate",
  tab_photo: "Photo Editor", tab_video: "Video Editor", tab_brand: "Property & Brand", tab_library: "Library",
  drop_photos: "Drag & drop photos here or tap to choose", originals_safe: "Original files are stored as-is and never modified",
  your_photos: "Your photos", select_all: "Select all", select_none: "Select none", pick_photo: "Choose a photo to start editing",
  grp_light: "Light", grp_color: "Colour", grp_detail: "Detail & noise", grp_geo: "Angle & perspective",
  auto_wb: "Auto white balance", auto_levels: "Auto levels", grp_remove: "Remove unwanted objects",
  remove_help: "Paint over a small object to remove (sign, cable, stain). Do not use it to hide real defects of the property.",
  brush_on: "Enable brush", brush_off: "Disable brush", clear_mask: "Clear selection", brush_size: "Brush size",
  grp_brand: "Logo, watermark & property card", add_logo: "Add logo", pos_br: "Bottom right", pos_bl: "Bottom left",
  pos_tr: "Top right", pos_tl: "Top left", pos_c: "Center", size: "Size", opacity: "Opacity",
  wm_text: "Watermark text (optional)", add_card: "Add property card (specs, price, phone, logo)",
  grp_output: "Export", format: "Size", f_original: "Original size", f_web: "Property portals (2048)", fit: "Fit",
  fit_blur: "Whole property + blurred background", fit_black: "Whole property + black background", fit_crop: "Crop to fill",
  filetype: "File type", reset: "Reset", preview: "Preview", export_one: "Export photo",
  auto_each: "Auto-analyse each photo in the batch", export_batch: "Export selected photos as a batch",
  drop_videos: "Drag & drop videos or music here or tap to choose", media_bin: "Video files", timeline: "Sequence (order & trim)",
  timeline_empty: "Add clips from the list above", set_in: "Clip starts here", set_out: "Clip ends here",
  grp_grade: "Colour grading", grp_fix: "Stabilisation & audio", stabilize: "Stabilise camera shake",
  keep_audio: "Keep the video's audio", denoise_audio: "Remove audio noise & enhance", letterbox: "Cinematic bars (2.39:1)",
  grp_music: "Music & transitions", music: "Music", music_vol: "Music level", transition: "Transition", trans_dur: "Duration (s)",
  none: "None", grp_texts: "Titles (Arabic / English)", add_text: "+ Add title", card_from: "Card appears at second",
  card_lang: "Card language", end_card: "End card (logo + price + contact)", preset: "Platform & quality",
  preview_fast: "Quick preview", export_video: "Export video", identity: "Identity", no_logo: "No logo uploaded",
  upload_logo: "Upload logo (transparent PNG preferred)", company_ar: "Company name (Arabic)", company_en: "Company name (English)",
  phone: "Contact number", website: "Website", property: "Property details",
  property_note: "Details are printed exactly as entered. The system never changes the property's real features.",
  title_ar: "Title (Arabic)", title_en: "Title (English)", price: "Price", currency: "Currency", beds: "Bedrooms", baths: "Bathrooms",
  area: "Area", unit: "Unit", loc_ar: "Location (Arabic)", loc_en: "Location (English)", extra_ar: "Extra feature (Arabic)",
  extra_en: "Extra feature (English)", save: "Save", saved: "Saved ✓", exports: "Exported files", refresh: "Refresh",
  originals: "Original files (kept unmodified)",
  // dynamic
  st_auto: "AI Auto", st_natural: "Natural", st_real_estate: "Real Estate", st_luxury: "Luxury", st_cinematic: "Cinematic", st_night: "Night Mode",
  exposure: "Exposure", contrast: "Contrast", highlights: "Highlights", shadows: "Shadows", clarity: "Clarity",
  saturation: "Saturation", vibrance: "Vibrance", warmth: "Warmth", tint: "Tint", teal_orange: "Cinematic teal/orange",
  golden: "Golden highlights", sharpen: "Sharpen", denoise: "Noise reduction", vignette: "Vignette",
  rotate: "Straighten (°)", perspective_v: "Vertical perspective", brightness: "Brightness", gamma: "Gamma (mid-tones)",
  analysing: "Analysing…", analysis_title: "AI analysis", chosen_style: "Chosen style", uploading: "Uploading…",
  queued: "Queued", running: "Processing", done: "Done", error: "Error", download: "Download", open: "Open",
  add: "+ Add", remove: "Remove", text_ph: "Title text (Arabic or English)", start: "Start", end: "End",
  pos_top: "Top", pos_center: "Center", pos_bottom: "Bottom", col_white: "White", col_gold: "Gold", box: "Box",
  need_clip: "Add at least one clip to the sequence", need_photo: "Choose a photo first", need_sel: "Select photos first",
  no_music: "No music", orig_kept: "original kept", auto_geo: "Auto straighten", ok_preview: "Drag the slider to compare Before / After",
  mask_hint: "Paint over the object, then press Preview", sec: "s", lines: "lines",
  logout: "Sign out", save_share: "Save to Photos / Share", preparing: "Preparing…",
};
const AR = {
  st_auto: "تلقائي بالذكاء الاصطناعي", st_natural: "طبيعي", st_real_estate: "عقاري", st_luxury: "فاخر", st_cinematic: "سينمائي", st_night: "ليلي",
  exposure: "التعريض", contrast: "التباين", highlights: "المناطق الساطعة", shadows: "الظلال", clarity: "الوضوح",
  saturation: "التشبّع", vibrance: "حيوية الألوان", warmth: "الدفء", tint: "الصبغة", teal_orange: "سينمائي (أزرق/برتقالي)",
  golden: "لمسة ذهبية", sharpen: "الحدّة", denoise: "إزالة التشويش", vignette: "تعتيم الأطراف",
  rotate: "تعديل الميلان (°)", perspective_v: "المنظور العمودي", brightness: "السطوع", gamma: "الدرجات المتوسطة (Gamma)",
  analysing: "جارٍ التحليل…", analysis_title: "تحليل الذكاء الاصطناعي", chosen_style: "النمط المختار", uploading: "جارٍ الرفع…",
  queued: "في الانتظار", running: "جارٍ المعالجة", done: "تم", error: "خطأ", download: "تنزيل", open: "فتح",
  add: "+ إضافة", remove: "حذف", text_ph: "نص العنوان (عربي أو English)", start: "من", end: "إلى",
  pos_top: "أعلى", pos_center: "الوسط", pos_bottom: "أسفل", col_white: "أبيض", col_gold: "ذهبي", box: "خلفية",
  need_clip: "أضف مقطعًا واحدًا على الأقل إلى التسلسل", need_photo: "اختر صورة أولًا", need_sel: "حدّد الصور أولًا",
  no_music: "بدون موسيقى", orig_kept: "الأصل محفوظ", auto_geo: "تصحيح تلقائي", ok_preview: "اسحب على الصورة للمقارنة بين قبل وبعد",
  mask_hint: "ارسم فوق العنصر ثم اضغط معاينة", sec: "ث", lines: "خطوط", brush_off: "إيقاف الفرشاة", saved: "تم الحفظ ✓",
  save_share: "حفظ في الصور / مشاركة", preparing: "جارٍ التجهيز…",
};
let lang = (() => { try { return localStorage.getItem("lang") || "ar"; } catch { return "ar"; } })();
const AR_STATIC = {};
function t(k) { return lang === "en" ? (EN[k] ?? k) : (AR[k] ?? AR_STATIC[k] ?? EN[k] ?? k); }
function applyLang() {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  $$("[data-i18n]").forEach(el => {
    const k = el.dataset.i18n;
    if (!(k in AR_STATIC)) AR_STATIC[k] = el.textContent;
    el.textContent = lang === "en" ? (EN[k] ?? AR_STATIC[k]) : AR_STATIC[k];
  });
  $("#langBtn").textContent = lang === "ar" ? "English" : "العربية";
  buildPhotoControls(); buildVideoControls(); renderTexts(); renderTimeline(); renderMusic(); updateMaskBtn();
}
$("#langBtn").onclick = () => { lang = lang === "ar" ? "en" : "ar"; try { localStorage.setItem("lang", lang); } catch {} applyLang(); };

// ------------------------------------------------------------------ api helpers
async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (r.status === 401) { location.href = "/login.html"; throw new Error("login required"); }
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
}
function upload(files, barEl) {
  return new Promise((resolve, reject) => {
    const fd = new FormData();
    [...files].forEach(f => fd.append("files", f, f.name));
    const x = new XMLHttpRequest();
    x.open("POST", "/api/upload");
    barEl.classList.remove("hidden");
    x.upload.onprogress = e => {
      if (!e.lengthComputable) return;
      const p = Math.round(e.loaded / e.total * 100);
      barEl.firstElementChild.style.width = p + "%";
      barEl.lastElementChild.textContent = `${t("uploading")} ${p}%`;
    };
    x.onload = () => { barEl.classList.add("hidden"); if (x.status === 401) { location.href = "/login.html"; return; } x.status < 300 ? resolve(JSON.parse(x.responseText)) : reject(new Error(x.responseText)); };
    x.onerror = () => { barEl.classList.add("hidden"); reject(new Error("upload failed")); };
    x.send(fd);
  });
}
function dropzone(zone, input, onFiles) {
  input.onchange = () => { if (input.files.length) onFiles(input.files); input.value = ""; };
  ["dragenter", "dragover"].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove("over"); }));
  zone.addEventListener("drop", e => { if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files); });
}
function fmtSize(b) { return b > 1e6 ? (b / 1e6).toFixed(1) + " MB" : Math.round(b / 1e3) + " KB"; }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

// iPhone: save to Photos / share sheet (Web Share API with files)
const canShareFiles = (() => { try { return !!(navigator.canShare && navigator.canShare({ files: [new File([""], "a.jpg", { type: "image/jpeg" })] })); } catch { return false; } })();
function shareBtn(o) {
  if (!canShareFiles || o.kind === "zip") return "";
  return `<button class="ghost sm share-btn" data-url="${o.url}" data-name="${esc(o.name)}">📲 ${t("save_share")}</button>`;
}
document.addEventListener("click", async e => {
  const b = e.target.closest(".share-btn"); if (!b) return;
  const label = b.textContent; b.disabled = true; b.textContent = t("preparing");
  try {
    const blob = await (await fetch(b.dataset.url, { credentials: "same-origin" })).blob();
    const file = new File([blob], b.dataset.name, { type: blob.type || (b.dataset.name.endsWith(".mp4") ? "video/mp4" : "image/jpeg") });
    await navigator.share({ files: [file], title: "Al Basmah" });
  } catch (err) { if (err.name !== "AbortError") alert(err.message); }
  b.disabled = false; b.textContent = label;
});

// job polling + progress UI
function watchJob(job, box, onDone) {
  const render = j => {
    const st = t(j.status === "done" ? "done" : j.status === "error" ? "error" : j.status === "queued" ? "queued" : "running");
    let h = `<div class="row between"><b>${st}</b><span>${Math.round(j.progress)}%</span></div><div class="bar"><div style="width:${j.progress}%"></div></div>`;
    if (j.message && j.status === "running") h += `<div class="muted small">${esc(j.message)}</div>`;
    if (j.error) h += `<div class="err">${esc(j.error)}</div>`;
    box.innerHTML = h;
  };
  render(job);
  const tick = async () => {
    let j;
    try { j = await api(`/api/jobs/${job.id}`); } catch { setTimeout(tick, 1500); return; }
    render(j);
    if (j.status === "done") onDone && onDone(j, box);
    else if (j.status !== "error") setTimeout(tick, 700);
  };
  setTimeout(tick, 500);
}

// ------------------------------------------------------------------ tabs
$$(".tab").forEach(b => b.onclick = () => {
  $$(".tab").forEach(x => x.classList.toggle("active", x === b));
  $$(".tabpane").forEach(p => p.classList.toggle("active", p.id === "tab-" + b.dataset.tab));
  if (b.dataset.tab === "library") loadLibrary();
});

// ================================================================== PHOTO
const STYLES = ["auto", "natural", "real_estate", "luxury", "cinematic", "night"];
const PHOTO_SLIDERS = {
  g_light: [["exposure", -2, 2, .05], ["contrast", -1, 1, .02], ["highlights", -1, 1, .02], ["shadows", -1, 1, .02], ["clarity", -1, 1, .02]],
  g_color: [["saturation", -1, 1, .02], ["vibrance", -1, 1, .02], ["warmth", -1, 1, .02], ["tint", -1, 1, .02], ["teal_orange", 0, 1, .02], ["golden", 0, 1, .02]],
  g_detail: [["sharpen", 0, 1, .02], ["denoise", 0, 1, .02], ["vignette", 0, 1, .02]],
  g_geo: [["rotate", -10, 10, .05], ["perspective_v", -0.2, 0.2, .002]],
};
const ZERO_PHOTO = { exposure: 0, contrast: 0, highlights: 0, shadows: 0, clarity: 0, saturation: 0, vibrance: 0, warmth: 0, tint: 0,
  teal_orange: 0, golden: 0, sharpen: 0, denoise: 0, vignette: 0, rotate: 0, perspective_v: 0, auto_wb: false, auto_levels: false };
const ps = { files: [], active: null, selected: new Set(), style: "auto", params: { ...ZERO_PHOTO }, masks: {}, brush: false, lastPreview: null };

function slider(container, key, min, max, step, obj, onchange) {
  const d = document.createElement("div");
  d.className = "sl";
  const v = obj[key] ?? 0;
  d.innerHTML = `<label><span>${t(key)}</span></label><input type="range" min="${min}" max="${max}" step="${step}" value="${v}"><output>${(+v).toFixed(step < .01 ? 3 : 2)}</output>`;
  const inp = $("input", d), out = $("output", d);
  inp.oninput = () => { obj[key] = +inp.value; out.textContent = (+inp.value).toFixed(step < .01 ? 3 : 2); onchange && onchange(); };
  inp.ondblclick = () => { inp.value = key === "contrast" && obj === vs.params ? 1 : 0; inp.oninput(); };
  container.appendChild(d);
}
function buildPhotoControls() {
  const chips = $("#photoStyles"); chips.innerHTML = "";
  STYLES.forEach(s => {
    const b = document.createElement("button");
    b.className = "chip" + (ps.style === s ? " on" : ""); b.textContent = t("st_" + s);
    b.onclick = () => { ps.style = s; buildPhotoControls(); analyzePhoto(); };
    chips.appendChild(b);
  });
  for (const [gid, list] of Object.entries(PHOTO_SLIDERS)) {
    const g = $("#" + gid); g.innerHTML = "";
    list.forEach(([k, a, b, s]) => slider(g, k, a, b, s, ps.params));
  }
  $("#autoWb").checked = !!ps.params.auto_wb; $("#autoLevels").checked = !!ps.params.auto_levels;
}
$("#autoWb").onchange = e => ps.params.auto_wb = e.target.checked;
$("#autoLevels").onchange = e => ps.params.auto_levels = e.target.checked;

async function loadPhotos() {
  ps.files = await api("/api/files?kind=image");
  renderPhotoGrid();
}
function renderPhotoGrid() {
  const g = $("#photoGrid"); g.innerHTML = "";
  ps.files.forEach(f => {
    const c = document.createElement("div");
    c.className = "card" + (ps.active?.id === f.id ? " active" : "");
    c.innerHTML = `<img loading="lazy" src="/api/files/${f.id}/thumb" alt=""><input type="checkbox" class="sel" ${ps.selected.has(f.id) ? "checked" : ""}>
      ${ps.masks[f.id] ? '<span class="badge">✎</span>' : ""}<div class="nm">${esc(f.name)}${f.width ? ` · ${f.width}×${f.height}` : ""}</div>`;
    $(".sel", c).onclick = e => { e.stopPropagation(); e.target.checked ? ps.selected.add(f.id) : ps.selected.delete(f.id); updateSelCount(); };
    c.onclick = () => selectPhoto(f);
    g.appendChild(c);
  });
  updateSelCount();
}
function updateSelCount() { $("#selCount").textContent = ps.selected.size; }
$("#selAll").onclick = () => { ps.files.forEach(f => ps.selected.add(f.id)); renderPhotoGrid(); };
$("#selNone").onclick = () => { ps.selected.clear(); renderPhotoGrid(); };

function selectPhoto(f) {
  ps.active = f; ps.brush = false; ps.lastPreview = null;
  renderPhotoGrid(); showOriginal(); analyzePhoto();
  if (window.innerWidth < 900) $("#viewer").scrollIntoView({ behavior: "smooth", block: "start" });
}
function showOriginal() {
  const v = $("#viewer");
  if (!ps.active) return;
  v.innerHTML = `<div class="mask-wrap"><img class="base" src="/api/files/${ps.active.id}/view?size=1600" alt=""><canvas></canvas></div>`;
  const img = $("img", v), cv = $("canvas", v);
  img.onload = () => setupMask(img, cv);
  $("#viewerHint").textContent = ps.brush ? t("mask_hint") : "";
  updateMaskBtn();
}
function setupMask(img, cv) {
  cv.width = img.naturalWidth; cv.height = img.naturalHeight;
  const ctx = cv.getContext("2d");
  if (ps.masks[ps.active.id]) { const m = new Image(); m.onload = () => ctx.drawImage(m, 0, 0, cv.width, cv.height); m.src = ps.masks[ps.active.id]; }
  cv.style.pointerEvents = ps.brush ? "auto" : "none";
  let drawing = false;
  const pos = e => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) * cv.width / r.width, (e.clientY - r.top) * cv.height / r.height, cv.width / r.width]; };
  cv.onpointerdown = e => { if (!ps.brush) return; drawing = true; cv.setPointerCapture(e.pointerId); const [x, y, s] = pos(e); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + .1, y); stroke(ctx, s); };
  cv.onpointermove = e => { if (!drawing) return; const [x, y, s] = pos(e); ctx.lineTo(x, y); stroke(ctx, s); };
  cv.onpointerup = cv.onpointercancel = () => { if (!drawing) return; drawing = false; ps.masks[ps.active.id] = cv.toDataURL("image/png"); renderPhotoGrid(); };
}
function stroke(ctx, s) { ctx.strokeStyle = "rgba(255,40,40,0.55)"; ctx.lineWidth = +$("#brushSize").value * s; ctx.lineCap = ctx.lineJoin = "round"; ctx.globalCompositeOperation = "copy"; ctx.stroke(); ctx.globalCompositeOperation = "source-over"; }
function updateMaskBtn() { $("#maskToggle").textContent = ps.brush ? t("brush_off") : t("brush_on"); $("#maskToggle").classList.toggle("on", ps.brush); }
$("#maskToggle").onclick = () => { if (!ps.active) return alert(t("need_photo")); ps.brush = !ps.brush; showOriginal(); };
$("#maskClear").onclick = () => { if (!ps.active) return; delete ps.masks[ps.active.id]; showOriginal(); renderPhotoGrid(); };

async function analyzePhoto() {
  if (!ps.active) return;
  const box = $("#photoAnalysis");
  box.classList.remove("hidden"); box.textContent = t("analysing");
  try {
    const a = await api("/api/photo/analyze", { method: "POST", body: JSON.stringify({ file_id: ps.active.id, style: ps.style === "auto" ? null : ps.style }) });
    ps.params = { ...ZERO_PHOTO, ...a.params };
    const items = [...a.reasons, ...a.adjustments].map(n => `<li>${esc(n[lang])}</li>`).join("");
    box.innerHTML = `<b>${t("analysis_title")}</b> · ${t("chosen_style")}: <b class="gold">${t("st_" + a.style)}</b><ul>${items}</ul>`;
    buildPhotoControls();
  } catch (e) { box.textContent = e.message; }
}

function photoParams() {
  const p = { ...ps.params };
  p.logo = $("#pLogo").checked; p.logo_position = $("#pLogoPos").value; p.logo_size = +$("#pLogoSize").value; p.logo_opacity = +$("#pLogoOp").value;
  p.watermark_text = $("#pWm").value.trim(); p.property_card = $("#pCard").checked; p.card_lang = $("#pCardLang").value;
  p.format = $("#pFormat").value; p.fit = $("#pFit").value;
  return p;
}
$("#pReset").onclick = () => { ps.style = "auto"; analyzePhoto(); };
$("#pPreview").onclick = () => runPhoto([ps.active?.id], true, false);
$("#pExport").onclick = () => runPhoto([ps.active?.id], false, false);
$("#pBatch").onclick = () => { if (!ps.selected.size) return alert(t("need_sel")); runPhoto([...ps.selected], false, $("#pAutoEach").checked); };

async function runPhoto(ids, preview, autoEach) {
  if (!ids[0]) return alert(t("need_photo"));
  const masks = {};
  ids.forEach(id => { if (ps.masks[id]) masks[id] = ps.masks[id]; });
  const body = { file_ids: ids, params: photoParams(), preview, auto_each: autoEach, style: ps.style === "auto" ? null : ps.style, masks, output: $("#pOut").value };
  const box = $("#photoJob");
  box.innerHTML = `<div class="muted small">${t("queued")}…</div>`;
  try {
    const job = await api("/api/photo/process", { method: "POST", body: JSON.stringify(body) });
    watchJob(job, box, (j, b) => {
      if (preview && j.outputs[0]) { showCompare(j.outputs[0].before, j.outputs[0].url); return; }
      b.insertAdjacentHTML("beforeend", `<div class="outputs">${j.outputs.map(o => `<div><a href="${o.url}" download>⬇ ${t("download")} ${esc(o.name)} (${fmtSize(o.size)}${o.width ? `, ${o.width}×${o.height}` : ""})</a>${shareBtn(o)}</div>`).join("")}</div>`);
      if (!preview && ids.length === 1 && j.outputs[0]) showCompare(`/api/files/${ids[0]}/view?size=1600`, j.outputs[0].url);
    });
  } catch (e) { box.innerHTML = `<div class="err">${esc(e.message)}</div>`; }
}
function showCompare(before, after) {
  ps.brush = false; updateMaskBtn();
  const v = $("#viewer");
  v.innerHTML = `<div class="cmp"><img src="${before}" alt=""><img class="after" src="${after}?v=${Date.now()}" alt=""><div class="divider"></div>
    <span class="lbl b">Before</span><span class="lbl a">After</span><input type="range" min="0" max="100" value="50" aria-label="compare"></div>`;
  const r = $("input", v), a = $(".after", v), d = $(".divider", v);
  r.oninput = () => { a.style.clipPath = `inset(0 0 0 ${r.value}%)`; d.style.left = r.value + "%"; };
  $("#viewerHint").textContent = t("ok_preview");
  if (window.innerWidth < 900) v.scrollIntoView({ behavior: "smooth", block: "center" });
}

dropzone($("#photoDrop"), $("#photoInput"), async files => {
  try {
    const res = await upload(files, $("#photoUp"));
    await loadPhotos();
    const imgs = res.filter(r => r.kind === "image");
    imgs.forEach(r => ps.selected.add(r.id));
    if (imgs[0]) selectPhoto(ps.files.find(f => f.id === imgs[0].id));
    renderPhotoGrid();
  } catch (e) { alert(e.message); }
});

// ================================================================== VIDEO
const VIDEO_SLIDERS = [["brightness", -0.3, 0.3, .01], ["contrast", 0.6, 1.6, .01], ["saturation", 0, 2, .01], ["gamma", 0.6, 1.8, .01],
  ["warmth", -1, 1, .02], ["teal_orange", 0, 1, .02], ["vignette", 0, 1, .02], ["sharpen", 0, 1, .02], ["denoise", 0, 1, .02]];
const vs = { files: [], audio: [], clips: [], active: -1, style: "auto",
  params: { brightness: 0, contrast: 1, saturation: 1, gamma: 1, warmth: 0, teal_orange: 0, vignette: 0, sharpen: 0, denoise: 0 },
  texts: [] };

function buildVideoControls() {
  const chips = $("#videoStyles"); chips.innerHTML = "";
  STYLES.forEach(s => {
    const b = document.createElement("button");
    b.className = "chip" + (vs.style === s ? " on" : ""); b.textContent = t("st_" + s);
    b.onclick = () => { vs.style = s; buildVideoControls(); analyzeVideo(); };
    chips.appendChild(b);
  });
  const g = $("#g_vgrade"); g.innerHTML = "";
  VIDEO_SLIDERS.forEach(([k, a, b, s]) => slider(g, k, a, b, s, vs.params));
}
async function loadVideos() {
  const all = await api("/api/files");
  vs.files = all.filter(f => f.kind === "video"); vs.audio = all.filter(f => f.kind === "audio");
  const bin = $("#videoBin"); bin.innerHTML = "";
  vs.files.forEach(f => {
    const c = document.createElement("div"); c.className = "card";
    c.innerHTML = `<img loading="lazy" src="/api/files/${f.id}/thumb" alt=""><span class="badge">${(f.duration || 0).toFixed(1)}${t("sec")}</span>
      <button class="gold-btn add sm">${t("add")}</button><div class="nm">${esc(f.name)} · ${f.width || "?"}×${f.height || "?"}</div>`;
    $(".add", c).onclick = e => { e.stopPropagation(); addClip(f); };
    c.onclick = () => addClip(f);
    bin.appendChild(c);
  });
  renderMusic();
}
function renderMusic() {
  const sel = $("#vMusic"); const cur = sel.value;
  sel.innerHTML = `<option value="">${t("no_music")}</option>` + vs.audio.map(a => `<option value="${a.id}">${esc(a.name)} (${(a.duration || 0).toFixed(0)}${t("sec")})</option>`).join("");
  sel.value = cur;
}
function addClip(f) {
  vs.clips.push({ file_id: f.id, name: f.name, start: 0, end: +(f.duration || 0).toFixed(2), duration: f.duration || 0 });
  vs.active = vs.clips.length - 1; renderTimeline(); openPlayer();
  if (vs.clips.length === 1) analyzeVideo();
}
function renderTimeline() {
  const tl = $("#timeline");
  if (!vs.clips.length) { tl.innerHTML = `<div class="muted small">${t("timeline_empty")}</div>`; $("#playerBox").classList.add("hidden"); return; }
  tl.innerHTML = "";
  vs.clips.forEach((c, i) => {
    const d = document.createElement("div"); d.className = "clip" + (i === vs.active ? " active" : "");
    d.innerHTML = `<img src="/api/files/${c.file_id}/thumb" alt=""><div><div class="small">${i + 1}. ${esc(c.name)}</div>
      <div class="times">${t("start")} <input type="number" step="0.1" min="0" value="${c.start}" class="s"> ${t("end")} <input type="number" step="0.1" min="0" value="${c.end}" class="e"> ${t("sec")}</div></div>
      <div class="btns"><button class="ghost sm up">▲</button><button class="ghost sm dn">▼</button><button class="ghost sm rm">✕</button></div>`;
    $(".s", d).onchange = e => { c.start = Math.max(0, +e.target.value); };
    $(".e", d).onchange = e => { c.end = Math.min(c.duration || 1e9, +e.target.value); };
    $(".up", d).onclick = e => { e.stopPropagation(); if (i > 0) { [vs.clips[i - 1], vs.clips[i]] = [vs.clips[i], vs.clips[i - 1]]; vs.active = i - 1; renderTimeline(); } };
    $(".dn", d).onclick = e => { e.stopPropagation(); if (i < vs.clips.length - 1) { [vs.clips[i + 1], vs.clips[i]] = [vs.clips[i], vs.clips[i + 1]]; vs.active = i + 1; renderTimeline(); } };
    $(".rm", d).onclick = e => { e.stopPropagation(); vs.clips.splice(i, 1); vs.active = Math.min(vs.active, vs.clips.length - 1); renderTimeline(); openPlayer(); };
    $("img", d).onclick = () => { vs.active = i; renderTimeline(); openPlayer(); };
    tl.appendChild(d);
  });
}
function openPlayer() {
  const c = vs.clips[vs.active];
  if (!c) return $("#playerBox").classList.add("hidden");
  $("#playerBox").classList.remove("hidden");
  const p = $("#player");
  const src = `/api/files/${c.file_id}/original`;
  if (!p.src.endsWith(src)) p.src = src;
  $("#playerInfo").textContent = c.name;
}
$("#setIn").onclick = () => { const c = vs.clips[vs.active]; if (!c) return; c.start = +$("#player").currentTime.toFixed(2); renderTimeline(); };
$("#setOut").onclick = () => { const c = vs.clips[vs.active]; if (!c) return; c.end = +$("#player").currentTime.toFixed(2); renderTimeline(); };

async function analyzeVideo() {
  const c = vs.clips[0];
  const box = $("#videoAnalysis");
  if (!c) return;
  box.classList.remove("hidden"); box.textContent = t("analysing");
  try {
    const a = await api("/api/video/analyze", { method: "POST", body: JSON.stringify({ file_id: c.file_id, style: vs.style === "auto" ? null : vs.style }) });
    const p = a.params;
    VIDEO_SLIDERS.forEach(([k]) => vs.params[k] = p[k]);
    $("#vStab").checked = !!p.stabilize; $("#vDenoiseAudio").checked = !!p.denoise_audio; $("#vLetterbox").checked = !!p.letterbox;
    const items = [...a.reasons, ...a.adjustments].map(n => `<li>${esc(n[lang])}</li>`).join("");
    box.innerHTML = `<b>${t("analysis_title")}</b> · ${t("chosen_style")}: <b class="gold">${t("st_" + a.style)}</b><ul>${items}</ul>`;
    buildVideoControls();
  } catch (e) { box.textContent = e.message; }
}

function renderTexts() {
  const box = $("#vTexts"); box.innerHTML = "";
  vs.texts.forEach((x, i) => {
    const d = document.createElement("div"); d.className = "txtrow";
    d.innerHTML = `<input class="t" placeholder="${t("text_ph")}" value="${esc(x.text)}" dir="auto">
      <label class="small">${t("start")} <input type="number" step="0.1" class="s" value="${x.start}"></label>
      <label class="small">${t("end")} <input type="number" step="0.1" class="e" value="${x.end}"></label>
      <select class="p"><option value="top">${t("pos_top")}</option><option value="center">${t("pos_center")}</option><option value="bottom">${t("pos_bottom")}</option></select>
      <select class="c"><option value="white">${t("col_white")}</option><option value="gold">${t("col_gold")}</option></select>
      <label class="check small"><input type="checkbox" class="b" ${x.box ? "checked" : ""}> ${t("box")}</label>
      <button class="ghost sm rm">${t("remove")}</button>`;
    $(".p", d).value = x.position; $(".c", d).value = x.color;
    $(".t", d).oninput = e => x.text = e.target.value;
    $(".s", d).onchange = e => x.start = +e.target.value;
    $(".e", d).onchange = e => x.end = +e.target.value;
    $(".p", d).onchange = e => x.position = e.target.value;
    $(".c", d).onchange = e => x.color = e.target.value;
    $(".b", d).onchange = e => x.box = e.target.checked;
    $(".rm", d).onclick = () => { vs.texts.splice(i, 1); renderTexts(); };
    box.appendChild(d);
  });
}
$("#addText").onclick = () => { const n = vs.texts.length; vs.texts.push({ text: "", start: n * 4 + 0.5, end: n * 4 + 4, position: "bottom", color: "white", box: true, size: 0.06 }); renderTexts(); };

function videoParams() {
  return { ...vs.params, stabilize: $("#vStab").checked, keep_audio: $("#vKeepAudio").checked, denoise_audio: $("#vDenoiseAudio").checked,
    letterbox: $("#vLetterbox").checked, music_id: $("#vMusic").value || null, music_volume: +$("#vMusicVol").value,
    transition: $("#vTrans").value, transition_duration: +$("#vTransDur").value, texts: vs.texts.filter(x => x.text.trim()),
    logo: $("#vLogo").checked, property_card: $("#vCard").checked, card_start: +$("#vCardStart").value, card_lang: $("#vCardLang").value,
    end_card: $("#vEnd").checked, preset: $("#vPreset").value, fit: $("#vFit").value };
}
async function runVideo(preview) {
  if (!vs.clips.length) return alert(t("need_clip"));
  const clips = vs.clips.map(c => ({ file_id: c.file_id, start: c.start, end: c.end }));
  const box = $("#videoJob");
  box.innerHTML = `<div class="muted small">${t("queued")}…</div>`;
  try {
    const job = await api("/api/video/render", { method: "POST", body: JSON.stringify({ clips, params: videoParams(), preview }) });
    watchJob(job, box, (j, b) => {
      const o = j.outputs[0];
      b.insertAdjacentHTML("beforeend", `<div class="outputs"><video src="${o.url}?v=${Date.now()}" controls playsinline></video>
        <a href="${o.url}" download>⬇ ${t("download")} ${esc(o.name)} (${fmtSize(o.size)}, ${o.width}×${o.height}, ${(o.duration || 0).toFixed(1)}${t("sec")})</a>${shareBtn(o)}</div>`);
    });
  } catch (e) { box.innerHTML = `<div class="err">${esc(e.message)}</div>`; }
}
$("#vPreview").onclick = () => runVideo(true);
$("#vExport").onclick = () => runVideo(false);

dropzone($("#videoDrop"), $("#videoInput"), async files => {
  try {
    const res = await upload(files, $("#videoUp"));
    await loadVideos();
    res.filter(r => r.kind === "video").forEach(r => addClip(vs.files.find(f => f.id === r.id) || r));
    const a = res.find(r => r.kind === "audio"); if (a) $("#vMusic").value = a.id;
  } catch (e) { alert(e.message); }
});

// ================================================================== BRAND
let settings = {};
async function loadSettings() {
  settings = await api("/api/settings");
  settings.property = settings.property || {};
  $$("[data-k]").forEach(i => i.value = settings[i.dataset.k] || "");
  $$("[data-p]").forEach(i => { if (settings.property[i.dataset.p] != null) i.value = settings.property[i.dataset.p]; });
  $("#logoBox").innerHTML = settings.logo_id ? `<img src="/api/files/${settings.logo_id}/original" alt="logo">` : `<span class="muted">${t("no_logo")}</span>`;
}
$("#saveBrand").onclick = async () => {
  $$("[data-k]").forEach(i => settings[i.dataset.k] = i.value.trim());
  $$("[data-p]").forEach(i => settings.property[i.dataset.p] = i.value.trim());
  await api("/api/settings", { method: "PUT", body: JSON.stringify(settings) });
  $("#saveMsg").textContent = t("saved"); setTimeout(() => $("#saveMsg").textContent = "", 2500);
};
$("#logoInput").onchange = async e => {
  const f = e.target.files[0]; if (!f) return;
  const fd = new FormData(); fd.append("files", f, f.name);
  const r = await (await fetch("/api/upload?role=logo", { method: "POST", body: fd, credentials: "same-origin" })).json();
  settings.logo_id = r[0].id;
  await api("/api/settings", { method: "PUT", body: JSON.stringify(settings) });
  loadSettings();
};

// ================================================================== LIBRARY
async function loadLibrary() {
  const jobs = await api("/api/jobs");
  $("#jobsList").innerHTML = jobs.map(j => `<div class="jobrow"><div class="row between wrap gap"><b>${esc(j.title)}</b>
    <span class="st ${j.status}">${t(j.status === "done" ? "done" : j.status === "error" ? "error" : "running")}</span></div>
    <div class="muted small">${new Date(j.created * 1000).toLocaleString(lang === "ar" ? "ar-AE" : "en-GB")}</div>
    <div class="outs">${(j.outputs || []).map(o => `<a href="${o.url}" target="_blank" download>⬇ ${esc(o.name)} (${fmtSize(o.size)})</a>`).join("")}</div>
    ${j.error ? `<div class="muted small" dir="ltr">${esc(j.error.slice(0, 300))}</div>` : ""}</div>`).join("");
  const files = await api("/api/files");
  $("#origList").innerHTML = files.map(f => `<a class="card" href="/api/files/${f.id}/original" download>
    ${f.kind === "audio" ? '<div style="aspect-ratio:4/3;display:grid;place-items:center;font-size:30px">♪</div>' : `<img loading="lazy" src="/api/files/${f.id}/thumb" alt="">`}
    <div class="nm">${esc(f.name)} · ${fmtSize(f.size)} · ${t("orig_kept")}</div></a>`).join("");
}
$("#refreshLib").onclick = loadLibrary;

// ------------------------------------------------------------------ init
api("/api/me").then(m => { if (m.auth) $("#logoutBtn").classList.remove("hidden"); }).catch(() => {});
$("#logoutBtn").onclick = async () => { await fetch("/api/logout", { method: "POST" }); location.href = "/login.html"; };
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
applyLang();
loadPhotos(); loadVideos(); loadSettings();
