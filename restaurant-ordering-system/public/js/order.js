(function () {
  'use strict';
  const { api, money, esc, setCurrency, TYPE_LABEL, fmtDateTime } = window.App;
  const root = document.getElementById('root');
  const token = new URLSearchParams(location.search).get('token') || '';
  let timer = null;
  let lastStatus = null;

  const READY_TEXT = { dine_in: 'Ready — on its way to your table', takeaway: 'Ready for pickup at the counter', delivery: 'Ready — out for delivery soon' };
  const DONE_TEXT = { dine_in: 'Served. Enjoy your meal!', takeaway: 'Picked up. Enjoy!', delivery: 'Delivered. Enjoy!' };

  function headline(o) {
    switch (o.status) {
      case 'pending': return ['Order received!', 'The kitchen will start preparing it shortly.'];
      case 'preparing': return ['Being prepared 👩‍🍳', 'Our chefs are cooking your food right now.'];
      case 'ready': return ['Your order is ready', READY_TEXT[o.order_type]];
      case 'completed': return ['Order completed', DONE_TEXT[o.order_type]];
      default: return ['Order cancelled', 'This order was cancelled. Please speak to our staff if this is unexpected.'];
    }
  }

  function render(o) {
    const [title, sub] = headline(o);
    const order = ['pending', 'preparing', 'ready', 'completed'];
    const idx = order.indexOf(o.status);
    const steps = ['Received', 'Preparing', 'Ready', o.order_type === 'delivery' ? 'Delivered' : o.order_type === 'takeaway' ? 'Picked up' : 'Served'];
    const billUrl = `/api/public/orders/${encodeURIComponent(o.public_token)}/bill.pdf`;
    root.innerHTML = `
      <section class="card confirm-hero">
        <div class="tick ${o.status === 'cancelled' ? 'cancel' : ''}" aria-hidden="true">${o.status === 'cancelled' ? '✕' : '✓'}</div>
        <div class="muted">Order number</div>
        <div class="order-no">#${esc(o.order_number)}</div>
        <h1 style="font-size:1.35rem;margin-top:.6rem">${esc(title)}</h1>
        <p class="muted" style="margin:.3rem 0 0">${esc(sub)}</p>
        ${o.status === 'cancelled' ? '' : `<div class="steps" aria-label="Order progress">${steps.map((s, i) => `<div class="step ${i < idx || o.status === 'completed' ? 'done' : i === idx ? 'current' : ''}"><div class="dot"></div>${s}</div>`).join('')}</div>`}
        ${['completed', 'cancelled'].includes(o.status) ? '' : '<p class="hint" style="margin-top:.8rem">This page updates automatically.</p>'}
      </section>

      <section class="card section">
        <h3>Order details</h3>
        <dl class="kv">
          <dt>Name</dt><dd>${esc(o.customer_name)}</dd>
          <dt>Type</dt><dd>${esc(TYPE_LABEL[o.order_type])}${o.table_number ? ` · Table ${o.table_number}` : ''}</dd>
          ${o.customer_phone ? `<dt>Phone</dt><dd>${esc(o.customer_phone)}</dd>` : ''}
          ${o.order_type === 'delivery' ? `<dt>Address</dt><dd>${esc(o.delivery_address)}</dd>` : ''}
          <dt>Placed</dt><dd>${esc(fmtDateTime(o.created_at))}</dd>
          <dt>Payment</dt><dd><span class="badge badge-${o.payment_status}">${o.payment_status === 'paid' ? 'Paid' : 'Pay at counter'}</span></dd>
          ${o.notes ? `<dt>Notes</dt><dd>${esc(o.notes)}</dd>` : ''}
        </dl>
      </section>

      <section class="card section">
        <h3>Items</h3>
        ${o.items.map((i) => `<div class="item-line"><span>${i.quantity} × ${esc(i.dish_name)}</span><strong>${money(i.line_total_cents)}</strong></div>`).join('')}
        <div class="totals" style="margin-top:.8rem">
          <div><span>Subtotal</span><span>${money(o.subtotal_cents)}</span></div>
          <div class="muted"><span>Tax</span><span>${money(o.tax_cents)}</span></div>
          ${o.delivery_fee_cents ? `<div class="muted"><span>Delivery fee</span><span>${money(o.delivery_fee_cents)}</span></div>` : ''}
          <div class="grand"><span>Total</span><span>${money(o.total_cents)}</span></div>
        </div>
        <div class="actions">
          <a class="btn" href="${billUrl}?download=1" download>⬇ Download bill (PDF)</a>
          <a class="btn btn-secondary" href="${billUrl}" target="_blank" rel="noopener">🖨 View / print bill</a>
          <a class="btn btn-secondary" href="/">＋ Order more</a>
        </div>
      </section>`;
  }

  async function load() {
    try {
      const o = await api(`/api/public/orders/${encodeURIComponent(token)}`);
      if (lastStatus && lastStatus !== o.status && navigator.vibrate) navigator.vibrate(200);
      lastStatus = o.status;
      render(o);
      if (['completed', 'cancelled'].includes(o.status)) clearInterval(timer);
    } catch (e) {
      if (e.status === 404 || !token) {
        clearInterval(timer);
        root.innerHTML = '<div class="card section empty"><div class="big">🔎</div>We couldn’t find that order.<br><br><a class="btn" href="/">Back to menu</a></div>';
      }
      // Network hiccups: keep the last render and retry on the next tick.
    }
  }

  api('/api/menu').then((m) => {
    setCurrency(m.settings.currency_symbol);
    document.getElementById('restName').textContent = m.settings.restaurant_name;
    document.title = `Order confirmation · ${m.settings.restaurant_name}`;
  }).catch(() => {}).finally(() => {
    load();
    timer = setInterval(load, 5000);
  });
})();
