'use strict';
const path = require('path');
const PDFDocument = require('pdfkit');
const { formatMoney } = require('../util');

const FONT = path.join(__dirname, '..', '..', 'assets', 'fonts', 'DejaVuSans.ttf');
const FONT_BOLD = path.join(__dirname, '..', '..', 'assets', 'fonts', 'DejaVuSans-Bold.ttf');

const TYPE_LABEL = { dine_in: 'Dine-in', takeaway: 'Takeaway', delivery: 'Delivery' };

function formatDate(isoStr, tz) {
  const d = new Date(isoStr);
  try {
    return d.toLocaleString('en-IN', { timeZone: tz || 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' });
  } catch (_) {
    return d.toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
  }
}

/**
 * Render a bill as a PDF stream.
 * format: 'a4' (default) or 'receipt' (80 mm thermal printer roll).
 */
function renderBill(order, settings, format = 'a4') {
  const receipt = format === 'receipt';
  const mm = 72 / 25.4;
  const margin = receipt ? 4 * mm : 50;
  const width = receipt ? 80 * mm : 595.28; // A4 width
  const lineCount = order.items.length;
  const height = receipt
    ? (82 + lineCount * 6 + (order.notes ? 14 : 0) + (order.order_type === 'delivery' ? 14 : 0) + (settings.gst_number ? 4 : 0)) * mm
    : 841.89;

  const doc = new PDFDocument({ size: [width, height], margin, info: { Title: `Bill #${order.order_number}` } });
  doc.registerFont('R', FONT);
  doc.registerFont('B', FONT_BOLD);

  const cur = settings.currency_symbol || '₹';
  const money = (c) => formatMoney(c, cur);
  const contentW = width - margin * 2;
  const fs = receipt ? { title: 12, body: 7.5, small: 6.5, total: 9 } : { title: 22, body: 10.5, small: 9, total: 13 };

  // Header
  doc.font('B').fontSize(fs.title).text(settings.restaurant_name || 'Restaurant', { align: 'center' });
  doc.font('R').fontSize(fs.small);
  if (settings.restaurant_address) doc.text(settings.restaurant_address, { align: 'center' });
  if (settings.restaurant_phone) doc.text(`Phone: ${settings.restaurant_phone}`, { align: 'center' });
  if (settings.gst_number) doc.text(`GSTIN: ${settings.gst_number}`, { align: 'center' });
  doc.moveDown(0.6);
  doc.font('B').fontSize(fs.body + 1).text(order.payment_status === 'paid' ? 'TAX INVOICE — PAID' : 'TAX INVOICE', { align: 'center' });
  doc.moveDown(0.4);

  const rule = () => {
    const y = doc.y + 2;
    doc.moveTo(margin, y).lineTo(width - margin, y).lineWidth(0.6).strokeColor('#999').stroke();
    doc.y = y + 4;
  };
  rule();

  // Order meta
  doc.font('R').fontSize(fs.body);
  const meta = [
    ['Bill No.', `#${order.order_number}`],
    ['Date', formatDate(order.created_at, settings.timezone)],
    ['Customer', order.customer_name],
    ['Order type', TYPE_LABEL[order.order_type] + (order.table_number ? ` — Table ${order.table_number}` : '')],
  ];
  if (order.customer_phone) meta.push(['Phone', order.customer_phone]);
  if (order.order_type === 'delivery') meta.push(['Deliver to', order.delivery_address]);
  const labelW = receipt ? 22 * mm : 90;
  for (const [k, v] of meta) {
    const y = doc.y;
    doc.font('B').text(k, margin, y, { width: labelW });
    const yAfterLabel = doc.y;
    doc.font('R').text(v, margin + labelW, y, { width: contentW - labelW });
    doc.y = Math.max(doc.y, yAfterLabel);
  }
  doc.moveDown(0.3);
  rule();

  // Items table
  const cols = receipt
    ? { name: contentW * 0.46, qty: contentW * 0.1, rate: contentW * 0.2, amt: contentW * 0.24 }
    : { name: contentW * 0.5, qty: contentW * 0.12, rate: contentW * 0.18, amt: contentW * 0.2 };
  const x = {
    name: margin,
    qty: margin + cols.name,
    rate: margin + cols.name + cols.qty,
    amt: margin + cols.name + cols.qty + cols.rate,
  };
  const row = (cells, font) => {
    const y = doc.y;
    doc.font(font);
    doc.text(cells[0], x.name, y, { width: cols.name - 4 });
    const yName = doc.y;
    doc.text(cells[1], x.qty, y, { width: cols.qty, align: 'center' });
    doc.text(cells[2], x.rate, y, { width: cols.rate, align: 'right' });
    doc.text(cells[3], x.amt, y, { width: cols.amt, align: 'right' });
    doc.y = Math.max(yName, doc.y) + (receipt ? 1 : 3);
  };
  doc.fontSize(fs.body);
  row(['Item', 'Qty', 'Rate', 'Amount'], 'B');
  rule();
  for (const it of order.items) {
    row([it.dish_name, String(it.quantity), money(it.unit_price_cents), money(it.line_total_cents)], 'R');
  }
  rule();

  // Totals
  const totalRow = (label, value, bold) => {
    const y = doc.y;
    doc.font(bold ? 'B' : 'R').fontSize(bold ? fs.total : fs.body);
    doc.text(label, margin, y, { width: contentW * 0.6, align: 'right' });
    doc.text(value, margin + contentW * 0.6, y, { width: contentW * 0.4, align: 'right' });
    doc.moveDown(0.15);
  };
  totalRow('Subtotal', money(order.subtotal_cents));
  totalRow(`Tax (GST ${settings.tax_rate_percent}%)`, money(order.tax_cents));
  if (order.delivery_fee_cents) totalRow('Delivery fee', money(order.delivery_fee_cents));
  rule();
  totalRow('TOTAL', money(order.total_cents), true);
  doc.moveDown(0.2);
  doc.font('R').fontSize(fs.small).text(`Payment: ${order.payment_status === 'paid' ? 'Paid' : 'Due'}`, margin, doc.y, { width: contentW, align: 'right' });

  if (order.notes) {
    doc.moveDown(0.6);
    doc.font('B').fontSize(fs.small).text('Notes: ', margin, doc.y, { continued: true, width: contentW });
    doc.font('R').text(order.notes);
  }

  doc.moveDown(1);
  doc.font('R').fontSize(fs.small).fillColor('#444').text('Thank you for dining with us!', margin, doc.y, { width: contentW, align: 'center' });
  doc.end();
  return doc;
}

module.exports = { renderBill };
