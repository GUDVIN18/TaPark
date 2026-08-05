/**
 * TA-Park AI Chat Widget
 * Самодостаточный виджет с изоляцией стилей через Shadow DOM
 */
(function () {
  'use strict';

  const WIDGET_TAG = 'ta-park-chat-widget';

  const STYLES = `
    :host {
      all: initial;
      display: block;
      position: fixed;
      z-index: 2147483647;
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color-scheme: light;
      --ink: #211738;
      --muted: #756d86;
      --primary: #542b86;
      --primary-dark: #35165f;
      --accent: #9b68ff;
      --mint: #48d3aa;
      --surface: #ffffff;
      --canvas: #f5f3fb;
      --line: rgba(61, 37, 96, 0.11);
      --shadow: 0 28px 80px rgba(47, 24, 79, 0.22);
    }
    :host([position="bottom-left"]) { left: 28px; right: auto; bottom: 26px; }
    :host(:not([position="bottom-left"])) { right: 28px; bottom: 26px; }
    *, *::before, *::after { box-sizing: border-box; }
    button, textarea { font: inherit; -webkit-tap-highlight-color: transparent; }

    .launcher {
      display: grid; width: 76px; height: 76px; place-items: center;
      color: var(--primary-dark); border: 0; border-radius: 26px; cursor: pointer;
      background: linear-gradient(135deg, #58d8b6 0%, #9b68ff 92%);
      box-shadow: 0 20px 45px rgba(71, 40, 118, 0.3);
      transition: transform 200ms ease, box-shadow 200ms ease, opacity 180ms ease;
    }
    .launcher:hover { transform: translateY(-4px) scale(1.03); box-shadow: 0 24px 54px rgba(71, 40, 118, 0.38); }
    .launcher[aria-expanded="true"] { pointer-events: none; opacity: 0; transform: scale(0.75); }
    .launcher-icon {
      display: grid; width: 43px; height: 36px; place-items: center;
      border-radius: 50%; background: white; box-shadow: 0 8px 18px rgba(53, 22, 95, 0.15);
    }
    .launcher-badge {
      position: absolute; top: -7px; right: -5px; display: grid; min-width: 30px; height: 30px;
      padding: 0 7px; place-items: center; color: white; font-size: 14px; font-weight: 900;
      border: 4px solid var(--canvas); border-radius: 999px; background: #ff5e7e;
    }

    .panel {
      position: fixed; z-index: 2147483647; display: grid;
      width: min(430px, calc(100vw - 32px)); height: min(700px, calc(100vh - 52px));
      overflow: hidden; grid-template-rows: auto minmax(0, 1fr) auto auto;
      border: 1px solid rgba(66, 41, 101, 0.1); border-radius: 30px;
      background: var(--surface); box-shadow: var(--shadow);
      opacity: 0; visibility: hidden; transform: translateY(30px) scale(0.94);
      transform-origin: bottom right; transition: opacity 220ms ease, transform 220ms ease, visibility 220ms;
    }
    :host([position="bottom-left"]) .panel { left: 28px; right: auto; bottom: 26px; transform-origin: bottom left; }
    :host(:not([position="bottom-left"])) .panel { right: 28px; bottom: 26px; }
    .panel.is-open { opacity: 1; visibility: visible; transform: translateY(0) scale(1); }

    .header {
      display: flex; align-items: center; gap: 13px; padding: 21px 20px; color: white;
      background: radial-gradient(circle at 12% -30%, rgba(105, 220, 188, 0.55), transparent 48%),
                  linear-gradient(135deg, #35165f, #582e88);
    }
    .avatar {
      display: grid; flex: 0 0 auto; width: 50px; height: 50px; place-items: center;
      color: var(--primary-dark); font-size: 19px; font-weight: 900; border-radius: 17px;
      background: linear-gradient(135deg, #5ed9b9, #9e6eff); box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);
    }
    .info { min-width: 0; flex: 1; }
    .info strong { display: block; overflow: hidden; font-size: 17px; text-overflow: ellipsis; white-space: nowrap; }
    .status { display: flex; align-items: center; gap: 7px; margin-top: 4px; color: rgba(255,255,255,0.68); font-size: 12px; }
    .status::before { width: 8px; height: 8px; content: ""; border-radius: 50%; background: #45dea5; box-shadow: 0 0 0 4px rgba(69,222,165,0.13); }
    .close-btn {
      display: grid; flex: 0 0 auto; width: 42px; height: 42px; place-items: center; color: white;
      border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; cursor: pointer;
      background: rgba(255,255,255,0.12); transition: background 150ms ease;
    }
    .close-btn:hover { background: rgba(255,255,255,0.2); }

    .messages {
      overflow-y: auto; padding: 22px 18px 14px; scroll-behavior: smooth;
      background: linear-gradient(rgba(248,247,252,0.93), rgba(248,247,252,0.93)),
                  radial-gradient(circle at 90% 10%, rgba(155,104,255,0.22), transparent 16rem);
    }
    .msg-row { display: flex; align-items: flex-end; gap: 9px; margin-bottom: 13px; animation: msgIn 230ms ease both; }
    .msg-row.user { justify-content: flex-end; }
    .msg-avatar {
      display: grid; flex: 0 0 auto; width: 28px; height: 28px; place-items: center;
      color: var(--primary-dark); font-size: 10px; font-weight: 900; border-radius: 10px;
      background: linear-gradient(135deg, #62d9b9, #aa79ff);
    }
    .msg-wrapper { display: flex; flex-direction: column; max-width: 82%; align-items: flex-start; }
    .user .msg-wrapper { align-items: flex-end; }
    .bubble {
      width: 100%; padding: 12px 14px; font-size: 14px; line-height: 1.5;
      white-space: pre-wrap; overflow-wrap: anywhere;
      border: 1px solid var(--line); border-radius: 17px 17px 17px 5px;
      background: white; box-shadow: 0 7px 18px rgba(56,34,86,0.05);
    }
    .user .bubble {
      color: white; border: 0; border-radius: 17px 17px 5px 17px;
      background: linear-gradient(135deg, #573087, #7343ab); box-shadow: 0 9px 20px rgba(73,38,117,0.16);
    }
    .msg-row.error .bubble { color: #943148; border-color: rgba(207,72,104,0.2); background: #fff4f6; }

    .feedback { display: flex; gap: 6px; margin-top: 6px; margin-left: 4px; opacity: 0; animation: fbIn 300ms ease forwards 150ms; }
    .no-feedback .feedback { display: none; }
    .fb-btn {
      display: grid; place-items: center; width: 28px; height: 28px; padding: 0;
      border: 1px solid var(--line); border-radius: 8px; background: white; color: var(--muted);
      cursor: pointer; transition: all 150ms ease;
    }
    .fb-btn svg { width: 14px; height: 14px; stroke-width: 2; }
    .fb-btn:hover:not(.is-active):not(:disabled) { border-color: var(--accent); color: var(--accent); background: #fbf9ff; }
    .fb-btn.is-active.like { background: var(--mint); border-color: var(--mint); color: white; }
    .fb-btn.is-active.dislike { background: #ff5e7e; border-color: #ff5e7e; color: white; }
    .fb-btn:disabled { cursor: default; opacity: 0.4; }

    .typing { display: flex; align-items: center; min-width: 62px; min-height: 42px; gap: 5px; }
    .typing span { width: 7px; height: 7px; border-radius: 50%; background: #937cab; animation: type 1.1s infinite ease-in-out; }
    .typing span:nth-child(2) { animation-delay: 120ms; }
    .typing span:nth-child(3) { animation-delay: 240ms; }

    .quick-q {
      display: flex; overflow: hidden; flex-wrap: wrap; gap: 8px; max-height: 190px;
      padding: 14px 16px; border-top: 1px solid var(--line); background: white;
      transition: max-height 200ms ease, padding 200ms ease, opacity 160ms ease;
    }
    .quick-q.hidden { max-height: 0; padding: 0; border-top-color: transparent; opacity: 0; pointer-events: none; }
    .qq-btn {
      padding: 9px 12px; color: #593386; font-size: 12px; font-weight: 750; line-height: 1.25;
      border: 1px solid rgba(139,80,225,0.42); border-radius: 999px; cursor: pointer; background: #fbf9ff;
      transition: color 150ms ease, background 150ms ease, transform 150ms ease;
    }
    .qq-btn:hover { color: white; background: var(--accent); transform: translateY(-1px); }

    .form { display: flex; align-items: flex-end; gap: 10px; padding: 14px 16px 16px; border-top: 1px solid var(--line); background: white; }
    .input-wrap {
      min-width: 0; flex: 1; padding: 2px 2px 2px 14px; border: 1px solid transparent;
      border-radius: 18px; background: #f5f3f8; transition: border-color 150ms ease, box-shadow 150ms ease;
    }
    .input-wrap:focus-within { border-color: rgba(139,80,225,0.45); box-shadow: 0 0 0 4px rgba(139,80,225,0.08); }
    .input {
      display: block; width: 100%; max-height: 110px; min-height: 48px; padding: 13px 0;
      resize: none; color: var(--ink); line-height: 1.45; border: 0; outline: 0; background: transparent;
    }
    .input::placeholder { color: #a39baa; }
    .send-btn {
      display: grid; flex: 0 0 auto; width: 50px; height: 50px; place-items: center; color: white;
      border: 0; border-radius: 17px; cursor: pointer;
      background: linear-gradient(135deg, #5d328e, #3b1867); box-shadow: 0 10px 22px rgba(62,25,106,0.22);
      transition: transform 150ms ease, opacity 150ms ease;
    }
    .send-btn:hover:not(:disabled) { transform: translateY(-2px); }
    .send-btn:disabled, .input:disabled { cursor: not-allowed; opacity: 0.55; }

    @keyframes msgIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes fbIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes type { 0%,60%,100% { opacity: 0.35; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-4px); } }

    @media (max-width: 560px) {
      .launcher { width: 68px; height: 68px; border-radius: 23px; }
      .panel { width: calc(100vw - 16px); height: min(720px, calc(100dvh - 16px)); border-radius: 25px; }
      :host([position="bottom-left"]) .panel { left: 8px; bottom: 8px; }
      :host(:not([position="bottom-left"])) .panel { right: 8px; bottom: 8px; }
      .header { padding: 17px 16px; }
      .quick-q { max-height: 230px; }
    }
  `;

  const TEMPLATE = `
    <button class="launcher" type="button" aria-label="Открыть чат" aria-controls="panel" aria-expanded="false">
      <span class="launcher-icon">
        <svg width="25" height="22" viewBox="0 0 26 23" fill="none">
          <path d="M13 1C6.37 1 1 5.48 1 11c0 2.62 1.21 5 3.19 6.78L3 22l4.96-2.15c1.53.73 3.25 1.15 5.04 1.15 6.63 0 12-4.48 12-10S19.63 1 13 1Z" fill="white"/>
          <circle cx="8" cy="11" r="1.6" fill="currentColor"/><circle cx="13" cy="11" r="1.6" fill="currentColor"/><circle cx="18" cy="11" r="1.6" fill="currentColor"/>
        </svg>
      </span>
      <span class="launcher-badge" aria-hidden="true">1</span>
    </button>

    <div class="panel" id="panel" role="dialog" aria-modal="true" aria-labelledby="chatTitle" aria-hidden="true">
      <header class="header">
        <div class="avatar" aria-hidden="true">AI</div>
        <div class="info"><strong id="chatTitle">Ассистент TA-Park</strong><span class="status">на связи · база знаний</span></div>
        <button class="close-btn" type="button" aria-label="Закрыть чат">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="m6 6 12 12M18 6 6 18" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>
        </button>
      </header>

      <div class="messages" role="log" aria-live="polite" aria-relevant="additions"></div>

      <div class="quick-q" aria-label="Частые вопросы">
        <button class="qq-btn" type="button">С чего начать?</button>
        <button class="qq-btn" type="button">Где посмотреть должников?</button>
        <button class="qq-btn" type="button">Как настроить штрафы?</button>
        <button class="qq-btn" type="button">Как создать договор?</button>
        <button class="qq-btn" type="button">Как выпустить авто на линию?</button>
        <button class="qq-btn" type="button">Как импортировать авто и водителей?</button>
      </div>

      <form class="form">
        <label class="input-wrap">
          <span style="position:absolute;width:1px;height:1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;">Сообщение</span>
          <textarea class="input" rows="1" maxlength="3000" placeholder="Спросите про TA-Park..." required></textarea>
        </label>
        <button class="send-btn" type="submit" aria-label="Отправить">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="m21 3-7.6 18-2.24-8.16L3 9.6 21 3Z" fill="currentColor"/>
            <path d="m11.16 12.84 4.57-4.57" stroke="#35165f" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
      </form>
    </div>
  `;

  class TaParkChatWidget extends HTMLElement {
    constructor() {
      super();
      this._config = {};
      this._isSending = false;
      this._userId = null;
    }

    connectedCallback() {
      const shadow = this.attachShadow({ mode: 'open' });
      shadow.innerHTML = '<style>' + STYLES + '</style>' + TEMPLATE;
      this._bindEvents(shadow);
      this._addInitialMessages(shadow);
    }

    init(config) {
      this._config = config || {};
      this._userId = config.userId || crypto.getRandomValues(new Uint32Array(1))[0] || 1;
      if (config.position) this.setAttribute('position', config.position);
    }

    _$(shadow, sel) { return shadow.querySelector(sel); }

    _bindEvents(shadow) {
      const launcher = this._$(shadow, '.launcher');
      const panel = this._$(shadow, '.panel');
      const closeBtn = this._$(shadow, '.close-btn');
      const form = this._$(shadow, '.form');
      const input = this._$(shadow, '.input');
      const sendBtn = this._$(shadow, '.send-btn');
      const messages = this._$(shadow, '.messages');
      const quickQ = this._$(shadow, '.quick-q');

      const setOpen = (open) => {
        panel.classList.toggle('is-open', open);
        panel.setAttribute('aria-hidden', String(!open));
        launcher.setAttribute('aria-expanded', String(open));
        if (open) setTimeout(() => input.focus(), 220);
        else launcher.focus();
      };

      launcher.addEventListener('click', () => setOpen(true));
      closeBtn.addEventListener('click', () => setOpen(false));
      this.addEventListener('keydown', e => { if (e.key === 'Escape' && panel.classList.contains('is-open')) setOpen(false); });

      input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 110) + 'px';
      });

      input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
      });

      form.addEventListener('submit', e => {
        e.preventDefault();
        const msg = input.value;
        input.value = '';
        input.style.height = 'auto';
        this._sendMessage(msg, shadow);
      });

      quickQ.querySelectorAll('.qq-btn').forEach(btn => {
        btn.addEventListener('click', () => this._sendMessage(btn.textContent, shadow));
      });

      messages.addEventListener('click', e => {
        const btn = e.target.closest('.fb-btn');
        if (!btn || btn.disabled) return;
        const wrapper = btn.closest('.msg-wrapper');
        const msgId = wrapper?.dataset.messageId || null;
        const msgUuid = wrapper?.dataset.messageUuid || null;
        const isLike = btn.classList.contains('like');
        const other = wrapper.querySelector(isLike ? '.fb-btn.dislike' : '.fb-btn.like');
        this._sendReaction(msgId, msgUuid, isLike, btn, other);
      });
    }

    _addInitialMessages(shadow) {
    const messages = this._$(shadow, '.messages');
    
    const first = this._createMsgEl('Привет! 👋 Я AI-ассистент TA-Park. Помогу разобраться в кабинете и отвечу на вопросы по базе знаний.', 'assistant');
    first.classList.add('no-feedback');
    messages.appendChild(first);

    const second = this._createMsgEl('С чего начнём? Выберите частый вопрос или напишите свой.', 'assistant');
    second.classList.add('no-feedback');
    messages.appendChild(second);
    }

    _scrollToBottom(shadow) {
      const m = this._$(shadow, '.messages');
      m.scrollTo({ top: m.scrollHeight, behavior: 'smooth' });
    }

    _createMsgEl(text, type, msgData) {
      msgData = msgData || {};
      const row = document.createElement('div');
      row.className = 'msg-row ' + type;

      if (type !== 'user') {
        const av = document.createElement('span');
        av.className = 'msg-avatar'; av.setAttribute('aria-hidden', 'true'); av.textContent = 'AI';
        row.appendChild(av);
      }

      const wrapper = document.createElement('div');
      wrapper.className = 'msg-wrapper';
      if (msgData.messageId) wrapper.dataset.messageId = msgData.messageId;
      if (msgData.messageUuid) wrapper.dataset.messageUuid = msgData.messageUuid;

      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      bubble.textContent = text;
      wrapper.appendChild(bubble);

      if (type === 'assistant') {
        const fb = document.createElement('div');
        fb.className = 'feedback';
        fb.innerHTML =
          '<button class="fb-btn like" type="button" aria-label="Полезный ответ"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg></button>' +
          '<button class="fb-btn dislike" type="button" aria-label="Бесполезный ответ"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg></button>';
        wrapper.appendChild(fb);
      }

      row.appendChild(wrapper);
      return row;
    }

    _createTypingEl() {
      const row = document.createElement('div');
      row.className = 'msg-row assistant';
      row.setAttribute('aria-label', 'Печатает');
      const av = document.createElement('span');
      av.className = 'msg-avatar'; av.setAttribute('aria-hidden', 'true'); av.textContent = 'AI';
      const wrapper = document.createElement('div');
      wrapper.className = 'msg-wrapper';
      const bubble = document.createElement('div');
      bubble.className = 'bubble typing';
      bubble.innerHTML = '<span></span><span></span><span></span>';
      wrapper.appendChild(bubble);
      row.append(av, wrapper);
      return row;
    }

    async _sendMessage(message, shadow) {
      const text = message.trim();
      if (!text || this._isSending) return;

      const messages = this._$(shadow, '.messages');
      const input = this._$(shadow, '.input');
      const sendBtn = this._$(shadow, '.send-btn');
      const quickQ = this._$(shadow, '.quick-q');

      quickQ.classList.add('hidden');
      messages.appendChild(this._createMsgEl(text, 'user'));
      this._scrollToBottom(shadow);

      this._isSending = true;
      input.disabled = true; sendBtn.disabled = true;

      const typing = this._createTypingEl();
      messages.appendChild(typing);
      this._scrollToBottom(shadow);

      try {
        const res = await fetch(this._config.apiEndpoint || '/ai/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Secret': this._config.apiSecret || '' },
          body: JSON.stringify({ message: text, user_id: this._userId })
        });

        let data;
        try { data = JSON.parse(await res.text()); } catch (e) { throw new Error('Неизвестный формат ответа'); }
        if (!res.ok) throw new Error(data.detail || ('Ошибка ' + res.status));
        if (!data.answer || !data.answer.trim()) throw new Error('Пустой ответ сервера');

        typing.remove();
        messages.appendChild(this._createMsgEl(data.answer.trim(), 'assistant', {
          messageId: data.message_id != null ? data.message_id : null,
          messageUuid: data.message_uuid != null ? data.message_uuid : null
        }));
      } catch (err) {
        typing.remove();
        messages.appendChild(this._createMsgEl('Не получилось связаться с ассистентом. ' + err.message, 'error'));
      } finally {
        this._isSending = false;
        input.disabled = false; sendBtn.disabled = false;
        input.focus();
        this._scrollToBottom(shadow);
      }
    }

    async _sendReaction(messageId, messageUuid, isLike, btn, otherBtn) {
      btn.classList.add('is-active');
      otherBtn.disabled = true;

      const payload = { user_id: this._userId, reaction: isLike };
      if (messageId != null) payload.message_id = Number(messageId);
      if (messageUuid) payload.message_uuid = messageUuid;

      try {
        const res = await fetch(this._config.reactionEndpoint || '/ai/set-reaction', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Secret': this._config.apiSecret || '' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Status ' + res.status);
      } catch (err) {
        console.error('Reaction error:', err);
        btn.classList.remove('is-active');
        otherBtn.disabled = false;
      }
    }
  }

  if (!customElements.get(WIDGET_TAG)) {
    customElements.define(WIDGET_TAG, TaParkChatWidget);
  }

  window.TaParkWidget = {
    init: function (config) {
      config = config || {};
      var el = document.querySelector(WIDGET_TAG);
      if (!el) {
        el = document.createElement(WIDGET_TAG);
        document.body.appendChild(el);
      }
      el.init(config);
    },
    destroy: function () {
      var el = document.querySelector(WIDGET_TAG);
      if (el) el.remove();
    }
  };
})();