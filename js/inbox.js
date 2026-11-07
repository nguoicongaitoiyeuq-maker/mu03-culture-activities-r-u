function mediaHtml(items, large, ticketId) {
  return (items || []).map((media, index) => {
    const mediaName = esc(media.name || (media.type && media.type.startsWith('video') ? 'Video evidence' : 'Image evidence'));
    const idLiteral = JSON.stringify(ticketId || '');
    if (media.type && media.type.startsWith('video')) {
      return `<div class="media-tile media-video-tile"><video ${large ? 'controls ' : ''}preload="metadata" src="${media.data}"></video><button type="button" class="media-open-button" onclick='viewTicketMedia(${idLiteral},${index})'>OPEN VIDEO</button><span>${mediaName}</span></div>`;
    }
    return `<button type="button" class="media-tile media-image-tile" onclick='viewTicketMedia(${idLiteral},${index})' title="Open evidence"><img src="${media.data}" alt="${mediaName}"><span>${mediaName}</span></button>`;
  }).join('');
}

function viewTicketMedia(id, index) {
  const ticket = state.tickets.find((item) => item.id === id);
  const media = ticket?.media?.[index];
  if (!media) return;
  let viewer = document.getElementById('ticketMediaViewer');
  if (!viewer) {
    viewer = document.createElement('div');
    viewer.id = 'ticketMediaViewer';
    viewer.addEventListener('click', (event) => { if (event.target === viewer) closeTicketMedia(); });
    document.body.appendChild(viewer);
  }
  const name = esc(media.name || 'Ticket evidence');
  const content = media.type && media.type.startsWith('video')
    ? `<video controls autoplay src="${media.data}"></video>`
    : `<img src="${media.data}" alt="${name}">`;
  viewer.innerHTML = `<div class="ticket-media-viewer-panel"><button type="button" class="ticket-media-close" onclick="closeTicketMedia()" aria-label="Close">&times;</button><div class="ticket-media-viewer-content">${content}</div><div class="ticket-media-viewer-name">${name}</div></div>`;
  viewer.classList.add('open');
}

function closeTicketMedia() {
  document.getElementById('ticketMediaViewer')?.classList.remove('open');
}

document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeTicketMedia(); });

function bindLeaderMedia() {
  document.querySelectorAll('.leader-media-input').forEach((input) => input.onchange = (event) => {
    const id = input.dataset.id;
    leaderMedia[id] = [];
    [...event.target.files].slice(0, 6).forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        leaderMedia[id].push({ name: file.name, type: file.type, data: reader.result });
        const preview = document.getElementById(`leader-preview-${id}`);
        if (preview) preview.innerHTML = leaderMedia[id].map((media) => media.type.startsWith('video') ? `<video controls src="${media.data}"></video>` : `<img src="${media.data}">`).join('');
      };
      reader.readAsDataURL(file);
    });
  });
}

async function openTicket(id) {
  expandedTickets[id] = true;
  viewedTickets[id] = true;
  renderAll();
  document.getElementById(`ticket-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  const ticket = state.tickets.find((item) => item.id === id);
  if (ticket?.can_review && !ticket.reviewed_at) {
    try {
      await api(`/api/tickets/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ reviewed: true }) });
      await load();
    } catch (error) {
      showToast(error.message || 'Không thể ghi nhận việc xem ticket', 'error');
    }
  }
}

function showHaveLine(id) {
  const panel = document.getElementById(`have-line-${id}`);
  if (panel) {
    panel.classList.remove('hidden');
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function workflowButtons(id) {
  return [...document.querySelectorAll('button[data-workflow-ticket]')].filter((button) => button.dataset.workflowTicket === id);
}

function setWorkflowBusy(id, busy, label) {
  workflowButtons(id).forEach((button) => {
    if (busy) {
      button.dataset.idleText = button.textContent;
      button.disabled = true;
      button.textContent = label;
    } else {
      button.disabled = false;
      button.textContent = button.dataset.idleText || button.textContent;
    }
  });
}

function requireAcknowledgment(id, inputId, message) {
  const input = document.getElementById(inputId);
  if (input?.checked) return true;
  input?.focus();
  showToast(message, 'error');
  return false;
}

function renderInbox() {
  const items = state.tickets.filter((ticket) => ticket.status !== 'CLOSED' && !ticket.status.includes('COMPLETED'));
  inboxCount.textContent = `${items.length} open`;
  inboxList.innerHTML = items.length ? items.map((ticket) => {
    const expanded = Boolean(expandedTickets[ticket.id] || viewedTickets[ticket.id]);
    const canRead = Boolean(ticket.can_manage) && ticket.status === 'WAITING FOR LEADER READ';
    const canConfirm = Boolean(ticket.can_confirm) && ticket.status === 'READ' && Boolean(ticket.read_at) && Boolean(ticket.reviewed_at) && Boolean(viewedTickets[ticket.id]);
    const canManage = Boolean(ticket.can_manage) && ['SHIFT LEADER CONFIRMED', 'READ', 'WAITING FOR LINE SHARING'].includes(ticket.status);
    const waitingForAssignedLeader = ticket.status === 'WAITING FOR LEADER READ' && !canRead && !canConfirm;
    const reviewRequired = Boolean(ticket.can_review) && ticket.status === 'READ' && !ticket.reviewed_at;
    const actions = canRead
      ? `<div class="workflow-step"><span class="step-label">Step 1 · Xác nhận đã đọc</span><label class="workflow-ack"><input id="read-ack-${ticket.id}" type="checkbox"><span>Tôi đã đọc và hiểu nội dung ticket này.</span></label><div class="leader-choice"><button class="btn green" data-workflow-ticket="${esc(ticket.id)}" onclick="readTicket('${ticket.id}')">ĐÁNH DẤU ĐÃ ĐỌC</button></div></div>`
      : canConfirm
        ? `<div class="workflow-step"><span class="step-label">Step 2 · Xác nhận ticket</span><label class="workflow-ack"><input id="confirm-ack-${ticket.id}" type="checkbox"><span>Tôi đã đọc và hiểu nội dung ticket này.</span></label><div class="leader-choice"><button class="btn green" data-workflow-ticket="${esc(ticket.id)}" onclick="confirmShift('${ticket.id}')">XÁC NHẬN &amp; TIẾP TỤC</button><button class="btn danger-outline" data-workflow-ticket="${esc(ticket.id)}" onclick="rejectShift('${ticket.id}')">TỪ CHỐI</button></div></div>`
      : canManage
        ? `<div class="workflow-step"><span class="step-label">Step 3 · Chia sẻ line</span><div class="leader-choice"><button class="btn danger-outline" data-workflow-ticket="${esc(ticket.id)}" onclick="noLine('${ticket.id}')">NO LINE</button><button class="btn green" data-workflow-ticket="${esc(ticket.id)}" onclick="showHaveLine('${ticket.id}')">HAVE LINE</button></div><div id="have-line-${ticket.id}" class="leader-actions hidden"><label class="workflow-ack"><input id="line-ack-${ticket.id}" type="checkbox"><span>Tôi đã đọc và hiểu toàn bộ quy trình sharing.</span></label><div class="field"><label>Line ID *</label><input id="line-${ticket.id}" required></div><div class="evidence-box"><label>Sharing image / video *</label><input class="leader-media-input" data-id="${esc(ticket.id)}" type="file" accept="image/*,video/*" multiple></div><div id="leader-preview-${esc(ticket.id)}" class="leader-preview"></div><button class="btn green" data-workflow-ticket="${esc(ticket.id)}" onclick="completeSharing('${ticket.id}')">SUBMIT HAVE LINE</button></div></div>`
        : waitingForAssignedLeader ? '<div class="workflow-note">Waiting for the assigned leader to read and submit this ticket.</div>' : '';
    return `<article id="ticket-${esc(ticket.id)}" class="leader-card ${expanded ? 'ticket-open' : 'ticket-collapsed'}"><div class="ticket-header"><div><div class="ticket-kicker">Production ticket</div><h3>${esc(ticket.title)}</h3><div class="meta">${esc(ticket.id)} · ${esc(ticket.family)} · ${badge(ticket.status)}</div><div class="ticket-assignee">Assigned leader: <b>${esc(ticket.leader || 'Not configured')}</b></div></div></div>${expanded ? `<div class="ticket-details"><div class="ticket-content-block"><span class="ticket-content-label">Sharing request</span><div class="leader-content">${esc(ticket.content)}</div></div><div class="ticket-facts"><div class="ticket-fact"><span>Sender email</span><b>${esc(ticket.owner)}</b></div><div class="ticket-fact"><span>Created</span><b>${new Date(ticket.sent_at).toLocaleString('vi-VN')}</b></div><div class="ticket-fact"><span>Leader read status</span><b>${ticket.read_at ? 'Leader has read this ticket' : 'Waiting for leader to read'}</b></div></div>${ticket.media?.length ? `<div class="ticket-evidence"><span class="ticket-content-label">Attached evidence · click to view</span><div class="leader-media">${mediaHtml(ticket.media, true, ticket.id)}</div></div>` : ''}${actions}</div>` : `<div class="ticket-summary"><p>${reviewRequired ? 'Open this ticket to review the leader status and evidence before confirming.' : 'Open this ticket to read the production details.'}</p><button class="btn primary" onclick="openTicket('${ticket.id}')">${reviewRequired ? 'OPEN &amp; REVIEW' : 'OPEN &amp; READ'}</button></div>`}</article>`;
  }).join('') : '<div class="panel empty">No tickets assigned to your areas.</div>';
  bindLeaderMedia();
}

function renderConfirm() {
  const items = state.tickets.filter((ticket) => ticket.status.includes('COMPLETED') && ticket.can_confirm);
  confirmList.innerHTML = items.length ? items.map((ticket) => `<article class="leader-card"><h3>${esc(ticket.title)}</h3><div class="meta">${esc(ticket.id)} · ${esc(ticket.family)} · ${badge(ticket.status)}</div><div class="leader-content">${esc(ticket.content)}</div><div class="leader-actions"><button class="btn green" onclick="closeTicket('${ticket.id}')">CONFIRM & CLOSE</button></div></article>`).join('') : '<div class="panel empty">Nothing is waiting for confirmation.</div>';
}

let workflowSubmitting = {};
let viewedTickets = {};

async function readTicket(id) {
  if (workflowSubmitting[id]) return;
  if (!requireAcknowledgment(id, `read-ack-${id}`, 'Vui lòng xác nhận bạn đã đọc và hiểu nội dung ticket.')) return;
  workflowSubmitting[id] = true;
  setWorkflowBusy(id, true, 'LOADING...');
  try { await patch(id, { status: 'READ' }); showToast('Ticket marked as read', 'success'); }
  catch (error) { showToast(error.message || 'Cannot mark ticket as read', 'error'); }
  finally { workflowSubmitting[id] = false; setWorkflowBusy(id, false); }
}

async function confirmShift(id) {
  if (workflowSubmitting[id]) return;
  if (!requireAcknowledgment(id, `confirm-ack-${id}`, 'Vui lòng xác nhận bạn đã đọc và hiểu nội dung ticket.')) return;
  workflowSubmitting[id] = true;
  setWorkflowBusy(id, true, 'SUBMITTING...');
  try { await patch(id, { status: 'SHIFT LEADER CONFIRMED' }); showToast('Ticket confirmed', 'success'); }
  catch (error) { showToast(error.message || 'Cannot confirm ticket', 'error'); }
  finally { workflowSubmitting[id] = false; setWorkflowBusy(id, false); }
}

async function rejectShift(id) {
  if (workflowSubmitting[id]) return;
  if (!requireAcknowledgment(id, `confirm-ack-${id}`, 'Vui lòng xác nhận bạn đã đọc và hiểu nội dung ticket.')) return;
  workflowSubmitting[id] = true;
  setWorkflowBusy(id, true, 'SUBMITTING...');
  try { await patch(id, { status: 'SHIFT LEADER REJECTED' }); showToast('Ticket rejected by shift leader', 'success'); }
  catch (error) { showToast(error.message || 'Cannot reject ticket', 'error'); }
  finally { workflowSubmitting[id] = false; setWorkflowBusy(id, false); }
}

async function completeSharing(id) {
  if (workflowSubmitting[id]) return;
  const line = (document.getElementById(`line-${id}`)?.value || '').trim();
  if (!line) { showToast('Please enter Line ID', 'error'); return; }
  if (!(leaderMedia[id] || []).length) { showToast('Please add sharing image or video', 'error'); return; }
  if (!requireAcknowledgment(id, `line-ack-${id}`, 'Vui lòng xác nhận bạn đã đọc và hiểu toàn bộ quy trình sharing.')) return;
  workflowSubmitting[id] = true;
  setWorkflowBusy(id, true, 'SUBMITTING...');
  try { await patch(id, { status: 'LINE SHARING COMPLETED', line_id: line, media: leaderMedia[id] || [] }); showToast('HAVE LINE submitted', 'success'); }
  catch (error) { showToast(error.message || 'Cannot submit HAVE LINE', 'error'); }
  finally { workflowSubmitting[id] = false; setWorkflowBusy(id, false); }
}

async function noLine(id) {
  if (workflowSubmitting[id]) return;
  workflowSubmitting[id] = true;
  setWorkflowBusy(id, true, 'SUBMITTING...');
  try { await patch(id, { status: 'NO LINE - COMPLETED' }); showToast('NO LINE confirmed', 'success'); }
  catch (error) { showToast(error.message || 'Cannot update ticket', 'error'); }
  finally { workflowSubmitting[id] = false; setWorkflowBusy(id, false); }
}
