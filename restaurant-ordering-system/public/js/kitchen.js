(function () {
  'use strict';
  const { api, esc, toast, TYPE_LABEL, TYPE_ICON, confirmDialog, logout, requireStaff } = window.App;
  const $ = (id) => document.getElementById(id);
  const orders = new Map();
  const fresh = new Set();
  let audioCtx = null;
  let soundOn = false;

  const NEXT = {
    pending: [['preparing', '👩‍🍳 Start preparing', '']],
    preparing: [['ready', '✅ Mark ready', 'btn-ok']],
    ready: [['completed', '🏁 Complete', 'btn-ok']],
  };

  function minutesSince(iso) { return Math.floor((Date.now() - new Date(iso).getTime()) / 60000); }

  function ticket(o) {
    const mins = minutesSince(o.created_at);
    const where = o.order_type === 'dine_in' ? `Table ${o.table_number}` : TYPE_LABEL[o.order_type];
    return `<article class="ticket ${o.status} ${fresh.has(o.id) ? 'new' : ''}" data-id="${o.id}">
      <div class="t-head"><span class="t-no">#${esc(o.order_number)}</span>
        <span class="badge badge-type">${TYPE_ICON[o.order_type]} ${esc(where)}</span>
        <span class="t-age ${mins >= 20 && o.status !== 'ready' ? 'late' : ''}" data-age="${esc(o.created_at)}">${mins} min</span></div>
      <div class="t-meta">${esc(o.customer_name)}${o.customer_phone ? ` · ${esc(o.customer_phone)}` : ''}
        · ${new Date(o.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
      <ul class="t-items">${o.items.map((i) => `<li><span class="q">${i.quantity}×</span><span>${esc(i.dish_name)}</span></li>`).join('')}</ul>
      ${o.notes ? `<div class="t-notes">📝 ${esc(o.notes)}</div>` : ''}
      ${o.order_type === 'delivery' ? `<div class="t-meta">📍 ${esc(o.delivery_address)}</div>` : ''}
      <div class="t-actions">
        ${(NEXT[o.status] || []).map(([s, label, cls]) => `<button type="button" class="btn btn-sm ${cls}" data-status="${s}">${label}</button>`).join('')}
        ${o.status === 'preparing' ? '<button type="button" class="btn btn-sm btn-secondary" data-status="pending" title="Move back to New">↩</button>' : ''}
        ${o.status === 'ready' ? '<button type="button" class="btn btn-sm btn-secondary" data-status="preparing" title="Move back to Preparing">↩</button>' : ''}
        <a class="btn btn-sm btn-secondary" href="/api/orders/${o.id}/bill.pdf?format=receipt" target="_blank" rel="noopener" title="Print receipt">🖨</a>
        <button type="button" class="btn btn-sm btn-secondary" data-cancel title="Cancel order">✕</button>
      </div></article>`;
  }

  function render() {
    for (const s of ['pending', 'preparing', 'ready']) {
      const list = [...orders.values()].filter((o) => o.status === s).sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id - b.id);
      $(`c-${s}`).textContent = list.length;
      $(`l-${s}`).innerHTML = list.length ? list.map(ticket).join('') : `<div class="k-empty">No ${s === 'pending' ? 'new' : s} orders</div>`;
    }
  }

  function upsert(o) {
    if (['completed', 'cancelled'].includes(o.status)) orders.delete(o.id);
    else orders.set(o.id, o);
  }

  async function loadAll() {
    try {
      const list = await api('/api/orders?status=active');
      orders.clear();
      list.forEach(upsert);
      render();
    } catch (e) {
      if (e.status === 401) location.href = '/login?next=/kitchen';
      else toast(e.message, 'error');
    }
  }

  function chime() {
    if (!soundOn || !audioCtx) return;
    const t = audioCtx.currentTime;
    [880, 1175, 1568].forEach((f, i) => {
      const o = audioCtx.createOscillator();
      const g = audioCtx.createGain();
      o.frequency.value = f;
      o.type = 'sine';
      g.gain.setValueAtTime(0.0001, t + i * 0.18);
      g.gain.exponentialRampToValueAtTime(0.35, t + i * 0.18 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.18 + 0.3);
      o.connect(g).connect(audioCtx.destination);
      o.start(t + i * 0.18);
      o.stop(t + i * 0.18 + 0.32);
    });
  }

  let es = null;
  function connect() {
    if (es) es.close();
    es = new EventSource('/api/orders/stream');
    es.addEventListener('open', () => { $('conn').classList.add('on'); loadAll(); });
    es.addEventListener('error', () => { $('conn').classList.remove('on'); });
    es.addEventListener('order_created', (ev) => {
      const o = JSON.parse(ev.data);
      fresh.add(o.id);
      setTimeout(() => { fresh.delete(o.id); }, 4000);
      upsert(o);
      render();
      chime();
      toast(`New order #${o.order_number} — ${o.order_type === 'dine_in' ? `Table ${o.table_number}` : TYPE_LABEL[o.order_type]}`, 'ok');
    });
    es.addEventListener('order_updated', (ev) => { upsert(JSON.parse(ev.data)); render(); });
  }

  $('board').addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const id = Number(btn.closest('[data-id]').dataset.id);
    let status = btn.dataset.status;
    if (btn.hasAttribute('data-cancel')) {
      const o = orders.get(id);
      if (!(await confirmDialog(`Cancel order #${o ? o.order_number : id}? This cannot be undone.`, { okText: 'Cancel order', danger: true }))) return;
      status = 'cancelled';
    }
    if (!status) return;
    btn.disabled = true;
    try {
      upsert(await api(`/api/orders/${id}/status`, { method: 'PATCH', body: { status } }));
      render();
    } catch (ex) {
      toast(ex.message, 'error');
      btn.disabled = false;
      loadAll();
    }
  });

  $('soundBtn').addEventListener('click', () => {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return toast('Sound is not supported in this browser', 'error');
    if (!audioCtx) audioCtx = new Ctx();
    soundOn = !soundOn;
    if (soundOn) { audioCtx.resume(); chime(); }
    $('soundBtn').textContent = soundOn ? '🔔 Sound on' : '🔕 Sound off';
  });
  $('refreshBtn').addEventListener('click', loadAll);
  $('logoutBtn').addEventListener('click', logout);

  function tick() {
    $('clock').textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    document.querySelectorAll('[data-age]').forEach((el) => {
      const m = minutesSince(el.dataset.age);
      el.textContent = `${m} min`;
      el.classList.toggle('late', m >= 20 && !el.closest('.ticket.ready'));
    });
  }

  requireStaff(['admin', 'kitchen']).then((me) => {
    if (!me) return;
    if (me.role === 'admin') $('adminLink').hidden = false;
    loadAll();
    connect();
    tick();
    setInterval(tick, 15000);
    setInterval(loadAll, 60000); // safety net in case an event was missed
  });
})();
