function mediaHtml(items, large) {
  return (items || []).map((media) => media.type && media.type.startsWith('video')
    ? `<video ${large ? 'controls ' : ''}src="${media.data}"></video>`
    : `<img src="${media.data}" alt="${esc(media.name || 'attachment')}">`).join('');
}

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

function openTicket(id) {
  expandedTickets[id] = true;
  const ticket = state.tickets.find((item) => item.id === id);
  renderAll();
  if (ticket && ticket.status === 'SHIFT LEADER CONFIRMED' && ticket.can_manage) patch(id, { status: 'READ' }).catch((error) => showToast(error.message || 'Cannot mark READ', 'error'));
}

function showHaveLine(id) {
  const panel = document.getElementById(`have-line-${id}`);
  if (panel) panel.classList.remove('hidden');
}

function renderInbox() {
  const items = state.tickets.filter((ticket) => ticket.status !== 'CLOSED' && !ticket.status.includes('COMPLETED'));
  inboxCount.textContent = `${items.length} open`;
  inboxList.innerHTML = items.length ? items.map((ticket) => {
    const expanded = expandedTickets[ticket.id] || !['WAITING FOR SHIFT LEADER CONFIRMATION', 'WAITING FOR LEADER READ'].includes(ticket.status);
    const canConfirm = Boolean(ticket.can_confirm) && ticket.status === 'WAITING FOR SHIFT LEADER CONFIRMATION';
    const canManage = Boolean(ticket.can_manage) && ['READ', 'SHIFT LEADER CONFIRMED', 'WAITING FOR LINE SHARING'].includes(ticket.status);
    const actions = canConfirm
      ? `<div class="workflow-step"><span class="step-label">Step 1 · Shift leader confirmation</span><div class="leader-choice"><button class="btn green" onclick="confirmShift('${ticket.id}')">CONFIRM &amp; SEND TO AREA</button><button class="btn danger-outline" onclick="rejectShift('${ticket.id}')">REJECT</button></div></div>`
      : canManage
        ? `<div class="workflow-step"><div class="leader-choice"><button class="btn danger-outline" onclick="noLine('${ticket.id}')">NO LINE</button><button class="btn green" onclick="showHaveLine('${ticket.id}')">HAVE LINE</button></div><div id="have-line-${ticket.id}" class="leader-actions hidden"><div class="field"><label>Line ID *</label><input id="line-${ticket.id}" required></div><div class="evidence-box"><label>Sharing image / video *</label><input class="leader-media-input" data-id="${ticket.id}" type="file" accept="image/*,video/*" multiple></div><div id="leader-preview-${ticket.id}" class="leader-preview"></div><button class="btn green" onclick="completeSharing('${ticket.id}')">SUBMIT HAVE LINE</button></div></div>`
        : '';
    return `<article class="leader-card ${expanded ? 'ticket-open' : 'ticket-collapsed'}"><div class="ticket-header"><div><div class="ticket-kicker">Area ticket</div><h3>${esc(ticket.title)}</h3><div class="meta">${esc(ticket.id)} · ${esc(ticket.family)} · ${badge(ticket.status)}</div></div></div>${expanded ? `<div class="ticket-details"><div class="leader-content">${esc(ticket.content)}</div><div class="ticket-facts"><div class="ticket-fact"><span>Sender email</span><b>${esc(ticket.owner)}</b></div><div class="ticket-fact"><span>Shift leader</span><b>${esc(ticket.shift_leader || 'Not configured')}</b></div><div class="ticket-fact"><span>Area leader</span><b>${esc(ticket.area_leader || 'Not configured')}</b></div><div class="ticket-fact"><span>Created</span><b>${new Date(ticket.sent_at).toLocaleString('vi-VN')}</b></div></div>${ticket.media?.length ? `<div class="leader-media">${mediaHtml(ticket.media, true)}</div>` : ''}${actions}</div>` : `<div class="ticket-summary"><p>Open this area ticket to view production details.</p><button class="btn primary" onclick="openTicket('${ticket.id}')">OPEN &amp; READ</button></div>`}</article>`;
  }).join('') : '<div class="panel empty">No tickets assigned to your areas.</div>';
  bindLeaderMedia();
}

function renderConfirm() {
  const items = state.tickets.filter((ticket) => ticket.status.includes('COMPLETED') && ticket.can_confirm);
  confirmList.innerHTML = items.length ? items.map((ticket) => `<article class="leader-card"><h3>${esc(ticket.title)}</h3><div class="meta">${esc(ticket.id)} · ${esc(ticket.family)} · ${badge(ticket.status)}</div><div class="leader-content">${esc(ticket.content)}</div><div class="leader-actions"><button class="btn green" onclick="closeTicket('${ticket.id}')">CONFIRM & CLOSE</button></div></article>`).join('') : '<div class="panel empty">Nothing is waiting for confirmation.</div>';
}

let workflowSubmitting = {};

async function confirmShift(id) {
  if (workflowSubmitting[id]) return;
  workflowSubmitting[id] = true;
  try { await patch(id, { status: 'SHIFT LEADER CONFIRMED' }); showToast('Ticket sent to the area team', 'success'); }
  catch (error) { showToast(error.message || 'Cannot confirm ticket', 'error'); }
  finally { workflowSubmitting[id] = false; }
}

async function rejectShift(id) {
  if (workflowSubmitting[id]) return;
  workflowSubmitting[id] = true;
  try { await patch(id, { status: 'SHIFT LEADER REJECTED' }); showToast('Ticket rejected by shift leader', 'success'); }
  catch (error) { showToast(error.message || 'Cannot reject ticket', 'error'); }
  finally { workflowSubmitting[id] = false; }
}

async function completeSharing(id) {
  if (workflowSubmitting[id]) return;
  const line = (document.getElementById(`line-${id}`)?.value || '').trim();
  if (!line) { showToast('Please enter Line ID', 'error'); return; }
  if (!(leaderMedia[id] || []).length) { showToast('Please add sharing image or video', 'error'); return; }
  const button = document.querySelector(`#have-line-${CSS.escape(id)} button`);
  workflowSubmitting[id] = true;
  if (button) { button.disabled = true; button.textContent = 'SUBMITTING...'; }
  try { await patch(id, { status: 'LINE SHARING COMPLETED', line_id: line, media: leaderMedia[id] || [] }); showToast('HAVE LINE submitted', 'success'); }
  catch (error) { showToast(error.message || 'Cannot submit HAVE LINE', 'error'); }
  finally { workflowSubmitting[id] = false; if (button) { button.disabled = false; button.textContent = 'SUBMIT HAVE LINE'; } }
}

async function noLine(id) {
  if (workflowSubmitting[id]) return;
  workflowSubmitting[id] = true;
  try { await patch(id, { status: 'NO LINE - COMPLETED' }); showToast('NO LINE confirmed', 'success'); }
  catch (error) { showToast(error.message || 'Cannot update ticket', 'error'); }
  finally { workflowSubmitting[id] = false; }
}
