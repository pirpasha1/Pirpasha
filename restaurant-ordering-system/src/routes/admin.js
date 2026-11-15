'use strict';
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const express = require('express');
const multer = require('multer');
const bcrypt = require('bcryptjs');
const QRCode = require('qrcode');
const config = require('../config');
const { getSettings, DEFAULT_SETTINGS } = require('../db');
const { requireRole } = require('../auth');
const { HttpError, str, int, moneyToCents, bool } = require('../util');
const { validatePassword } = require('./auth');
const { iso } = require('../services/orders');

const IMAGE_SIGNATURES = [
  { ext: '.jpg', test: (b) => b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff },
  { ext: '.png', test: (b) => b.slice(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) },
  { ext: '.webp', test: (b) => b.slice(0, 4).toString('ascii') === 'RIFF' && b.slice(8, 12).toString('ascii') === 'WEBP' },
];

function validImageUrl(v) {
  const url = str(v, { field: 'Image', max: 500 });
  if (!url) return '';
  if (url.startsWith('/images/') || url.startsWith('/uploads/')) {
    if (url.includes('..')) throw new HttpError(400, 'Invalid image path');
    return url;
  }
  try {
    const u = new URL(url);
    if (u.protocol === 'https:' || u.protocol === 'http:') return url;
  } catch (_) { /* fall through */ }
  throw new HttpError(400, 'Image must be an uploaded photo or an http(s) URL');
}

module.exports = function adminRoutes(db) {
  const r = express.Router();
  r.use(requireRole('admin'));
  fs.mkdirSync(config.uploadsDir, { recursive: true });

  // ---------- Dashboard stats ----------
  async function defaultPasswordUsers() {
    const out = [];
    for (const [username, pw] of [[config.adminUsername, config.adminPassword], [config.kitchenUsername, config.kitchenPassword]]) {
      const u = db.prepare('SELECT password_hash FROM users WHERE username = ?').get(username);
      if (u && pw && (await bcrypt.compare(pw, u.password_hash))) out.push(username);
    }
    return out;
  }

  r.get('/stats', async (req, res) => {
    const from = req.query.from ? new Date(String(req.query.from)) : new Date(Date.now() - 864e5);
    if (Number.isNaN(from.getTime())) throw new HttpError(400, 'Invalid date');
    const since = from.toISOString().replace('T', ' ').slice(0, 19);
    const row = db.prepare(`SELECT
        COUNT(*) AS orders,
        COALESCE(SUM(CASE WHEN status != 'cancelled' THEN total_cents END), 0) AS revenue_cents,
        COALESCE(SUM(CASE WHEN payment_status = 'paid' AND status != 'cancelled' THEN total_cents END), 0) AS paid_cents,
        SUM(CASE WHEN status IN ('pending','preparing','ready') THEN 1 ELSE 0 END) AS active
      FROM orders WHERE created_at >= ?`).get(since);
    const top = db.prepare(`SELECT oi.dish_name AS name, SUM(oi.quantity) AS qty
      FROM order_items oi JOIN orders o ON o.id = oi.order_id
      WHERE o.created_at >= ? AND o.status != 'cancelled'
      GROUP BY oi.dish_name ORDER BY qty DESC LIMIT 5`).all(since);
    const dishes = db.prepare('SELECT COUNT(*) AS total, SUM(is_available) AS available FROM dishes').get();
    res.json({
      ...row,
      active: row.active || 0,
      top_dishes: top,
      dishes_total: dishes.total,
      dishes_available: dishes.available || 0,
      default_passwords: await defaultPasswordUsers(),
    });
  });

  // ---------- Categories ----------
  const catList = db.prepare(`SELECT c.*, (SELECT COUNT(*) FROM dishes d WHERE d.category_id = c.id) AS dish_count
    FROM categories c ORDER BY sort_order, name`);
  r.get('/categories', (_req, res) => res.json(catList.all()));

  function catInput(body) {
    return {
      name: str(body.name, { field: 'Category name', required: true, max: 40 }),
      sort_order: int(body.sort_order ?? 0, { field: 'Sort order', min: 0, max: 9999 }),
    };
  }
  const uniq = (fn, msg) => {
    try { return fn(); } catch (e) {
      if (String(e.code).startsWith('SQLITE_CONSTRAINT_UNIQUE')) throw new HttpError(409, msg);
      throw e;
    }
  };

  r.post('/categories', (req, res) => {
    const c = catInput(req.body || {});
    const info = uniq(() => db.prepare('INSERT INTO categories (name, sort_order) VALUES (?, ?)').run(c.name, c.sort_order), 'A category with this name already exists');
    res.status(201).json(db.prepare('SELECT * FROM categories WHERE id = ?').get(info.lastInsertRowid));
  });

  r.put('/categories/:id', (req, res) => {
    const id = int(req.params.id, { field: 'Category id', min: 1 });
    const c = catInput(req.body || {});
    const info = uniq(() => db.prepare('UPDATE categories SET name = ?, sort_order = ? WHERE id = ?').run(c.name, c.sort_order, id), 'A category with this name already exists');
    if (!info.changes) throw new HttpError(404, 'Category not found');
    res.json(db.prepare('SELECT * FROM categories WHERE id = ?').get(id));
  });

  r.delete('/categories/:id', (req, res) => {
    const id = int(req.params.id, { field: 'Category id', min: 1 });
    const n = db.prepare('SELECT COUNT(*) AS c FROM dishes WHERE category_id = ?').get(id).c;
    if (n > 0) throw new HttpError(409, `Move or delete the ${n} dish(es) in this category first`);
    const info = db.prepare('DELETE FROM categories WHERE id = ?').run(id);
    if (!info.changes) throw new HttpError(404, 'Category not found');
    res.json({ ok: true });
  });

  // ---------- Dishes ----------
  const dishById = db.prepare('SELECT * FROM dishes WHERE id = ?');
  const fmtDish = (d) => d && { ...d, is_veg: !!d.is_veg, is_available: !!d.is_available, created_at: iso(d.created_at), updated_at: iso(d.updated_at) };

  r.get('/dishes', (_req, res) => {
    res.json(db.prepare(`SELECT d.*, c.name AS category_name FROM dishes d JOIN categories c ON c.id = d.category_id
      ORDER BY c.sort_order, d.sort_order, d.name`).all().map(fmtDish));
  });

  function dishInput(body) {
    const category_id = int(body.category_id, { field: 'Category', min: 1 });
    if (!db.prepare('SELECT 1 FROM categories WHERE id = ?').get(category_id)) throw new HttpError(400, 'Category does not exist');
    return {
      category_id,
      name: str(body.name, { field: 'Dish name', required: true, max: 80 }),
      description: str(body.description, { field: 'Description', max: 400 }),
      price_cents: moneyToCents(body.price),
      image_url: validImageUrl(body.image_url),
      is_veg: bool(body.is_veg) ? 1 : 0,
      is_available: body.is_available === undefined ? 1 : bool(body.is_available) ? 1 : 0,
      sort_order: int(body.sort_order ?? 0, { field: 'Sort order', min: 0, max: 9999 }),
    };
  }

  function removeUploadIfUnused(url) {
    if (!url || !url.startsWith('/uploads/')) return;
    const still = db.prepare('SELECT 1 FROM dishes WHERE image_url = ?').get(url);
    if (still) return;
    const file = path.join(config.uploadsDir, path.basename(url));
    fs.promises.unlink(file).catch(() => {});
  }

  r.post('/dishes', (req, res) => {
    const d = dishInput(req.body || {});
    const info = db.prepare(`INSERT INTO dishes (category_id, name, description, price_cents, image_url, is_veg, is_available, sort_order)
      VALUES (@category_id, @name, @description, @price_cents, @image_url, @is_veg, @is_available, @sort_order)`).run(d);
    res.status(201).json(fmtDish(dishById.get(info.lastInsertRowid)));
  });

  r.put('/dishes/:id', (req, res) => {
    const id = int(req.params.id, { field: 'Dish id', min: 1 });
    const before = dishById.get(id);
    if (!before) throw new HttpError(404, 'Dish not found');
    const d = dishInput(req.body || {});
    db.prepare(`UPDATE dishes SET category_id=@category_id, name=@name, description=@description, price_cents=@price_cents,
      image_url=@image_url, is_veg=@is_veg, is_available=@is_available, sort_order=@sort_order, updated_at=datetime('now')
      WHERE id=@id`).run({ ...d, id });
    if (before.image_url !== d.image_url) removeUploadIfUnused(before.image_url);
    res.json(fmtDish(dishById.get(id)));
  });

  r.patch('/dishes/:id/availability', (req, res) => {
    const id = int(req.params.id, { field: 'Dish id', min: 1 });
    const v = bool(req.body && req.body.is_available) ? 1 : 0;
    const info = db.prepare("UPDATE dishes SET is_available = ?, updated_at = datetime('now') WHERE id = ?").run(v, id);
    if (!info.changes) throw new HttpError(404, 'Dish not found');
    res.json(fmtDish(dishById.get(id)));
  });

  r.delete('/dishes/:id', (req, res) => {
    const id = int(req.params.id, { field: 'Dish id', min: 1 });
    const before = dishById.get(id);
    if (!before) throw new HttpError(404, 'Dish not found');
    db.prepare('DELETE FROM dishes WHERE id = ?').run(id); // order_items keep a name/price snapshot
    removeUploadIfUnused(before.image_url);
    res.json({ ok: true });
  });

  // ---------- Image upload ----------
  const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 3 * 1024 * 1024, files: 1 },
  });
  r.post('/uploads', (req, res, next) => {
    upload.single('image')(req, res, (err) => {
      if (err) return next(new HttpError(400, err.code === 'LIMIT_FILE_SIZE' ? 'Image must be 3 MB or smaller' : 'Upload failed'));
      if (!req.file) return next(new HttpError(400, 'Choose an image to upload'));
      const sig = IMAGE_SIGNATURES.find((s) => s.test(req.file.buffer));
      if (!sig) return next(new HttpError(400, 'Only JPEG, PNG or WebP images are allowed'));
      const name = `${crypto.randomBytes(12).toString('hex')}${sig.ext}`;
      fs.writeFile(path.join(config.uploadsDir, name), req.file.buffer, (e) => {
        if (e) return next(e);
        res.status(201).json({ url: `/uploads/${name}` });
      });
    });
  });

  // ---------- Tables & QR codes ----------
  const tableById = db.prepare('SELECT * FROM restaurant_tables WHERE id = ?');
  r.get('/tables', (_req, res) => res.json(db.prepare('SELECT * FROM restaurant_tables ORDER BY table_number').all()));

  function tableInput(body) {
    return {
      table_number: int(body.table_number, { field: 'Table number', min: 1, max: 9999 }),
      seats: int(body.seats ?? 4, { field: 'Seats', min: 1, max: 50 }),
      is_active: body.is_active === undefined ? 1 : bool(body.is_active) ? 1 : 0,
    };
  }

  r.post('/tables', (req, res) => {
    const t = tableInput(req.body || {});
    const info = uniq(() => db.prepare('INSERT INTO restaurant_tables (table_number, seats, is_active) VALUES (@table_number, @seats, @is_active)').run(t), `Table ${t.table_number} already exists`);
    res.status(201).json(tableById.get(info.lastInsertRowid));
  });

  r.put('/tables/:id', (req, res) => {
    const id = int(req.params.id, { field: 'Table id', min: 1 });
    const t = tableInput(req.body || {});
    const info = uniq(() => db.prepare('UPDATE restaurant_tables SET table_number=@table_number, seats=@seats, is_active=@is_active WHERE id=@id').run({ ...t, id }), `Table ${t.table_number} already exists`);
    if (!info.changes) throw new HttpError(404, 'Table not found');
    res.json(tableById.get(id));
  });

  r.delete('/tables/:id', (req, res) => {
    const id = int(req.params.id, { field: 'Table id', min: 1 });
    const info = db.prepare('DELETE FROM restaurant_tables WHERE id = ?').run(id);
    if (!info.changes) throw new HttpError(404, 'Table not found');
    res.json({ ok: true });
  });

  function tableUrl(req, tableNumber) {
    const base = (getSettings(db).public_base_url || `${req.protocol}://${req.get('host')}`).replace(/\/+$/, '');
    return `${base}/?table=${tableNumber}`;
  }

  r.get('/tables/:id/qr', (req, res) => {
    const t = tableById.get(int(req.params.id, { field: 'Table id', min: 1 }));
    if (!t) throw new HttpError(404, 'Table not found');
    res.json({ table_number: t.table_number, url: tableUrl(req, t.table_number) });
  });

  r.get('/tables/:id/qr.png', async (req, res) => {
    const t = tableById.get(int(req.params.id, { field: 'Table id', min: 1 }));
    if (!t) throw new HttpError(404, 'Table not found');
    const png = await QRCode.toBuffer(tableUrl(req, t.table_number), { type: 'png', width: 600, margin: 2, errorCorrectionLevel: 'M' });
    res.set('Content-Type', 'image/png');
    res.set('Cache-Control', 'no-store');
    if (req.query.download) res.set('Content-Disposition', `attachment; filename="table-${t.table_number}-qr.png"`);
    res.send(png);
  });

  // ---------- Settings ----------
  r.get('/settings', (_req, res) => res.json(getSettings(db)));

  r.put('/settings', (req, res) => {
    const b = req.body || {};
    const next = {
      restaurant_name: str(b.restaurant_name, { field: 'Restaurant name', required: true, max: 80 }),
      restaurant_address: str(b.restaurant_address, { field: 'Address', max: 200 }),
      restaurant_phone: str(b.restaurant_phone, { field: 'Phone', max: 30 }),
      gst_number: str(b.gst_number, { field: 'GST number', max: 30 }),
      currency_symbol: str(b.currency_symbol, { field: 'Currency symbol', required: true, max: 4 }),
      tax_rate_percent: String(Number(b.tax_rate_percent)),
      delivery_fee: String(moneyToCents(b.delivery_fee, 'Delivery fee') / 100),
      public_base_url: str(b.public_base_url, { field: 'Public URL', max: 200 }),
      timezone: str(b.timezone, { field: 'Time zone', max: 60 }) || DEFAULT_SETTINGS.timezone,
    };
    const tax = Number(b.tax_rate_percent);
    if (!Number.isFinite(tax) || tax < 0 || tax > 50) throw new HttpError(400, 'Tax rate must be between 0 and 50');
    if (next.public_base_url) {
      try {
        const u = new URL(next.public_base_url);
        if (!['http:', 'https:'].includes(u.protocol)) throw new Error();
      } catch (_) { throw new HttpError(400, 'Public URL must start with http:// or https://'); }
    }
    try { new Intl.DateTimeFormat('en', { timeZone: next.timezone }); } catch (_) { throw new HttpError(400, 'Unknown time zone'); }
    const up = db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value');
    db.transaction(() => { for (const [k, v] of Object.entries(next)) up.run(k, v); })();
    res.json(getSettings(db));
  });

  // ---------- Staff users ----------
  r.get('/users', (_req, res) => res.json(db.prepare('SELECT id, username, role, created_at FROM users ORDER BY role, username').all().map((u) => ({ ...u, created_at: iso(u.created_at) }))));

  r.post('/users', async (req, res) => {
    const b = req.body || {};
    const username = str(b.username, { field: 'Username', required: true, min: 3, max: 30 });
    if (!/^[A-Za-z0-9_.-]+$/.test(username)) throw new HttpError(400, 'Username may contain letters, numbers, dot, dash and underscore');
    const role = String(b.role || '');
    if (!['admin', 'kitchen'].includes(role)) throw new HttpError(400, 'Role must be admin or kitchen');
    const hash = await bcrypt.hash(validatePassword(b.password), 12);
    const info = uniq(() => db.prepare('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)').run(username, hash, role), 'That username is taken');
    res.status(201).json(db.prepare('SELECT id, username, role FROM users WHERE id = ?').get(info.lastInsertRowid));
  });

  r.put('/users/:id/password', async (req, res) => {
    const id = int(req.params.id, { field: 'User id', min: 1 });
    const hash = await bcrypt.hash(validatePassword(req.body && req.body.password), 12);
    const info = db.prepare('UPDATE users SET password_hash = ? WHERE id = ?').run(hash, id);
    if (!info.changes) throw new HttpError(404, 'User not found');
    res.json({ ok: true });
  });

  r.delete('/users/:id', (req, res) => {
    const id = int(req.params.id, { field: 'User id', min: 1 });
    if (id === req.user.id) throw new HttpError(400, 'You cannot delete your own account');
    const u = db.prepare('SELECT role FROM users WHERE id = ?').get(id);
    if (!u) throw new HttpError(404, 'User not found');
    if (u.role === 'admin' && db.prepare("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'").get().c <= 1) {
      throw new HttpError(400, 'At least one admin is required');
    }
    db.prepare('DELETE FROM users WHERE id = ?').run(id);
    res.json({ ok: true });
  });

  return r;
};
