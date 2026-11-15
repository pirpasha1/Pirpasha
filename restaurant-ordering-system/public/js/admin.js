(function () {
  'use strict';
  const A = window.App;
  const { api, money, esc, toast, modal, confirmDialog, STATUS_LABEL, TYPE_LABEL, TYPE_ICON, fmtDateTime, timeAgo } = A;
  const panel = document.getElementById('panel');
  let me = null;
  let settings = {};
  let current = '';
  let es = null;

  const TRANSITIONS = {
    pending: ['preparing', 'ready', 'cancelled'],
    preparing: ['ready', 'pending', 'cancelled'],
    ready: ['completed', 'preparing', 'cancelled'],
    completed: [],
    cancelled: [],
  };
  const ACTION_LABEL = { pending: '↩ Back to New', preparing: '👩‍🍳 Preparing', ready: '✅ Ready', completed: '🏁 Complete', cancelled: '✕ Cancel order' };

  const startOfToday = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
  const localDateStr = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const statusBadge = (s) => `<span class="badge badge-${s}">${STATUS_LABEL[s]}</span>`;
  const payBadge = (p) => `<span class="badge badge-${p}">${p === 'paid' ? 'Paid' : 'Unpaid'}</span>`;
  const formData = (form) => Object.fromEntries(new FormData(form).entries());
  const loading = () => { panel.innerHTML = '<div class="empty"><div class="big">⏳</div>Loading…</div>'; };

  function showError(e) {
    if (e.status === 401) { location.href = '/login?next=/admin'; return; }
    toast(e.message, 'error');
  }

  // Wrap a submit handler: disables the button, shows errors inline.
  function onSubmit(form, handler) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = form.querySelector('[type=submit]') || document.querySelector(`[form="${form.id}"]`);
      const err = form.querySelector('.alert-error');
      if (err) err.hidden = true;
      if (btn) btn.disabled = true;
      try {
        await handler(formData(form));
      } catch (ex) {
        if (ex.status === 401) return showError(ex);
        if (err) { err.textContent = ex.message; err.hidden = false; err.scrollIntoView({ block: 'nearest' }); } else toast(ex.message, 'error');
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }

  // ============ Tabs ============
  const PANELS = { dashboard, orders: ordersPanel, menu: dishesPanel, categories: categoriesPanel, tables: tablesPanel, settings: settingsPanel, staff: staffPanel };

  function go(tab) {
    if (!PANELS[tab]) tab = 'dashboard';
    current = tab;
    document.querySelectorAll('.tab').forEach((t) => {
      const on = t.dataset.tab === tab;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on);
    });
    if (location.hash !== `#${tab}`) history.replaceState(null, '', `#${tab}`);
    loading();
    PANELS[tab]().catch(showError);
  }
  document.getElementById('tabs').addEventListener('click', (e) => { const t = e.target.closest('[data-tab]'); if (t) go(t.dataset.tab); });
  window.addEventListener('hashchange', () => go(location.hash.slice(1)));
  document.getElementById('logoutBtn').addEventListener('click', A.logout);

  // ============ Live updates ============
  function connectStream() {
    es = new EventSource('/api/orders/stream');
    let refreshTimer;
    const refresh = () => {
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(() => { if (current === 'dashboard' || current === 'orders') PANELS[current](true).catch(() => {}); }, 400);
    };
    es.addEventListener('order_created', (ev) => {
      const o = JSON.parse(ev.data);
      toast(`New order #${o.order_number} · ${money(o.total_cents)}`, 'ok');
      refresh();
    });
    es.addEventListener('order_updated', refresh);
  }

  // ============ Dashboard ============
  async function dashboard(silent) {
    const from = startOfToday().toISOString();
    const [stats, recent] = await Promise.all([
      api(`/api/admin/stats?from=${encodeURIComponent(from)}`),
      api('/api/orders?status=all&limit=8'),
    ]);
    if (current !== 'dashboard') return;
    panel.innerHTML = `
      ${stats.default_passwords && stats.default_passwords.length ? `<div class="alert alert-warn">⚠ The default password is still set for: <strong>${stats.default_passwords.map(esc).join(', ')}</strong>. <a href="#staff">Change it now</a>.</div>` : ''}
      <div class="panel-head"><h2>Today</h2><a class="btn btn-secondary btn-sm" href="#orders">All orders →</a></div>
      <div class="stats">
        <div class="card stat"><div class="label">Orders today</div><div class="value">${stats.orders}</div></div>
        <div class="card stat"><div class="label">Revenue today</div><div class="value">${money(stats.revenue_cents)}</div></div>
        <div class="card stat"><div class="label">Collected</div><div class="value">${money(stats.paid_cents)}</div></div>
        <div class="card stat"><div class="label">In progress</div><div class="value">${stats.active}</div></div>
        <div class="card stat"><div class="label">Dishes available</div><div class="value">${stats.dishes_available}/${stats.dishes_total}</div></div>
      </div>
      <div class="row" style="align-items:start">
        <section class="card" style="padding:1rem 1.1rem"><h3 style="margin-bottom:.6rem">Recent orders</h3>
          ${recent.length ? `<div class="table-wrap"><table class="data"><tbody>${recent.map((o) => `
            <tr class="clickable" data-order="${o.id}"><td><strong>#${esc(o.order_number)}</strong><div class="muted" style="font-size:.8rem">${timeAgo(o.created_at)}</div></td>
            <td>${esc(o.customer_name)}<div class="muted" style="font-size:.8rem">${TYPE_ICON[o.order_type]} ${TYPE_LABEL[o.order_type]}${o.table_number ? ` · T${o.table_number}` : ''}</div></td>
            <td class="num">${money(o.total_cents)}</td><td>${statusBadge(o.status)}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">No orders yet today.</div>'}
        </section>
        <section class="card" style="padding:1rem 1.1rem"><h3 style="margin-bottom:.6rem">Best sellers today</h3>
          ${stats.top_dishes.length ? stats.top_dishes.map((d, i) => `<div class="item-line"><span>${i + 1}. ${esc(d.name)}</span><strong>${d.qty}</strong></div>`).join('') : '<div class="empty">No sales yet.</div>'}
        </section>
      </div>`;
    panel.querySelectorAll('[data-order]').forEach((tr) => tr.addEventListener('click', () => openOrder(Number(tr.dataset.order))));
    if (!silent) panel.scrollTop = 0;
  }

  // ============ Orders ============
  const orderFilters = { status: 'all', date: localDateStr(new Date()), q: '' };

  async function ordersPanel(silent) {
    if (!silent || !document.getElementById('ordersBody')) {
      panel.innerHTML = `
        <div class="panel-head"><h2>Orders</h2></div>
        <form class="filters" id="orderFilters">
          <select name="status" aria-label="Status">
            ${['all', 'active', 'pending', 'preparing', 'ready', 'completed', 'cancelled'].map((s) => `<option value="${s}" ${orderFilters.status === s ? 'selected' : ''}>${s === 'all' ? 'All statuses' : s === 'active' ? 'Active (not finished)' : STATUS_LABEL[s]}</option>`).join('')}
          </select>
          <input type="date" name="date" aria-label="Date" value="${orderFilters.date}">
          <input type="search" name="q" placeholder="Search name, phone or order #" value="${esc(orderFilters.q)}" aria-label="Search">
          <button class="btn btn-secondary" type="submit">Search</button>
        </form>
        <div class="card"><div class="table-wrap"><table class="data">
          <thead><tr><th>Order</th><th>Customer</th><th class="hide-sm">Type</th><th class="hide-sm">Items</th><th class="num">Total</th><th>Status</th><th class="hide-sm">Payment</th></tr></thead>
          <tbody id="ordersBody"></tbody></table></div></div>`;
      const f = document.getElementById('orderFilters');
      const apply = () => { Object.assign(orderFilters, formData(f)); ordersPanel(true).catch(showError); };
      f.addEventListener('submit', (e) => { e.preventDefault(); apply(); });
      f.status.addEventListener('change', apply);
      f.date.addEventListener('change', apply);
      document.getElementById('ordersBody').addEventListener('click', (e) => {
        const tr = e.target.closest('[data-order]');
        if (tr) openOrder(Number(tr.dataset.order));
      });
    }
    const params = new URLSearchParams({ status: orderFilters.status, limit: 300 });
    if (orderFilters.date) {
      const [y, m, d] = orderFilters.date.split('-').map(Number);
      const start = new Date(y, m - 1, d);
      const end = new Date(y, m - 1, d + 1);
      params.set('from', start.toISOString());
      params.set('to', end.toISOString());
    }
    if (orderFilters.q) params.set('q', orderFilters.q);
    const list = await api(`/api/orders?${params}`);
    const body = document.getElementById('ordersBody');
    if (!body) return;
    body.innerHTML = list.length ? list.map((o) => `
      <tr class="clickable" data-order="${o.id}">
        <td><strong>#${esc(o.order_number)}</strong><div class="muted" style="font-size:.8rem">${new Date(o.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div></td>
        <td>${esc(o.customer_name)}${o.customer_phone ? `<div class="muted" style="font-size:.8rem">${esc(o.customer_phone)}</div>` : ''}</td>
        <td class="hide-sm">${TYPE_ICON[o.order_type]} ${TYPE_LABEL[o.order_type]}${o.table_number ? ` · T${o.table_number}` : ''}</td>
        <td class="hide-sm">${o.items.reduce((a, i) => a + i.quantity, 0)}</td>
        <td class="num">${money(o.total_cents)}</td>
        <td>${statusBadge(o.status)}</td>
        <td class="hide-sm">${payBadge(o.payment_status)}</td>
      </tr>`).join('') : '<tr><td colspan="7"><div class="empty">No orders found for these filters.</div></td></tr>';
  }

  async function openOrder(id) {
    let o;
    try { o = await api(`/api/orders/${id}`); } catch (e) { return showError(e); }
    const bill = `/api/orders/${o.id}/bill.pdf`;
    const m = modal({
      title: `Order #${o.order_number}`,
      wide: true,
      content: `
        <div style="display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.8rem">${statusBadge(o.status)} ${payBadge(o.payment_status)} <span class="badge badge-type">${TYPE_ICON[o.order_type]} ${TYPE_LABEL[o.order_type]}</span></div>
        <dl class="kv">
          <dt>Customer</dt><dd>${esc(o.customer_name)}</dd>
          ${o.customer_phone ? `<dt>Phone</dt><dd><a href="tel:${esc(o.customer_phone)}">${esc(o.customer_phone)}</a></dd>` : ''}
          ${o.table_number ? `<dt>Table</dt><dd>${o.table_number}</dd>` : ''}
          ${o.order_type === 'delivery' ? `<dt>Address</dt><dd>${esc(o.delivery_address)}</dd>` : ''}
          <dt>Placed</dt><dd>${esc(fmtDateTime(o.created_at))}</dd>
          ${o.notes ? `<dt>Notes</dt><dd>${esc(o.notes)}</dd>` : ''}
        </dl>
        <div style="margin-top:1rem">${o.items.map((i) => `<div class="item-line"><span>${i.quantity} × ${esc(i.dish_name)} <span class="muted">@ ${money(i.unit_price_cents)}</span></span><strong>${money(i.line_total_cents)}</strong></div>`).join('')}</div>
        <div class="totals" style="margin-top:.8rem">
          <div><span>Subtotal</span><span>${money(o.subtotal_cents)}</span></div>
          <div class="muted"><span>Tax</span><span>${money(o.tax_cents)}</span></div>
          ${o.delivery_fee_cents ? `<div class="muted"><span>Delivery fee</span><span>${money(o.delivery_fee_cents)}</span></div>` : ''}
          <div class="grand"><span>Total</span><span>${money(o.total_cents)}</span></div>
        </div>
        ${TRANSITIONS[o.status].length ? `<h3 style="margin:1.2rem 0 .5rem;font-size:1rem">Change status</h3>
          <div style="display:flex;gap:.4rem;flex-wrap:wrap">${TRANSITIONS[o.status].map((s) => `<button type="button" class="btn btn-sm ${s === 'cancelled' ? 'btn-danger' : s === 'completed' || s === 'ready' ? 'btn-ok' : 'btn-secondary'}" data-set-status="${s}">${ACTION_LABEL[s]}</button>`).join('')}</div>` : ''}
        <h3 style="margin:1.2rem 0 .5rem;font-size:1rem">Bill</h3>
        <div style="display:flex;gap:.4rem;flex-wrap:wrap">
          <a class="btn btn-sm btn-secondary" href="${bill}" target="_blank" rel="noopener">🖨 Print A4 bill</a>
          <a class="btn btn-sm btn-secondary" href="${bill}?format=receipt" target="_blank" rel="noopener">🧾 Print receipt (80 mm)</a>
          <a class="btn btn-sm btn-secondary" href="${bill}?download=1" download>⬇ Download PDF</a>
          <a class="btn btn-sm btn-secondary" href="/order?token=${esc(o.public_token)}" target="_blank" rel="noopener">Customer view ↗</a>
        </div>`,
      footer: o.status === 'cancelled' ? '<button type="button" class="btn btn-secondary" data-close>Close</button>'
        : `<button type="button" class="btn btn-secondary" data-close>Close</button>
           <button type="button" class="btn ${o.payment_status === 'paid' ? 'btn-secondary' : 'btn-ok'}" data-pay="${o.payment_status === 'paid' ? 'unpaid' : 'paid'}">${o.payment_status === 'paid' ? 'Mark as unpaid' : '💰 Mark as paid'}</button>`,
    });
    m.el.addEventListener('click', async (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      try {
        if (b.dataset.setStatus) {
          const s = b.dataset.setStatus;
          if (s === 'cancelled' && !(await confirmDialog(`Cancel order #${o.order_number}?`, { okText: 'Cancel order', danger: true }))) return;
          b.disabled = true;
          await api(`/api/orders/${o.id}/status`, { method: 'PATCH', body: { status: s } });
          toast(`Order #${o.order_number} → ${STATUS_LABEL[s]}`, 'ok');
        } else if (b.dataset.pay) {
          b.disabled = true;
          await api(`/api/orders/${o.id}/payment`, { method: 'PATCH', body: { payment_status: b.dataset.pay } });
          toast(b.dataset.pay === 'paid' ? 'Marked as paid' : 'Marked as unpaid', 'ok');
        } else return;
        m.close();
        if (PANELS[current]) PANELS[current](true).catch(showError);
        openOrder(o.id);
      } catch (ex) { b.disabled = false; showError(ex); }
    });
  }

  // ============ Dishes ============
  const dishFilter = { cat: '', q: '' };
  let cats = [];

  async function dishesPanel() {
    const [dishes, categories] = await Promise.all([api('/api/admin/dishes'), api('/api/admin/categories')]);
    cats = categories;
    const q = dishFilter.q.toLowerCase();
    const list = dishes.filter((d) => (!dishFilter.cat || String(d.category_id) === dishFilter.cat) && (!q || d.name.toLowerCase().includes(q)));
    panel.innerHTML = `
      <div class="panel-head"><h2>Dishes</h2><button class="btn" type="button" id="addDish">＋ Add dish</button></div>
      <div class="filters">
        <select id="dCat" aria-label="Category"><option value="">All categories</option>${cats.map((c) => `<option value="${c.id}" ${dishFilter.cat === String(c.id) ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}</select>
        <input type="search" id="dQ" placeholder="Search dishes" value="${esc(dishFilter.q)}" aria-label="Search dishes">
      </div>
      <div class="card"><div class="table-wrap"><table class="data">
        <thead><tr><th>Dish</th><th class="hide-sm">Category</th><th class="num">Price</th><th>Available</th><th></th></tr></thead>
        <tbody>${list.length ? list.map((d) => `
          <tr data-id="${d.id}">
            <td><div style="display:flex;gap:.7rem;align-items:center"><img class="thumb" src="${esc(d.image_url || A.FALLBACK_IMG)}" alt="" data-fallback loading="lazy">
              <div><div style="display:flex;gap:.4rem;align-items:center;font-weight:600"><span class="veg-mark ${d.is_veg ? '' : 'nonveg'}"></span>${esc(d.name)}</div>
              <div class="muted hide-sm" style="font-size:.8rem;max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(d.description)}</div></div></div></td>
            <td class="hide-sm">${esc(d.category_name)}</td>
            <td class="num"><strong>${money(d.price_cents)}</strong></td>
            <td><label class="switch" title="${d.is_available ? 'Available' : 'Sold out'}"><input type="checkbox" data-avail="${d.id}" ${d.is_available ? 'checked' : ''} aria-label="${esc(d.name)} available"><span></span></label></td>
            <td style="white-space:nowrap;text-align:right"><button class="btn btn-sm btn-secondary" type="button" data-edit="${d.id}">Edit</button>
              <button class="btn btn-sm btn-ghost" type="button" data-del="${d.id}" aria-label="Delete ${esc(d.name)}">🗑</button></td>
          </tr>`).join('') : '<tr><td colspan="5"><div class="empty">No dishes found.</div></td></tr>'}</tbody></table></div></div>`;
    A.wireImageFallbacks(panel);
    const byId = new Map(dishes.map((d) => [String(d.id), d]));
    document.getElementById('addDish').addEventListener('click', () => dishModal(null));
    document.getElementById('dCat').addEventListener('change', (e) => { dishFilter.cat = e.target.value; dishesPanel().catch(showError); });
    let t;
    document.getElementById('dQ').addEventListener('input', (e) => {
      clearTimeout(t);
      t = setTimeout(() => { dishFilter.q = e.target.value.trim(); dishesPanel().then(() => { const i = document.getElementById('dQ'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }).catch(showError); }, 250);
    });
    panel.querySelector('tbody').addEventListener('click', async (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.edit) dishModal(byId.get(b.dataset.edit));
      if (b.dataset.del) {
        const d = byId.get(b.dataset.del);
        if (!(await confirmDialog(`Delete "${d.name}" from the menu? Past orders and bills are not affected.`, { okText: 'Delete', danger: true }))) return;
        try { await api(`/api/admin/dishes/${d.id}`, { method: 'DELETE' }); toast('Dish deleted', 'ok'); dishesPanel().catch(showError); } catch (ex) { showError(ex); }
      }
    });
    panel.querySelector('tbody').addEventListener('change', async (e) => {
      const cb = e.target.closest('[data-avail]');
      if (!cb) return;
      cb.disabled = true;
      try {
        const d = await api(`/api/admin/dishes/${cb.dataset.avail}/availability`, { method: 'PATCH', body: { is_available: cb.checked } });
        toast(`${d.name} is now ${d.is_available ? 'available' : 'sold out'}`, 'ok');
      } catch (ex) { cb.checked = !cb.checked; showError(ex); } finally { cb.disabled = false; }
    });
  }

  function dishModal(d) {
    if (!cats.length) { toast('Create a category first', 'error'); return go('categories'); }
    const isNew = !d;
    d = d || { name: '', description: '', price_cents: 0, category_id: dishFilter.cat ? Number(dishFilter.cat) : cats[0].id, image_url: '', is_veg: true, is_available: true, sort_order: 0 };
    const m = modal({
      title: isNew ? 'Add dish' : `Edit ${d.name}`,
      content: `<form id="dishForm" novalidate>
        <div class="alert alert-error" hidden></div>
        <img class="img-preview" id="imgPreview" src="${esc(d.image_url || A.FALLBACK_IMG)}" alt="Dish photo preview" data-fallback>
        <div class="field"><label for="imgFile">Photo</label>
          <input type="file" id="imgFile" accept="image/jpeg,image/png,image/webp">
          <div class="hint">JPEG, PNG or WebP, up to 3 MB. Landscape 4:3 photos look best.</div></div>
        <div class="field"><label for="imgUrl">…or image URL</label><input type="url" id="imgUrl" name="image_url" value="${esc(d.image_url)}" placeholder="https://…"></div>
        <div class="field"><label for="dName">Name *</label><input type="text" id="dName" name="name" required maxlength="80" value="${esc(d.name)}"></div>
        <div class="row">
          <div class="field"><label for="dCatSel">Category *</label><select id="dCatSel" name="category_id">${cats.map((c) => `<option value="${c.id}" ${c.id === d.category_id ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}</select></div>
          <div class="field"><label for="dPrice">Price (${esc(settings.currency_symbol || '₹')}) *</label><input type="number" id="dPrice" name="price" min="0" step="0.01" required value="${(d.price_cents / 100).toFixed(2)}"></div>
        </div>
        <div class="field"><label for="dDesc">Description</label><textarea id="dDesc" name="description" maxlength="400">${esc(d.description)}</textarea></div>
        <div class="row">
          <div class="field"><label class="checkbox"><input type="checkbox" name="is_veg" ${d.is_veg ? 'checked' : ''}> Vegetarian</label></div>
          <div class="field"><label class="checkbox"><input type="checkbox" name="is_available" ${d.is_available ? 'checked' : ''}> Available to order</label></div>
        </div>
        <div class="field"><label for="dSort">Display order</label><input type="number" id="dSort" name="sort_order" min="0" value="${d.sort_order}"><div class="hint">Lower numbers appear first in the category.</div></div>
      </form>`,
      footer: `<button type="button" class="btn btn-secondary" data-close>Cancel</button><button type="submit" form="dishForm" class="btn">${isNew ? 'Add dish' : 'Save changes'}</button>`,
    });
    const form = m.el.querySelector('#dishForm');
    const preview = m.el.querySelector('#imgPreview');
    const urlInput = m.el.querySelector('#imgUrl');
    A.wireImageFallbacks(m.el);
    urlInput.addEventListener('change', () => { preview.src = urlInput.value || A.FALLBACK_IMG; });
    m.el.querySelector('#imgFile').addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (file.size > 3 * 1024 * 1024) { toast('Image must be 3 MB or smaller', 'error'); e.target.value = ''; return; }
      const fd = new FormData();
      fd.append('image', file);
      preview.style.opacity = '.5';
      try {
        const res = await api('/api/admin/uploads', { method: 'POST', form: fd });
        urlInput.value = res.url;
        preview.src = res.url;
        toast('Photo uploaded — remember to save', 'ok');
      } catch (ex) { showError(ex); e.target.value = ''; } finally { preview.style.opacity = '1'; }
    });
    onSubmit(form, async (data) => {
      const body = { ...data, is_veg: form.is_veg.checked, is_available: form.is_available.checked };
      if (isNew) await api('/api/admin/dishes', { method: 'POST', body });
      else await api(`/api/admin/dishes/${d.id}`, { method: 'PUT', body });
      toast(isNew ? 'Dish added' : 'Dish saved', 'ok');
      m.close();
      dishesPanel().catch(showError);
    });
  }

  // ============ Categories ============
  async function categoriesPanel() {
    const list = await api('/api/admin/categories');
    panel.innerHTML = `
      <div class="panel-head"><h2>Categories</h2><button class="btn" type="button" id="addCat">＋ Add category</button></div>
      <div class="card"><div class="table-wrap"><table class="data">
        <thead><tr><th>Name</th><th class="num">Order</th><th class="num">Dishes</th><th></th></tr></thead>
        <tbody>${list.map((c) => `<tr><td><strong>${esc(c.name)}</strong></td><td class="num">${c.sort_order}</td><td class="num">${c.dish_count}</td>
          <td style="text-align:right;white-space:nowrap"><button class="btn btn-sm btn-secondary" type="button" data-edit="${c.id}">Edit</button>
          <button class="btn btn-sm btn-ghost" type="button" data-del="${c.id}" aria-label="Delete ${esc(c.name)}">🗑</button></td></tr>`).join('') || '<tr><td colspan="4"><div class="empty">No categories yet.</div></td></tr>'}</tbody>
      </table></div></div>`;
    const byId = new Map(list.map((c) => [String(c.id), c]));
    document.getElementById('addCat').addEventListener('click', () => catModal(null, list.length));
    panel.querySelector('tbody').addEventListener('click', async (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.edit) catModal(byId.get(b.dataset.edit));
      if (b.dataset.del) {
        const c = byId.get(b.dataset.del);
        if (!(await confirmDialog(`Delete category "${c.name}"?`, { okText: 'Delete', danger: true }))) return;
        try { await api(`/api/admin/categories/${c.id}`, { method: 'DELETE' }); toast('Category deleted', 'ok'); categoriesPanel().catch(showError); } catch (ex) { showError(ex); }
      }
    });
  }

  function catModal(c, count = 0) {
    const isNew = !c;
    c = c || { name: '', sort_order: count };
    const m = modal({
      title: isNew ? 'Add category' : 'Edit category',
      content: `<form id="catForm" novalidate><div class="alert alert-error" hidden></div>
        <div class="field"><label for="cName">Name *</label><input id="cName" name="name" type="text" required maxlength="40" value="${esc(c.name)}"></div>
        <div class="field"><label for="cSort">Display order</label><input id="cSort" name="sort_order" type="number" min="0" value="${c.sort_order}"></div></form>`,
      footer: `<button type="button" class="btn btn-secondary" data-close>Cancel</button><button type="submit" form="catForm" class="btn">Save</button>`,
    });
    onSubmit(m.el.querySelector('#catForm'), async (data) => {
      if (isNew) await api('/api/admin/categories', { method: 'POST', body: data });
      else await api(`/api/admin/categories/${c.id}`, { method: 'PUT', body: data });
      toast('Category saved', 'ok');
      m.close();
      categoriesPanel().catch(showError);
    });
  }

  // ============ Tables & QR ============
  async function tablesPanel() {
    const list = await api('/api/admin/tables');
    const base = settings.public_base_url || location.origin;
    const isLocal = /localhost|127\.0\.0\.1/.test(base);
    const v = Date.now();
    panel.innerHTML = `
      <div class="panel-head"><h2>Tables &amp; QR codes</h2>
        <a class="btn btn-secondary" href="/qr-print" target="_blank" rel="noopener">🖨 Print all QR codes</a>
        <button class="btn" type="button" id="addTable">＋ Add table</button></div>
      <div class="alert ${isLocal ? 'alert-warn' : 'alert-info'}">QR codes open <strong>${esc(base)}/?table=N</strong>.
        ${isLocal ? 'This is a local address that phones cannot reach — set the <a href="#settings">Public URL</a> to your network or internet address before printing.' : 'Change this under <a href="#settings">Settings → Public URL</a>.'}</div>
      <div class="qr-grid">${list.map((t) => `
        <div class="card qr-card" data-id="${t.id}">
          <div class="tno">Table ${t.table_number}</div>
          <div class="muted" style="font-size:.85rem">${t.seats} seats · ${t.is_active ? '<span style="color:var(--ok)">Active</span>' : '<span style="color:var(--danger)">Inactive</span>'}</div>
          <img src="/api/admin/tables/${t.id}/qr.png?v=${v}" alt="QR code for table ${t.table_number}" loading="lazy">
          <div class="btns">
            <a class="btn btn-sm btn-secondary" href="/api/admin/tables/${t.id}/qr.png?download=1" download>⬇ PNG</a>
            <a class="btn btn-sm btn-secondary" href="/?table=${t.table_number}" target="_blank" rel="noopener">Open</a>
            <button class="btn btn-sm btn-secondary" type="button" data-edit="${t.id}">Edit</button>
            <button class="btn btn-sm btn-ghost" type="button" data-del="${t.id}" aria-label="Delete table ${t.table_number}">🗑</button>
          </div></div>`).join('') || '<div class="empty">No tables yet. Add your first table.</div>'}</div>`;
    const byId = new Map(list.map((t) => [String(t.id), t]));
    document.getElementById('addTable').addEventListener('click', () => {
      const next = list.reduce((a, t) => Math.max(a, t.table_number), 0) + 1;
      tableModal(null, next);
    });
    panel.querySelector('.qr-grid').addEventListener('click', async (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.edit) tableModal(byId.get(b.dataset.edit));
      if (b.dataset.del) {
        const t = byId.get(b.dataset.del);
        if (!(await confirmDialog(`Delete table ${t.table_number}? Its printed QR code will stop working.`, { okText: 'Delete', danger: true }))) return;
        try { await api(`/api/admin/tables/${t.id}`, { method: 'DELETE' }); toast('Table deleted', 'ok'); tablesPanel().catch(showError); } catch (ex) { showError(ex); }
      }
    });
  }

  function tableModal(t, nextNumber) {
    const isNew = !t;
    t = t || { table_number: nextNumber, seats: 4, is_active: 1 };
    const m = modal({
      title: isNew ? 'Add table' : `Edit table ${t.table_number}`,
      content: `<form id="tableForm" novalidate><div class="alert alert-error" hidden></div>
        <div class="row"><div class="field"><label for="tNo">Table number *</label><input id="tNo" name="table_number" type="number" min="1" required value="${t.table_number}"></div>
        <div class="field"><label for="tSeats">Seats</label><input id="tSeats" name="seats" type="number" min="1" max="50" value="${t.seats}"></div></div>
        <label class="checkbox"><input type="checkbox" name="is_active" ${t.is_active ? 'checked' : ''}> Active (customers can order from this table)</label></form>`,
      footer: `<button type="button" class="btn btn-secondary" data-close>Cancel</button><button type="submit" form="tableForm" class="btn">Save</button>`,
    });
    const form = m.el.querySelector('#tableForm');
    onSubmit(form, async (data) => {
      const body = { ...data, is_active: form.is_active.checked };
      if (isNew) await api('/api/admin/tables', { method: 'POST', body });
      else await api(`/api/admin/tables/${t.id}`, { method: 'PUT', body });
      toast('Table saved', 'ok');
      m.close();
      tablesPanel().catch(showError);
    });
  }

  // ============ Settings ============
  async function settingsPanel() {
    settings = await api('/api/admin/settings');
    const s = settings;
    panel.innerHTML = `
      <div class="panel-head"><h2>Settings</h2></div>
      <form class="card" id="settingsForm" style="padding:1.2rem;max-width:720px" novalidate>
        <div class="alert alert-error" hidden></div>
        <div class="field"><label for="sName">Restaurant name *</label><input id="sName" name="restaurant_name" type="text" required maxlength="80" value="${esc(s.restaurant_name)}"></div>
        <div class="field"><label for="sAddr">Address</label><input id="sAddr" name="restaurant_address" type="text" maxlength="200" value="${esc(s.restaurant_address)}"></div>
        <div class="row">
          <div class="field"><label for="sPhone">Phone</label><input id="sPhone" name="restaurant_phone" type="text" maxlength="30" value="${esc(s.restaurant_phone)}"></div>
          <div class="field"><label for="sGst">GSTIN / Tax number</label><input id="sGst" name="gst_number" type="text" maxlength="30" value="${esc(s.gst_number)}"><div class="hint">Printed on bills when set.</div></div>
        </div>
        <div class="row">
          <div class="field"><label for="sCur">Currency symbol *</label><input id="sCur" name="currency_symbol" type="text" required maxlength="4" value="${esc(s.currency_symbol)}"></div>
          <div class="field"><label for="sTax">Tax rate (%)</label><input id="sTax" name="tax_rate_percent" type="number" min="0" max="50" step="0.01" value="${esc(s.tax_rate_percent)}"></div>
        </div>
        <div class="row">
          <div class="field"><label for="sFee">Delivery fee</label><input id="sFee" name="delivery_fee" type="number" min="0" step="0.01" value="${esc(s.delivery_fee)}"></div>
          <div class="field"><label for="sTz">Time zone (for bills)</label><input id="sTz" name="timezone" type="text" maxlength="60" value="${esc(s.timezone)}" placeholder="Asia/Kolkata"></div>
        </div>
        <div class="field"><label for="sUrl">Public URL (used in table QR codes)</label><input id="sUrl" name="public_base_url" type="url" maxlength="200" value="${esc(s.public_base_url)}" placeholder="${esc(location.origin)}">
          <div class="hint">The address customers' phones use to reach this system, e.g. http://192.168.1.20:3000 or https://order.myrestaurant.com. Leave empty to use the address you are browsing from.</div></div>
        <button class="btn" type="submit">Save settings</button>
      </form>`;
    onSubmit(document.getElementById('settingsForm'), async (data) => {
      settings = await api('/api/admin/settings', { method: 'PUT', body: data });
      A.setCurrency(settings.currency_symbol);
      document.getElementById('restName').textContent = settings.restaurant_name;
      toast('Settings saved', 'ok');
    });
  }

  // ============ Staff ============
  async function staffPanel() {
    const users = await api('/api/admin/users');
    panel.innerHTML = `
      <div class="panel-head"><h2>Staff accounts</h2><button class="btn" type="button" id="addUser">＋ Add staff</button></div>
      <div class="card" style="margin-bottom:1.2rem"><div class="table-wrap"><table class="data">
        <thead><tr><th>Username</th><th>Role</th><th class="hide-sm">Created</th><th></th></tr></thead>
        <tbody>${users.map((u) => `<tr><td><strong>${esc(u.username)}</strong>${u.id === me.id ? ' <span class="muted">(you)</span>' : ''}</td>
          <td><span class="badge badge-type">${u.role === 'admin' ? 'Admin' : 'Kitchen'}</span></td>
          <td class="hide-sm">${esc(new Date(u.created_at).toLocaleDateString())}</td>
          <td style="text-align:right;white-space:nowrap">${u.id === me.id ? '' : `<button class="btn btn-sm btn-secondary" type="button" data-reset="${u.id}" data-name="${esc(u.username)}">Reset password</button>
            <button class="btn btn-sm btn-ghost" type="button" data-del="${u.id}" data-name="${esc(u.username)}" aria-label="Delete ${esc(u.username)}">🗑</button>`}</td></tr>`).join('')}</tbody>
      </table></div></div>
      <form class="card" id="pwForm" style="padding:1.2rem;max-width:520px" novalidate>
        <h3 style="margin-bottom:.8rem">Change my password</h3>
        <div class="alert alert-error" hidden></div>
        <div class="field"><label for="pwCur">Current password</label><input id="pwCur" name="current_password" type="password" autocomplete="current-password" required></div>
        <div class="field"><label for="pwNew">New password</label><input id="pwNew" name="new_password" type="password" autocomplete="new-password" required minlength="8"><div class="hint">At least 8 characters with letters and numbers.</div></div>
        <div class="field"><label for="pwNew2">Repeat new password</label><input id="pwNew2" name="repeat" type="password" autocomplete="new-password" required></div>
        <button class="btn" type="submit">Update password</button>
      </form>`;
    document.getElementById('addUser').addEventListener('click', userModal);
    panel.querySelector('tbody').addEventListener('click', async (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.reset) resetModal(b.dataset.reset, b.dataset.name);
      if (b.dataset.del) {
        if (!(await confirmDialog(`Delete staff account "${b.dataset.name}"?`, { okText: 'Delete', danger: true }))) return;
        try { await api(`/api/admin/users/${b.dataset.del}`, { method: 'DELETE' }); toast('Account deleted', 'ok'); staffPanel().catch(showError); } catch (ex) { showError(ex); }
      }
    });
    const pwForm = document.getElementById('pwForm');
    onSubmit(pwForm, async (data) => {
      if (data.new_password !== data.repeat) throw new Error('The new passwords do not match');
      await api('/api/auth/change-password', { method: 'POST', body: data });
      pwForm.reset();
      toast('Password updated', 'ok');
    });
  }

  function userModal() {
    const m = modal({
      title: 'Add staff account',
      content: `<form id="userForm" novalidate><div class="alert alert-error" hidden></div>
        <div class="field"><label for="uName">Username *</label><input id="uName" name="username" type="text" required maxlength="30" autocapitalize="none" autocomplete="off"></div>
        <div class="field"><label for="uRole">Role</label><select id="uRole" name="role"><option value="kitchen">Kitchen — sees and updates orders</option><option value="admin">Admin — full access</option></select></div>
        <div class="field"><label for="uPw">Password *</label><input id="uPw" name="password" type="password" required minlength="8" autocomplete="new-password"><div class="hint">At least 8 characters with letters and numbers.</div></div></form>`,
      footer: `<button type="button" class="btn btn-secondary" data-close>Cancel</button><button type="submit" form="userForm" class="btn">Create account</button>`,
    });
    onSubmit(m.el.querySelector('#userForm'), async (data) => {
      await api('/api/admin/users', { method: 'POST', body: data });
      toast('Account created', 'ok');
      m.close();
      staffPanel().catch(showError);
    });
  }

  function resetModal(id, name) {
    const m = modal({
      title: `Reset password for ${name}`,
      content: `<form id="resetForm" novalidate><div class="alert alert-error" hidden></div>
        <div class="field"><label for="rPw">New password *</label><input id="rPw" name="password" type="password" required minlength="8" autocomplete="new-password"><div class="hint">At least 8 characters with letters and numbers.</div></div></form>`,
      footer: `<button type="button" class="btn btn-secondary" data-close>Cancel</button><button type="submit" form="resetForm" class="btn">Reset password</button>`,
    });
    onSubmit(m.el.querySelector('#resetForm'), async (data) => {
      await api(`/api/admin/users/${id}/password`, { method: 'PUT', body: data });
      toast('Password reset', 'ok');
      m.close();
    });
  }

  // ============ Boot ============
  A.requireStaff(['admin']).then(async (user) => {
    if (!user) return;
    me = user;
    document.getElementById('who').textContent = `Signed in as ${user.username}`;
    try {
      settings = await api('/api/admin/settings');
      A.setCurrency(settings.currency_symbol);
      document.getElementById('restName').textContent = settings.restaurant_name;
      document.title = `Admin · ${settings.restaurant_name}`;
    } catch (e) { showError(e); }
    connectStream();
    go(location.hash.slice(1) || 'dashboard');
  });
})();
