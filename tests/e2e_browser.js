// End-to-end UI test: drives the real app in Chromium (desktop + iPhone emulation).
// Usage: node tests/e2e_browser.js [baseUrl] [outDir]
const { chromium, devices } = require("playwright");
const path = require("path");
const fs = require("fs");
const BASE = process.argv[2] || "http://localhost:8000";
const OUT = process.argv[3] || path.join(__dirname, "..", "test-results");
const S = path.join(__dirname, "..", "samples");
fs.mkdirSync(OUT, { recursive: true });
const results = [];
const ok = (name, pass, info = "") => { results.push({ name, pass, info }); console.log(pass ? "PASS" : "FAIL", name, info); };

async function waitJob(page, sel, timeout = 600000) {
  await page.waitForFunction(s => !!document.querySelector(s + " .bar"), sel, { timeout: 30000 });
  await page.waitForFunction(s => { const t = document.querySelector(s)?.textContent || ""; return /تم|Done|خطأ|Error/.test(t) && document.querySelector(s + " .bar"); }, sel, { timeout });
  await page.waitForTimeout(400);
  return page.$eval(sel, e => e.innerText);
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(BASE);
  await page.waitForSelector("#photoStyles .chip");
  await page.screenshot({ path: `${OUT}/01_home_ar.png` });
  ok("page loads in Arabic RTL", await page.evaluate(() => document.documentElement.dir === "rtl"));

  // ---- brand settings
  await page.click('[data-tab="brand"]');
  await page.setInputFiles("#logoInput", path.join(S, "logo_placeholder.png"));
  await page.waitForSelector("#logoBox img");
  const fill = { company_ar: "البصمة للعقارات", company_en: "Al Basmah Real Estate", phone: "+971 50 123 4567", website: "albasmah.ae" };
  for (const [k, v] of Object.entries(fill)) await page.fill(`[data-k="${k}"]`, v);
  const prop = { title_ar: "فيلا فاخرة للبيع - دبي هيلز", title_en: "Luxury Villa for Sale - Dubai Hills", price: "4500000", beds: "5", baths: "6", area: "6200", location_ar: "دبي هيلز استيت، دبي", location_en: "Dubai Hills Estate, Dubai" };
  for (const [k, v] of Object.entries(prop)) await page.fill(`[data-p="${k}"]`, v);
  await page.click("#saveBrand");
  await page.waitForFunction(() => document.querySelector("#saveMsg").textContent.length > 0);
  const st = await (await page.request.get(BASE + "/api/settings")).json();
  ok("brand + property saved", st.property.price === "4500000" && !!st.logo_id);
  await page.screenshot({ path: `${OUT}/02_brand.png`, fullPage: true });

  // ---- photos: drag&drop input upload
  await page.click('[data-tab="photo"]');
  const photos = ["facade_tilted_12mp.jpg", "interior_dark_noisy.jpg", "coffee_yellow_cast.jpg", "outdoor_rocket.jpg", "iphone_photo.heic"].map(f => path.join(S, f));
  await page.setInputFiles("#photoInput", photos);
  await page.waitForFunction(() => document.querySelectorAll("#photoGrid .card").length >= 5, null, { timeout: 60000 });
  ok("5 photos uploaded (incl. HEIC)", true);
  // pick facade
  await page.click('#photoGrid .card:has-text("facade")');
  await page.waitForFunction(() => /عقاري|ليلي|Real|Night/.test(document.querySelector("#photoAnalysis").textContent), null, { timeout: 30000 });
  const analysisText = await page.$eval("#photoAnalysis", e => e.innerText);
  ok("auto analysis shows style + adjustments", /الميلان|Straighten/.test(analysisText), analysisText.replace(/\n/g, " | "));
  await page.screenshot({ path: `${OUT}/03_photo_analysis.png` });
  // manual override: change exposure slider
  await page.$eval('#g_light input[type=range]', el => { el.value = 0.3; el.dispatchEvent(new Event("input")); });
  // object removal: paint over the red sign (at ~72% x, 87% y of the original before geometry)
  await page.click('summary:has-text("إزالة")');
  await page.click("#maskToggle");
  await page.waitForSelector(".mask-wrap canvas");
  await page.waitForTimeout(800);
  const box = await page.$eval(".mask-wrap canvas", c => { const r = c.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; });
  await page.mouse.move(box.x + box.w * 0.705, box.y + box.h * 0.85);
  await page.mouse.down();
  for (let i = 0; i <= 10; i++) await page.mouse.move(box.x + box.w * (0.705 + 0.03 * i / 10), box.y + box.h * (0.85 + 0.04 * (i % 2)), { steps: 3 });
  await page.mouse.up();
  ok("mask drawn", await page.evaluate(() => document.querySelector("#photoGrid .card.active .badge") !== null));
  await page.click("#pPreview");
  await waitJob(page, "#photoJob");
  await page.waitForSelector(".cmp img.after");
  await page.waitForTimeout(1500);
  await page.$eval(".cmp input", el => { el.value = 35; el.dispatchEvent(new Event("input")); });
  await page.screenshot({ path: `${OUT}/04_photo_before_after.png` });
  ok("before/after preview shown", true);

  // export single photo with property card, story format
  await page.click('summary:has-text("الشعار")');
  await page.check("#pCard");
  await page.selectOption("#pFormat", "story");
  await page.click("#pExport");
  const exp = await waitJob(page, "#photoJob");
  ok("single export (story + property card)", /تم/.test(exp), exp.split("\n").slice(-1)[0]);
  await page.screenshot({ path: `${OUT}/05_photo_export.png` });

  // batch export: all selected, auto per photo, landscape web + logo
  await page.uncheck("#pCard");
  await page.check("#pLogo");
  await page.selectOption("#pFormat", "web");
  await page.click("#pBatch");
  const batch = await waitJob(page, "#photoJob");
  ok("batch export with zip", /albasmah_photos\.zip/.test(batch), batch.split("\n").filter(l => /zip/.test(l)).join(""));

  // ---- video
  await page.click('[data-tab="video"]');
  await page.setInputFiles("#videoInput", ["shaky_1080p.mp4", "portrait_iphone.mov", "music_test.mp3"].map(f => path.join(S, f)));
  await page.waitForFunction(() => document.querySelectorAll("#timeline .clip").length === 2, null, { timeout: 60000 });
  await page.waitForFunction(() => /عقاري|ليلي|فاخر|Real/.test(document.querySelector("#videoAnalysis").textContent), null, { timeout: 60000 });
  const va = await page.$eval("#videoAnalysis", e => e.innerText);
  ok("video analysis (shake detected)", /اهتزاز|shake/.test(va), va.replace(/\n/g, " | "));
  ok("music auto-selected", await page.$eval("#vMusic", e => !!e.value));
  // trim first clip 1..7s
  await page.fill("#timeline .clip:nth-child(1) input.s", "1"); await page.dispatchEvent("#timeline .clip:nth-child(1) input.s", "change");
  await page.fill("#timeline .clip:nth-child(1) input.e", "7"); await page.dispatchEvent("#timeline .clip:nth-child(1) input.e", "change");
  // reorder: move clip 2 up then back down (test buttons)
  await page.click("#timeline .clip:nth-child(2) .up");
  const first = await page.$eval("#timeline .clip:nth-child(1)", e => e.innerText);
  ok("reorder clips", /portrait/.test(first));
  await page.click("#timeline .clip:nth-child(1) .dn");
  await page.click("#addText");
  await page.fill("#vTexts .txtrow:nth-child(1) input.t", "فيلا فاخرة في دبي هيلز");
  await page.selectOption("#vTexts .txtrow:nth-child(1) select.c", "gold");
  await page.selectOption("#vTexts .txtrow:nth-child(1) select.p", "top");
  await page.click("#addText");
  await page.fill("#vTexts .txtrow:nth-child(2) input.t", "Luxury Villa - Dubai Hills");
  await page.click('#tab-video summary:has-text("الشعار")');
  await page.check("#vCard"); await page.fill("#vCardStart", "7"); await page.check("#vEnd");
  await page.screenshot({ path: `${OUT}/06_video_setup.png`, fullPage: true });
  await page.click("#vPreview");
  const vp = await waitJob(page, "#videoJob", 300000);
  ok("video quick preview", /تم/.test(vp), vp.split("\n").slice(-1)[0]);
  await page.selectOption("#vPreset", "reels");
  await page.click("#vExport");
  const ve = await waitJob(page, "#videoJob", 900000);
  ok("video export Reels 1080x1920", /1080×1920/.test(ve), ve.split("\n").slice(-1)[0]);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/07_video_export.png` });

  // ---- library + English
  await page.click('[data-tab="library"]');
  await page.waitForSelector(".jobrow");
  await page.screenshot({ path: `${OUT}/08_library.png` });
  await page.click("#langBtn");
  await page.click('[data-tab="photo"]');
  ok("English LTR toggle", await page.evaluate(() => document.documentElement.dir === "ltr" && /Photo Editor/.test(document.body.innerText)));
  await page.screenshot({ path: `${OUT}/09_english.png` });
  ok("no JS errors (desktop)", errors.length === 0, errors.join("; "));

  // ---- iPhone emulation
  const m = await browser.newContext({ ...devices["iPhone 13"] });
  const mp = await m.newPage();
  const merr = [];
  mp.on("pageerror", e => merr.push(e.message));
  await mp.goto(BASE);
  await mp.waitForSelector("#photoGrid .card");
  await mp.click("#photoGrid .card");
  await mp.waitForFunction(() => document.querySelector("#photoAnalysis").textContent.length > 20, null, { timeout: 30000 });
  await mp.screenshot({ path: `${OUT}/10_iphone_photo.png`, fullPage: false });
  const overflow = await mp.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  ok("iPhone: no horizontal overflow", !overflow);
  await mp.click("#pPreview");
  await waitJob(mp, "#photoJob");
  await mp.waitForSelector(".cmp img.after");
  await mp.waitForTimeout(1200);
  await mp.screenshot({ path: `${OUT}/11_iphone_preview.png` });
  await mp.click('[data-tab="video"]');
  await mp.waitForTimeout(800);
  await mp.screenshot({ path: `${OUT}/12_iphone_video.png` });
  ok("no JS errors (iPhone)", merr.length === 0, merr.join("; "));

  fs.writeFileSync(`${OUT}/e2e_results.json`, JSON.stringify(results, null, 2));
  await browser.close();
  const failed = results.filter(r => !r.pass).length;
  console.log(`\n${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
