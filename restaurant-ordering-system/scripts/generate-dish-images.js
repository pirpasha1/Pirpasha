#!/usr/bin/env node
'use strict';
/**
 * Generates the illustrated dish images shipped with the demo menu
 * (public/images/dishes/*.svg). Replace any of them with a real photograph
 * from Admin → Dishes → Edit → Upload photo.
 */
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, '..', 'public', 'images', 'dishes');
const W = 600;
const H = 450;
const CX = W / 2;
const CY = H / 2 + 6;

function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

const defs = (bg1, bg2) => `
<defs>
  <radialGradient id="bg" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="${bg1}"/><stop offset="1" stop-color="${bg2}"/></radialGradient>
  <radialGradient id="plate" cx="45%" cy="40%" r="60%"><stop offset="0" stop-color="#ffffff"/><stop offset="0.85" stop-color="#f1efea"/><stop offset="1" stop-color="#d9d5cc"/></radialGradient>
  <radialGradient id="shine" cx="35%" cy="30%" r="40%"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#000" flood-opacity=".28"/></filter>
  <filter id="soft"><feGaussianBlur stdDeviation="1.2"/></filter>
</defs>`;

const background = (bg1, bg2, pattern) => {
  let p = '';
  if (pattern === 'wood') {
    for (let y = 0; y < H; y += 26) p += `<path d="M0 ${y} Q ${W / 2} ${y + 10} ${W} ${y}" stroke="#000" stroke-opacity=".06" stroke-width="2" fill="none"/>`;
  } else if (pattern === 'cloth') {
    for (let x = 0; x < W; x += 50) p += `<rect x="${x}" y="0" width="25" height="${H}" fill="#fff" opacity=".05"/>`;
    for (let y = 0; y < H; y += 50) p += `<rect x="0" y="${y}" width="${W}" height="25" fill="#fff" opacity=".05"/>`;
  }
  return `<rect width="${W}" height="${H}" fill="url(#bg)"/>${p}`;
};

const plate = (r = 175, extra = '') =>
  `<g filter="url(#shadow)"><circle cx="${CX}" cy="${CY}" r="${r}" fill="url(#plate)"/></g>
   <circle cx="${CX}" cy="${CY}" r="${r * 0.78}" fill="#fbfaf7" stroke="#e4e0d8" stroke-width="2"/>${extra}`;

const bowl = (r, rim, fill) =>
  `<g filter="url(#shadow)"><circle cx="${CX}" cy="${CY}" r="${r}" fill="${rim}"/></g>
   <circle cx="${CX}" cy="${CY}" r="${r * 0.86}" fill="${fill}"/>`;

const leaf = (x, y, s, rot, c = '#3f8f3a') =>
  `<path transform="translate(${x} ${y}) rotate(${rot}) scale(${s})" d="M0 0 C 8 -10 22 -10 30 0 C 22 10 8 10 0 0Z" fill="${c}"/><path transform="translate(${x} ${y}) rotate(${rot}) scale(${s})" d="M2 0 L28 0" stroke="#2b6b27" stroke-width="1"/>`;

function scatterLeaves(r, n, cx, cy, radius, c) {
  let s = '';
  for (let i = 0; i < n; i++) {
    const a = r() * Math.PI * 2;
    const d = Math.sqrt(r()) * radius;
    s += leaf(cx + Math.cos(a) * d, cy + Math.sin(a) * d, 0.35 + r() * 0.25, r() * 360, c);
  }
  return s;
}

function dots(r, n, cx, cy, radius, colors, size = [2, 4]) {
  let s = '';
  for (let i = 0; i < n; i++) {
    const a = r() * Math.PI * 2;
    const d = Math.sqrt(r()) * radius;
    const c = colors[Math.floor(r() * colors.length)];
    s += `<circle cx="${(cx + Math.cos(a) * d).toFixed(1)}" cy="${(cy + Math.sin(a) * d).toFixed(1)}" r="${(size[0] + r() * (size[1] - size[0])).toFixed(1)}" fill="${c}"/>`;
  }
  return s;
}

function glass({ liquid, liquid2, top, garnish = '', straw = '#e53935', bubbles = false, r }) {
  const gx = CX - 70;
  const gy = 95;
  const gw = 140;
  const gh = 270;
  let b = '';
  if (bubbles) for (let i = 0; i < 22; i++) b += `<circle cx="${gx + 18 + r() * (gw - 36)}" cy="${gy + 70 + r() * (gh - 90)}" r="${1.5 + r() * 3}" fill="none" stroke="#fff" stroke-opacity=".8"/>`;
  return `
  <ellipse cx="${CX}" cy="${gy + gh + 8}" rx="105" ry="16" fill="#000" opacity=".18" filter="url(#soft)"/>
  <defs><linearGradient id="liq" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${liquid}"/><stop offset="1" stop-color="${liquid2}"/></linearGradient>
  <linearGradient id="glassG" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset=".3" stop-color="#fff" stop-opacity=".08"/><stop offset=".8" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#fff" stop-opacity=".45"/></linearGradient></defs>
  <path d="M${gx + 40} ${gy - 60} L${gx + 70} ${gy + 140}" stroke="${straw}" stroke-width="12" stroke-linecap="round"/>
  <path d="M${gx} ${gy} L${gx + 12} ${gy + gh} Q ${CX} ${gy + gh + 10} ${gx + gw - 12} ${gy + gh} L${gx + gw} ${gy}Z" fill="#fff" fill-opacity=".25" stroke="#fff" stroke-opacity=".7" stroke-width="3"/>
  <path d="M${gx + 6} ${gy + 40} L${gx + 15} ${gy + gh - 4} Q ${CX} ${gy + gh + 6} ${gx + gw - 15} ${gy + gh - 4} L${gx + gw - 6} ${gy + 40}Z" fill="url(#liq)"/>
  ${top ? `<path d="M${gx + 6} ${gy + 40} L${gx + gw - 6} ${gy + 40} L${gx + gw - 8} ${gy + 72} Q ${CX} ${gy + 84} ${gx + 8} ${gy + 72}Z" fill="${top}"/>` : ''}
  ${b}
  <path d="M${gx} ${gy} L${gx + 12} ${gy + gh} Q ${CX} ${gy + gh + 10} ${gx + gw - 12} ${gy + gh} L${gx + gw} ${gy}Z" fill="url(#glassG)"/>
  <ellipse cx="${CX}" cy="${gy}" rx="70" ry="9" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="3"/>
  ${garnish}`;
}

const DISHES = {
  'paneer-tikka': { bg: ['#f6d7a7', '#c97b3c'], pattern: 'wood', draw(r) {
    let s = plate();
    const colors = ['#f3e2b8', '#e2702a', '#4f9a3c', '#d6402f', '#f3e2b8', '#e98a3a'];
    for (let k = 0; k < 3; k++) {
      const y = CY - 60 + k * 60;
      s += `<line x1="${CX - 150}" y1="${y + 5}" x2="${CX + 150}" y2="${y - 5}" stroke="#8d6e63" stroke-width="5" stroke-linecap="round"/>`;
      for (let i = 0; i < 6; i++) {
        const x = CX - 115 + i * 44;
        const c = colors[(i + k) % colors.length];
        s += `<rect x="${x}" y="${y - 18 - i * 0.3}" width="34" height="34" rx="7" fill="${c}" transform="rotate(${(r() - 0.5) * 16} ${x + 17} ${y})"/>`;
        s += `<rect x="${x + 4}" y="${y - 14}" width="10" height="5" rx="2" fill="#4e2a12" opacity=".55"/>`;
      }
    }
    s += `<path d="M${CX + 95} ${CY + 92} q 18 -8 34 4" stroke="#fff" stroke-width="7" fill="none" stroke-linecap="round" opacity=".8"/>`;
    s += `<circle cx="${CX - 120}" cy="${CY + 95}" r="18" fill="#f5e663"/><circle cx="${CX - 120}" cy="${CY + 95}" r="13" fill="#fbf3a6"/>`;
    return s + scatterLeaves(r, 7, CX, CY, 120);
  } },

  'chicken-wings': { bg: ['#ffe0b2', '#d84315'], pattern: 'wood', draw(r) {
    let s = plate();
    for (let i = 0; i < 7; i++) {
      const a = (i / 7) * Math.PI * 2 + 0.3;
      const x = CX + Math.cos(a) * 75;
      const y = CY + Math.sin(a) * 70;
      s += `<g transform="translate(${x} ${y}) rotate(${(a * 180) / Math.PI + 90})">
        <ellipse rx="34" ry="22" fill="#a1381b"/><ellipse rx="30" ry="18" fill="#c4521f"/>
        <ellipse cx="-8" cy="-6" rx="12" ry="5" fill="#f29c4a" opacity=".7"/>
        <ellipse cx="26" rx="12" ry="9" fill="#8a2e14"/></g>`;
    }
    s += `<circle cx="${CX}" cy="${CY}" r="34" fill="#fff" stroke="#ddd"/><circle cx="${CX}" cy="${CY}" r="27" fill="#7cb342"/><circle cx="${CX - 8}" cy="${CY - 8}" r="6" fill="#aed581"/>`;
    s += dots(r, 40, CX, CY, 120, ['#ffffff', '#212121'], [1, 2]);
    return s;
  } },

  bruschetta: { bg: ['#e8f5e9', '#6d8b4f'], pattern: 'wood', draw(r) {
    let s = `<g filter="url(#shadow)"><rect x="${CX - 210}" y="${CY - 120}" width="420" height="240" rx="26" fill="#8d5a33"/></g>
      <rect x="${CX - 200}" y="${CY - 110}" width="400" height="220" rx="22" fill="#a86d41"/>`;
    for (let i = 0; i < 3; i++) {
      const x = CX - 125 + i * 125;
      const y = CY + (i === 1 ? -10 : 10);
      s += `<g transform="rotate(${(r() - 0.5) * 14} ${x} ${y})"><ellipse cx="${x}" cy="${y}" rx="58" ry="78" fill="#c8893f"/><ellipse cx="${x}" cy="${y}" rx="50" ry="70" fill="#ecc27a"/></g>`;
      for (let k = 0; k < 16; k++) {
        const dx = (r() - 0.5) * 70;
        const dy = (r() - 0.5) * 100;
        s += `<rect x="${x + dx}" y="${y + dy}" width="${10 + r() * 6}" height="${10 + r() * 6}" rx="3" fill="${r() > 0.3 ? '#d32f2f' : '#ef5350'}" transform="rotate(${r() * 90} ${x + dx} ${y + dy})"/>`;
      }
      s += leaf(x - 18, y - 10, 0.9, r() * 360, '#2e7d32') + leaf(x + 4, y + 20, 0.7, r() * 360, '#388e3c');
    }
    return s;
  } },

  'spring-rolls': { bg: ['#fff3e0', '#f57c00'], pattern: 'cloth', draw(r) {
    let s = plate();
    for (let i = 0; i < 4; i++) {
      const y = CY - 75 + i * 40;
      const rot = -20 + i * 4;
      s += `<g transform="rotate(${rot} ${CX - 20} ${y})"><rect x="${CX - 120}" y="${y - 17}" width="190" height="36" rx="18" fill="#c07a1c"/>
        <rect x="${CX - 116}" y="${y - 14}" width="182" height="26" rx="13" fill="#e9a63b"/>
        <path d="M${CX - 100} ${y - 4} h150" stroke="#fbd38d" stroke-width="4" stroke-linecap="round" opacity=".7"/></g>`;
    }
    s += `<circle cx="${CX + 110}" cy="${CY + 80}" r="38" fill="#fff" stroke="#ddd"/><circle cx="${CX + 110}" cy="${CY + 80}" r="30" fill="#e53935"/>`;
    s += dots(r, 14, CX + 110, CY + 80, 24, ['#ff8a65', '#b71c1c'], [1.5, 2.5]);
    return s + scatterLeaves(r, 4, CX - 90, CY + 90, 30, '#43a047');
  } },

  'butter-chicken': { bg: ['#ffe0b2', '#8d4b25'], pattern: 'wood', draw(r) {
    let s = bowl(170, '#3e2723', '#e46b1f');
    s += `<circle cx="${CX}" cy="${CY}" r="146" fill="#d9541a"/>`;
    for (let i = 0; i < 9; i++) {
      const a = r() * Math.PI * 2;
      const d = 30 + r() * 80;
      s += `<ellipse cx="${CX + Math.cos(a) * d}" cy="${CY + Math.sin(a) * d}" rx="${20 + r() * 8}" ry="${15 + r() * 6}" fill="#b5401a" transform="rotate(${r() * 180} ${CX + Math.cos(a) * d} ${CY + Math.sin(a) * d})"/>`;
    }
    s += `<path d="M${CX + 6} ${CY} a 8 8 0 1 1 -16 0 a 18 18 0 1 1 36 0 a 30 30 0 1 1 -60 0 a 42 42 0 1 1 84 0 a 54 54 0 1 1 -108 0" stroke="#fff4e0" stroke-width="8" fill="none" stroke-linecap="round" opacity=".9"/>`;
    s += `<circle cx="${CX}" cy="${CY}" r="146" fill="url(#shine)"/>`;
    return s + dots(r, 30, CX, CY, 120, ['#2e7d32', '#43a047'], [2, 4]);
  } },

  'margherita-pizza': { bg: ['#d7ccc8', '#5d4037'], pattern: 'wood', draw(r) {
    let s = `<g filter="url(#shadow)"><circle cx="${CX}" cy="${CY}" r="185" fill="#8d6e63"/></g>
      <circle cx="${CX}" cy="${CY}" r="168" fill="#d9a05b"/><circle cx="${CX}" cy="${CY}" r="150" fill="#c62828"/>
      <circle cx="${CX}" cy="${CY}" r="150" fill="#e53935" opacity=".6"/>`;
    for (let i = 0; i < 26; i++) s += `<circle cx="${CX + (r() - 0.5) * 300 * 0.95}" cy="${CY + (r() - 0.5) * 300 * 0.95}" r="3" fill="#7b1d1d" opacity=".5"/>`;
    for (let i = 0; i < 18; i++) s += `<circle cx="${CX + Math.cos(i * 1.3) * (i < 7 ? 15 : i * 7)}" cy="${CY + Math.sin(i * 1.3) * (i < 7 ? 15 : i * 7)}" r="1.5" fill="#000" opacity=".3"/>`;
    for (let i = 0; i < 7; i++) {
      const a = (i / 7) * Math.PI * 2;
      const d = i === 0 ? 0 : 92;
      s += `<ellipse cx="${CX + Math.cos(a) * d}" cy="${CY + Math.sin(a) * d}" rx="30" ry="26" fill="#fffde7"/><ellipse cx="${CX + Math.cos(a) * d - 6}" cy="${CY + Math.sin(a) * d - 6}" rx="12" ry="8" fill="#fff" opacity=".9"/>`;
    }
    for (let i = 0; i < 6; i++) { const a = (i / 6) * Math.PI * 2 + 0.5; s += leaf(CX + Math.cos(a) * 55, CY + Math.sin(a) * 55, 1.1, r() * 360, '#2e7d32'); }
    for (let i = 0; i < 4; i++) { const a = (i / 4) * Math.PI; s += `<line x1="${CX + Math.cos(a) * 168}" y1="${CY + Math.sin(a) * 168}" x2="${CX - Math.cos(a) * 168}" y2="${CY - Math.sin(a) * 168}" stroke="#7a4a2a" stroke-width="2" opacity=".5"/>`; }
    return s;
  } },

  'veg-biryani': { bg: ['#fff8e1', '#b8860b'], pattern: 'cloth', draw(r) {
    let s = bowl(172, '#6d4c41', '#f7e7b4');
    for (let i = 0; i < 520; i++) {
      const a = r() * Math.PI * 2;
      const d = Math.sqrt(r()) * 140;
      const c = r() < 0.35 ? '#f2a516' : r() < 0.5 ? '#ffd54f' : '#fff8e7';
      s += `<ellipse cx="${(CX + Math.cos(a) * d).toFixed(1)}" cy="${(CY + Math.sin(a) * d).toFixed(1)}" rx="7" ry="2.2" fill="${c}" transform="rotate(${Math.floor(r() * 180)} ${(CX + Math.cos(a) * d).toFixed(1)} ${(CY + Math.sin(a) * d).toFixed(1)})"/>`;
    }
    s += dots(r, 18, CX, CY, 120, ['#ef6c00', '#43a047', '#c62828'], [5, 8]);
    s += dots(r, 40, CX, CY - 20, 60, ['#6d3b14', '#8d5524'], [2, 4]);
    s += `<circle cx="${CX}" cy="${CY}" r="148" fill="url(#shine)"/>`;
    return s + scatterLeaves(r, 6, CX, CY, 100, '#2e7d32');
  } },

  'grilled-salmon': { bg: ['#e0f2f1', '#37615a'], pattern: 'cloth', draw(r) {
    let s = plate();
    s += `<ellipse cx="${CX - 60}" cy="${CY + 50}" rx="70" ry="45" fill="#f3e9d2"/><ellipse cx="${CX - 70}" cy="${CY + 40}" rx="40" ry="20" fill="#fffaf0"/>`;
    for (let i = 0; i < 8; i++) s += `<ellipse cx="${CX + 70 + (r() - 0.5) * 70}" cy="${CY + 70 + (r() - 0.5) * 40}" rx="22" ry="8" fill="${r() > 0.5 ? '#558b2f' : '#33691e'}" transform="rotate(${r() * 180} ${CX + 70} ${CY + 70})"/>`;
    s += `<g transform="rotate(-12 ${CX} ${CY - 40})"><clipPath id="fc"><path d="M${CX - 120} ${CY - 50} C ${CX - 110} ${CY - 110}, ${CX + 100} ${CY - 115}, ${CX + 125} ${CY - 60} C ${CX + 130} ${CY - 20}, ${CX - 100} ${CY + 5}, ${CX - 120} ${CY - 50}Z"/></clipPath><path d="M${CX - 120} ${CY - 50} C ${CX - 110} ${CY - 110}, ${CX + 100} ${CY - 115}, ${CX + 125} ${CY - 60} C ${CX + 130} ${CY - 20}, ${CX - 100} ${CY + 5}, ${CX - 120} ${CY - 50}Z" fill="#f08a5d"/>
      <path d="M${CX - 110} ${CY - 55} C ${CX - 100} ${CY - 100}, ${CX + 90} ${CY - 105}, ${CX + 115} ${CY - 62}" stroke="#ffb38a" stroke-width="10" fill="none" opacity=".7"/>`;
    s += '<g clip-path="url(#fc)">';
    for (let i = 0; i < 7; i++) s += `<line x1="${CX - 90 + i * 36}" y1="${CY - 120}" x2="${CX - 115 + i * 36}" y2="${CY}" stroke="#7a3315" stroke-width="7" stroke-linecap="round" opacity=".7"/>`;
    s += '</g></g>';
    s += `<g transform="translate(${CX + 120} ${CY - 20})"><path d="M0 0 A 30 30 0 0 1 60 0 Z" fill="#fbc02d"/><path d="M6 -2 A 24 24 0 0 1 54 -2 Z" fill="#fff59d"/></g>`;
    return s + scatterLeaves(r, 5, CX, CY - 50, 60, '#33691e');
  } },

  'pasta-alfredo': { bg: ['#fffde7', '#9e8b5b'], pattern: 'wood', draw(r) {
    let s = plate() + `<clipPath id="pc"><circle cx="${CX}" cy="${CY}" r="122"/></clipPath><g clip-path="url(#pc)">`;
    for (let i = 0; i < 110; i++) {
      const a = r() * Math.PI * 2;
      const d = Math.sqrt(r()) * 105;
      const x = CX + Math.cos(a) * d;
      const y = CY + Math.sin(a) * d;
      const len = 40 + r() * 50;
      s += `<path d="M${x} ${y} q ${len / 2} ${(r() - 0.5) * 60} ${len} 0" stroke="${r() > 0.5 ? '#f3dc9c' : '#e9cd82'}" stroke-width="11" fill="none" stroke-linecap="round" transform="rotate(${r() * 360} ${x} ${y})"/>`;
    }
    s += `</g><circle cx="${CX}" cy="${CY}" r="110" fill="#fff8e1" opacity=".25"/>`;
    s += dots(r, 60, CX, CY, 105, ['#3e2723', '#5d4037'], [1, 2]);
    return s + dots(r, 30, CX, CY, 100, ['#2e7d32', '#558b2f'], [2, 3.5]);
  } },

  'mango-lassi': { bg: ['#fff8e1', '#ff9800'], pattern: 'cloth', draw(r) {
    return glass({ liquid: '#ffd54f', liquid2: '#ffa000', top: '#fff3c4', straw: '#43a047', r,
      garnish: leaf(CX - 10, 128, 1.1, -30, '#2e7d32') + leaf(CX + 4, 126, 0.9, 200, '#43a047') + dots(r, 10, CX, 132, 40, ['#ffb300', '#ff8f00'], [2, 3]) });
  } },

  'cold-coffee': { bg: ['#efebe9', '#6d4c41'], pattern: 'wood', draw(r) {
    let ice = '';
    for (let i = 0; i < 4; i++) ice += `<rect x="${CX - 50 + i * 22}" y="${150 + (i % 2) * 40}" width="34" height="34" rx="6" fill="#fff" opacity=".25" transform="rotate(${r() * 40} ${CX - 30 + i * 22} ${170})"/>`;
    return glass({ liquid: '#b07a4f', liquid2: '#5d3a1f', top: '#f5e6d3', straw: '#212121', r,
      garnish: ice + `<path d="M${CX - 52} 128 q 26 -40 52 -10 q 26 -40 52 -10 q -20 25 -52 20 q -32 5 -52 0Z" fill="#fffaf2"/>` + dots(r, 14, CX, 118, 35, ['#4e342e', '#3e2723'], [1.5, 2.5]) });
  } },

  'lime-soda': { bg: ['#f1f8e9', '#689f38'], pattern: 'cloth', draw(r) {
    let ice = '';
    for (let i = 0; i < 4; i++) ice += `<rect x="${CX - 50 + i * 22}" y="${150 + (i % 2) * 50}" width="34" height="34" rx="6" fill="#fff" opacity=".35" transform="rotate(${r() * 40} ${CX - 30 + i * 22} ${170})"/>`;
    return glass({ liquid: '#e6f5c4', liquid2: '#b9de7e', bubbles: true, straw: '#fdd835', r,
      garnish: ice + `<g transform="translate(${CX + 70} 98)"><circle r="34" fill="#7cb342"/><circle r="29" fill="#dcedc8"/>${Array.from({ length: 8 }, (_, i) => `<line x1="0" y1="0" x2="${Math.cos(i * 0.785) * 27}" y2="${Math.sin(i * 0.785) * 27}" stroke="#9ccc65" stroke-width="2"/>`).join('')}<circle r="4" fill="#9ccc65"/></g>` + leaf(CX - 40, 132, 1, -40, '#2e7d32') });
  } },

  'masala-chai': { bg: ['#fbe9e7', '#8d4b2b'], pattern: 'wood', draw(r) {
    let s = `<ellipse cx="${CX}" cy="${CY + 120}" rx="170" ry="34" fill="#000" opacity=".18" filter="url(#soft)"/>
      <ellipse cx="${CX}" cy="${CY + 105}" rx="165" ry="36" fill="#fafafa" stroke="#ddd" stroke-width="2"/>
      <path d="M${CX - 110} ${CY - 40} L ${CX - 90} ${CY + 90} Q ${CX} ${CY + 115} ${CX + 90} ${CY + 90} L ${CX + 110} ${CY - 40}Z" fill="#f5f5f5" stroke="#d7d7d7" stroke-width="2"/>
      <path d="M${CX + 106} ${CY - 10} q 60 0 50 50 q -8 40 -62 40" stroke="#eeeeee" stroke-width="16" fill="none"/>
      <ellipse cx="${CX}" cy="${CY - 40}" rx="110" ry="26" fill="#f0f0f0" stroke="#d7d7d7" stroke-width="2"/>
      <ellipse cx="${CX}" cy="${CY - 38}" rx="98" ry="20" fill="#c08552"/><ellipse cx="${CX - 20}" cy="${CY - 42}" rx="40" ry="7" fill="#e0b080" opacity=".7"/>
      <path d="M${CX - 100} ${CY + 20} Q ${CX} ${CY + 50} ${CX + 100} ${CY + 20}" stroke="#c0392b" stroke-width="6" fill="none" opacity=".6"/>`;
    for (let i = 0; i < 3; i++) s += `<path d="M${CX - 40 + i * 40} ${CY - 70} c -20 -25 20 -40 0 -70 c -15 -20 10 -35 0 -50" stroke="#fff" stroke-width="7" fill="none" stroke-linecap="round" opacity=".55"/>`;
    s += `<g transform="translate(${CX + 150} ${CY + 125}) rotate(-20)"><rect x="-40" y="-6" width="80" height="12" rx="6" fill="#8d5524"/><rect x="-40" y="-6" width="80" height="5" rx="3" fill="#a9713d"/></g>`;
    s += `<g transform="translate(${CX - 175} ${CY + 120})"><path d="M0 -14 L4 -4 L14 0 L4 4 L0 14 L-4 4 L-14 0 L-4 -4Z" fill="#5d4037"/></g>`;
    return s + dots(r, 5, CX - 150, CY + 140, 18, ['#558b2f'], [3, 5]);
  } },

  'gulab-jamun': { bg: ['#fce4ec', '#ad1457'], pattern: 'cloth', draw(r) {
    let s = bowl(165, '#eeeeee', '#e8a74a');
    s += `<circle cx="${CX}" cy="${CY}" r="140" fill="#d98a2b" opacity=".6"/>`;
    for (const [dx, dy] of [[-55, -15], [55, 15]]) {
      s += `<circle cx="${CX + dx}" cy="${CY + dy}" r="62" fill="#5d2a0c"/><circle cx="${CX + dx}" cy="${CY + dy}" r="56" fill="#7a3a12"/>
        <ellipse cx="${CX + dx - 20}" cy="${CY + dy - 22}" rx="20" ry="11" fill="#fff" opacity=".35" transform="rotate(-30 ${CX + dx - 20} ${CY + dy - 22})"/>`;
    }
    s += dots(r, 26, CX, CY, 110, ['#7cb342', '#9ccc65'], [2, 3.5]);
    s += dots(r, 8, CX, CY, 110, ['#e91e63'], [2, 3]);
    return s + `<circle cx="${CX}" cy="${CY}" r="140" fill="url(#shine)"/>`;
  } },

  'chocolate-brownie': { bg: ['#efebe9', '#4e342e'], pattern: 'wood', draw(r) {
    let s = plate();
    s += `<g transform="rotate(-8 ${CX - 30} ${CY})"><rect x="${CX - 120}" y="${CY - 70}" width="160" height="140" rx="10" fill="#3e2015"/><rect x="${CX - 112}" y="${CY - 62}" width="144" height="124" rx="8" fill="#4e2a1a"/>`;
    for (let i = 0; i < 20; i++) s += `<path d="M${CX - 110 + r() * 140} ${CY - 60 + r() * 120} l ${4 + r() * 8} ${2 + r() * 6}" stroke="#2a130a" stroke-width="3" stroke-linecap="round"/>`;
    s += '</g>';
    s += `<path d="M${CX - 140} ${CY - 40} C ${CX - 80} ${CY - 90}, ${CX - 20} ${CY + 30}, ${CX + 40} ${CY - 30} S ${CX + 80} ${CY + 60}, ${CX + 20} ${CY + 90}" stroke="#2a130a" stroke-width="8" fill="none" stroke-linecap="round"/>`;
    s += `<circle cx="${CX + 85}" cy="${CY - 40}" r="52" fill="#fff8e1"/><circle cx="${CX + 70}" cy="${CY - 56}" r="20" fill="#fff" opacity=".9"/>${dots(r, 10, CX + 85, CY - 40, 40, ['#3e2723'], [1.5, 2])}`;
    s += leaf(CX + 95, CY - 90, 0.9, -60, '#43a047') + leaf(CX + 98, CY - 88, 0.8, 10, '#2e7d32');
    return s + dots(r, 18, CX, CY + 100, 50, ['#795548', '#4e342e'], [1.5, 3]);
  } },

  cheesecake: { bg: ['#ede7f6', '#4527a0'], pattern: 'cloth', draw(r) {
    let s = plate();
    s += `<path d="M${CX - 120} ${CY + 70} L ${CX + 130} ${CY + 90} L ${CX + 10} ${CY - 110} Z" fill="#d4a056"/>
      <path d="M${CX - 108} ${CY + 58} L ${CX + 118} ${CY + 76} L ${CX + 8} ${CY - 98} Z" fill="#fff4d6"/>
      <path d="M${CX - 120} ${CY + 70} L ${CX + 130} ${CY + 90}" stroke="#a87432" stroke-width="12" stroke-linecap="round"/>`;
    s += dots(r, 26, CX + 5, CY - 10, 55, ['#283593', '#3949ab', '#1a237e'], [6, 10]);
    s += dots(r, 26, CX + 5, CY - 10, 55, ['#7e57c2'], [2, 3]);
    s += `<path d="M${CX - 80} ${CY + 110} q 40 10 90 0 q 50 -10 90 5" stroke="#5e35b1" stroke-width="7" fill="none" stroke-linecap="round" opacity=".8"/>`;
    return s + leaf(CX + 10, CY - 50, 1, -70, '#43a047') + dots(r, 5, CX - 120, CY - 60, 20, ['#303f9f'], [7, 9]);
  } },
};

fs.mkdirSync(OUT, { recursive: true });
let seed = 7;
for (const [name, d] of Object.entries(DISHES)) {
  const r = rng(seed++ * 9973);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${name.replace(/-/g, ' ')}">${defs(d.bg[0], d.bg[1])}${background(d.bg[0], d.bg[1], d.pattern)}${d.draw(r)}</svg>\n`;
  fs.writeFileSync(path.join(OUT, `${name}.svg`), svg);
}
console.log(`Wrote ${Object.keys(DISHES).length} dish images to ${OUT}`);
