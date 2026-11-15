# Restaurant Digital Ordering System — Project Plan

## 1. Goals

A self-hosted ordering system for one restaurant:

| # | Requirement | Where it lives |
|---|-------------|----------------|
| 1 | Digital menu with a photo for every dish | `public/index.html`, images in `public/images/dishes` + admin uploads in `data/uploads` |
| 2 | Categories (Starters, Main Course, Beverages, Desserts, + custom) | `categories` table, admin "Categories" tab |
| 3 | Cart | Client-side cart (persisted in `localStorage`), prices re-computed on the server |
| 4 | Customer name + table number | Checkout form; table pre-filled from the QR code link |
| 5 | Dine-in / Takeaway / Delivery | `orders.order_type`, delivery requires phone + address |
| 6 | Order confirmation | `public/order.html?token=…` with live status |
| 7 | Admin dashboard (dishes, prices, availability) | `public/admin.html` |
| 8 | Kitchen dashboard (incoming orders) | `public/kitchen.html`, live via Server-Sent Events |
| 9 | Printable PDF bill | `GET /api/orders/:id/bill.pdf` (staff) and `GET /api/public/orders/:token/bill.pdf` (customer) |
| 10 | QR code per table | `GET /api/tables/:id/qr.png`, printable sheet `public/qr-print.html` |
| 11 | Responsive (Android phones, tablets, desktops) | Mobile-first CSS, tested at 360px / 800px / 1366px |

## 2. Architecture

```
Browser (vanilla JS, no build step)
   │  JSON over HTTPS, httpOnly session cookie, SSE for live updates
Express 5 (Node.js ≥ 22)
   ├─ routes/public.js   menu, place order, order status, customer bill
   ├─ routes/auth.js     login / logout / me / change password
   ├─ routes/admin.js    dishes, categories, tables, settings, users, uploads
   ├─ routes/orders.js   staff order list, status changes, bill PDF, SSE stream
   ├─ services/pdf.js    PDFKit bill generator
   ├─ services/events.js in-process event bus → SSE
   └─ db.js              better-sqlite3 (WAL mode, foreign keys ON), migrations + seed
SQLite database file: data/restaurant.db
```

**Why SQLite (better-sqlite3)?** A single restaurant needs a database that is
ACID-compliant, zero-maintenance and easy to back up (copy one file). WAL mode
allows concurrent readers while orders are written. Every write that touches more
than one row (placing an order) runs inside a transaction.

## 3. Security

* Passwords hashed with **bcrypt** (cost 12).
* Sessions are **JWT in an httpOnly, SameSite=Strict cookie** (8 h expiry); the
  secret comes from `JWT_SECRET` or is generated once and stored in `data/.jwt-secret`.
* Role-based access: `admin` (everything) and `kitchen` (orders only).
* Login rate-limited (10 attempts / 15 min / IP); order placement rate-limited.
* `helmet` security headers + strict Content-Security-Policy (no inline scripts).
* All SQL uses prepared statements. All user text rendered with `textContent`/escaping.
* **Prices are never trusted from the browser** — the server looks up each dish,
  checks availability, and computes subtotal, tax, delivery fee and total.
* Customers reach their own order only through a random 32-hex-char token.
* Image uploads: JPEG/PNG/WebP only, max 3 MB, file signature checked, random filename.

## 4. Database structure

```sql
users            (id PK, username UNIQUE, password_hash, role CHECK IN ('admin','kitchen'),
                  created_at)

categories       (id PK, name UNIQUE, sort_order, created_at)

dishes           (id PK, category_id FK→categories ON DELETE RESTRICT, name, description,
                  price_cents INTEGER ≥ 0, image_url, is_veg 0/1, is_available 0/1,
                  sort_order, created_at, updated_at)

restaurant_tables(id PK, table_number INTEGER UNIQUE, seats, is_active 0/1, created_at)

orders           (id PK, order_number UNIQUE, public_token UNIQUE, customer_name,
                  customer_phone, order_type CHECK IN ('dine_in','takeaway','delivery'),
                  table_number, delivery_address, notes,
                  status CHECK IN ('pending','preparing','ready','completed','cancelled'),
                  payment_status CHECK IN ('unpaid','paid'),
                  subtotal_cents, tax_cents, delivery_fee_cents, total_cents,
                  created_at, updated_at)

order_items      (id PK, order_id FK→orders ON DELETE CASCADE,
                  dish_id FK→dishes ON DELETE SET NULL,
                  dish_name, unit_price_cents, quantity CHECK 1..50, line_total_cents)

settings         (key PK, value)   -- restaurant_name, address, phone, currency_symbol,
                                   -- tax_rate_percent, delivery_fee, public_base_url, gst_number
```

Money is stored as **integer cents/paise** to avoid floating-point rounding errors.
`order_items` keeps a snapshot of name and price so old bills never change when the
menu is edited.

Indexes: `orders(status)`, `orders(created_at)`, `order_items(order_id)`,
`dishes(category_id)`.

## 5. Order lifecycle

```
pending ──► preparing ──► ready ──► completed
   │            │            │
   └────────────┴────────────┴──► cancelled
```

Kitchen and admin can move an order forward; the customer's confirmation page polls
the status every 5 s. New orders appear instantly on the kitchen board (SSE) with an
audible chime.

## 6. Testing plan

* `npm test` — API integration tests (node:test): auth, roles, menu, ordering
  validation, price tampering, status flow, PDF, QR, uploads, settings.
* `npm run test:ui` — Playwright end-to-end run at phone, tablet and desktop sizes:
  browse menu → add to cart → checkout (all three order types) → confirmation →
  kitchen board → admin edits → bill download; checks that every button works and
  there is no horizontal scroll.
