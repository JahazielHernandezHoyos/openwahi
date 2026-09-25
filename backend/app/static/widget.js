/**
 * OpenWahi Chat Widget v2
 *
 * Embed on any website:
 *   <script src="https://your-backend.example.com/static/widget.js"
 *           data-widget-token="wgt_...">
 *   </script>
 *
 * Optional data attributes:
 *   data-title            — Chat window title  (default: "Soporte")
 *   data-placeholder      — Input placeholder  (default: "Escribe un mensaje...")
 *   data-primary-color    — Primary hex color  (overrides DB config)
 *   data-secondary-color  — Secondary hex color (overrides DB config)
 *   data-position         — "right" | "left"   (default: "right")
 *   data-dark             — "true" to force dark mode
 *
 * When loaded via next/script (document.currentScript === null), the host page
 * must set window globals before loading this script:
 *   window.__OPENWAHI_TOKEN__
 *   window.__OPENWAHI_BACKEND_URL__
 *   window.__OPENWAHI_TITLE__         (optional)
 *   window.__OPENWAHI_PLACEHOLDER__   (optional)
 *   window.__OPENWAHI_PRIMARY_COLOR__ (optional)
 *   window.__OPENWAHI_SECONDARY_COLOR__(optional)
 *   window.__OPENWAHI_POSITION__      (optional)
 *   window.__OPENWAHI_DARK__          (optional, boolean)
 */
(function () {
  "use strict";

  // ── Guard: prevent double-init ────────────────────────────────────────────
  if (window.__OPENWAHI_WIDGET_LOADED__) return;
  window.__OPENWAHI_WIDGET_LOADED__ = true;

  // ── Config resolution ─────────────────────────────────────────────────────
  // Priority: data-attribute > window global > default
  var script = document.currentScript || (function () {
    var tags = document.querySelectorAll("script[data-widget-token]");
    return tags.length ? tags[tags.length - 1] : null;
  })();

  function attr(name, winKey, def) {
    if (script && script.getAttribute(name)) return script.getAttribute(name);
    if (window[winKey] !== undefined && window[winKey] !== null && window[winKey] !== "")
      return window[winKey];
    return def;
  }

  var BACKEND_URL = (script && script.src)
    ? script.src.replace(/\/static\/widget\.js.*$/, "")
    : (window.__OPENWAHI_BACKEND_URL__ || "");

  var TOKEN          = attr("data-widget-token",    "__OPENWAHI_TOKEN__",           "");
  var TITLE          = attr("data-title",            "__OPENWAHI_TITLE__",           "Soporte");
  var PLACEHOLDER    = attr("data-placeholder",      "__OPENWAHI_PLACEHOLDER__",     "Escribe un mensaje...");
  var POSITION       = attr("data-position",         "__OPENWAHI_POSITION__",        "right");
  var FORCE_DARK     = attr("data-dark",             "__OPENWAHI_DARK__",            false);

  // Colors start as nulls; they'll be resolved from DB config first, then these overrides
  var COLOR_OVERRIDE   = attr("data-primary-color",   "__OPENWAHI_PRIMARY_COLOR__",   null);
  var COLOR2_OVERRIDE  = attr("data-secondary-color", "__OPENWAHI_SECONDARY_COLOR__", null);

  if (!TOKEN) {
    console.warn("[OpenWahi Widget] data-widget-token is required.");
    return;
  }
  if (!BACKEND_URL) {
    console.warn("[OpenWahi Widget] could not determine backend URL.");
    return;
  }

  // ── Theme defaults ────────────────────────────────────────────────────────
  var isDark = FORCE_DARK === true || FORCE_DARK === "true";

  // Light theme defaults (for external clients)
  var theme = {
    bubbleBg:    "#2563eb",
    bubbleText:  "#ffffff",
    winBg:       "#ffffff",
    winBorder:   "#e2e8f0",
    headerBg:    "#2563eb",
    headerText:  "#ffffff",
    msgUserBg:   "#2563eb",
    msgUserText: "#ffffff",
    msgBotBg:    "#f1f5f9",
    msgBotText:  "#1e293b",
    inputBg:     "#ffffff",
    inputBorder: "#e2e8f0",
    inputText:   "#0f172a",
    inputFocus:  "#2563eb",
    sendBg:      "#2563eb",
    divider:     "#e2e8f0",
    typingText:  "#94a3b8",
  };

  // Dark theme (for sites that want a dark widget)
  if (isDark) {
    theme = {
      bubbleBg:    "#2563eb",
      bubbleText:  "#ffffff",
      winBg:       "#0f0f0f",
      winBorder:   "#262626",
      headerBg:    "#111111",
      headerText:  "#f8fafc",
      msgUserBg:   "#2563eb",
      msgUserText: "#ffffff",
      msgBotBg:    "#1a1a1a",
      msgBotText:  "#e2e8f0",
      inputBg:     "#1a1a1a",
      inputBorder: "#333333",
      inputText:   "#f1f5f9",
      inputFocus:  "#2563eb",
      sendBg:      "#2563eb",
      divider:     "#262626",
      typingText:  "#64748b",
    };
  }

  // ── Visitor ID ────────────────────────────────────────────────────────────
  var VISITOR_KEY = "openwahi_visitor_id";
  var visitorId = localStorage.getItem(VISITOR_KEY);
  if (!visitorId) {
    visitorId = (typeof crypto !== "undefined" && crypto.randomUUID)
      ? crypto.randomUUID()
      : "v-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem(VISITOR_KEY, visitorId);
  }

  // ── Fetch remote config (colors) then render ──────────────────────────────
  function fetchConfigAndInit() {
    var url = BACKEND_URL + "/widget/config?widget_token=" + encodeURIComponent(TOKEN);
    fetch(url, { method: "GET" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (cfg) {
        if (cfg) {
          // Apply DB colors first, then per-embed overrides win
          var primary   = COLOR_OVERRIDE  || cfg.primary_color   || null;
          var secondary = COLOR2_OVERRIDE || cfg.secondary_color || null;
          if (primary) {
            theme.bubbleBg   = primary;
            theme.headerBg   = primary;
            theme.msgUserBg  = primary;
            theme.inputFocus = primary;
            theme.sendBg     = primary;
          }
          if (secondary) {
            theme.msgBotBg = secondary;
          }
        }
        renderWidget();
      })
      .catch(function () {
        // Fallback: proceed with defaults / overrides even if config fetch fails
        if (COLOR_OVERRIDE) {
          theme.bubbleBg   = COLOR_OVERRIDE;
          theme.headerBg   = COLOR_OVERRIDE;
          theme.msgUserBg  = COLOR_OVERRIDE;
          theme.inputFocus = COLOR_OVERRIDE;
          theme.sendBg     = COLOR_OVERRIDE;
        }
        if (COLOR2_OVERRIDE) {
          theme.msgBotBg = COLOR2_OVERRIDE;
        }
        renderWidget();
      });
  }

  // ── CSS ───────────────────────────────────────────────────────────────────
  function buildCss(t) {
    return [
      /* Bubble */
      "#openwahi-bubble{",
        "position:fixed;bottom:24px;" + POSITION + ":24px;",
        "width:56px;height:56px;border-radius:50%;",
        "background:" + t.bubbleBg + ";color:" + t.bubbleText + ";",
        "cursor:pointer;",
        "box-shadow:0 4px 20px rgba(0,0,0,.35);",
        "display:flex;align-items:center;justify-content:center;",
        "z-index:2147483647;border:none;outline:none;",
        "transition:transform .2s,box-shadow .2s;",
      "}",
      "#openwahi-bubble:hover{transform:scale(1.08);box-shadow:0 6px 24px rgba(0,0,0,.45);}",
      "#openwahi-bubble svg{width:26px;height:26px;fill:" + t.bubbleText + ";pointer-events:none;}",

      /* Window */
      "#openwahi-window{",
        "display:none;position:fixed;bottom:90px;" + POSITION + ":24px;",
        "width:368px;max-width:calc(100vw - 32px);",
        "height:540px;max-height:calc(100vh - 110px);",
        "background:" + t.winBg + ";",
        "border:1px solid " + t.winBorder + ";",
        "border-radius:16px;",
        "box-shadow:0 12px 40px rgba(0,0,0,.3);",
        "z-index:2147483647;",
        "flex-direction:column;overflow:hidden;",
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;",
        "animation:openwahiSlideIn .22s cubic-bezier(.175,.885,.32,1.1) both;",
      "}",
      "#openwahi-window.open{display:flex;}",
      "@keyframes openwahiSlideIn{from{opacity:0;transform:translateY(12px) scale(.97)}to{opacity:1;transform:none}}",

      /* Header */
      "#openwahi-header{",
        "background:" + t.headerBg + ";",
        "color:" + t.headerText + ";",
        "padding:14px 16px;",
        "font-size:15px;font-weight:600;",
        "display:flex;align-items:center;justify-content:space-between;",
        "flex-shrink:0;",
      "}",
      "#openwahi-header-info{display:flex;align-items:center;gap:10px;}",
      "#openwahi-avatar{",
        "width:36px;height:36px;border-radius:50%;",
        "background:rgba(255,255,255,.2);",
        "display:flex;align-items:center;justify-content:center;flex-shrink:0;",
      "}",
      "#openwahi-avatar svg{width:20px;height:20px;fill:" + t.headerText + ";}",
      "#openwahi-header-text{}",
      "#openwahi-header-name{font-size:14px;font-weight:700;line-height:1.2;}",
      "#openwahi-header-status{font-size:11px;opacity:.8;display:flex;align-items:center;gap:4px;}",
      "#openwahi-status-dot{",
        "width:7px;height:7px;border-radius:50%;background:#22c55e;",
        "box-shadow:0 0 0 2px rgba(34,197,94,.3);",
        "animation:openwahiPulse 2s infinite;",
      "}",
      "@keyframes openwahiPulse{0%,100%{opacity:1}50%{opacity:.5}}",
      "#openwahi-close-btn{",
        "background:rgba(255,255,255,.15);border:none;",
        "color:" + t.headerText + ";cursor:pointer;",
        "width:28px;height:28px;border-radius:50%;",
        "display:flex;align-items:center;justify-content:center;",
        "font-size:18px;line-height:1;padding:0;",
        "transition:background .15s;",
      "}",
      "#openwahi-close-btn:hover{background:rgba(255,255,255,.25);}",

      /* Messages */
      "#openwahi-messages{",
        "flex:1;overflow-y:auto;",
        "padding:16px 14px;",
        "display:flex;flex-direction:column;gap:10px;",
        "font-size:14px;",
        "scrollbar-width:thin;",
        "scrollbar-color:" + t.winBorder + " transparent;",
      "}",
      "#openwahi-messages::-webkit-scrollbar{width:4px;}",
      "#openwahi-messages::-webkit-scrollbar-track{background:transparent;}",
      "#openwahi-messages::-webkit-scrollbar-thumb{background:" + t.winBorder + ";border-radius:2px;}",

      /* Messages — bubbles */
      ".openwahi-msg{",
        "max-width:82%;padding:10px 14px;border-radius:16px;",
        "line-height:1.5;word-break:break-word;",
        "font-size:13.5px;",
        "animation:openwahiFadeMsg .18s ease both;",
      "}",
      "@keyframes openwahiFadeMsg{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}",
      ".openwahi-msg.user{",
        "background:" + t.msgUserBg + ";color:" + t.msgUserText + ";",
        "align-self:flex-end;border-bottom-right-radius:4px;",
        "margin-left:auto;",
      "}",
      ".openwahi-msg.assistant{",
        "background:" + t.msgBotBg + ";color:" + t.msgBotText + ";",
        "align-self:flex-start;border-bottom-left-radius:4px;",
      "}",

      /* Typing indicator */
      ".openwahi-typing{display:flex;align-items:center;gap:4px;padding:12px 14px;}",
      ".openwahi-typing span{",
        "width:8px;height:8px;border-radius:50%;",
        "background:" + t.typingText + ";",
        "animation:openwahiDot 1.2s infinite;",
      "}",
      ".openwahi-typing span:nth-child(2){animation-delay:.2s;}",
      ".openwahi-typing span:nth-child(3){animation-delay:.4s;}",
      "@keyframes openwahiDot{0%,80%,100%{transform:scale(.8);opacity:.5}40%{transform:scale(1.1);opacity:1}}",

      /* Input row */
      "#openwahi-input-row{",
        "display:flex;gap:8px;padding:10px 12px;",
        "border-top:1px solid " + t.divider + ";",
        "background:" + t.winBg + ";",
        "flex-shrink:0;",
      "}",
      "#openwahi-input{",
        "flex:1;",
        "border:1.5px solid " + t.inputBorder + ";",
        "border-radius:12px;",
        "padding:9px 13px;",
        "font-family:inherit;font-size:13.5px;",
        "outline:none;resize:none;",
        "background:" + t.inputBg + ";",
        "color:" + t.inputText + ";",
        "transition:border-color .15s;",
        "min-height:38px;max-height:120px;",
        "line-height:1.45;",
      "}",
      "#openwahi-input::placeholder{color:" + t.typingText + ";}",
      "#openwahi-input:focus{border-color:" + t.inputFocus + ";}",
      "#openwahi-send{",
        "background:" + t.sendBg + ";",
        "border:none;border-radius:12px;",
        "width:40px;height:40px;min-width:40px;",
        "cursor:pointer;",
        "display:flex;align-items:center;justify-content:center;",
        "align-self:flex-end;",
        "transition:opacity .15s,transform .1s;",
      "}",
      "#openwahi-send:hover{opacity:.88;transform:scale(1.05);}",
      "#openwahi-send:disabled{opacity:.4;cursor:not-allowed;transform:none;}",
      "#openwahi-send svg{width:17px;height:17px;fill:#fff;display:block;}",

      /* Empty state */
      "#openwahi-empty{",
        "flex:1;display:flex;flex-direction:column;",
        "align-items:center;justify-content:center;",
        "padding:24px;text-align:center;",
        "color:" + t.typingText + ";font-size:13px;gap:8px;",
      "}",
      "#openwahi-empty svg{width:40px;height:40px;opacity:.4;fill:" + t.typingText + ";}",
    ].join("");
  }

  // ── HTML template ─────────────────────────────────────────────────────────
  function buildHtml() {
    return {
      bubble: [
        '<svg viewBox="0 0 24 24" aria-hidden="true">',
          '<path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>',
        '</svg>',
      ].join(""),

      window: [
        '<div id="openwahi-header">',
          '<div id="openwahi-header-info">',
            '<div id="openwahi-avatar">',
              '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg>',
            '</div>',
            '<div id="openwahi-header-text">',
              '<div id="openwahi-header-name">' + escapeHtml(TITLE) + '</div>',
              '<div id="openwahi-header-status">',
                '<div id="openwahi-status-dot"></div>',
                '<span>En línea</span>',
              '</div>',
            '</div>',
          '</div>',
          '<button id="openwahi-close-btn" aria-label="Cerrar chat">',
            '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
          '</button>',
        '</div>',
        '<div id="openwahi-messages" role="log" aria-live="polite" aria-label="Mensajes">',
          '<div id="openwahi-empty">',
            '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/></svg>',
            '<p>¿En qué podemos ayudarte hoy?</p>',
          '</div>',
        '</div>',
        '<div id="openwahi-input-row">',
          '<textarea id="openwahi-input" rows="1"',
            ' placeholder="' + escapeHtml(PLACEHOLDER) + '"',
            ' aria-label="Mensaje"',
          '></textarea>',
          '<button id="openwahi-send" aria-label="Enviar mensaje">',
            '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
          '</button>',
        '</div>',
      ].join(""),
    };
  }

  // ── Render ────────────────────────────────────────────────────────────────
  function renderWidget() {
    // Inject CSS
    var style = document.createElement("style");
    style.id = "openwahi-widget-styles";
    style.textContent = buildCss(theme);
    document.head.appendChild(style);

    // Bubble
    var bubble = document.createElement("button");
    bubble.id = "openwahi-bubble";
    bubble.setAttribute("aria-label", "Abrir chat");
    bubble.setAttribute("aria-expanded", "false");
    var html = buildHtml();
    bubble.innerHTML = html.bubble;
    document.body.appendChild(bubble);

    // Chat window
    var win = document.createElement("div");
    win.id = "openwahi-window";
    win.setAttribute("role", "dialog");
    win.setAttribute("aria-modal", "true");
    win.setAttribute("aria-label", TITLE);
    win.innerHTML = html.window;
    document.body.appendChild(win);

    // DOM refs
    var messagesEl  = document.getElementById("openwahi-messages");
    var emptyEl     = document.getElementById("openwahi-empty");
    var inputEl     = document.getElementById("openwahi-input");
    var sendBtn     = document.getElementById("openwahi-send");
    var closeBtnEl  = document.getElementById("openwahi-close-btn");
    var isOpen      = false;
    var isSending   = false;
    var historyLoaded = false;

    // ── Helpers ──────────────────────────────────────────────────────────
    function escapeHtmlInline(str) {
      return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function renderText(str) {
      // Convert newlines to <br>, escape HTML
      return escapeHtmlInline(str).replace(/\n/g, "<br>");
    }

    function appendMessage(role, content, isTyping) {
      if (emptyEl && emptyEl.parentNode === messagesEl) {
        messagesEl.removeChild(emptyEl);
      }

      var el = document.createElement("div");
      if (isTyping) {
        el.className = "openwahi-typing";
        el.innerHTML = "<span></span><span></span><span></span>";
      } else {
        el.className = "openwahi-msg " + role;
        el.innerHTML = renderText(content);
      }
      messagesEl.appendChild(el);
      return el;
    }

    function scrollToBottom(smooth) {
      if (smooth) {
        messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: "smooth" });
      } else {
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }
    }

    function autoResize() {
      inputEl.style.height = "auto";
      inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
    }

    // ── Toggle ────────────────────────────────────────────────────────────
    function openWidget() {
      isOpen = true;
      win.classList.add("open");
      bubble.setAttribute("aria-expanded", "true");
      inputEl.focus();
      if (!historyLoaded) {
        historyLoaded = true;
        loadHistory();
      }
    }

    function closeWidget() {
      isOpen = false;
      win.classList.remove("open");
      bubble.setAttribute("aria-expanded", "false");
    }

    bubble.addEventListener("click", function () {
      isOpen ? closeWidget() : openWidget();
    });
    closeBtnEl.addEventListener("click", closeWidget);

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isOpen) closeWidget();
    });

    // ── Load history ──────────────────────────────────────────────────────
    function loadHistory() {
      var url = BACKEND_URL + "/widget/history"
        + "?widget_token=" + encodeURIComponent(TOKEN)
        + "&visitor_id="   + encodeURIComponent(visitorId);

      fetch(url, { method: "GET" })
        .then(function (r) {
          // 404 means no prior conversation — that is fine, not an error
          if (r.status === 404) return null;
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (data) {
          if (!data || !Array.isArray(data.messages) || data.messages.length === 0) return;
          data.messages.forEach(function (m) {
            appendMessage(m.role, m.content);
          });
          scrollToBottom(false);
        })
        .catch(function (err) {
          console.warn("[OpenWahi Widget] Could not load history:", err);
        });
    }

    // ── Send message ──────────────────────────────────────────────────────
    function send() {
      var text = inputEl.value.trim();
      if (!text || isSending) return;

      appendMessage("user", text);
      inputEl.value = "";
      autoResize();
      scrollToBottom(true);

      var typingEl = appendMessage("assistant", null, true);
      isSending = true;
      sendBtn.disabled = true;

      fetch(BACKEND_URL + "/widget/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          visitor_id:   visitorId,
          message:      text,
          widget_token: TOKEN,
        }),
      })
        .then(function (r) {
          if (!r.ok) {
            return r.json().then(function (body) {
              throw new Error(body.detail || "HTTP " + r.status);
            });
          }
          return r.json();
        })
        .then(function (data) {
          if (typingEl.parentNode === messagesEl) messagesEl.removeChild(typingEl);
          appendMessage("assistant", data.reply || "Sin respuesta del servidor.");
          scrollToBottom(true);
        })
        .catch(function (err) {
          if (typingEl.parentNode === messagesEl) messagesEl.removeChild(typingEl);
          var msg = err && err.message
            ? "Error: " + err.message
            : "Error de conexión. Intenta de nuevo.";
          appendMessage("assistant", msg);
          scrollToBottom(true);
          console.error("[OpenWahi Widget] Chat error:", err);
        })
        .finally(function () {
          isSending = false;
          sendBtn.disabled = false;
          inputEl.focus();
        });
    }

    sendBtn.addEventListener("click", send);
    inputEl.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });
    inputEl.addEventListener("input", autoResize);
  }

  // ── escapeHtml (needed before renderWidget runs) ──────────────────────────
  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── Kick off ───────────────────────────────────────────────────────────────
  fetchConfigAndInit();

})();
