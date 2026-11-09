function renderAll() {
  renderKpis();
  renderSummary();
  renderRows();
  renderData();
  renderWorkflowPareto();
  renderInbox();
  renderConfirm();
  renderFamilies();
  refreshSla();
}

function applyState(session, tickets, familiesList, dashboardTickets) {
  state.user = session.user;
  state.displayName = session.display_name || session.user;
  state.today = session.today;
  state.role = session.role || 'MEMBER';
  state.canCreateTicket = session.can_create_ticket === true || CFM_EMAILS.has(String(session.user || '').trim().toLowerCase());
  state.canViewCfm = session.can_view_cfm === true || session.role === 'SHIFT_LEADER' || CFM_EMAILS.has(String(session.user || '').trim().toLowerCase());
  state.canViewData = session.can_view_data === true;
  state.teamsConfigured = Boolean(session.teams_configured);
  state.tickets = tickets;
  state.dashboardTickets = dashboardTickets ?? tickets;
  state.families = familiesList;
  userPill.textContent = state.displayName;
  document.querySelectorAll('[data-page="create"], [data-new-ticket]').forEach((element) => element.classList.toggle('hidden', !state.canCreateTicket));
  document.querySelectorAll('[data-cfm-menu]').forEach((element) => element.classList.toggle('hidden', !state.canViewCfm));
  document.querySelectorAll('[data-page="data"]').forEach((element) => element.classList.toggle('hidden', !state.canViewData));
  renderFamilyOptions();
  setAccountEmail(session.user);
  const dayPicker = document.getElementById('dayPicker');
  if (dayPicker) updateDateFilterUI();
  renderAll();
  showPage(requestedPage());
}

function renderFamilyOptions() {
  const select = document.getElementById('family');
  if (!select) return;
  const current = select.value;
  const names = state.families
    .filter((name) => name !== 'Core Teams')
    .sort((left, right) => left === 'ALL MU03' ? -1 : right === 'ALL MU03' ? 1 : 0);
  select.innerHTML = '<option value="" disabled>Select a family model</option>' + names
    .map((name) => `<option value="${esc(name)}">${esc(name)}</option>`)
    .join('');
  select.value = names.includes(current) ? current : '';
}

function setAccountEmail(email) {
  const input = document.getElementById('ownerEmail');
  if (input) input.value = String(email || '').trim().toLowerCase();
}

let bootstrapUsed = false;

function load() {
  if (window.__BOOTSTRAP__ && !bootstrapUsed) {
    bootstrapUsed = true;
    const boot = window.__BOOTSTRAP__;
    applyState(boot, boot.tickets || [], boot.families || [], boot.dashboard_tickets || boot.tickets || []);
    return Promise.resolve();
  }
  return Promise.allSettled([api('/api/session'), api('/api/tickets'), api('/api/families'), api('/api/dashboard/tickets')]).then((results) => {
    const sessionResult = results[0];
    if (sessionResult.status !== 'fulfilled') throw sessionResult.reason;
    const tickets = results[1].status === 'fulfilled' ? results[1].value : [];
    const dashboardTickets = results[3].status === 'fulfilled' && Array.isArray(results[3].value) ? results[3].value : [];
    applyState(sessionResult.value, tickets, results[2].status === 'fulfilled' ? results[2].value : [], dashboardTickets);
  });
}

function showToast(message, kind) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.style.cssText = 'position:fixed;right:24px;bottom:24px;z-index:9999;padding:14px 18px;border-radius:10px;color:#fff;font-weight:700;box-shadow:0 8px 24px #0003;max-width:360px';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.background = kind === 'error' ? '#b42318' : '#137333';
  toast.style.display = 'block';
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => toast.style.display = 'none', 3200);
}

let ticketSubmitting = false;
let ticketSubmitOverlay;

function setTicketSubmitLoading(visible, message = 'Đang gửi ticket...') {
  if (!ticketSubmitOverlay) {
    ticketSubmitOverlay = document.createElement('div');
    ticketSubmitOverlay.id = 'ticketSubmitOverlay';
    ticketSubmitOverlay.setAttribute('role', 'status');
    ticketSubmitOverlay.setAttribute('aria-live', 'polite');
    ticketSubmitOverlay.innerHTML = '<div class="ticket-submit-card"><span class="ticket-submit-spinner" aria-hidden="true"></span><strong>Đang gửi ticket...</strong><span class="ticket-submit-copy"></span></div>';
    ticketSubmitOverlay.style.cssText = 'position:fixed;inset:0;z-index:10000;display:none;align-items:center;justify-content:center;background:rgba(15,23,42,.58);backdrop-filter:blur(3px);padding:24px;';
    const style = document.createElement('style');
    style.textContent = '.ticket-submit-card{display:flex;flex-direction:column;align-items:center;gap:12px;min-width:250px;padding:28px 32px;border-radius:16px;background:#fff;color:#172033;box-shadow:0 18px 50px #0005;text-align:center}.ticket-submit-card strong{font-size:16px}.ticket-submit-copy{font-size:13px;color:#667085}.ticket-submit-spinner{width:42px;height:42px;border:4px solid #e5e7eb;border-top-color:#b42318;border-radius:50%;animation:mu03-ticket-spin .8s linear infinite}@keyframes mu03-ticket-spin{to{transform:rotate(360deg)}}';
    document.head.appendChild(style);
    document.body.appendChild(ticketSubmitOverlay);
  }
  const copy = ticketSubmitOverlay.querySelector('.ticket-submit-copy');
  if (copy) copy.textContent = message;
  ticketSubmitOverlay.style.display = visible ? 'flex' : 'none';
}

async function createTicket() {
  if (!state.canCreateTicket) {
    showToast('Your account is not allowed to create tickets.', 'error');
    return;
  }
  if (ticketSubmitting) return;
  const button = document.querySelector('#create .leader-actions .btn.primary');
  ticketSubmitting = true;
  if (button) { button.disabled = true; button.textContent = 'SENDING...'; }
  setTicketSubmitLoading(true, 'Ticket đang được chuyển tới leader, vui lòng chờ trong giây lát.');
  try {
    const result = await api('/api/tickets', { method: 'POST', body: JSON.stringify({ title: title.value, content: content.value, family: family.value, cause: 'General', media: state.media }) });
    const createdTickets = Array.isArray(result.tickets) ? result.tickets : [result];
    const ticket = createdTickets[0];
    const sentCount = Number(result.count || createdTickets.length || 1);
    createdTickets.forEach((created) => applyTicketUpdate(created));
    clearForm();
    showPage('dashboard');
    showToast(sentCount > 1 ? `Gửi ticket thành công tới ${sentCount} leaders` : `Gửi ticket thành công: ${ticket.id}`, 'success');
    void load().catch((refreshError) => console.warn('Ticket list refresh failed after send', refreshError));
  } catch (error) { showToast(error.message || 'Không thể tạo ticket', 'error'); }
  finally { ticketSubmitting = false; setTicketSubmitLoading(false); if (button) { button.disabled = false; button.textContent = 'SEND TICKET'; } }
}

function clearForm() {
  title.value = '';
  content.value = '';
  setAccountEmail(state.user);
  state.media = [];
  mediaPreview.innerHTML = '';
}

function applyTicketUpdate(updated) {
  if (!updated?.id) return;
  const merge = (ticket) => ticket.id === updated.id ? { ...ticket, ...updated } : ticket;
  state.tickets = state.tickets.some((ticket) => ticket.id === updated.id)
    ? state.tickets.map(merge)
    : [...state.tickets, updated];
  state.dashboardTickets = state.dashboardTickets.some((ticket) => ticket.id === updated.id)
    ? state.dashboardTickets.map(merge)
    : [...state.dashboardTickets, updated];
  renderAll();
}

function patch(id, payload) {
  return api(`/api/tickets/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) })
    .then((updated) => { applyTicketUpdate(updated); return updated; });
}

function markRead(id) { patch(id, { status: 'READ' }); }

async function closeTicket(id) {
  const buttons = [...document.querySelectorAll('button[data-confirm-ticket]')].filter((button) => button.dataset.confirmTicket === id);
  if (buttons.some((button) => button.disabled)) return;
  buttons.forEach((button) => { button.disabled = true; button.textContent = 'CLOSING...'; });
  try {
    await patch(id, { status: 'CLOSED' });
    showToast('Ticket closed successfully', 'success');
  } catch (error) {
    showToast(error.message || 'Cannot close ticket', 'error');
    buttons.forEach((button) => { button.disabled = false; button.textContent = 'CONFIRM & CLOSE'; });
  }
}

mediaInput.onchange = (event) => {
  [...event.target.files].slice(0, 6).forEach((file) => {
    const reader = new FileReader();
    reader.onload = () => {
      state.media.push({ name: file.name, type: file.type, data: reader.result });
      mediaPreview.innerHTML = state.media.map((media) => `<div class="media">${media.type.startsWith('video') ? `<video controls src="${media.data}"></video>` : `<img src="${media.data}">`}<span>${esc(media.name)}</span></div>`).join('');
    };
    reader.readAsDataURL(file);
  });
  event.target.value = '';
};
