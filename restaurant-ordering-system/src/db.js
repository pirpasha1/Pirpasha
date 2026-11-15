'use strict';
const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');
const bcrypt = require('bcryptjs');
const config = require('./config');

const SCHEMA = `
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('admin','kitchen')),
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dishes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  category_id   INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
  name          TEXT NOT NULL,
  description   TEXT NOT NULL DEFAULT '',
  price_cents   INTEGER NOT NULL CHECK (price_cents >= 0),
  image_url     TEXT NOT NULL DEFAULT '',
  is_veg        INTEGER NOT NULL DEFAULT 1 CHECK (is_veg IN (0,1)),
  is_available  INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0,1)),
  sort_order    INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dishes_category ON dishes(category_id);

CREATE TABLE IF NOT EXISTS restaurant_tables (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  table_number INTEGER NOT NULL UNIQUE CHECK (table_number > 0),
  seats        INTEGER NOT NULL DEFAULT 4 CHECK (seats > 0),
  is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  order_number       TEXT NOT NULL UNIQUE,
  public_token       TEXT NOT NULL UNIQUE,
  customer_name      TEXT NOT NULL,
  customer_phone     TEXT NOT NULL DEFAULT '',
  order_type         TEXT NOT NULL CHECK (order_type IN ('dine_in','takeaway','delivery')),
  table_number       INTEGER,
  delivery_address   TEXT NOT NULL DEFAULT '',
  notes              TEXT NOT NULL DEFAULT '',
  status             TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','preparing','ready','completed','cancelled')),
  payment_status     TEXT NOT NULL DEFAULT 'unpaid' CHECK (payment_status IN ('unpaid','paid')),
  subtotal_cents     INTEGER NOT NULL,
  tax_cents          INTEGER NOT NULL,
  delivery_fee_cents INTEGER NOT NULL DEFAULT 0,
  total_cents        INTEGER NOT NULL,
  created_at         TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at         TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);

CREATE TABLE IF NOT EXISTS order_items (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id         INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  dish_id          INTEGER REFERENCES dishes(id) ON DELETE SET NULL,
  dish_name        TEXT NOT NULL,
  unit_price_cents INTEGER NOT NULL,
  quantity         INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 50),
  line_total_cents INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
`;

const DEFAULT_SETTINGS = {
  restaurant_name: 'Spice Garden',
  restaurant_address: '12 MG Road, Bengaluru 560001',
  restaurant_phone: '+91 98765 43210',
  gst_number: '',
  currency_symbol: '₹',
  tax_rate_percent: '5',
  delivery_fee: '40',
  public_base_url: '',
  timezone: 'Asia/Kolkata',
};

const SEED_CATEGORIES = ['Starters', 'Main Course', 'Beverages', 'Desserts'];

// [category, name, description, price, veg, image]
const SEED_DISHES = [
  ['Starters', 'Paneer Tikka', 'Cottage cheese cubes marinated in spiced yoghurt, chargrilled in the tandoor with peppers and onion.', 260, 1, 'paneer-tikka.svg'],
  ['Starters', 'Crispy Chicken Wings', 'Golden fried wings tossed in a sticky chilli-garlic glaze, served with mint dip.', 290, 0, 'chicken-wings.svg'],
  ['Starters', 'Tomato Bruschetta', 'Toasted sourdough topped with tomato, basil, garlic and extra-virgin olive oil.', 220, 1, 'bruschetta.svg'],
  ['Starters', 'Veg Spring Rolls', 'Crisp rolls stuffed with stir-fried vegetables and glass noodles, sweet chilli sauce.', 199, 1, 'spring-rolls.svg'],
  ['Main Course', 'Butter Chicken', 'Tandoori chicken simmered in a velvety tomato, butter and cream gravy.', 380, 0, 'butter-chicken.svg'],
  ['Main Course', 'Margherita Pizza', 'Wood-fired 10" pizza with San Marzano tomato, fresh mozzarella and basil.', 349, 1, 'margherita-pizza.svg'],
  ['Main Course', 'Hyderabadi Veg Biryani', 'Fragrant basmati layered with vegetables, saffron and fried onions, served with raita.', 320, 1, 'veg-biryani.svg'],
  ['Main Course', 'Grilled Salmon', 'Herb-crusted salmon fillet with lemon butter, sautéed greens and mash.', 650, 0, 'grilled-salmon.svg'],
  ['Main Course', 'Fettuccine Alfredo', 'Ribbon pasta in a rich parmesan cream sauce with cracked black pepper.', 330, 1, 'pasta-alfredo.svg'],
  ['Beverages', 'Mango Lassi', 'Chilled yoghurt smoothie blended with Alphonso mango and a hint of cardamom.', 120, 1, 'mango-lassi.svg'],
  ['Beverages', 'Cold Coffee', 'Creamy iced coffee blended with milk and a scoop of vanilla ice cream.', 150, 1, 'cold-coffee.svg'],
  ['Beverages', 'Fresh Lime Soda', 'Freshly squeezed lime with soda — sweet, salted or mixed.', 90, 1, 'lime-soda.svg'],
  ['Beverages', 'Masala Chai', 'Assam tea brewed with milk, ginger, cardamom and cinnamon.', 60, 1, 'masala-chai.svg'],
  ['Desserts', 'Gulab Jamun', 'Two warm milk dumplings soaked in rose-cardamom sugar syrup.', 110, 1, 'gulab-jamun.svg'],
  ['Desserts', 'Chocolate Brownie', 'Warm fudgy brownie with vanilla ice cream and chocolate sauce.', 180, 1, 'chocolate-brownie.svg'],
  ['Desserts', 'Blueberry Cheesecake', 'Baked New York cheesecake on a buttery biscuit base with blueberry compote.', 240, 1, 'cheesecake.svg'],
];

function openDatabase(file = config.dbFile) {
  if (file !== ':memory:') fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new Database(file);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  db.pragma('busy_timeout = 5000');
  db.exec(SCHEMA);
  seed(db);
  return db;
}

function seed(db) {
  const insertSetting = db.prepare('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)');
  for (const [k, v] of Object.entries(DEFAULT_SETTINGS)) insertSetting.run(k, v);

  const userCount = db.prepare('SELECT COUNT(*) AS c FROM users').get().c;
  if (userCount === 0) {
    const ins = db.prepare('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)');
    ins.run(config.adminUsername, bcrypt.hashSync(config.adminPassword, 12), 'admin');
    ins.run(config.kitchenUsername, bcrypt.hashSync(config.kitchenPassword, 12), 'kitchen');
  }

  const catCount = db.prepare('SELECT COUNT(*) AS c FROM categories').get().c;
  if (catCount === 0) {
    const tx = db.transaction(() => {
      const insCat = db.prepare('INSERT INTO categories (name, sort_order) VALUES (?, ?)');
      const ids = {};
      SEED_CATEGORIES.forEach((name, i) => { ids[name] = insCat.run(name, i).lastInsertRowid; });
      const insDish = db.prepare(`INSERT INTO dishes
        (category_id, name, description, price_cents, image_url, is_veg, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?)`);
      SEED_DISHES.forEach(([cat, name, desc, price, veg, img], i) => {
        insDish.run(ids[cat], name, desc, price * 100, `/images/dishes/${img}`, veg, i);
      });
    });
    tx();
  }

  const tableCount = db.prepare('SELECT COUNT(*) AS c FROM restaurant_tables').get().c;
  if (tableCount === 0) {
    const ins = db.prepare('INSERT INTO restaurant_tables (table_number, seats) VALUES (?, ?)');
    for (let i = 1; i <= 10; i++) ins.run(i, i <= 6 ? 4 : 6);
  }
}

function getSettings(db) {
  const rows = db.prepare('SELECT key, value FROM settings').all();
  const s = { ...DEFAULT_SETTINGS };
  for (const r of rows) s[r.key] = r.value;
  return s;
}

module.exports = { openDatabase, getSettings, DEFAULT_SETTINGS };
