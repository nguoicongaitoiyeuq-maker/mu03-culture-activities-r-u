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
  if (ticket && ticket.status === 'WAITING FOR LEADER READ') patch(id, { status: 'READ' }).catch((error) => showToast(error.message || 'Không thể đánh dấu READ', 'error'));
}

function showHaveLine(id) {
  const panel = document.getElementById(`have-line-${id}`);
  if (panel) panel.classList.remove('hidden');
}

function renderInbox() {
  const items = state.tickets.filter((ticket) => ticket.status !== 'CLOSED' && !ticket.status.includes('COMPLETED'));
  inboxCount.textContent = `${items.length} open`;
  inboxList.innerHTML = items.length ? items.map((ticket) => {
    const expanded = expandedTickets[ticket.id] || ticket.status !== 'WAITING FOR LEADER READ';
    const canChoose = ticket.status === 'READ' || ticket.status === 'WAITING FOR LINE SHARING';
    return `<article class="leader-card ${expanded ? 'ticket-open' : 'ticket-collapsed'}"><div class="ticket-header"><div><div class="ticket-kicker">Leader review ticket</div><h3>${esc(ticket.title)}</h3><div class="meta">${esc(ticket.id)} · ${esc(ticket.family)} · ${badge(ticket.status)}</div></div></div>${expanded ? `<div class="ticket-details"><div class="leader-content">${esc(ticket.content)}</div><div class="ticket-facts"><div class="ticket-fact"><span>Sender / Department</span><b>${esc(ticket.department || '—')}</b></div><div class="ticket-fact"><span>Leader</span><b>${esc(ticket.leader || 'Leader Inbox')}</b></div><div class="ticket-fact"><span>Cause</span><b>${esc(ticket.cause || 'General')}</b></div><div class="ticket-fact"><span>Created</span><b>${new Date(ticket.sent_at).toLocaleString('vi-VN')}</b></div></div>${ticket.media?.length ? `<div class="leader-media">${mediaHtml(ticket.media, true)}</div>` : ''}${canChoose ? `<div class="workflow-step"><span class="step-label">Step 2 · Leader decision</span><div class="leader-choice"><button class="btn danger-outline" onclick="noLine('${ticket.id}')">NO LINE</button><button class="btn green" onclick="showHaveLine('${ticket.id}')">HAVE LINE</button></div><div id="have-line-${ticket.id}" class="leader-actions hidden"><div class="field"><label>Line ID *</label><input id="line-${ticket.id}" placeholder="Enter line ID" required></div><div class="evidence-box"><label>Evidence image / video *</label><input class="leader-media-input" data-id="${ticket.id}" type="file" accept="image/*,video/*" multiple><div class="meta">Evidence image/video is optional.</div></div><div id="leader-preview-${ticket.id}" class="leader-preview"></div><button class="btn green" onclick="completeSharing('${ticket.id}')">SUBMIT HAVE LINE</button></div></div>` : '<div class="notice section-space">Ticket has been opened and marked READ. Choose the next workflow step above.</div>'}</div>` : `<div class="ticket-summary"><p>Click to open the ticket and read all production details.</p><button class="btn primary" onclick="openTicket('${ticket.id}')">OPEN &amp; READ</button></div>`}</article>`;
  }).join('') : '<div class="panel empty">No open tickets waiting for leader action.</div>';
  bindLeaderMedia();
}

function renderConfirm() {
  const items = state.tickets.filter((ticket) => ticket.status.includes('COMPLETED'));
  confirmList.innerHTML = items.length ? items.map((ticket) => `<article class="leader-card"><h3>${esc(ticket.title)}</h3><div class="meta">${esc(ticket.id)} · ${esc(ticket.family)} · ${badge(ticket.status)}</div><div class="leader-content">${esc(ticket.content)}</div><div class="leader-actions"><button class="btn green" onclick="closeTicket('${ticket.id}')">CONFIRM & CLOSE</button></div></article>`).join('') : '<div class="panel empty">Nothing is waiting for confirmation.</div>';
}

let workflowSubmitting = {};

async function completeSharing(id) {
  if (workflowSubmitting[id]) return;
  const line = (document.getElementById(`line-${id}`)?.value || '').trim();
  if (!line) { showToast('Vui lòng nhập Line ID', 'error'); return; }
  const button = document.querySelector(`#have-line-${CSS.escape(id)} button`);
  workflowSubmitting[id] = true;
  if (button) { button.disabled = true; button.textContent = 'SUBMITTING...'; }
  try { await patch(id, { status: 'LINE SHARING COMPLETED', line_id: line, media: leaderMedia[id] || [] }); showToast('Đã submit HAVE LINE thành công', 'success'); }
  catch (error) { showToast(error.message || 'Không thể submit HAVE LINE', 'error'); }
  finally { workflowSubmitting[id] = false; if (button) { button.disabled = false; button.textContent = 'SUBMIT HAVE LINE'; } }
}

async function noLine(id) {
  if (workflowSubmitting[id]) return;
  workflowSubmitting[id] = true;
  try { await patch(id, { status: 'NO LINE - COMPLETED' }); showToast('Đã xác nhận NO LINE', 'success'); }
  catch (error) { showToast(error.message || 'Không thể cập nhật ticket', 'error'); }
  finally { workflowSubmitting[id] = false; }
}
