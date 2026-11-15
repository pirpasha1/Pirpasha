'use strict';
/**
 * End-to-end browser test (Playwright + Chromium).
 * Runs the full customer → kitchen → admin journey on phone, tablet and desktop
 * sizes and fails on any JavaScript error, failed request or horizontal overflow.
 *
 *   npm run test:ui            (screenshots are written to test-output/)
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const assert = require('node:assert/strict');
const { chromium, devices } = require('playwright');

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'rs-ui-'));
process.env.DATA_DIR = TMP;
const { createApp } = require('../src/app');

const OUT = path.join(__dirname, '..', 'test-output');
fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = [
  { name: 'phone', options: { ...devices['Pixel 7'] } },
  { name: 'tablet', options: { ...devices['Galaxy Tab S4'] } },
  { name: 'desktop', options: { viewport: { width: 1366, height: 800 } } },
];

let base;
let passed = 0;
const step = async (label, fn) => {
  process.stdout.write(`  • ${label} … `);
  await fn();
  passed++;
  console.log('ok');
};

function watch(page, label) {
  const problems = [];
  page.on('pageerror', (e) => problems.push(`[${label}] JS error: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error' && !/status of 4\d\d/.test(m.text())) problems.push(`[${label}] console: ${m.text()}`); });
  page.on('response', (r) => {
    const u = r.url();
    // 401 from /api/auth/me is the expected "not signed in" probe on the login page.
    if (r.status() >= 400 && !u.endsWith('/api/auth/me')) problems.push(`[${label}] HTTP ${r.status()} ${u}`);
  });
  page.on('requestfailed', (r) => { if (!/stream|favicon/.test(r.url()) && r.failure().errorText !== 'net::ERR_ABORTED') problems.push(`[${label}] failed ${r.url()} ${r.failure().errorText}`); });
  return problems;
}

async function noHorizontalScroll(page, where) {
  const { sw, cw } = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  assert.ok(sw <= cw + 1, `${where}: page scrolls horizontally (${sw} > ${cw})`);
}

async function allImagesLoaded(page) {
  await page.evaluate(async () => {
    for (const img of document.querySelectorAll('img')) img.loading = 'eager';
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise((r) => setTimeout(r, 400));
    window.scrollTo(0, 0);
  });
  await page.waitForFunction(() => [...document.querySelectorAll('img')].every((i) => i.complete), null, { timeout: 8000 });
  const broken = await page.evaluate(() => [...document.querySelectorAll('img')].filter((i) => !i.naturalWidth).map((i) => i.src));
  assert.deepEqual(broken, [], 'all images load');
}

async function login(page, user, pass) {
  await page.goto(`${base}/login`);
  await page.fill('#username', user);
  await page.fill('#password', pass);
  await page.click('#submitBtn');
}

async function customerJourney(browser, vp) {
  const ctx = await browser.newContext(vp.options);
  const page = await ctx.newPage();
  const problems = watch(page, `${vp.name}/customer`);

  await step(`${vp.name}: QR link sets table and menu renders`, async () => {
    await page.goto(`${base}/?table=3`);
    await page.waitForSelector('.dish');
    assert.equal(await page.textContent('#tablePill'), 'Table 3');
    assert.ok(!page.url().includes('table='), 'table param removed from URL');
    assert.equal(await page.locator('.dish').count(), 16);
    assert.equal(await page.locator('.menu-section h2').count(), 4);
    await allImagesLoaded(page);
    await noHorizontalScroll(page, `${vp.name} menu`);
    await page.screenshot({ path: path.join(OUT, `${vp.name}-1-menu.png`) });
  });

  await step(`${vp.name}: category tabs, search and veg filter`, async () => {
    await page.click('#catTabs >> text=Desserts');
    assert.equal(await page.locator('.menu-section').count(), 1);
    assert.equal(await page.locator('.dish').count(), 3);
    await page.click('#catTabs >> text=All');
    await page.fill('#search', 'lassi');
    await page.waitForFunction(() => document.querySelectorAll('.dish').length === 1);
    await page.fill('#search', 'zzzz');
    await page.waitForSelector('text=No dishes match your search.');
    await page.fill('#search', '');
    await page.waitForFunction(() => document.querySelectorAll('.dish').length === 16);
    await page.check('#vegOnly');
    assert.equal(await page.locator('.dish .veg-mark.nonveg').count(), 0);
    assert.equal(await page.locator('.dish').count(), 13);
    await page.uncheck('#vegOnly');
  });

  await step(`${vp.name}: add to cart with quantity stepper`, async () => {
    const tikka = page.locator('.dish', { hasText: 'Paneer Tikka' });
    await tikka.locator('button:has-text("Add")').click();
    await tikka.locator('[data-inc]').click();
    assert.equal(await tikka.locator('output').textContent(), '2');
    const lassi = page.locator('.dish', { hasText: 'Mango Lassi' });
    await lassi.locator('button:has-text("Add")').click();
    assert.equal(await page.textContent('#cartCount'), '3');
    if (vp.name === 'desktop') assert.ok(await page.locator('#cartBar').isHidden(), 'cart bar hidden on desktop');
    else assert.ok(await page.locator('#cartBar').isVisible(), 'floating cart bar on mobile');
    await page.screenshot({ path: path.join(OUT, `${vp.name}-2-cart-added.png`) });
  });

  await step(`${vp.name}: cart drawer edits quantities`, async () => {
    await (vp.name === 'desktop' ? page.click('#openCart') : page.click('#cartBar'));
    await page.waitForSelector('.drawer .cart-line');
    assert.equal(await page.locator('.drawer .cart-line').count(), 2);
    const lassiLine = page.locator('.cart-line', { hasText: 'Mango Lassi' });
    await lassiLine.locator('[data-dec]').click();
    assert.equal(await page.locator('.drawer .cart-line').count(), 1);
    await page.click('[data-close-drawer].icon-btn');
    await page.locator('.dish', { hasText: 'Mango Lassi' }).locator('button:has-text("Add")').click();
    await page.click('#openCart');
    assert.equal(await page.locator('.drawer .cart-line').count(), 2);
    await noHorizontalScroll(page, `${vp.name} cart`);
    await page.screenshot({ path: path.join(OUT, `${vp.name}-3-cart.png`) });
  });

  let token;
  await step(`${vp.name}: checkout validation and dine-in order`, async () => {
    await page.click('text=Continue to checkout');
    assert.equal(await page.inputValue('#cTable'), '3');
    assert.equal(await page.getAttribute('#cTable', 'readonly'), '');
    await page.fill('#cName', '');
    await page.click('#placeBtn');
    assert.match(await page.textContent('#formError'), /enter your name/);
    await page.fill('#cName', `Guest ${vp.name}`);
    await page.fill('#cNotes', 'No onions please');
    await page.screenshot({ path: path.join(OUT, `${vp.name}-4-checkout.png`) });
    await page.click('#placeBtn');
    await page.waitForURL(/\/order\?token=/);
    token = new URL(page.url()).searchParams.get('token');
    await page.waitForSelector('.order-no');
    assert.match(await page.textContent('h1'), /Order received/);
    assert.match(await page.textContent('.kv'), /Table 3/);
    await noHorizontalScroll(page, `${vp.name} confirmation`);
    await page.screenshot({ path: path.join(OUT, `${vp.name}-5-confirmation.png`), fullPage: true });
  });

  await step(`${vp.name}: bill download link returns a PDF`, async () => {
    const href = await page.getAttribute('a:has-text("Download bill")', 'href');
    const res = await page.request.get(base + href);
    assert.equal(res.headers()['content-type'], 'application/pdf');
    assert.equal((await res.body()).subarray(0, 5).toString(), '%PDF-');
    const [download] = await Promise.all([page.waitForEvent('download'), page.click('a:has-text("Download bill")')]);
    assert.match(download.suggestedFilename(), /^bill-\d+\.pdf$/);
  });

  await step(`${vp.name}: cart is cleared and "Order more" returns to menu`, async () => {
    await page.click('text=Order more');
    await page.waitForSelector('.dish');
    assert.ok(await page.locator('#cartCount').isHidden());
    assert.match(await page.textContent('#myOrdersLink'), /Order #\d+/);
  });

  if (vp.name === 'desktop') {
    await step('desktop: takeaway and delivery orders through the UI', async () => {
      await page.locator('.dish', { hasText: 'Cold Coffee' }).locator('button:has-text("Add")').click();
      await page.click('#openCart');
      await page.click('text=Continue to checkout');
      await page.click('label[for=t-takeaway]');
      assert.equal(await page.locator('#cTable').count(), 0);
      await page.fill('#cName', 'Takeaway Tom');
      await page.click('#placeBtn');
      await page.waitForURL(/\/order\?token=/);
      assert.match(await page.textContent('.kv'), /Takeaway/);

      await page.goto(`${base}/`);
      await page.locator('.dish', { hasText: 'Butter Chicken' }).locator('button:has-text("Add")').click();
      await page.click('#openCart');
      await page.click('text=Continue to checkout');
      await page.click('label[for=t-delivery]');
      assert.ok(await page.locator('text=Delivery fee').isVisible());
      await page.fill('#cName', 'Delivery Dia');
      await page.fill('#cPhone', '');
      await page.click('#placeBtn');
      assert.match(await page.textContent('#formError'), /phone number/);
      await page.fill('#cPhone', '9876543210');
      await page.click('#placeBtn');
      assert.match(await page.textContent('#formError'), /delivery address/);
      await page.fill('#cAddr', '221B Baker Street, Bengaluru');
      await page.click('#placeBtn');
      await page.waitForURL(/\/order\?token=/);
      assert.match(await page.textContent('.totals'), /Delivery fee/);
    });
  }

  assert.deepEqual(problems, [], 'no errors on customer pages');
  return { ctx, page, token };
}

async function kitchenJourney(browser, vp, customer) {
  const ctx = await browser.newContext(vp.options);
  const page = await ctx.newPage();
  const problems = watch(page, `${vp.name}/kitchen`);

  await step(`${vp.name}: kitchen login and board`, async () => {
    await login(page, 'kitchen', 'Kitchen@123');
    await page.waitForURL(/\/kitchen/);
    await page.waitForSelector('.ticket');
    await page.waitForFunction(() => document.getElementById('conn').classList.contains('on'));
    assert.ok(await page.locator('#adminLink').isHidden(), 'no admin link for kitchen role');
    await noHorizontalScroll(page, `${vp.name} kitchen`);
  });

  await step(`${vp.name}: new order appears live with notes`, async () => {
    await page.click('#soundBtn');
    assert.match(await page.textContent('#soundBtn'), /Sound on/);
    const before = await page.locator('#l-pending .ticket').count();
    const res = await page.request.post(`${base}/api/orders`, { data: { customer_name: `Live ${vp.name}`, order_type: 'dine_in', table_number: 7, notes: 'Extra spicy', items: [{ dish_id: 5, quantity: 2 }] } });
    assert.equal(res.status(), 201);
    await page.waitForFunction((n) => document.querySelectorAll('#l-pending .ticket').length === n + 1, before, { timeout: 5000 });
    const t = page.locator('.ticket', { hasText: `Live ${vp.name}` });
    assert.match(await t.textContent(), /Extra spicy/);
    assert.match(await t.textContent(), /Table 7/);
    await page.screenshot({ path: path.join(OUT, `${vp.name}-6-kitchen.png`), fullPage: true });
  });

  await step(`${vp.name}: kitchen moves the customer's order through statuses`, async () => {
    const num = await customer.page.evaluate(async (tok) => (await (await fetch(`/api/public/orders/${tok}`)).json()).order_number, customer.token);
    const ticket = () => page.locator('.ticket', { hasText: `#${num}` });
    await ticket().locator('text=Start preparing').click();
    await page.waitForSelector(`#l-preparing .ticket:has-text("#${num}")`);
    await ticket().locator('[title="Move back to New"]').click();
    await page.waitForSelector(`#l-pending .ticket:has-text("#${num}")`);
    await ticket().locator('text=Start preparing').click();
    await ticket().locator('text=Mark ready').click();
    await page.waitForSelector(`#l-ready .ticket:has-text("#${num}")`);
    await customer.page.goto(`${base}/order?token=${customer.token}`);
    await customer.page.waitForSelector('text=Your order is ready', { timeout: 7000 });
    const [popup] = await Promise.all([page.waitForEvent('popup'), ticket().locator('[title="Print receipt"]').click()]);
    await popup.close();
    await ticket().locator('text=Complete').click();
    await page.waitForFunction((n) => !document.body.textContent.includes(`#${n}`), num);
    await customer.page.waitForSelector('text=Order completed', { timeout: 7000 });
    await customer.page.screenshot({ path: path.join(OUT, `${vp.name}-7-customer-completed.png`), fullPage: true });
  });

  await step(`${vp.name}: kitchen cancels an order (with confirmation)`, async () => {
    const t = page.locator('.ticket', { hasText: `Live ${vp.name}` });
    await t.locator('[data-cancel]').click();
    await page.click('.modal button:has-text("Cancel")'); // dismiss
    assert.equal(await t.count(), 1);
    await t.locator('[data-cancel]').click();
    await page.click('.modal [data-ok]');
    await page.waitForFunction((n) => !document.body.textContent.includes(n), `Live ${vp.name}`);
  });

  await step(`${vp.name}: kitchen cannot open admin and can sign out`, async () => {
    await page.goto(`${base}/admin`);
    await page.waitForURL(/\/kitchen/);
    await page.click('#logoutBtn');
    await page.waitForURL(/\/login/);
  });

  assert.deepEqual(problems, [], 'no errors on kitchen pages');
  await ctx.close();
}

async function adminJourney(browser, vp) {
  const ctx = await browser.newContext({ ...vp.options, acceptDownloads: true });
  const page = await ctx.newPage();
  const problems = watch(page, `${vp.name}/admin`);
  const tab = (name) => page.click(`.tab[data-tab="${name}"]`);

  await step(`${vp.name}: admin login redirect and dashboard`, async () => {
    await page.goto(`${base}/admin`);
    await page.waitForURL(/\/login\?next=/);
    await page.fill('#username', 'admin');
    await page.fill('#password', 'wrong');
    await page.click('#submitBtn');
    await page.waitForSelector('#err:not([hidden])');
    problems.length = 0; // the 401 above is expected
    await page.fill('#password', 'Admin@123');
    await page.click('#submitBtn');
    await page.waitForURL(/\/admin/);
    await page.waitForSelector('.stat');
    assert.ok(await page.locator('text=default password is still set').isVisible());
    await noHorizontalScroll(page, `${vp.name} dashboard`);
    await page.screenshot({ path: path.join(OUT, `${vp.name}-8-admin-dashboard.png`), fullPage: true });
  });

  await step(`${vp.name}: orders list, detail, payment and bills`, async () => {
    await tab('orders');
    await page.waitForSelector('#ordersBody tr.clickable');
    await page.fill('input[name=q]', `Guest ${vp.name}`);
    await page.click('#orderFilters button[type=submit]');
    await page.waitForFunction(() => document.querySelectorAll('#ordersBody tr.clickable').length === 1);
    await page.click('#ordersBody tr.clickable');
    await page.waitForSelector('.modal');
    await page.click('.modal [data-pay="paid"]');
    await page.waitForSelector('.modal [data-pay="unpaid"]');
    const [popup] = await Promise.all([page.waitForEvent('popup'), page.click('.modal a:has-text("Print A4 bill")')]);
    await popup.close();
    const [dl] = await Promise.all([page.waitForEvent('download'), page.click('.modal a:has-text("Download PDF")')]);
    assert.match(dl.suggestedFilename(), /\.pdf$/);
    await page.screenshot({ path: path.join(OUT, `${vp.name}-9-admin-order.png`) });
    await page.click('.modal [data-close].icon-btn');
    await page.selectOption('select[name=status]', 'cancelled');
    await page.waitForFunction(() => !!document.querySelector('#ordersBody'));
  });

  await step(`${vp.name}: toggle availability and edit price`, async () => {
    await tab('menu');
    await page.waitForSelector('.switch');
    const row = page.locator('tr', { hasText: 'Cold Coffee' });
    await row.locator('.switch').click();
    await page.waitForSelector('text=Cold Coffee is now sold out');
    const menu = await page.request.get(`${base}/api/menu`);
    const coffee = (await menu.json()).categories.flatMap((c) => c.dishes).find((d) => d.name === 'Cold Coffee');
    assert.equal(coffee.is_available, false);
    await row.locator('.switch').click();
    await page.waitForSelector('text=Cold Coffee is now available');

    await page.locator('tr', { hasText: 'Masala Chai' }).locator('[data-edit]').click();
    await page.fill('#dPrice', '65');
    await page.click('.modal button[type=submit]');
    await page.waitForSelector('text=Dish saved');
    assert.match(await page.locator('tr', { hasText: 'Masala Chai' }).textContent(), /65\.00/);
  });

  await step(`${vp.name}: add dish with uploaded photo, then delete it`, async () => {
    await page.click('#addDish');
    const png = Buffer.from('89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd49a730000001649444154789c63f8cf800002ff0bfcc000000c8c022a1b2f6a6a0000000049454e44ae426082', 'hex');
    await page.setInputFiles('#imgFile', { name: 'kulfi.png', mimeType: 'image/png', buffer: png });
    await page.waitForFunction(() => document.getElementById('imgUrl').value.startsWith('/uploads/'));
    await page.fill('#dName', `Kulfi ${vp.name}`);
    await page.selectOption('#dCatSel', { label: 'Desserts' });
    await page.fill('#dPrice', '99');
    await page.fill('#dDesc', 'Frozen saffron dessert');
    await page.click('.modal button[type=submit]');
    await page.waitForSelector('text=Dish added');
    const r = await page.request.get(`${base}/api/menu`);
    const d = (await r.json()).categories.flatMap((c) => c.dishes).find((x) => x.name === `Kulfi ${vp.name}`);
    assert.ok(d && d.image_url.startsWith('/uploads/'));
    await page.locator('tr', { hasText: `Kulfi ${vp.name}` }).locator('[data-del]').click();
    await page.click('.modal [data-ok]');
    await page.waitForSelector('text=Dish deleted');
    assert.equal(await page.locator('tr', { hasText: `Kulfi ${vp.name}` }).count(), 0);
    // Validation is shown inside the modal
    await page.click('#addDish');
    await page.fill('#dName', '');
    await page.click('.modal button[type=submit]');
    await page.waitForSelector('.modal .alert-error:not([hidden])');
    await page.click('.modal [data-close].icon-btn');
  });

  await step(`${vp.name}: categories add/edit/delete`, async () => {
    await tab('categories');
    await page.click('#addCat');
    await page.fill('#cName', `Specials ${vp.name}`);
    await page.click('.modal button[type=submit]');
    await page.waitForSelector(`td:has-text("Specials ${vp.name}")`);
    await page.locator('tr', { hasText: `Specials ${vp.name}` }).locator('[data-edit]').click();
    await page.fill('#cName', `Chef Specials ${vp.name}`);
    await page.click('.modal button[type=submit]');
    await page.waitForSelector(`td:has-text("Chef Specials ${vp.name}")`);
    await page.locator('tr', { hasText: `Chef Specials ${vp.name}` }).locator('[data-del]').click();
    await page.click('.modal [data-ok]');
    await page.waitForSelector('text=Category deleted');
    await page.locator('tr', { hasText: 'Starters' }).locator('[data-del]').click();
    await page.click('.modal [data-ok]');
    await page.waitForSelector('text=Move or delete');
    problems.length = 0; // expected 409
  });

  await step(`${vp.name}: tables, QR codes and print sheet`, async () => {
    await tab('tables');
    await page.waitForSelector('.qr-card img');
    await allImagesLoaded(page);
    await page.click('#addTable');
    const n = await page.inputValue('#tNo');
    await page.click('.modal button[type=submit]');
    await page.waitForSelector(`.qr-card:has-text("Table ${n}")`);
    const card = page.locator('.qr-card', { hasText: `Table ${n}` });
    const [dl] = await Promise.all([page.waitForEvent('download'), card.locator('text=PNG').click()]);
    assert.equal(dl.suggestedFilename(), `table-${n}-qr.png`);
    await card.locator('[data-edit]').click();
    await page.fill('#tSeats', '8');
    await page.click('.modal button[type=submit]');
    await page.waitForSelector(`.qr-card:has-text("8 seats")`);
    await page.locator('.qr-card', { hasText: `Table ${n}` }).locator('[data-del]').click();
    await page.click('.modal [data-ok]');
    await page.waitForSelector('text=Table deleted');
    await noHorizontalScroll(page, `${vp.name} tables`);
    await page.screenshot({ path: path.join(OUT, `${vp.name}-10-admin-tables.png`) });
    const [sheet] = await Promise.all([page.waitForEvent('popup'), page.click('text=Print all QR codes')]);
    await sheet.waitForSelector('.qr-tent img');
    await allImagesLoaded(sheet);
    await sheet.screenshot({ path: path.join(OUT, `${vp.name}-11-qr-sheet.png`) });
    await sheet.close();
  });

  await step(`${vp.name}: settings save and reflect on the menu`, async () => {
    await tab('settings');
    await page.fill('#sName', `Spice Garden ${vp.name}`);
    await page.fill('#sUrl', 'not a url');
    await page.click('#settingsForm button[type=submit]');
    await page.waitForSelector('#settingsForm .alert-error:not([hidden])');
    problems.length = 0; // expected 400
    await page.fill('#sUrl', '');
    await page.click('#settingsForm button[type=submit]');
    await page.waitForSelector('text=Settings saved');
    assert.equal(await page.textContent('#restName'), `Spice Garden ${vp.name}`);
  });

  await step(`${vp.name}: staff add, reset password, delete, change own password`, async () => {
    await tab('staff');
    await page.click('#addUser');
    await page.fill('#uName', `cook${vp.name}`);
    await page.fill('#uPw', 'Cook12345');
    await page.click('.modal button[type=submit]');
    await page.waitForSelector(`td:has-text("cook${vp.name}")`);
    await page.locator('tr', { hasText: `cook${vp.name}` }).locator('[data-reset]').click();
    await page.fill('#rPw', 'Cook54321');
    await page.click('.modal button[type=submit]');
    await page.waitForSelector('text=Password reset');
    await page.locator('tr', { hasText: `cook${vp.name}` }).locator('[data-del]').click();
    await page.click('.modal [data-ok]');
    await page.waitForSelector('text=Account deleted');
    await page.fill('#pwCur', 'Admin@123');
    await page.fill('#pwNew', 'Better123');
    await page.fill('#pwNew2', 'Different1');
    await page.click('#pwForm button[type=submit]');
    await page.waitForSelector('#pwForm .alert-error:not([hidden])');
    await page.fill('#pwNew2', 'Better123');
    await page.click('#pwForm button[type=submit]');
    await page.waitForSelector('text=Password updated');
    // restore for the next viewport
    await page.request.post(`${base}/api/auth/change-password`, { data: { current_password: 'Better123', new_password: 'Admin@123' }, headers: { origin: base } });
  });

  await step(`${vp.name}: sign out`, async () => {
    await page.click('#logoutBtn');
    await page.waitForURL(/\/login/);
  });

  assert.deepEqual(problems, [], 'no errors on admin pages');
  await ctx.close();
}

(async () => {
  const app = createApp({ dbFile: path.join(TMP, 'ui.db'), loginLimit: 1000, orderLimit: 1000 });
  const server = http.createServer(app);
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  let failed = false;
  try {
    for (const vp of VIEWPORTS) {
      console.log(`\n${vp.name.toUpperCase()}`);
      const customer = await customerJourney(browser, vp);
      await kitchenJourney(browser, vp, customer);
      await customer.ctx.close();
      await adminJourney(browser, vp);
    }
    console.log(`\n✔ ${passed} UI checks passed. Screenshots: ${OUT}`);
  } catch (e) {
    failed = true;
    console.log('FAILED');
    console.error(e);
  } finally {
    await browser.close();
    server.closeAllConnections();
    server.close();
    app.locals.db.close();
    fs.rmSync(TMP, { recursive: true, force: true });
  }
  process.exit(failed ? 1 : 0);
})();
