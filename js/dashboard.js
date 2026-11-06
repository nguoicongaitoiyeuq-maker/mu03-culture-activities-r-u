function miniBars(values) {
  const max = Math.max(...values, 1);
  return `<div class="mini-bars">${values.map((value) => `<i style="height:${Math.max(8, Math.round(value / max * 38))}px"></i>`).join('')}</div>`;
}

function renderKpis() {}

function renderKpisLegacy() {
  const items = state.tickets.filter((ticket) => state.day === 'all' || ticket.day === state.day);
  const active = items.filter((ticket) => ticket.status !== 'CLOSED');
  const definitions = [
    ['Total tickets', items.length, 'all signals'],
    ['Leader read queue', items.filter((ticket) => ticket.status === 'WAITING FOR LEADER READ').length, 'needs attention'],
    ['Line sharing queue', items.filter((ticket) => ticket.status === 'WAITING FOR LINE SHARING' || ticket.status === 'READ').length, 'line action'],
    ['Completed sharing', items.filter((ticket) => ticket.status.includes('COMPLETED')).length, 'completed'],
    ['Awaiting confirmation', items.filter((ticket) => ticket.status.includes('COMPLETED')).length, 'close the loop'],
    ['Closed', items.filter((ticket) => ticket.status === 'CLOSED').length, 'closed tickets'],
    ['Open over 24h', active.filter((ticket) => Date.now() - new Date(ticket.sent_at) > 86400000).length, 'SLA watch'],
    ['Media attached', items.reduce((total, ticket) => total + (ticket.media || []).length, 0), 'visual evidence']
  ];
  kpis.innerHTML = definitions.map((definition, index) => `<div class="stat"><div class="stat-label">${definition[0]}</div><div class="stat-value">${definition[1]}</div><div class="stat-note">${definition[2]}</div>${miniBars(items.slice(0, 7).reverse().map((ticket, itemIndex) => index === 0 ? itemIndex + 1 : (ticket.media || []).length + (ticket.status === 'CLOSED' ? 2 : 1)))}</div>`).join('');
}

function formatSla(ticket) {
  const left = 86400000 - (Date.now() - new Date(ticket.sent_at).getTime());
  if (left <= 0) return `<span class="timeline overdue">OVERDUE ${Math.floor(Math.abs(left) / 3600000)}h</span>`;
  const hours = Math.floor(left / 3600000);
  const minutes = Math.floor(left % 3600000 / 60000);
  const seconds = Math.floor(left % 60000 / 1000);
  return `<span class="timeline" data-sla="${esc(ticket.sent_at)}">TIME LEFT ${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}</span>`;
}

function renderWorkflowPareto() {
  const items = state.tickets.filter((ticket) => state.day === 'all' || ticket.day === state.day);
  const counts = {};
  items.forEach((ticket) => { counts[ticket.status] = (counts[ticket.status] || 0) + 1; });
  const box = document.getElementById('workflowPareto');
  if (!box) return;
  box.textContent = '';
  const max = Math.max(1, ...Object.values(counts));
  Object.keys(counts).forEach((status) => {
    const column = document.createElement('div');
    column.className = 'pareto-bar-col';
    const value = document.createElement('div');
    value.className = 'pareto-value';
    value.textContent = counts[status];
    const bar = document.createElement('div');
    bar.className = 'pareto-bar';
    bar.style.height = `${Math.max(8, counts[status] / max * 140)}px`;
    const label = document.createElement('div');
    label.className = 'pareto-label';
    label.textContent = status;
    column.append(value, bar, label);
    box.appendChild(column);
  });
}

function renderRows() {
  const items = state.tickets.filter((ticket) => state.day === 'all' || ticket.day === state.day);
  ticketRows.innerHTML = items.length ? items.map((ticket) => `<tr><td><b>${esc(ticket.id)}</b><br><span class="meta">${new Date(ticket.sent_at).toLocaleString('vi-VN')}</span></td><td>${esc(ticket.title)}</td><td>${esc(ticket.family)}</td><td>${leaderName(ticket.leader)}</td><td>${esc(ticket.line_id || '—')}</td><td>${badge(ticket.status)}</td><td>${formatSla(ticket)}</td></tr>`).join('') : '<tr><td colspan="7" class="empty">No tickets for this date.</td></tr>';
  scopeLabel.textContent = `${state.user || ''} · ${state.day === 'all' ? 'all dates' : state.day}`;
}

function renderSummary() {
  const items = state.tickets.filter((ticket) => state.day === 'all' || ticket.day === state.day);
  const sent = items.length;
  const pending = items.filter((ticket) => ticket.status !== 'CLOSED' && !ticket.status.includes('COMPLETED')).length;
  const read = items.filter((ticket) => ticket.status === 'READ').length;
  const completed = items.filter((ticket) => ticket.status.includes('COMPLETED')).length;
  const closed = items.filter((ticket) => ticket.status === 'CLOSED').length;
  const max = Math.max(sent, pending, read, completed, closed, 1);
  summarySent.textContent = sent;
  summaryPending.textContent = pending;
  summaryRead.textContent = read;
  summaryCfm.textContent = completed;
  summaryClosed.textContent = closed;
  summarySentBar.style.height = `${Math.max(8, sent / max * 72)}px`;
  summaryPendingBar.style.height = `${Math.max(8, pending / max * 72)}px`;
  summaryReadBar.style.height = `${Math.max(8, read / max * 72)}px`;
  summaryCfmBar.style.height = `${Math.max(8, completed / max * 72)}px`;
  summaryClosedBar.style.height = `${Math.max(8, closed / max * 72)}px`;
  summaryDate.textContent = state.day === 'all' ? 'All dates' : state.day;
}

function refreshSla() {
  document.querySelectorAll('[data-sla]').forEach((element) => {
    const left = 86400000 - (Date.now() - new Date(element.dataset.sla).getTime());
    if (left <= 0) { element.className = 'timeline overdue'; element.textContent = 'OVERDUE'; return; }
    element.textContent = `TIME LEFT ${String(Math.floor(left / 3600000)).padStart(2, '0')}:${String(Math.floor(left % 3600000 / 60000)).padStart(2, '0')}:${String(Math.floor(left % 60000 / 1000)).padStart(2, '0')}`;
  });
}
