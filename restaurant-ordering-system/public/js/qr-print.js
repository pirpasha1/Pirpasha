(function () {
  'use strict';
  const { api, esc, requireStaff } = window.App;
  const sheet = document.getElementById('sheet');
  let tables = [];
  let name = '';

  function render() {
    const onlyActive = document.getElementById('onlyActive').checked;
    const list = tables.filter((t) => !onlyActive || t.is_active);
    sheet.innerHTML = list.map((t) => `
      <div class="qr-tent">
        <h2>${esc(name)}</h2>
        <div class="t">Table ${t.table_number}</div>
        <img src="/api/admin/tables/${t.id}/qr.png" alt="QR code for table ${t.table_number}">
        <div><strong>Scan to view the menu &amp; order</strong></div>
        <div class="muted" style="font-size:.85rem">Point your phone camera at the code</div>
      </div>`).join('') || '<div class="empty">No tables to print.</div>';
  }

  document.getElementById('onlyActive').addEventListener('change', render);
  document.getElementById('printBtn').addEventListener('click', () => window.print());

  requireStaff(['admin']).then(async (me) => {
    if (!me) return;
    const [list, settings] = await Promise.all([api('/api/admin/tables'), api('/api/admin/settings')]);
    tables = list;
    name = settings.restaurant_name;
    render();
  });
})();
