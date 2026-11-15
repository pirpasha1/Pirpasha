(function () {
  'use strict';
  const { api, money, esc, toast, setCurrency, wireImageFallbacks, TYPE_ICON } = window.App;

  const CART_KEY = 'rs_cart_v1';
  const TABLE_KEY = 'rs_table';
  const ORDERS_KEY = 'rs_my_orders';

  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (_) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* private mode */ } },
    del(k) { try { localStorage.removeItem(k); } catch (_) { /* ignore */ } },
  };

  const state = {
    settings: {},
    categories: [],
    dishes: new Map(),
    cart: store.get(CART_KEY, {}), // { dishId: qty }
    table: null,
    activeCat: 'all',
    search: '',
    vegOnly: false,
    checkout: { name: '', phone: '', type: 'dine_in', address: '', notes: '' },
  };

  const $ = (id) => document.getElementById(id);

  // ---------- Table from QR code ----------
  async function resolveTable() {
    const params = new URLSearchParams(location.search);
    const fromQr = params.get('table');
    if (fromQr) {
      try {
        const t = await api(`/api/tables/${encodeURIComponent(fromQr)}`);
        state.table = t.table_number;
        store.set(TABLE_KEY, { n: t.table_number, at: Date.now() });
        toast(`Welcome! You're ordering for Table ${t.table_number}`, 'ok');
      } catch (_) {
        toast(`Table "${fromQr}" was not found. Please ask our staff for help.`, 'error');
      }
      params.delete('table');
      history.replaceState(null, '', location.pathname + (params.toString() ? `?${params}` : ''));
    } else {
      const saved = store.get(TABLE_KEY, null);
      // Remember the scanned table for 4 hours (one visit).
      if (saved && Date.now() - saved.at < 4 * 3600 * 1000) state.table = saved.n;
    }
    renderTablePill();
  }

  function renderTablePill() {
    const pill = $('tablePill');
    if (state.table) { pill.textContent = `Table ${state.table}`; pill.hidden = false; } else pill.hidden = true;
  }

  // ---------- Menu ----------
  async function loadMenu() {
    try {
      const data = await api('/api/menu');
      state.settings = data.settings;
      state.categories = data.categories;
      state.dishes.clear();
      data.categories.forEach((c) => c.dishes.forEach((d) => state.dishes.set(String(d.id), d)));
      setCurrency(data.settings.currency_symbol);
      document.title = `Menu · ${data.settings.restaurant_name}`;
      $('restName').textContent = data.settings.restaurant_name;
      $('heroTitle').textContent = data.settings.restaurant_name;
      $('heroSub').textContent = [data.settings.restaurant_address, data.settings.restaurant_phone].filter(Boolean).join(' · ') || 'Order right from your phone.';
      // Drop cart lines for dishes that disappeared or became unavailable.
      let dropped = 0;
      for (const id of Object.keys(state.cart)) {
        const d = state.dishes.get(id);
        if (!d || !d.is_available) { delete state.cart[id]; dropped++; }
      }
      if (dropped) { saveCart(); toast(`${dropped} item(s) in your cart are no longer available and were removed`); }
      renderTabs();
      renderMenu();
      renderCartBadge();
    } catch (e) {
      $('menu').innerHTML = `<div class="empty"><div class="big">😕</div>Could not load the menu. ${esc(e.message)}<br><br><button class="btn" id="retry" type="button">Try again</button></div>`;
      $('retry').addEventListener('click', loadMenu);
    }
  }

  function renderTabs() {
    const tabs = [{ id: 'all', name: 'All' }, ...state.categories.filter((c) => c.dishes.length)];
    $('catTabs').innerHTML = tabs.map((c) => `<button type="button" class="chip ${state.activeCat === String(c.id) ? 'active' : ''}" data-cat="${c.id}">${esc(c.name)}</button>`).join('');
  }

  function visibleDishes(cat) {
    const q = state.search.toLowerCase();
    return cat.dishes.filter((d) => (!state.vegOnly || d.is_veg) && (!q || d.name.toLowerCase().includes(q) || d.description.toLowerCase().includes(q)));
  }

  function dishCard(d) {
    const qty = state.cart[d.id] || 0;
    const control = !d.is_available
      ? '<button class="btn btn-secondary btn-sm" type="button" disabled>Sold out</button>'
      : qty
        ? `<div class="stepper" role="group" aria-label="Quantity of ${esc(d.name)}"><button type="button" data-dec="${d.id}" aria-label="Remove one">−</button><output>${qty}</output><button type="button" data-inc="${d.id}" aria-label="Add one">+</button></div>`
        : `<button class="btn btn-sm" type="button" data-inc="${d.id}">Add +</button>`;
    return `<article class="card dish ${d.is_available ? '' : 'soldout'}" id="dish-${d.id}">
      <div class="dish-img"><img src="${esc(d.image_url || window.App.FALLBACK_IMG)}" alt="${esc(d.name)}" loading="lazy" data-fallback>
        ${d.is_available ? '' : '<span class="soldout-tag">Sold out</span>'}</div>
      <div class="dish-body">
        <div class="dish-title"><span class="veg-mark ${d.is_veg ? '' : 'nonveg'}" title="${d.is_veg ? 'Vegetarian' : 'Non-vegetarian'}"></span>${esc(d.name)}</div>
        <div class="dish-desc">${esc(d.description)}</div>
        <div class="dish-foot"><span class="price">${money(d.price_cents)}</span>${control}</div>
      </div></article>`;
  }

  function renderMenu() {
    const cats = state.activeCat === 'all' ? state.categories : state.categories.filter((c) => String(c.id) === state.activeCat);
    const html = cats.map((c) => {
      const list = visibleDishes(c);
      if (!list.length) return '';
      return `<section class="menu-section" id="cat-${c.id}"><h2>${esc(c.name)} <small>${list.length} item${list.length > 1 ? 's' : ''}</small></h2>
        <div class="dish-grid">${list.map(dishCard).join('')}</div></section>`;
    }).join('');
    $('menu').innerHTML = html || '<div class="empty"><div class="big">🔍</div>No dishes match your search.</div>';
    wireImageFallbacks($('menu'));
  }

  function refreshDish(id) {
    const el = document.getElementById(`dish-${id}`);
    const d = state.dishes.get(String(id));
    if (el && d) {
      const tmp = document.createElement('div');
      tmp.innerHTML = dishCard(d);
      const fresh = tmp.firstElementChild;
      // Only swap the price/quantity row so the loaded image does not flicker.
      el.querySelector('.dish-foot').replaceWith(fresh.querySelector('.dish-foot'));
    }
  }

  // ---------- Cart ----------
  function saveCart() { store.set(CART_KEY, state.cart); }

  function changeQty(id, delta) {
    id = String(id);
    const d = state.dishes.get(id);
    if (!d || !d.is_available) return;
    const next = Math.max(0, Math.min(50, (state.cart[id] || 0) + delta));
    if (next === 0) delete state.cart[id]; else state.cart[id] = next;
    if (delta > 0 && next === 50) toast('Maximum 50 of one dish per order');
    saveCart();
    refreshDish(id);
    renderCartBadge();
    if (drawer) renderDrawer();
  }

  function cartLines() {
    return Object.entries(state.cart).map(([id, qty]) => ({ dish: state.dishes.get(id), qty })).filter((l) => l.dish);
  }

  function totals(type) {
    const subtotal = cartLines().reduce((a, l) => a + l.dish.price_cents * l.qty, 0);
    const tax = Math.round((subtotal * (Number(state.settings.tax_rate_percent) || 0)) / 100);
    const delivery = type === 'delivery' ? Math.round((Number(state.settings.delivery_fee) || 0) * 100) : 0;
    return { subtotal, tax, delivery, total: subtotal + tax + delivery };
  }

  function renderCartBadge() {
    const count = Object.values(state.cart).reduce((a, b) => a + b, 0);
    const badge = $('cartCount');
    badge.textContent = count;
    badge.hidden = count === 0;
    $('cartBar').hidden = count === 0;
    document.body.classList.toggle('has-cart-bar', count > 0);
    $('cartBarCount').textContent = `${count} item${count === 1 ? '' : 's'}`;
    $('cartBarTotal').textContent = money(totals('').subtotal);
  }

  // ---------- Drawer: cart + checkout ----------
  let drawer = null;
  let step = 'cart';

  function openDrawer(s = 'cart') {
    step = s;
    if (!drawer) {
      drawer = document.createElement('div');
      drawer.innerHTML = '<div class="drawer-backdrop" data-close-drawer></div><aside class="drawer" role="dialog" aria-modal="true" aria-label="Your order"></aside>';
      document.body.appendChild(drawer);
      drawer.addEventListener('click', onDrawerClick);
      drawer.addEventListener('input', onDrawerInput);
      drawer.addEventListener('change', onDrawerInput);
      drawer.addEventListener('submit', onSubmit);
      document.addEventListener('keydown', onEsc);
      document.body.style.overflow = 'hidden';
    }
    renderDrawer();
    const focusable = drawer.querySelector('.drawer-head button');
    if (focusable) focusable.focus();
  }

  function closeDrawer() {
    if (!drawer) return;
    drawer.remove();
    drawer = null;
    document.removeEventListener('keydown', onEsc);
    document.body.style.overflow = '';
  }
  const onEsc = (e) => { if (e.key === 'Escape') closeDrawer(); };

  function renderDrawer() {
    const panel = drawer.querySelector('.drawer');
    const lines = cartLines();
    if (step === 'checkout' && lines.length === 0) step = 'cart';

    if (step === 'cart') {
      const t = totals('');
      panel.innerHTML = `
        <div class="drawer-head"><h2>Your cart</h2><button class="icon-btn" type="button" data-close-drawer aria-label="Close cart">✕</button></div>
        <div class="drawer-body">${lines.length ? lines.map(({ dish: d, qty }) => `
          <div class="cart-line">
            <img src="${esc(d.image_url || window.App.FALLBACK_IMG)}" alt="" data-fallback>
            <div><div class="name">${esc(d.name)}</div><div class="sub">${money(d.price_cents)} × ${qty} = <strong>${money(d.price_cents * qty)}</strong></div></div>
            <div class="stepper" role="group" aria-label="Quantity of ${esc(d.name)}"><button type="button" data-dec="${d.id}" aria-label="Remove one">−</button><output>${qty}</output><button type="button" data-inc="${d.id}" aria-label="Add one">+</button></div>
          </div>`).join('') : '<div class="empty"><div class="big">🛒</div>Your cart is empty.<br>Add some delicious dishes!</div>'}
          ${lines.length ? '<button type="button" class="btn btn-ghost btn-sm" data-clear style="margin-top:.6rem">Clear cart</button>' : ''}
        </div>
        ${lines.length ? `<div class="drawer-foot">
          <div class="totals"><div><span>Subtotal</span><span>${money(t.subtotal)}</span></div>
          <div class="muted"><span>Tax (${esc(state.settings.tax_rate_percent)}%)</span><span>${money(t.tax)}</span></div></div>
          <button class="btn btn-block" type="button" data-goto="checkout" style="margin-top:.8rem">Continue to checkout →</button>
        </div>` : ''}`;
    } else {
      const c = state.checkout;
      if (state.table && !c._typeTouched) c.type = 'dine_in';
      const t = totals(c.type);
      const types = [['dine_in', 'Dine-in'], ['takeaway', 'Takeaway'], ['delivery', 'Delivery']];
      panel.innerHTML = `
        <div class="drawer-head"><button class="icon-btn" type="button" data-goto="cart" aria-label="Back to cart">←</button><h2>Checkout</h2><button class="icon-btn" type="button" data-close-drawer aria-label="Close">✕</button></div>
        <form id="checkoutForm" novalidate style="display:contents">
        <div class="drawer-body">
          <div id="formError" class="alert alert-error" hidden></div>
          <div class="field"><label for="cName">Your name *</label><input id="cName" name="name" type="text" required maxlength="60" autocomplete="name" value="${esc(c.name)}"></div>
          <div class="field"><span class="sr-only" id="typeLbl">Order type</span>
            <div class="segmented" role="radiogroup" aria-labelledby="typeLbl">${types.map(([v, l]) => `
              <input type="radio" name="type" id="t-${v}" value="${v}" ${c.type === v ? 'checked' : ''}><label for="t-${v}"><span class="ico" aria-hidden="true">${TYPE_ICON[v]}</span>${l}</label>`).join('')}
            </div></div>
          ${c.type === 'dine_in' ? `<div class="field"><label for="cTable">Table number *</label>
            <input id="cTable" name="table" type="number" inputmode="numeric" min="1" required value="${state.table || ''}" ${state.table ? 'readonly' : ''}>
            <div class="hint">${state.table ? 'Detected from the QR code on your table. <a href="#" data-change-table>Change</a>' : 'You can find the number on your table.'}</div></div>` : ''}
          <div class="field"><label for="cPhone">Phone number ${c.type === 'delivery' ? '*' : '<span class="muted">(optional)</span>'}</label>
            <input id="cPhone" name="phone" type="tel" inputmode="tel" maxlength="20" autocomplete="tel" value="${esc(c.phone)}" ${c.type === 'delivery' ? 'required' : ''}></div>
          ${c.type === 'delivery' ? `<div class="field"><label for="cAddr">Delivery address *</label><textarea id="cAddr" name="address" required maxlength="300" autocomplete="street-address">${esc(c.address)}</textarea></div>` : ''}
          <div class="field"><label for="cNotes">Special instructions <span class="muted">(optional)</span></label>
            <textarea id="cNotes" name="notes" maxlength="300" placeholder="e.g. less spicy, no onions">${esc(c.notes)}</textarea></div>
        </div>
        <div class="drawer-foot">
          <div class="totals"><div><span>Subtotal</span><span>${money(t.subtotal)}</span></div>
            <div class="muted"><span>Tax (${esc(state.settings.tax_rate_percent)}%)</span><span>${money(t.tax)}</span></div>
            ${t.delivery ? `<div class="muted"><span>Delivery fee</span><span>${money(t.delivery)}</span></div>` : ''}
            <div class="grand"><span>Total</span><span>${money(t.total)}</span></div></div>
          <button class="btn btn-block" type="submit" id="placeBtn" style="margin-top:.8rem">Place order · ${money(t.total)}</button>
        </div></form>`;
    }
    wireImageFallbacks(panel);
  }

  function onDrawerClick(e) {
    const t = e.target.closest('button, a');
    if (e.target.matches('[data-close-drawer]') || (t && t.matches('[data-close-drawer]'))) return closeDrawer();
    if (!t) return;
    if (t.dataset.inc) changeQty(t.dataset.inc, 1);
    else if (t.dataset.dec) changeQty(t.dataset.dec, -1);
    else if (t.dataset.goto) { step = t.dataset.goto; renderDrawer(); }
    else if (t.hasAttribute('data-clear')) { state.cart = {}; saveCart(); renderCartBadge(); renderMenu(); renderDrawer(); }
    else if (t.hasAttribute('data-change-table')) {
      e.preventDefault();
      state.table = null;
      store.del(TABLE_KEY);
      renderTablePill();
      renderDrawer();
      const inp = document.getElementById('cTable');
      if (inp) inp.focus();
    }
  }

  function onDrawerInput(e) {
    const c = state.checkout;
    const el = e.target;
    const errBox = document.getElementById('formError');
    if (errBox && e.type === 'input') errBox.hidden = true;
    if (el.name === 'type' && e.type === 'change') {
      c.type = el.value;
      c._typeTouched = true;
      renderDrawer();
      return;
    }
    if (el.name === 'name') c.name = el.value;
    if (el.name === 'phone') c.phone = el.value;
    if (el.name === 'address') c.address = el.value;
    if (el.name === 'notes') c.notes = el.value;
  }

  async function onSubmit(e) {
    e.preventDefault();
    const c = state.checkout;
    const errBox = document.getElementById('formError');
    const showErr = (msg, field) => {
      errBox.textContent = msg;
      errBox.hidden = false;
      errBox.scrollIntoView({ block: 'nearest' });
      if (field) { const f = document.getElementById(field); if (f) f.focus(); }
    };
    const tableInput = document.getElementById('cTable');
    if (c.name.trim().length < 2) return showErr('Please enter your name', 'cName');
    if (c.type === 'dine_in' && !(tableInput && Number(tableInput.value) > 0)) return showErr('Please enter your table number', 'cTable');
    if (c.type === 'delivery' && !c.phone.trim()) return showErr('Please enter a phone number for delivery', 'cPhone');
    if (c.type === 'delivery' && c.address.trim().length < 10) return showErr('Please enter your full delivery address', 'cAddr');

    const btn = document.getElementById('placeBtn');
    btn.disabled = true;
    btn.textContent = 'Placing order…';
    try {
      const order = await api('/api/orders', {
        method: 'POST',
        body: {
          customer_name: c.name,
          customer_phone: c.phone,
          order_type: c.type,
          table_number: c.type === 'dine_in' ? Number(tableInput.value) : null,
          delivery_address: c.type === 'delivery' ? c.address : '',
          notes: c.notes,
          items: cartLines().map((l) => ({ dish_id: l.dish.id, quantity: l.qty })),
        },
      });
      if (c.type === 'dine_in') store.set(TABLE_KEY, { n: order.table_number, at: Date.now() });
      const mine = store.get(ORDERS_KEY, []).filter((o) => o.token !== order.public_token);
      mine.unshift({ token: order.public_token, number: order.order_number, at: Date.now() });
      store.set(ORDERS_KEY, mine.slice(0, 10));
      state.cart = {};
      saveCart();
      store.set('rs_last_customer', { name: c.name, phone: c.phone, address: c.address });
      location.href = `/order?token=${order.public_token}`;
    } catch (err) {
      btn.disabled = false;
      btn.textContent = 'Place order';
      showErr(err.message);
      if (/unavailable|no longer/.test(err.message)) loadMenu();
    }
  }

  // ---------- Wiring ----------
  $('menu').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.inc) changeQty(b.dataset.inc, 1);
    if (b.dataset.dec) changeQty(b.dataset.dec, -1);
  });
  $('catTabs').addEventListener('click', (e) => {
    const b = e.target.closest('[data-cat]');
    if (!b) return;
    state.activeCat = b.dataset.cat;
    renderTabs();
    renderMenu();
    window.scrollTo({ top: document.querySelector('.hero').offsetHeight, behavior: 'smooth' });
  });
  let searchTimer;
  $('search').addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.search = e.target.value.trim(); renderMenu(); }, 150);
  });
  $('vegOnly').addEventListener('change', (e) => { state.vegOnly = e.target.checked; renderMenu(); });
  $('openCart').addEventListener('click', () => openDrawer('cart'));
  $('cartBar').addEventListener('click', () => openDrawer('cart'));

  const last = store.get('rs_last_customer', null);
  if (last) Object.assign(state.checkout, { name: last.name || '', phone: last.phone || '', address: last.address || '' });
  const mine = store.get(ORDERS_KEY, []);
  if (mine.length) {
    const link = $('myOrdersLink');
    link.href = `/order?token=${encodeURIComponent(mine[0].token)}`;
    link.textContent = `Order #${mine[0].number}`;
    link.hidden = false;
  }

  resolveTable().then(loadMenu);
})();
