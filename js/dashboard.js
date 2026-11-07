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

function chartGroups() {
  const configured = (state.families || []).filter((name) => name && name !== 'ALL MU03' && name !== 'Ban Văn Hóa');
  const discovered = state.tickets.flatMap((ticket) => [ticket.target_family, ticket.family]).filter(Boolean);
  return [...new Set([...configured, ...discovered].filter((name) => name !== 'ALL MU03' && name !== 'Ban Văn Hóa'))];
}

function ticketGroup(ticket) {
  return ticket.family === 'ALL MU03' ? (ticket.target_family || 'ALL MU03') : ticket.family;
}

function renderGroupCharts() {
  const items = state.tickets.filter((ticket) => state.day === 'all' || ticket.day === state.day);
  const groups = chartGroups();
  const definitions = {
    sent: (ticket) => Boolean(ticket.id),
    pending: (ticket) => ticket.status !== 'CLOSED' && !ticket.status.includes('COMPLETED'),
    cfm: (ticket) => ticket.status === 'SHIFT LEADER CONFIRMED',
    closed: (ticket) => ticket.status === 'CLOSED'
  };
  Object.entries(definitions).forEach(([key, matches]) => {
    const card = document.querySelector(`[data-chart="${key}"]`);
    if (!card) return;
    const counts = Object.fromEntries(groups.map((group) => [group, 0]));
    items.filter(matches).forEach((ticket) => {
      const group = ticketGroup(ticket);
      if (Object.prototype.hasOwnProperty.call(counts, group)) counts[group] += 1;
    });
    const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
    const max = Math.max(1, ...Object.values(counts));
    const stage = card.querySelector('.group-chart-stage');
    const totalNode = card.querySelector('.group-chart-head strong');
    totalNode.textContent = total;
    stage.innerHTML = groups.map((group) => {
      const value = counts[group];
      const height = value ? Math.max(8, Math.round(value / max * 126)) : 3;
      return `<div class="group-chart-column ${value ? 'has-value' : ''}" title="${esc(group)}: ${value}"><span class="group-chart-value">${value || ''}</span><i style="height:${height}px"></i><b>${esc(group)}</b></div>`;
    }).join('');
  });
}

function renderRows() {
  const items = state.tickets.filter((ticket) => state.day === 'all' || ticket.day === state.day);
  ticketRows.innerHTML = items.length ? items.map((ticket) => `<tr><td><b>${esc(ticket.id)}</b><br><span class="meta">${new Date(ticket.sent_at).toLocaleString('vi-VN')}</span></td><td>${esc(ticket.title)}</td><td>${esc(ticket.family)}</td><td>${leaderName(ticket.leader)}</td><td>${esc(ticket.line_id || '—')}</td><td>${badge(ticket.status)}</td><td>${formatSla(ticket)}</td></tr>`).join('') : '<tr><td colspan="7" class="empty">No tickets for this date.</td></tr>';
  scopeLabel.textContent = `${state.user || ''} · ${state.day === 'all' ? 'all dates' : state.day}`;
}

function renderData() {
  const list = document.getElementById('dataList');
  if (!list) return;
  const items = state.tickets.filter((ticket) => ticket.status === 'CLOSED' && (state.day === 'all' || ticket.day === state.day));
  list.innerHTML = items.length ? items.map((ticket) => {
    const media = (ticket.media || []).map((item) => item.type?.startsWith('video')
      ? `<video controls preload="metadata" src="${item.data}" aria-label="${esc(item.name)}"></video>`
      : `<img src="${item.data}" alt="${esc(item.name)}">`).join('');
    return `<article class="data-record"><div class="data-record-head"><div><span class="data-kicker">Closed ticket</span><h3>${esc(ticket.title)}</h3><p>${esc(ticket.id)} · ${esc(ticket.target_family || ticket.family)} · ${esc(ticket.line_id || 'No line')}</p></div><time>${new Date(ticket.closed_at || ticket.sent_at).toLocaleString('vi-VN')}</time></div><div class="data-record-body"><div><strong>Leader</strong><span>${esc(leaderName(ticket.leader))}</span></div><div><strong>Status</strong><span>${badge(ticket.status)}</span></div><div><strong>Content</strong><p>${esc(ticket.content)}</p></div></div>${media ? `<div class="data-media">${media}</div>` : '<div class="data-no-media">No evidence attached.</div>'}</article>`;
  }).join('') : '<div class="data-empty">No closed tickets for this date.</div>';
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
  renderGroupCharts();
}

function refreshSla() {
  document.querySelectorAll('[data-sla]').forEach((element) => {
    const left = 86400000 - (Date.now() - new Date(element.dataset.sla).getTime());
    if (left <= 0) { element.className = 'timeline overdue'; element.textContent = 'OVERDUE'; return; }
    element.textContent = `TIME LEFT ${String(Math.floor(left / 3600000)).padStart(2, '0')}:${String(Math.floor(left % 3600000 / 60000)).padStart(2, '0')}:${String(Math.floor(left % 60000 / 1000)).padStart(2, '0')}`;
  });
}
