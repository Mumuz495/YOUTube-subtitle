const form = document.querySelector("#fetch-form");
const submitButton = document.querySelector("#submit");
const immersiveButton = document.querySelector("#immersive-translate");
const translateCheckbox = document.querySelector("#translate");
const pdfFileInput = document.querySelector("#pdf-file");
const statusText = document.querySelector("#status");
const transcript = document.querySelector("#transcript");
const warnings = document.querySelector("#warnings");
const downloadLinks = document.querySelector("#download-links");
const DEFAULT_PDF_MAX_UPLOAD_BYTES = 200 * 1024 * 1024;
let pdfMaxUploadBytes = DEFAULT_PDF_MAX_UPLOAD_BYTES;
let pdfMaxUploadLabel = "200 MB";
let vocabEntries = [];
let ttsVoices = [];
let currentAudio = null;
let ttsRunId = 0;

loadUploadConfig().catch(() => {});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitter = event.submitter;
  const isImmersive = submitter?.id === "immersive-translate";
  if (isImmersive) {
    translateCheckbox.checked = true;
  }

  const url = document.querySelector("#url").value.trim();
  const pdfFile = pdfFileInput?.files?.[0] || null;
  if (!url && !pdfFile) {
    statusText.innerHTML = '<span class="error">请粘贴链接，或选择一个 PDF 文件。</span>';
    return;
  }
  if (pdfFile && !pdfFile.name.toLowerCase().endsWith(".pdf") && pdfFile.type !== "application/pdf") {
    statusText.innerHTML = '<span class="error">请选择 PDF 文件。</span>';
    return;
  }
  if (pdfFile && pdfFile.size > pdfMaxUploadBytes) {
    const sizeMb = formatFileSize(pdfFile.size);
    statusText.innerHTML = `<span class="error">PDF 文件太大：${escapeHtml(sizeMb)}。当前网页上传上限是 ${escapeHtml(pdfMaxUploadLabel)}。</span>`;
    return;
  }

  setLoading(true, isImmersive, Boolean(pdfFile));
  renderWarnings([]);
  downloadLinks.innerHTML = "";
  transcript.className = `transcript empty${isImmersive ? " immersive" : ""}`;
  transcript.innerHTML = pdfFile
    ? "<p>正在上传并读取 PDF…若为扫描版，系统将进行 OCR，可能需要几分钟，请耐心等待。</p>"
    : isImmersive
      ? "<p>正在连接 DeepSeek，生成双语沉浸预览...</p>"
      : "<p>正在抓取内容，频道、播放列表和文章可能需要更久...</p>";

  const payload = {
    url,
    limit: document.querySelector("#limit").value,
    output: document.querySelector("#output").value.trim() || "output",
    translate: isImmersive || translateCheckbox.checked,
  };

  try {
    const result = pdfFile
      ? await fetchPdfContent(pdfFile, payload, isImmersive)
      : await fetchLinkedContent(payload);
    renderResult(result, isImmersive);
  } catch (error) {
    statusText.innerHTML = `<span class="error">${escapeHtml(error.message)}</span>`;
    transcript.className = "transcript empty";
    transcript.innerHTML = "<p>可以检查链接、PDF 文本、网络、依赖安装，或确认该视频是否有字幕、该文章是否公开可读。</p>";
  } finally {
    setLoading(false);
  }
});

async function fetchLinkedContent(payload) {
  const response = await fetch("/api/fetch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok || result.error) {
    throw new Error(result.error || "抓取失败");
  }
  return result;
}

async function loadUploadConfig() {
  const response = await fetch("/api/config");
  if (!response.ok) {
    return;
  }
  const config = await response.json();
  if (Number(config.pdf_max_upload_bytes) > 0) {
    pdfMaxUploadBytes = Number(config.pdf_max_upload_bytes);
  }
  if (config.pdf_max_upload_label) {
    pdfMaxUploadLabel = String(config.pdf_max_upload_label);
  }
  const hint = document.querySelector("#pdf-upload-hint");
  if (hint) {
    hint.textContent = `支持文本 PDF 与较大扫描版 PDF，单文件最大 ${pdfMaxUploadLabel}。扫描版 OCR 可能需要几分钟。`;
  }
}

async function fetchPdfContent(file, payload) {
  const formData = new FormData();
  formData.append("pdf", file, file.name);
  formData.append("filename", file.name);
  formData.append("output", payload.output);
  formData.append("translate", payload.translate ? "true" : "false");

  const response = await fetch("/api/pdf-upload", {
    method: "POST",
    body: formData,
  });
  const result = await response.json();
  if (!response.ok || result.error) {
    throw new Error(result.error || "PDF 读取失败");
  }
  return result;
}

function formatFileSize(bytes) {
  const mb = Number(bytes || 0) / 1024 / 1024;
  return `${mb.toFixed(mb >= 10 ? 0 : 1)} MB`;
}

function setLoading(isLoading, isImmersive = false, isPdf = false) {
  submitButton.disabled = isLoading;
  immersiveButton.disabled = isLoading;
  submitButton.textContent = isLoading ? (isPdf ? "上传中..." : "抓取中...") : "抓取内容";
  immersiveButton.textContent = isLoading && isImmersive ? "翻译中..." : "沉浸式翻译";
  if (isLoading) {
    statusText.textContent = isPdf
      ? "正在上传 PDF。扫描版将进行 OCR，可能需要几分钟。"
      : isImmersive
        ? "正在调用 DeepSeek 生成双语预览。"
        : "正在处理。";
  }
}

function renderResult(result, isImmersive = false) {
  renderWarnings(result.warnings || []);
  const okItems = (result.results || []).filter((item) => item.ok);
  const failedItems = (result.results || []).filter((item) => !item.ok);
  const sourceLabel = renderSourceCount(okItems[0]);
  statusText.textContent = isImmersive
    ? `双语预览已生成：完成 ${okItems.length} 个${sourceLabel}，跳过 ${failedItems.length} 个。`
    : `完成 ${okItems.length} 个${sourceLabel}，跳过 ${failedItems.length} 个。`;

  if (!okItems.length) {
    transcript.className = "transcript empty";
    transcript.innerHTML = "<p>没有拿到可用内容。可能是作者关闭字幕、视频不可用、网页需要登录，或平台暂时限制请求。</p>";
    return;
  }

  const first = okItems[0];
  renderDownloads(first.files);
  if (isImmersive) {
    renderStudySheet(first);
    return;
  }

  transcript.className = `transcript${isImmersive ? " immersive" : ""}`;
  transcript.innerHTML = (first.preview || []).map(renderLine).join("");
}

transcript.addEventListener("contextmenu", async (event) => {
  const sheet = event.target.closest(".study-sheet");
  if (!sheet) {
    return;
  }

  const selection = window.getSelection();
  let term = normalizeSelection(selection?.toString() || "");
  let fallbackRange = null;
  if (!term) {
    const hit = getWordAtPoint(event);
    term = hit.term;
    fallbackRange = hit.range;
  }

  if (!term) {
    return;
  }

  event.preventDefault();
  const line = event.target.closest(".sheet-line");
  const row = event.target.closest(".sheet-row");
  const paragraphIndex = Number(row?.dataset.paragraph || line?.dataset.paragraph || 0);
  const context = line?.querySelector(".sheet-en")?.textContent || sheet.textContent || "";
  if (fallbackRange) {
    highlightRange(fallbackRange, term);
  } else {
    highlightSelection(selection, term);
  }
  await addVocabEntry(term, context, paragraphIndex);
});

document.addEventListener("click", async (event) => {
  const speakButton = event.target.closest("[data-speak]");
  if (speakButton) {
    handleSpeakButton(speakButton);
    return;
  }

  if (event.target.id === "stop-speech") {
    stopSpeech();
    return;
  }

  if (event.target.id === "export-study-sheet") {
    await exportStudySheet(event.target);
    return;
  }

  if (event.target.id !== "copy-vocab") {
    return;
  }

  const text = vocabEntries
    .map((entry) => `第 ${entry.paragraphIndex || "-"} 段\t${entry.term}\t${entry.part_of_speech} ${entry.definition_zh}`)
    .join("\n");
  await navigator.clipboard.writeText(text);
  event.target.textContent = "已复制";
  setTimeout(() => {
    event.target.textContent = "复制合集";
  }, 1200);
});

function renderStudySheet(item) {
  vocabEntries = [];
  const paragraphs = buildStudyParagraphs(item.full || item.preview || []);
  transcript.className = `transcript immersive sheet-mode${item.media_embed_url ? " has-media" : ""}`;
  transcript.innerHTML = `
    ${renderMediaPanel(item)}
    <section class="study-sheet" tabindex="0" aria-label="双语精读稿">
      <header class="sheet-titlebar">
        <article class="sheet-paper sheet-heading">
          <div class="sheet-brand">Study Sheet</div>
          <div>
            <h3>${escapeHtml(item.title || "双语精读稿")}</h3>
            ${renderSourceMeta(item)}
            ${renderTtsControls()}
          </div>
        </article>
        <aside class="vocab-sidebar vocab-sidebar-head" aria-label="生词合集">
        <div class="vocab-head">
          <h3>生词合集</h3>
          <div class="vocab-actions">
            <button id="copy-vocab" type="button">复制合集</button>
            <label class="export-choice">
              <span>格式</span>
              <select id="export-format">
                <option value="docx">DOCX</option>
                <option value="pdf">PDF</option>
                <option value="html">HTML</option>
              </select>
            </label>
            <button id="export-study-sheet" type="button">导出精读稿</button>
          </div>
        </div>
        <p class="vocab-hint">选中英文词或短语后右键，会自动加入这里。</p>
        <p id="vocab-count" class="vocab-empty">还没有标注。</p>
        </aside>
      </header>
      <div class="sheet-body">
        ${paragraphs.map(renderSheetLine).join("")}
      </div>
    </section>
  `;
  hydrateSpeechControls();
}

function renderMediaPanel(item) {
  if (!item.media_embed_url) {
    return "";
  }

  return `
    <section class="study-media" aria-label="视频播放器">
      <iframe
        src="${escapeHtml(item.media_embed_url)}"
        title="视频播放器"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen
      ></iframe>
    </section>
  `;
}

function renderSourceMeta(item) {
  const title = item.title || (item.source_type === "video" ? item.video_id : "") || "未识别";
  const author = item.author || "未识别";
  const sourceUrl = item.source_url || (item.video_id ? `https://www.youtube.com/watch?v=${item.video_id}` : "") || "未识别";
  return `
    <dl class="sheet-meta" aria-label="来源信息">
      <div class="sheet-meta-row">
        <dt>题目：</dt>
        <dd>${escapeHtml(title)}</dd>
      </div>
      <div class="sheet-meta-row">
        <dt>作者：</dt>
        <dd>${escapeHtml(author)}</dd>
      </div>
      <div class="sheet-meta-row">
        <dt>网址：</dt>
        <dd>${escapeHtml(sourceUrl)}</dd>
      </div>
    </dl>
  `;
}

function renderSourceCount(item) {
  if (item?.source_type === "pdf") {
    return "PDF";
  }
  return item?.source_type === "article" ? "文章" : "视频";
}

function renderTtsControls() {
  return `
    <div class="tts-controls" aria-label="朗读控制">
      <select id="voice-profile" aria-label="朗读声音">
        <option value="us-female">US 女声</option>
        <option value="us-male">US 男声</option>
        <option value="uk-female">UK 女声</option>
        <option value="uk-male">UK 男声</option>
        <option value="default">系统默认</option>
      </select>
      <select id="voice-rate" aria-label="朗读速度">
        <option value="0.85">慢速</option>
        <option value="1" selected>正常</option>
        <option value="1.15">稍快</option>
      </select>
      <button class="tts-action" type="button" data-speak="all">朗读全文</button>
      <button class="tts-action" id="stop-speech" type="button">停止</button>
    </div>
  `;
}

async function exportStudySheet(button) {
  const sheet = document.querySelector(".study-sheet");
  if (!sheet) {
    return;
  }

  const clone = sheet.cloneNode(true);
  clone.querySelectorAll(".vocab-actions, .tts-controls, .speak-button").forEach((node) => node.remove());
  const html = buildStandaloneStudySheetHtml(clone.outerHTML);
  const output = document.querySelector("#output").value.trim() || "output";
  const exportFormat = document.querySelector("#export-format")?.value || "docx";
  button.textContent = "导出中...";
  button.disabled = true;
  let exported = false;

  try {
    const response = await fetch("/api/export-study-sheet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ html, output, format: exportFormat }),
    });
    const result = await response.json();
    if (!response.ok || result.error) {
      throw new Error(result.error || "精读稿导出失败");
    }
    addStudySheetDownload(result.file, exportFormat);
    exported = true;
    button.textContent = `已生成 ${exportFormat.toUpperCase()}`;
    if (exportFormat === "html") {
      downloadCurrentHtmlStudySheet(html);
    } else {
      triggerStudySheetDownload(result.file);
    }
    setTimeout(() => {
      button.textContent = "导出精读稿";
    }, 1600);
  } catch (error) {
    renderWarnings([error.message]);
  } finally {
    if (!exported) {
      button.textContent = "导出精读稿";
    }
    button.disabled = false;
  }
}

function triggerStudySheetDownload(path) {
  const link = document.createElement("a");
  link.href = `/download?path=${encodeURIComponent(path)}`;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function downloadCurrentHtmlStudySheet(html) {
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "study-sheet.html";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function addStudySheetDownload(path, exportFormat = "html") {
  if (!path) {
    return;
  }

  const normalizedFormat = exportFormat.toUpperCase();
  const existing = downloadLinks.querySelector(`[data-export="study-sheet-${exportFormat}"]`);
  if (existing) {
    existing.href = `/download?path=${encodeURIComponent(path)}`;
    return;
  }

  const link = document.createElement("a");
  link.dataset.export = `study-sheet-${exportFormat}`;
  link.href = `/download?path=${encodeURIComponent(path)}`;
  link.textContent = `精读稿 ${normalizedFormat}`;
  downloadLinks.appendChild(link);
}

function buildStandaloneStudySheetHtml(sheetHtml) {
  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>双语精读稿</title>
    <style>
      ${collectStylesForExport()}
      body { margin: 0; background: #f3f5f8; padding: 28px; }
      .study-sheet { max-width: 960px; min-height: auto; }
      .vocab-hint { display: none; }
      @media print {
        body { background: #ffffff; padding: 0; }
        .study-sheet { border: 0; box-shadow: none; max-width: none; }
      }
    </style>
  </head>
  <body>${sheetHtml}</body>
</html>`;
}

function collectStylesForExport() {
  return Array.from(document.styleSheets)
    .map((sheet) => {
      try {
        return Array.from(sheet.cssRules).map((rule) => rule.cssText).join("\n");
      } catch {
        return "";
      }
    })
    .join("\n");
}

function buildStudyParagraphs(items) {
  const paragraphs = [];
  let current = [];

  for (const item of items) {
    current.push(item);
    const text = String(item.text || "").trim();
    const isBoundary = /[.!?]"?$/.test(text) || current.length >= 5;
    if (isBoundary) {
      paragraphs.push(current);
      current = [];
    }
  }

  if (current.length) {
    paragraphs.push(current);
  }

  return paragraphs;
}

function renderSheetLine(group, index) {
  const english = group.map((item) => item.text || "").join(" ");
  const chinese = group.map((item) => item.text_zh || "").filter(Boolean).join("");
  const paragraphIndex = index + 1;
  return `
    <section class="sheet-row" data-paragraph="${paragraphIndex}">
      <article class="sheet-line" data-paragraph="${paragraphIndex}">
        <div class="sheet-line-tools">
          <button class="speak-button speak-paragraph" type="button" data-speak="paragraph" aria-label="朗读第 ${paragraphIndex} 段">🔊</button>
        </div>
        <p class="sheet-en">${escapeHtml(english)}</p>
        ${chinese ? `<p class="sheet-zh">${escapeHtml(chinese)}</p>` : ""}
      </article>
      <aside class="paragraph-vocab" aria-label="第 ${paragraphIndex} 段生词">
        <div class="paragraph-vocab-list" data-paragraph="${paragraphIndex}"></div>
      </aside>
    </section>
  `;
}

function normalizeSelection(value) {
  const text = value.replace(/\s+/g, " ").trim();
  if (!text || text.length > 80 || /[\u4e00-\u9fff]/.test(text)) {
    return "";
  }
  return text.replace(/^[^A-Za-z]+|[^A-Za-z]+$/g, "");
}

function highlightSelection(selection, term) {
  if (!selection || selection.rangeCount === 0) {
    return;
  }

  highlightRange(selection.getRangeAt(0), term);
  selection.removeAllRanges();
}

function getWordAtPoint(event) {
  const range = document.caretRangeFromPoint
    ? document.caretRangeFromPoint(event.clientX, event.clientY)
    : document.caretPositionFromPoint?.(event.clientX, event.clientY);

  const node = range?.startContainer || range?.offsetNode;
  const offset = range?.startOffset ?? range?.offset;
  if (!node || node.nodeType !== Node.TEXT_NODE) {
    return { term: "", range: null };
  }

  const text = node.textContent || "";
  let start = offset;
  let end = offset;
  while (start > 0 && /[A-Za-z'-]/.test(text[start - 1])) {
    start -= 1;
  }
  while (end < text.length && /[A-Za-z'-]/.test(text[end])) {
    end += 1;
  }

  const term = normalizeSelection(text.slice(start, end));
  if (!term) {
    return { term: "", range: null };
  }

  const wordRange = document.createRange();
  wordRange.setStart(node, start);
  wordRange.setEnd(node, end);
  return { term, range: wordRange };
}

function highlightRange(range, term) {
  const mark = document.createElement("mark");
  mark.className = "vocab-mark";
  mark.dataset.term = term;

  try {
    range.surroundContents(mark);
  } catch {
  }
}

async function addVocabEntry(term, context, paragraphIndex = 0) {
  const existing = vocabEntries.find((entry) =>
    entry.term.toLowerCase() === term.toLowerCase() && entry.paragraphIndex === paragraphIndex
  );
  if (existing) {
    renderVocabList();
    return;
  }

  const pending = { term, paragraphIndex, part_of_speech: "处理中", definition_zh: "正在调用 DeepSeek...", example_zh: "" };
  vocabEntries.push(pending);
  renderVocabList();

  try {
    const response = await fetch("/api/vocab", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term, context }),
    });
    const result = await response.json();
    if (!response.ok || result.error) {
      throw new Error(result.error || "生词处理失败");
    }
    Object.assign(pending, result.entry);
  } catch (error) {
    pending.part_of_speech = "error";
    pending.definition_zh = error.message;
  }

  renderVocabList();
}

function renderVocabList() {
  const count = document.querySelector("#vocab-count");
  const paragraphLists = document.querySelectorAll(".paragraph-vocab-list");
  if (!count || !paragraphLists.length) {
    return;
  }

  paragraphLists.forEach((list) => {
    list.innerHTML = "";
  });

  if (!vocabEntries.length) {
    count.textContent = "还没有标注。";
    return;
  }

  count.textContent = `已标注 ${vocabEntries.length} 个生词。`;
  for (const entry of vocabEntries) {
    const list = document.querySelector(`.paragraph-vocab-list[data-paragraph="${entry.paragraphIndex}"]`);
    if (!list) {
      continue;
    }
    list.insertAdjacentHTML("beforeend", `
    <article class="vocab-card">
      <div class="vocab-card-head">
        <span class="vocab-term">${escapeHtml(entry.term)}</span>
        <button class="speak-button speak-word" type="button" data-speak="word" data-text="${escapeHtml(entry.term)}" aria-label="朗读 ${escapeHtml(entry.term)}">🔊</button>
      </div>
      <p>${escapeHtml(entry.part_of_speech)} ${escapeHtml(entry.definition_zh)}</p>
      ${entry.example_zh ? `<small>${escapeHtml(entry.example_zh)}</small>` : ""}
    </article>
    `);
  }
}

function hydrateSpeechControls() {
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
    return;
  }

  ttsVoices = window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => {
    ttsVoices = window.speechSynthesis.getVoices();
  };
}

function handleSpeakButton(button) {
  const mode = button.dataset.speak;
  if (mode === "all") {
    speakText(getWholeArticleText(), button);
    return;
  }

  if (mode === "paragraph") {
    const row = button.closest(".sheet-row");
    speakText(row?.querySelector(".sheet-en")?.textContent || "", button);
    return;
  }

  if (mode === "word") {
    speakText(button.dataset.text || button.closest(".vocab-card")?.querySelector(".vocab-term")?.textContent || "", button);
  }
}

function getWholeArticleText() {
  return Array.from(document.querySelectorAll(".sheet-en"))
    .map((node) => node.textContent.trim())
    .filter(Boolean)
    .join("\n\n");
}

async function speakText(text, button) {
  const cleanText = String(text || "").replace(/\s+/g, " ").trim();
  if (!cleanText) {
    return;
  }

  stopSpeech();
  const runId = ++ttsRunId;
  const profile = document.querySelector("#voice-profile")?.value || "us-female";
  const rate = document.querySelector("#voice-rate")?.value || "1";

  button?.classList.add("is-speaking");
  try {
    await speakTextWithApi(cleanText, profile, rate, runId);
  } catch (error) {
    if ("speechSynthesis" in window && "SpeechSynthesisUtterance" in window && runId === ttsRunId) {
      await speakTextWithBrowser(cleanText, profile, rate, runId);
    } else {
      renderWarnings([error.message || "朗读生成失败"]);
    }
  } finally {
    if (runId === ttsRunId) {
      button?.classList.remove("is-speaking");
    }
  }
}

async function speakTextWithApi(text, profile, rate, runId) {
  const chunks = splitSpeechText(text);
  for (const chunk of chunks) {
    if (runId !== ttsRunId) {
      return;
    }
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: chunk,
        output: document.querySelector("#output").value.trim() || "output",
        voice_profile: profile,
        rate,
      }),
    });
    const result = await response.json();
    if (!response.ok || result.error) {
      throw new Error(result.error || "朗读音频生成失败");
    }
    const audioUrl = `/download?path=${encodeURIComponent(result.file)}`;
    await playAudioUrl(audioUrl, runId);
  }
}

function splitSpeechText(text) {
  const paragraphs = String(text).split(/\n{2,}/).map((item) => item.trim()).filter(Boolean);
  const chunks = [];
  let current = "";
  for (const paragraph of paragraphs.length ? paragraphs : [text]) {
    if ((current + "\n\n" + paragraph).length > 2800 && current) {
      chunks.push(current);
      current = paragraph;
    } else {
      current = current ? `${current}\n\n${paragraph}` : paragraph;
    }
  }
  if (current) {
    chunks.push(current);
  }
  return chunks.flatMap((chunk) => {
    if (chunk.length <= 3200) {
      return [chunk];
    }
    return chunk.match(/.{1,2800}(?:\s|$)/g)?.map((item) => item.trim()).filter(Boolean) || [chunk.slice(0, 3200)];
  });
}

function playAudioUrl(url, runId) {
  return new Promise((resolve, reject) => {
    if (runId !== ttsRunId) {
      resolve();
      return;
    }
    currentAudio = new Audio(url);
    currentAudio.onended = () => resolve();
    currentAudio.onerror = () => reject(new Error("音频播放失败"));
    currentAudio.play().catch(reject);
  });
}

function speakTextWithBrowser(text, profile, rate, runId) {
  return new Promise((resolve, reject) => {
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = chooseVoice(profile);
    utterance.lang = profile.startsWith("uk") ? "en-GB" : "en-US";
    utterance.rate = Number(rate || 1);
    utterance.pitch = profile.endsWith("male") ? 0.92 : 1.04;
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang || utterance.lang;
    }
    utterance.onend = () => resolve();
    utterance.onerror = () => reject(new Error("浏览器朗读失败"));
    if (runId === ttsRunId) {
      window.speechSynthesis.speak(utterance);
    }
  });
}

function chooseVoice(profile) {
  const voices = ttsVoices.length ? ttsVoices : window.speechSynthesis.getVoices();
  if (profile === "default" || !voices.length) {
    return null;
  }

  const lang = profile.startsWith("uk") ? "en-GB" : "en-US";
  const genderHints = profile.endsWith("male")
    ? ["david", "mark", "guy", "george", "james", "ryan", "daniel", "male"]
    : ["zira", "jenny", "aria", "libby", "sonia", "hazel", "susan", "female"];
  const languageMatches = voices.filter((voice) => String(voice.lang || "").toLowerCase().startsWith(lang.toLowerCase()));
  const hinted = languageMatches.find((voice) => {
    const name = String(voice.name || "").toLowerCase();
    return genderHints.some((hint) => name.includes(hint));
  });
  return hinted || languageMatches[0] || voices.find((voice) => String(voice.lang || "").toLowerCase().startsWith("en")) || null;
}

function stopSpeech() {
  ttsRunId += 1;
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  document.querySelectorAll(".speak-button.is-speaking, .tts-action.is-speaking").forEach((button) => {
    button.classList.remove("is-speaking");
  });
}

function renderWarnings(items) {
  if (!items.length) {
    warnings.hidden = true;
    warnings.innerHTML = "";
    return;
  }
  warnings.hidden = false;
  warnings.innerHTML = items.map((item) => `<p>${escapeHtml(item)}</p>`).join("");
}

function renderDownloads(files = {}) {
  const labels = { txt: "原文 TXT", zh: "中文 TXT", practice: "双语跟读稿", json: "JSON" };
  downloadLinks.innerHTML = Object.entries(files)
    .map(([key, path]) => `<a href="/download?path=${encodeURIComponent(path)}">${labels[key] || key}</a>`)
    .join("");
}

function renderLine(item) {
  return `
    <article class="line">
      <span class="time">${escapeHtml(formatTimestamp(item.start || 0))}</span>
      <div>
        <p class="en">${escapeHtml(item.text || "")}</p>
        ${item.text_zh ? `<p class="zh">${escapeHtml(item.text_zh)}</p>` : ""}
      </div>
    </article>
  `;
}

function formatTimestamp(seconds) {
  const totalMs = Math.round(Number(seconds) * 1000);
  const hours = Math.floor(totalMs / 3600000);
  const minutes = Math.floor((totalMs % 3600000) / 60000);
  const secs = Math.floor((totalMs % 60000) / 1000);
  const millis = totalMs % 1000;
  return `${pad(hours)}:${pad(minutes)}:${pad(secs)}.${String(millis).padStart(3, "0")}`;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
