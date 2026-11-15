'use strict';
/* API integration tests — run with `npm test`. Uses a throw-away database. */
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'rs-test-'));
process.env.DATA_DIR = TMP;
const { createApp } = require('../src/app');

let server;
let base;

before(async () => {
  const app = createApp({ dbFile: path.join(TMP, 'test.db'), loginLimit: 1000, orderLimit: 1000 });
  server = http.createServer(app);
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  server.closeAllConnections();
  await new Promise((r) => server.close(r));
  fs.rmSync(TMP, { recursive: true, force: true });
});

/** Tiny fetch wrapper with an optional cookie jar. */
function client() {
  let cookie = '';
  return async function call(method, url, body, headers = {}) {
    const opts = { method, headers: { ...headers } };
    if (cookie) opts.headers.cookie = cookie;
    if (body instanceof FormData) opts.body = body;
    else if (typeof body === 'string') { opts.body = body; opts.headers['content-type'] = 'application/json'; }
    else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers['content-type'] = 'application/json'; }
    const res = await fetch(base + url, opts);
    const set = res.headers.get('set-cookie');
    if (set) cookie = set.split(';')[0].endsWith('=') ? '' : set.split(';')[0];
    const type = res.headers.get('content-type') || '';
    const data = type.includes('json') ? await res.json() : Buffer.from(await res.arrayBuffer());
    return { status: res.status, data, headers: res.headers };
  };
}

const anon = client();
const admin = client();
const kitchen = client();
let menu;
const dish = (name) => menu.categories.flatMap((c) => c.dishes).find((d) => d.name === name);

test('health check and menu with 4 categories of photographed dishes', async () => {
  assert.equal((await anon('GET', '/api/health')).status, 200);
  const r = await anon('GET', '/api/menu');
  assert.equal(r.status, 200);
  menu = r.data;
  assert.deepEqual(menu.categories.map((c) => c.name), ['Starters', 'Main Course', 'Beverages', 'Desserts']);
  const dishes = menu.categories.flatMap((c) => c.dishes);
  assert.equal(dishes.length, 16);
  for (const d of dishes) {
    assert.ok(d.image_url, `${d.name} has an image`);
    const img = await anon('GET', d.image_url);
    assert.equal(img.status, 200, `${d.image_url} is served`);
  }
  assert.equal(menu.settings.currency_symbol, '₹');
});

test('static pages are served', async () => {
  for (const p of ['/', '/order', '/login', '/admin', '/kitchen', '/qr-print']) {
    const r = await anon('GET', p);
    assert.equal(r.status, 200, p);
    assert.match(r.data.toString(), /<!doctype html>/i);
  }
});

test('security headers are set', async () => {
  const r = await anon('GET', '/');
  assert.match(r.headers.get('content-security-policy'), /script-src 'self'/);
  assert.equal(r.headers.get('x-content-type-options'), 'nosniff');
  assert.equal(r.headers.get('x-powered-by'), null);
});

let dineIn;
test('dine-in order: server computes prices and ignores client-supplied prices', async () => {
  const tikka = dish('Paneer Tikka');
  const lassi = dish('Mango Lassi');
  const r = await anon('POST', '/api/orders', {
    customer_name: 'Asha',
    order_type: 'dine_in',
    table_number: 4,
    notes: 'Less spicy',
    items: [{ dish_id: tikka.id, quantity: 2, price_cents: 1 }, { dish_id: lassi.id, quantity: 1 }, { dish_id: tikka.id, quantity: 1 }],
    total_cents: 5,
  });
  assert.equal(r.status, 201, JSON.stringify(r.data));
  dineIn = r.data;
  assert.equal(dineIn.status, 'pending');
  assert.equal(dineIn.items.length, 2, 'duplicate lines merged');
  assert.equal(dineIn.items[0].quantity, 3);
  const subtotal = tikka.price_cents * 3 + lassi.price_cents;
  assert.equal(dineIn.subtotal_cents, subtotal);
  assert.equal(dineIn.tax_cents, Math.round(subtotal * 0.05));
  assert.equal(dineIn.delivery_fee_cents, 0);
  assert.equal(dineIn.total_cents, subtotal + dineIn.tax_cents);
  assert.match(dineIn.public_token, /^[a-f0-9]{32}$/);
  assert.match(dineIn.order_number, /^\d+$/);
});

test('takeaway and delivery orders', async () => {
  const t = await anon('POST', '/api/orders', { customer_name: 'Ben', order_type: 'takeaway', table_number: 99, items: [{ dish_id: dish('Cold Coffee').id, quantity: 1 }] });
  assert.equal(t.status, 201);
  assert.equal(t.data.table_number, null, 'table ignored for takeaway');
  assert.equal(t.data.delivery_fee_cents, 0);

  const d = await anon('POST', '/api/orders', {
    customer_name: 'Chitra', order_type: 'delivery', customer_phone: '+91 99887 76655',
    delivery_address: '45 Park Street, Kolkata 700016', items: [{ dish_id: dish('Butter Chicken').id, quantity: 1 }],
  });
  assert.equal(d.status, 201);
  assert.equal(d.data.delivery_fee_cents, 4000);
  assert.equal(d.data.total_cents, d.data.subtotal_cents + d.data.tax_cents + 4000);
});

test('order validation errors', async () => {
  const id = dish('Gulab Jamun').id;
  const cases = [
    [{ customer_name: 'A', order_type: 'takeaway', items: [{ dish_id: id, quantity: 1 }] }, /Name must be at least/],
    [{ customer_name: 'Dev', order_type: 'takeaway', items: [] }, /cart is empty/],
    [{ customer_name: 'Dev', order_type: 'teleport', items: [{ dish_id: id, quantity: 1 }] }, /Dine-in, Takeaway or Delivery/],
    [{ customer_name: 'Dev', order_type: 'dine_in', items: [{ dish_id: id, quantity: 1 }] }, /Table number/],
    [{ customer_name: 'Dev', order_type: 'dine_in', table_number: 999, items: [{ dish_id: id, quantity: 1 }] }, /Table 999 does not exist/],
    [{ customer_name: 'Dev', order_type: 'delivery', delivery_address: '1 Long Street, City', items: [{ dish_id: id, quantity: 1 }] }, /Phone number is required/],
    [{ customer_name: 'Dev', order_type: 'delivery', customer_phone: '9876543210', items: [{ dish_id: id, quantity: 1 }] }, /Delivery address/],
    [{ customer_name: 'Dev', order_type: 'takeaway', customer_phone: 'call me', items: [{ dish_id: id, quantity: 1 }] }, /valid phone/],
    [{ customer_name: 'Dev', order_type: 'takeaway', items: [{ dish_id: id, quantity: 0 }] }, /Quantity/],
    [{ customer_name: 'Dev', order_type: 'takeaway', items: [{ dish_id: id, quantity: 51 }] }, /Quantity/],
    [{ customer_name: 'Dev', order_type: 'takeaway', items: [{ dish_id: id, quantity: 30 }, { dish_id: id, quantity: 30 }] }, /Maximum quantity/],
    [{ customer_name: 'Dev', order_type: 'takeaway', items: [{ dish_id: 99999, quantity: 1 }] }, /no longer on the menu/],
  ];
  for (const [body, re] of cases) {
    const r = await anon('POST', '/api/orders', body);
    assert.equal(r.status, 400, JSON.stringify(body));
    assert.match(r.data.error, re);
  }
  const bad = await anon('POST', '/api/orders', '{not json');
  assert.equal(bad.status, 400);
  assert.equal(bad.data.error, 'Invalid JSON');
});

test('customer can view own order and download bills by token only', async () => {
  const r = await anon('GET', `/api/public/orders/${dineIn.public_token}`);
  assert.equal(r.status, 200);
  assert.equal(r.data.customer_name, 'Asha');
  assert.equal((await anon('GET', '/api/public/orders/0123456789abcdef0123456789abcdef')).status, 404);
  assert.equal((await anon('GET', '/api/public/orders/not-a-token')).status, 404);
  for (const q of ['', '?format=receipt', '?download=1']) {
    const pdf = await anon('GET', `/api/public/orders/${dineIn.public_token}/bill.pdf${q}`);
    assert.equal(pdf.status, 200);
    assert.equal(pdf.headers.get('content-type'), 'application/pdf');
    assert.equal(pdf.data.subarray(0, 5).toString(), '%PDF-');
    assert.ok(pdf.data.length > 2000);
  }
  const dl = await anon('GET', `/api/public/orders/${dineIn.public_token}/bill.pdf?download=1`);
  assert.match(dl.headers.get('content-disposition'), /attachment; filename="bill-\d+\.pdf"/);
});

test('staff endpoints require authentication', async () => {
  for (const [m, u] of [['GET', '/api/orders'], ['GET', '/api/admin/dishes'], ['GET', '/api/admin/settings'], ['PATCH', `/api/orders/${dineIn.id}/status`], ['GET', `/api/orders/${dineIn.id}/bill.pdf`], ['GET', '/api/auth/me']]) {
    assert.equal((await anon(m, u, m === 'PATCH' ? { status: 'ready' } : undefined)).status, 401, `${m} ${u}`);
  }
  const forged = await anon('GET', '/api/orders', undefined, { cookie: 'rsid=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOjEsInJvbGUiOiJhZG1pbiJ9.bad' });
  assert.equal(forged.status, 401);
});

test('login: wrong password rejected, correct one sets httpOnly cookie', async () => {
  const bad = await admin('POST', '/api/auth/login', { username: 'admin', password: 'nope' });
  assert.equal(bad.status, 401);
  assert.equal(bad.data.error, 'Incorrect username or password');
  const missing = await admin('POST', '/api/auth/login', { username: 'ghost', password: 'nope' });
  assert.equal(missing.status, 401);
  const ok = await admin('POST', '/api/auth/login', { username: 'admin', password: 'Admin@123' });
  assert.equal(ok.status, 200);
  assert.equal(ok.data.role, 'admin');
  const cookie = ok.headers.get('set-cookie');
  assert.match(cookie, /HttpOnly/i);
  assert.match(cookie, /SameSite=Strict/i);
  assert.equal((await admin('GET', '/api/auth/me')).data.username, 'admin');
  const k = await kitchen('POST', '/api/auth/login', { username: 'KITCHEN', password: 'Kitchen@123' });
  assert.equal(k.status, 200, 'usernames are case-insensitive');
});

test('role separation: kitchen cannot use admin APIs or mark payments', async () => {
  assert.equal((await kitchen('GET', '/api/orders')).status, 200);
  assert.equal((await kitchen('GET', '/api/admin/dishes')).status, 403);
  assert.equal((await kitchen('PUT', '/api/admin/settings', {})).status, 403);
  assert.equal((await kitchen('PATCH', `/api/orders/${dineIn.id}/payment`, { payment_status: 'paid' })).status, 403);
});

test('kitchen receives new orders live over Server-Sent Events', async () => {
  const k = await kitchen('GET', '/api/auth/me');
  assert.equal(k.status, 200);
  const login = await fetch(`${base}/api/auth/login`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ username: 'kitchen', password: 'Kitchen@123' }) });
  const cookie = login.headers.get('set-cookie').split(';')[0];
  const got = new Promise((resolve, reject) => {
    const req = http.get(`${base}/api/orders/stream`, { headers: { cookie } }, (res) => {
      assert.match(res.headers['content-type'], /^text\/event-stream/);
      let buf = '';
      res.on('data', (c) => {
        buf += c;
        const m = buf.match(/event: order_created\ndata: (.*)\n/);
        if (m) { req.destroy(); resolve(JSON.parse(m[1])); }
      });
    });
    req.on('error', (e) => { if (e.code !== 'ECONNRESET') reject(e); });
    setTimeout(() => reject(new Error('no SSE event')), 4000);
  });
  await new Promise((r) => setTimeout(r, 150));
  const placed = await anon('POST', '/api/orders', { customer_name: 'Live Test', order_type: 'takeaway', items: [{ dish_id: dish('Masala Chai').id, quantity: 2 }] });
  const evt = await got;
  assert.equal(evt.id, placed.data.id);
  assert.equal(evt.items[0].quantity, 2);
});

test('order status workflow and transition rules', async () => {
  const list = await kitchen('GET', '/api/orders?status=active');
  assert.ok(list.data.some((o) => o.id === dineIn.id));
  for (const s of ['preparing', 'ready']) {
    const r = await kitchen('PATCH', `/api/orders/${dineIn.id}/status`, { status: s });
    assert.equal(r.status, 200);
    assert.equal(r.data.status, s);
  }
  assert.equal((await anon('GET', `/api/public/orders/${dineIn.public_token}`)).data.status, 'ready');
  assert.equal((await kitchen('PATCH', `/api/orders/${dineIn.id}/status`, { status: 'eaten' })).status, 400);
  assert.equal((await kitchen('PATCH', `/api/orders/${dineIn.id}/status`, { status: 'completed' })).status, 200);
  const back = await kitchen('PATCH', `/api/orders/${dineIn.id}/status`, { status: 'preparing' });
  assert.equal(back.status, 409, 'completed orders are final');
  assert.equal((await kitchen('PATCH', '/api/orders/99999/status', { status: 'ready' })).status, 404);
  const active = await kitchen('GET', '/api/orders?status=active');
  assert.ok(!active.data.some((o) => o.id === dineIn.id));
});

test('admin marks payment, filters orders and prints staff bills', async () => {
  const p = await admin('PATCH', `/api/orders/${dineIn.id}/payment`, { payment_status: 'paid' });
  assert.equal(p.status, 200);
  assert.equal(p.data.payment_status, 'paid');
  assert.equal((await admin('PATCH', `/api/orders/${dineIn.id}/payment`, { payment_status: 'free' })).status, 400);
  const search = await admin('GET', '/api/orders?status=all&q=Chitra');
  assert.equal(search.data.length, 1);
  assert.equal(search.data[0].order_type, 'delivery');
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today.getTime() + 864e5);
  const ranged = await admin('GET', `/api/orders?status=all&from=${today.toISOString()}&to=${tomorrow.toISOString()}`);
  assert.ok(ranged.data.length >= 4);
  const none = await admin('GET', '/api/orders?status=all&from=2001-01-01T00:00:00Z&to=2001-01-02T00:00:00Z');
  assert.equal(none.data.length, 0);
  assert.equal((await admin('GET', '/api/orders?status=bogus')).status, 400);
  const pdf = await kitchen('GET', `/api/orders/${dineIn.id}/bill.pdf?format=receipt`);
  assert.equal(pdf.data.subarray(0, 5).toString(), '%PDF-');
  const stats = await admin('GET', `/api/admin/stats?from=${today.toISOString()}`);
  assert.equal(stats.status, 200);
  assert.ok(stats.data.orders >= 4);
  assert.equal(stats.data.paid_cents, dineIn.total_cents);
  assert.deepEqual(stats.data.default_passwords.sort(), ['admin', 'kitchen']);
});

let newDish;
test('admin manages dishes, prices and availability', async () => {
  const cats = (await admin('GET', '/api/admin/categories')).data;
  const desserts = cats.find((c) => c.name === 'Desserts');
  const c = await admin('POST', '/api/admin/dishes', { category_id: desserts.id, name: 'Kulfi', description: 'Saffron pistachio kulfi', price: '149.50', is_veg: true, image_url: '/images/dishes/gulab-jamun.svg' });
  assert.equal(c.status, 201, JSON.stringify(c.data));
  newDish = c.data;
  assert.equal(newDish.price_cents, 14950);
  assert.equal(newDish.is_available, true);

  const u = await admin('PUT', `/api/admin/dishes/${newDish.id}`, { ...newDish, price: 159, image_url: newDish.image_url });
  assert.equal(u.data.price_cents, 15900);

  for (const bad of [{ price: -1 }, { price: 'abc' }, { name: '' }, { category_id: 9999 }, { image_url: 'javascript:alert(1)' }, { image_url: '/images/../../etc/passwd' }]) {
    const r = await admin('PUT', `/api/admin/dishes/${newDish.id}`, { category_id: desserts.id, name: 'Kulfi', price: 10, ...bad });
    assert.equal(r.status, 400, JSON.stringify(bad));
  }

  const off = await admin('PATCH', `/api/admin/dishes/${newDish.id}/availability`, { is_available: false });
  assert.equal(off.data.is_available, false);
  const m = await anon('GET', '/api/menu');
  assert.equal(m.data.categories.flatMap((x) => x.dishes).find((d) => d.id === newDish.id).is_available, false);
  const order = await anon('POST', '/api/orders', { customer_name: 'Eve', order_type: 'takeaway', items: [{ dish_id: newDish.id, quantity: 1 }] });
  assert.equal(order.status, 400);
  assert.match(order.data.error, /currently unavailable/);

  await admin('PATCH', `/api/admin/dishes/${newDish.id}/availability`, { is_available: true });
  const ok = await anon('POST', '/api/orders', { customer_name: 'Eve', order_type: 'takeaway', items: [{ dish_id: newDish.id, quantity: 2 }] });
  assert.equal(ok.status, 201);
  assert.equal(ok.data.subtotal_cents, 31800);

  // Deleting the dish keeps the historic bill intact.
  assert.equal((await admin('DELETE', `/api/admin/dishes/${newDish.id}`)).status, 200);
  const old = await anon('GET', `/api/public/orders/${ok.data.public_token}`);
  assert.equal(old.data.items[0].dish_name, 'Kulfi');
  assert.equal(old.data.items[0].dish_id, null);
  assert.equal((await admin('DELETE', `/api/admin/dishes/${newDish.id}`)).status, 404);
});

test('admin manages categories', async () => {
  const c = await admin('POST', '/api/admin/categories', { name: 'Soups', sort_order: 1 });
  assert.equal(c.status, 201);
  assert.equal((await admin('POST', '/api/admin/categories', { name: 'soups' })).status, 409);
  assert.equal((await admin('PUT', `/api/admin/categories/${c.data.id}`, { name: 'Soups & Salads', sort_order: 2 })).data.name, 'Soups & Salads');
  const starters = (await admin('GET', '/api/admin/categories')).data.find((x) => x.name === 'Starters');
  const del = await admin('DELETE', `/api/admin/categories/${starters.id}`);
  assert.equal(del.status, 409);
  assert.match(del.data.error, /Move or delete/);
  assert.equal((await admin('DELETE', `/api/admin/categories/${c.data.id}`)).status, 200);
});

test('photo upload accepts real images only', async () => {
  const png = Buffer.from('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201a5f9d1c40000000049454e44ae426082', 'hex');
  const fd = new FormData();
  fd.append('image', new Blob([png], { type: 'image/png' }), 'dish.png');
  const up = await admin('POST', '/api/admin/uploads', fd);
  assert.equal(up.status, 201, JSON.stringify(up.data));
  assert.match(up.data.url, /^\/uploads\/[a-f0-9]{24}\.png$/);
  const served = await anon('GET', up.data.url);
  assert.equal(served.status, 200);
  assert.equal(served.headers.get('content-type'), 'image/png');

  const fake = new FormData();
  fake.append('image', new Blob(['<script>alert(1)</script>'], { type: 'image/png' }), 'evil.png');
  const rej = await admin('POST', '/api/admin/uploads', fake);
  assert.equal(rej.status, 400);
  assert.match(rej.data.error, /JPEG, PNG or WebP/);

  const big = new FormData();
  big.append('image', new Blob([Buffer.concat([png, Buffer.alloc(3.2 * 1024 * 1024)])], { type: 'image/png' }), 'big.png');
  assert.match((await admin('POST', '/api/admin/uploads', big)).data.error, /3 MB/);
  assert.equal((await kitchen('POST', '/api/admin/uploads', fd)).status, 403);
});

test('tables and QR codes', async () => {
  const t = await admin('POST', '/api/admin/tables', { table_number: 21, seats: 2 });
  assert.equal(t.status, 201);
  assert.equal((await admin('POST', '/api/admin/tables', { table_number: 21 })).status, 409);
  const png = await admin('GET', `/api/admin/tables/${t.data.id}/qr.png`);
  assert.equal(png.headers.get('content-type'), 'image/png');
  assert.equal(png.data.subarray(1, 4).toString(), 'PNG');
  const info = await admin('GET', `/api/admin/tables/${t.data.id}/qr`);
  assert.equal(info.data.url, `${base}/?table=21`);
  assert.equal((await anon('GET', '/api/tables/21')).data.seats, 2);

  await admin('PUT', `/api/admin/tables/${t.data.id}`, { table_number: 21, seats: 2, is_active: false });
  assert.equal((await anon('GET', '/api/tables/21')).status, 404);
  const o = await anon('POST', '/api/orders', { customer_name: 'Faye', order_type: 'dine_in', table_number: 21, items: [{ dish_id: dish('Masala Chai').id, quantity: 1 }] });
  assert.equal(o.status, 400);
  assert.equal((await admin('DELETE', `/api/admin/tables/${t.data.id}`)).status, 200);
});

test('settings: validation, public URL in QR codes, tax rate applied to new orders', async () => {
  const s = (await admin('GET', '/api/admin/settings')).data;
  assert.equal((await admin('PUT', '/api/admin/settings', { ...s, tax_rate_percent: 80 })).status, 400);
  assert.equal((await admin('PUT', '/api/admin/settings', { ...s, public_base_url: 'ftp://x' })).status, 400);
  assert.equal((await admin('PUT', '/api/admin/settings', { ...s, timezone: 'Mars/Olympus' })).status, 400);
  const saved = await admin('PUT', '/api/admin/settings', { ...s, restaurant_name: 'Curry House', tax_rate_percent: 18, public_base_url: 'https://order.example.com/', gst_number: '29ABCDE1234F1Z5' });
  assert.equal(saved.status, 200);
  assert.equal(saved.data.restaurant_name, 'Curry House');
  assert.equal((await anon('GET', '/api/menu')).data.settings.restaurant_name, 'Curry House');
  const tables = (await admin('GET', '/api/admin/tables')).data;
  assert.equal((await admin('GET', `/api/admin/tables/${tables[0].id}/qr`)).data.url, 'https://order.example.com/?table=1');
  const o = await anon('POST', '/api/orders', { customer_name: 'Gita', order_type: 'takeaway', items: [{ dish_id: dish('Masala Chai').id, quantity: 1 }] });
  assert.equal(o.data.tax_cents, Math.round(dish('Masala Chai').price_cents * 0.18));
  await admin('PUT', '/api/admin/settings', { ...s });
});

test('staff accounts and password changes', async () => {
  assert.equal((await admin('POST', '/api/admin/users', { username: 'chef', role: 'kitchen', password: 'short' })).status, 400);
  assert.equal((await admin('POST', '/api/admin/users', { username: 'chef', role: 'kitchen', password: 'onlyletters' })).status, 400);
  assert.equal((await admin('POST', '/api/admin/users', { username: 'chef', role: 'waiter', password: 'Chef12345' })).status, 400);
  const u = await admin('POST', '/api/admin/users', { username: 'chef', role: 'kitchen', password: 'Chef12345' });
  assert.equal(u.status, 201);
  assert.equal((await admin('POST', '/api/admin/users', { username: 'Chef', role: 'kitchen', password: 'Chef12345' })).status, 409);

  const chef = client();
  assert.equal((await chef('POST', '/api/auth/login', { username: 'chef', password: 'Chef12345' })).status, 200);
  assert.equal((await chef('POST', '/api/auth/change-password', { current_password: 'wrong', new_password: 'NewPass123' })).status, 400);
  assert.equal((await chef('POST', '/api/auth/change-password', { current_password: 'Chef12345', new_password: 'NewPass123' })).status, 200);
  assert.equal((await client()('POST', '/api/auth/login', { username: 'chef', password: 'NewPass123' })).status, 200);

  assert.equal((await admin('PUT', `/api/admin/users/${u.data.id}/password`, { password: 'Reset12345' })).status, 200);
  assert.equal((await client()('POST', '/api/auth/login', { username: 'chef', password: 'Reset12345' })).status, 200);

  const me = (await admin('GET', '/api/auth/me')).data;
  assert.equal((await admin('DELETE', `/api/admin/users/${me.id}`)).status, 400);
  assert.equal((await admin('DELETE', `/api/admin/users/${u.data.id}`)).status, 200);
  assert.equal((await chef('GET', '/api/orders')).status, 401, 'deleted user session is rejected');
});

test('cross-origin state-changing requests are blocked', async () => {
  const r = await admin('POST', '/api/admin/categories', { name: 'Evil' }, { origin: 'https://evil.example' });
  assert.equal(r.status, 403);
  const same = await admin('POST', '/api/admin/categories', { name: 'Good' }, { origin: base });
  assert.equal(same.status, 201);
});

test('logout ends the session', async () => {
  const c = client();
  await c('POST', '/api/auth/login', { username: 'admin', password: 'Admin@123' });
  assert.equal((await c('GET', '/api/auth/me')).status, 200);
  await c('POST', '/api/auth/logout');
  assert.equal((await c('GET', '/api/auth/me')).status, 401);
});

test('login attempts are rate limited', async () => {
  const app = createApp({ dbFile: path.join(TMP, 'rl.db'), loginLimit: 3 });
  const s = http.createServer(app);
  await new Promise((r) => s.listen(0, '127.0.0.1', r));
  const url = `http://127.0.0.1:${s.address().port}/api/auth/login`;
  const statuses = [];
  for (let i = 0; i < 5; i++) {
    const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ username: 'admin', password: 'bad' }) });
    statuses.push(r.status);
  }
  s.closeAllConnections();
  await new Promise((r) => s.close(r));
  app.locals.db.close();
  assert.deepEqual(statuses, [401, 401, 401, 429, 429]);
});

test('unknown API routes return JSON 404', async () => {
  const r = await anon('GET', '/api/nope');
  assert.equal(r.status, 404);
  assert.equal(r.data.error, 'Not found');
});
