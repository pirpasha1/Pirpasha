/* Shared helpers for every page. Loaded before page scripts. */
(function () {
  'use strict';

  async function api(path, { method = 'GET', body, form } = {}) {
    const opts = { method, headers: {}, credentials: 'same-origin' };
    if (form) opts.body = form;
    else if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(path, opts);
    } catch (_) {
      throw Object.assign(new Error('Network error — please check your connection'), { status: 0 });
    }
    const isJson = (res.headers.get('content-type') || '').includes('application/json');
    const data = isJson ? await res.json() : null;
    if (!res.ok) throw Object.assign(new Error((data && data.error) || `Request failed (${res.status})`), { status: res.status });
    return data;
  }

  let currency = '₹';
  function setCurrency(sym) { if (sym) currency = sym; }
  function money(cents) {
    const v = (cents / 100).toFixed(2).split('.');
    return `${currency}${Number(v[0]).toLocaleString('en-IN')}.${v[1]}`;
  }

  const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ESC[c]);

  function toast(msg, type = '') {
    let box = document.getElementById('toasts');
    if (!box) {
      box = document.createElement('div');
      box.id = 'toasts';
      box.setAttribute('role', 'status');
      box.setAttribute('aria-live', 'polite');
      document.body.appendChild(box);
    }
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    box.appendChild(t);
    setTimeout(() => t.remove(), type === 'error' ? 5000 : 2800);
  }

  /** Open a modal. `content` is an HTML string. Returns { el, close }. */
  function modal({ title, content, footer = '', onClose, wide = false }) {
    const back = document.createElement('div');
    back.className = 'modal-backdrop';
    back.innerHTML = `<div class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}" style="${wide ? 'width:min(760px,100%)' : ''}">
      <div class="modal-head"><h2>${esc(title)}</h2><button type="button" class="icon-btn" data-close aria-label="Close">✕</button></div>
      <div class="modal-body">${content}</div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : ''}</div>`;
    const prevFocus = document.activeElement;
    const close = () => {
      back.remove();
      document.removeEventListener('keydown', onKey);
      if (onClose) onClose();
      if (prevFocus && prevFocus.focus) prevFocus.focus();
    };
    const onKey = (e) => { if (e.key === 'Escape') close(); };
    back.addEventListener('click', (e) => {
      if (e.target === back || e.target.closest('[data-close]')) close();
    });
    document.addEventListener('keydown', onKey);
    document.body.appendChild(back);
    const first = back.querySelector('input:not([type=hidden]), select, textarea, button:not([data-close])');
    if (first) setTimeout(() => first.focus(), 30);
    return { el: back, close };
  }

  function confirmDialog(message, { okText = 'Confirm', danger = false } = {}) {
    return new Promise((resolve) => {
      let done = false;
      const m = modal({
        title: 'Please confirm',
        content: `<p style="margin:0">${esc(message)}</p>`,
        footer: `<button type="button" class="btn btn-secondary" data-close>Cancel</button>
                 <button type="button" class="btn ${danger ? 'btn-danger' : ''}" data-ok>${esc(okText)}</button>`,
        onClose: () => { if (!done) resolve(false); },
      });
      m.el.querySelector('[data-ok]').addEventListener('click', () => { done = true; m.close(); resolve(true); });
    });
  }

  const STATUS_LABEL = { pending: 'New', preparing: 'Preparing', ready: 'Ready', completed: 'Completed', cancelled: 'Cancelled' };
  const TYPE_LABEL = { dine_in: 'Dine-in', takeaway: 'Takeaway', delivery: 'Delivery' };
  const TYPE_ICON = { dine_in: '🍽', takeaway: '🥡', delivery: '🛵' };

  function timeAgo(iso) {
    const s = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
    if (s < 60) return 'just now';
    const m = Math.floor(s / 60);
    if (m < 60) return `${m} min ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h} h ${m % 60} min ago`;
    return new Date(iso).toLocaleDateString();
  }
  const fmtDateTime = (iso) => new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });

  const FALLBACK_IMG = '/images/placeholder.svg';
  /** Replace broken dish images with a placeholder (CSP forbids inline onerror). */
  function wireImageFallbacks(root = document) {
    root.querySelectorAll('img[data-fallback]').forEach((img) => {
      if (img.dataset.wired) return;
      img.dataset.wired = '1';
      img.addEventListener('error', () => { if (!img.src.endsWith(FALLBACK_IMG)) img.src = FALLBACK_IMG; });
      if (img.complete && img.naturalWidth === 0 && img.src) img.src = FALLBACK_IMG;
    });
  }

  async function logout() {
    try { await api('/api/auth/logout', { method: 'POST' }); } catch (_) { /* ignore */ }
    location.href = '/login';
  }

  /** Ensure a staff session; redirects to the login page otherwise. */
  async function requireStaff(roles) {
    try {
      const me = await api('/api/auth/me');
      if (roles && !roles.includes(me.role)) {
        location.href = me.role === 'kitchen' ? '/kitchen' : '/admin';
        return null;
      }
      return me;
    } catch (e) {
      location.href = `/login?next=${encodeURIComponent(location.pathname + location.search)}`;
      return null;
    }
  }

  window.App = {
    api, money, setCurrency, esc, toast, modal, confirmDialog, timeAgo, fmtDateTime,
    STATUS_LABEL, TYPE_LABEL, TYPE_ICON, wireImageFallbacks, logout, requireStaff, FALLBACK_IMG,
  };
})();
