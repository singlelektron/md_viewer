"use strict";

(() => {
  const content = document.getElementById("document");
  const viewport = document.getElementById("viewport");
  const title = document.getElementById("document-title");
  const status = document.getElementById("status");
  const theme = document.getElementById("theme");
  const empty = document.getElementById("empty-state");
  const error = document.getElementById("error");
  const themes = new Set(["moonlit", "graphite", "paper"]);
  let revision = -1;
  let eventCount = 0;
  let themeRequest = 0;
  let renderGeneration = 0;
  let html = null;
  let documentName = null;

  function showError(message) {
    error.textContent = message || "";
    error.hidden = !message;
  }

  // Anchor by an existing block where possible, then fall back to scroll offset.
  // Replacing content should not send a reader back to the top while typing.
  function rememberScroll() {
    const top = viewport.getBoundingClientRect().top;
    const blocks = [...content.children];
    const index = blocks.findIndex((block) => block.getBoundingClientRect().bottom > top);
    const block = blocks[index];
    return {
      index,
      text: block?.textContent,
      offset: block ? block.getBoundingClientRect().top - top : 0,
      scrollTop: viewport.scrollTop,
    };
  }

  function restoreScroll(anchor) {
    if (anchor.scrollTop < 2) {
      viewport.scrollTop = 0;
      return;
    }
    const blocks = [...content.children];
    const exact = anchor.text && blocks.find((block) => block.textContent === anchor.text);
    const block = exact || blocks[anchor.index];
    if (block) {
      const top = block.getBoundingClientRect().top - viewport.getBoundingClientRect().top;
      viewport.scrollTop += top - anchor.offset;
    } else {
      viewport.scrollTop = anchor.scrollTop;
    }
  }

  function typesetMath() {
    for (const node of content.querySelectorAll(".math-inline, .math-display")) {
      const source = node.getAttribute("data-tex") || "";
      if (!window.katex) {
        node.textContent = source;
        node.classList.add("katex-error");
        continue;
      }
      try {
        window.katex.render(source, node, {
          displayMode: node.classList.contains("math-display"),
          throwOnError: false,
          trust: false,
          strict: "warn",
          maxExpand: 1000,
          maxSize: 20,
          output: "htmlAndMathml",
          errorColor: "currentColor",
        });
      } catch {
        // Do not inject error HTML: parse errors may contain arbitrary source.
        node.textContent = source;
        node.classList.add("katex-error");
      }
    }
    keepMathPunctuation();
  }

  function keepMathPunctuation() {
    // WebKit can break after an atomic formula even before closing punctuation.
    // Keep that suffix in one inline box, preserving its original markup and text.
    for (const math of content.querySelectorAll(".math-inline")) {
      let next = math;
      while (next) {
        if (next.nextSibling) {
          next = next.nextSibling;
          while (next.nodeType === Node.ELEMENT_NODE &&
                 getComputedStyle(next).display === "inline" && next.firstChild) {
            next = next.firstChild;
          }
          break;
        }
        next = next.parentElement;
        if (!next || next === content || getComputedStyle(next).display !== "inline") {
          next = null;
        }
      }
      if (next?.nodeType !== Node.TEXT_NODE) continue;
      const suffix = next.textContent.match(/^[ \t\r\n]*[.,;:!?…。，、；：！？）)\]】》〉」』”’]+/u)?.[0];
      if (!suffix) continue;

      const range = document.createRange();
      range.setStartBefore(math);
      range.setEnd(next, suffix.length);
      const parent = range.commonAncestorContainer;
      const group = document.createElement("span");
      group.className = "math-run";
      if (math.parentNode === parent && next.parentNode === parent) {
        group.append(range.extractContents());
        range.insertNode(group);
        continue;
      }
      // Split partial emphasis/span ancestors at the boundary rather than moving
      // punctuation into the formula's style or making the whole paragraph nowrap.
      const before = document.createRange();
      before.selectNodeContents(parent);
      before.setEndBefore(math);
      const prefix = before.extractContents();
      range.setStart(parent, 0);
      group.append(range.extractContents());
      parent.prepend(prefix, group);
    }
  }

  function applyPreview(preview) {
    if (!preview || !Number.isSafeInteger(preview.revision) || preview.revision < revision) return;
    revision = preview.revision;
    content.dataset.revision = String(revision);
    title.textContent = preview.title || "md_viewer";
    title.title = preview.title || "md_viewer";
    document.title = preview.title ? `${preview.title} — md_viewer` : "md_viewer";
    status.dataset.connected = String(Boolean(preview.connected));
    status.textContent = preview.connected
      ? (preview.modified ? "Live · unsaved" : "Live")
      : (preview.title ? "Disconnected" : "Waiting");
    status.title = preview.connected ? "Preview updates as you type" : "No active editor connection";
    if (themes.has(preview.theme)) {
      document.documentElement.dataset.theme = preview.theme;
      theme.value = preview.theme;
    }
    showError(preview.error);

    const nextHtml = preview.html || "";
    if (html !== nextHtml || documentName !== preview.title) {
      const generation = ++renderGeneration;
      const sameDocument = documentName === preview.title;
      const anchor = sameDocument ? rememberScroll() : null;
      html = nextHtml;
      documentName = preview.title;
      // Markdown HTML is produced and sanitized by the Rust core.
      content.innerHTML = html;
      content.hidden = !html;
      empty.hidden = Boolean(html);
      typesetMath();
      for (const link of content.querySelectorAll("a[href]")) {
        if (!link.getAttribute("href").startsWith("#")) {
          link.dataset.external = "true";
          link.title = "Links stay in the preview; external navigation is disabled";
        }
      }
      if (anchor) restoreScroll(anchor);
      else viewport.scrollTop = 0;
      const settledScroll = viewport.scrollTop;
      // Local math fonts may finish loading after the first layout. Restore only
      // if no newer content or user scroll has superseded this render.
      if (anchor && document.fonts) {
        document.fonts.ready.then(() => {
          if (generation === renderGeneration && viewport.scrollTop === settledScroll) {
            restoreScroll(anchor);
          }
        });
      }
    }
  }

  content.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (!link) return;
    event.preventDefault();
    const href = link.getAttribute("href");
    if (href.startsWith("#")) {
      try {
        const destination = document.getElementById(decodeURIComponent(href.slice(1)));
        if (destination && content.contains(destination)) destination.scrollIntoView({ block: "start" });
      } catch {
        // An invalid fragment has no navigation side effects.
      }
    }
  });
  // Middle-click must not open a second WebView either.
  content.addEventListener("auxclick", (event) => {
    if (event.target.closest("a[href]")) event.preventDefault();
  });

  async function initialize() {
    const api = window.__TAURI__;
    if (!api?.core?.invoke || !api?.event?.listen) {
      status.textContent = "Unavailable";
      showError("Open md_viewer as a desktop application to connect your note.");
      theme.disabled = true;
      return;
    }

    theme.addEventListener("change", async () => {
      const request = ++themeRequest;
      const count = eventCount;
      try {
        const preview = await api.core.invoke("set_theme", { theme: theme.value });
        if (request === themeRequest && count === eventCount) applyPreview(preview);
      } catch {
        if (request === themeRequest) {
          theme.value = document.documentElement.dataset.theme;
          showError("Could not change the theme. Please try again.");
        }
      }
    });

    try {
      await api.event.listen("preview-updated", (event) => {
        eventCount += 1;
        applyPreview(event.payload);
      });
      const count = eventCount;
      const preview = await api.core.invoke("get_preview");
      // An editor update may arrive while the initial command is in flight.
      if (count === eventCount) applyPreview(preview);
      await api.core.invoke("frontend_ready");
    } catch {
      status.textContent = "Unavailable";
      status.dataset.connected = "false";
      showError("Could not connect to the preview. Close this window and start it again from Neovim.");
    }
  }

  initialize();
})();
