# Restaurant Digital Ordering System

A complete, self-hosted ordering system for a restaurant:

* **Customers** scan the QR code on their table, browse a photo menu, add dishes to a
  cart and order as **Dine-in, Takeaway or Delivery**. They get an order confirmation
  page that updates live and a **printable PDF bill**.
* **Kitchen** staff see new orders appear instantly (with a sound alert) and move
  them through *New → Preparing → Ready → Completed*.
* **Admins** manage dishes, photos, prices, availability, categories, tables and QR
  codes, settings, staff accounts, orders and payments.

Works on Android phones, tablets and computers. No build step and no external services.

| Page | URL | Who |
|------|-----|-----|
| Menu & ordering | `/` (QR codes open `/?table=N`) | Customers |
| Order confirmation | `/order?token=…` | Customers |
| Kitchen dashboard | `/kitchen` | Kitchen + admin |
| Admin dashboard | `/admin` | Admin |
| Staff sign-in | `/login` | Staff |

See [`docs/PLAN.md`](docs/PLAN.md) for the project plan, architecture, security design
and the full **database structure**.

---

## 1. Installation

### Requirements
* **Node.js 22 or newer** (LTS recommended) — <https://nodejs.org>
* On Linux, the database driver may compile once on install; if that fails,
  install build tools: `sudo apt install build-essential python3`.
  (Windows and macOS normally download a ready-made binary.)

### Steps

```bash
cd restaurant-ordering-system
npm install          # install dependencies
npm start            # start the server on port 3000
```

Open <http://localhost:3000>. The terminal also prints your network address
(e.g. `http://192.168.1.20:3000`) — phones and tablets on the same Wi-Fi use that one.

The first start creates `data/restaurant.db` with a demo menu of 16 dishes in four
categories (Starters, Main Course, Beverages, Desserts) and 10 tables.

### Default staff accounts — change these immediately

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `Admin@123` |
| Kitchen | `kitchen` | `Kitchen@123` |

Sign in at `/login`, then go to **Admin → Staff** to change passwords. The admin
dashboard shows a warning until you do. You can also set your own initial
credentials before the first start (see configuration below).

---

## 2. First-time setup checklist

1. **Admin → Settings**: restaurant name, address, phone, GSTIN, currency, tax rate,
   delivery fee and time zone (these appear on bills).
2. **Admin → Settings → Public URL**: the address customers' phones will use, e.g.
   `http://192.168.1.20:3000` on your Wi-Fi or `https://order.myrestaurant.com`.
   QR codes point to this address. (If it's empty, the address you are browsing from
   is used — `localhost` will **not** work from a phone.)
3. **Admin → Dishes**: edit the demo dishes or add your own. Click **Edit → Photo** to
   upload a real photograph of each dish (JPEG/PNG/WebP, max 3 MB, 4:3 looks best).
   The demo menu ships with illustrated images so it works offline — replace them
   with your own photos.
4. **Admin → Tables & QR**: add/remove tables, then **Print all QR codes** and place
   one on each table.
5. Open **/kitchen** on the kitchen tablet/screen and tap **Enable sound**.

---

## 3. Daily use

* **Customer:** scan table QR → pick dishes → cart → checkout (name, order type,
  phone/address for delivery, notes) → confirmation with live status and bill PDF.
* **Kitchen:** tickets show order number, table/type, items, notes and how long ago
  they were placed (red after 20 min). Buttons: *Start preparing*, *Mark ready*,
  *Complete*, move back (↩), print receipt (🖨), cancel (✕).
* **Admin → Orders:** filter by date/status/search; open an order to change status,
  **mark as paid**, print an **A4 bill** or an **80 mm thermal receipt**, or download the PDF.
* **Sold out?** Flip the *Available* switch in **Admin → Dishes** — the menu updates
  immediately and the dish can't be ordered.

---

## 4. Configuration

All settings are optional environment variables. Copy `.env.example` to `.env`
(it is loaded automatically by `npm start`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `3000` | HTTP port |
| `HOST` | `0.0.0.0` | Listen address |
| `DATA_DIR` | `./data` | Database, uploaded photos, session secret |
| `JWT_SECRET` | auto-generated | Session signing key (≥ 32 chars) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `Admin@123` | First admin (only on first start) |
| `KITCHEN_USERNAME` / `KITCHEN_PASSWORD` | `kitchen` / `Kitchen@123` | First kitchen user |
| `COOKIE_SECURE` | `false` | Set `true` when served over HTTPS |
| `TRUST_PROXY` | `false` | Set `true` behind nginx / a load balancer |

---

## 5. Running in production

```bash
npm install --omit=dev
npm install -g pm2
pm2 start npm --name restaurant -- start
pm2 save && pm2 startup     # restart automatically after reboot
```

For internet access put it behind a reverse proxy with HTTPS (e.g. nginx or Caddy)
and set `COOKIE_SECURE=true` and `TRUST_PROXY=true`. For Server-Sent Events through
nginx, disable buffering for `/api/orders/stream` (`proxy_buffering off;`).

**Backups:** stop the server (or use `sqlite3 data/restaurant.db ".backup backup.db"`)
and copy the `data/` folder — it contains the database and uploaded photos.

---

## 6. Testing

```bash
npm test          # 23 API integration tests (auth, roles, ordering, pricing, PDFs, QR, uploads…)
npm run test:ui   # 64 browser checks at phone, tablet and desktop sizes (needs Playwright + Chromium)
```

For the UI test, install the browser once with `npx playwright install chromium`.
Screenshots are saved to `test-output/`.

---

## 7. Project structure

```
server.js                 entry point
src/
  app.js                  Express app, security headers, routing, error handling
  config.js               environment configuration
  db.js                   schema, migrations and demo seed data
  auth.js                 JWT cookie sessions, roles, CSRF origin check
  util.js                 validation and money helpers
  routes/public.js        menu, place order, order status, customer bill
  routes/auth.js          login, logout, change password
  routes/orders.js        staff order list, status, payment, bills, live stream
  routes/admin.js         dishes, uploads, categories, tables + QR, settings, staff
  services/orders.js      order validation and server-side price calculation
  services/pdf.js         PDF bill (A4 + 80 mm receipt)
  services/events.js      live updates (Server-Sent Events)
public/                   frontend (HTML, CSS, vanilla JS) and dish images
scripts/generate-dish-images.js   regenerates the demo dish illustrations
assets/fonts/             DejaVu Sans (₹ glyph for PDFs)
test/                     API and browser tests
docs/PLAN.md              project plan and database structure
```

## Troubleshooting

* **Phone can't open the QR link** — set *Settings → Public URL* to the computer's
  network address, make sure the phone is on the same Wi-Fi, and allow port 3000
  through the computer's firewall.
* **`npm install` fails on better-sqlite3** — check `node -v` is 22+; on Linux install
  `build-essential` and `python3`.
* **Kitchen doesn't beep** — browsers require a tap first: press **Enable sound**.
* **Forgot the admin password** — stop the server and run
  `node -e "const D=require('better-sqlite3'),b=require('bcryptjs');new D('data/restaurant.db').prepare('UPDATE users SET password_hash=? WHERE username=?').run(b.hashSync('NewPass123',12),'admin')"`.
