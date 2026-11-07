function renderAll() {
  renderKpis();
  renderSummary();
  renderRows();
  renderWorkflowPareto();
  renderInbox();
  renderConfirm();
  renderFamilies();
  refreshSla();
}

function applyState(session, tickets, familiesList) {
  state.user = session.user;
  state.displayName = session.display_name || session.user;
  state.today = session.today;
  state.role = session.role || 'MEMBER';
  state.canCreateTicket = session.can_create_ticket === true || CFM_EMAILS.has(String(session.user || '').trim().toLowerCase());
  state.canViewCfm = session.can_view_cfm === true || session.role === 'SHIFT_LEADER' || CFM_EMAILS.has(String(session.user || '').trim().toLowerCase());
  state.teamsConfigured = Boolean(session.teams_configured);
  state.tickets = tickets;
  state.families = familiesList;
  userPill.textContent = state.displayName;
  document.querySelectorAll('[data-page="create"], [data-new-ticket]').forEach((element) => element.classList.toggle('hidden', !state.canCreateTicket));
  document.querySelectorAll('[data-cfm-menu]').forEach((element) => element.classList.toggle('hidden', !state.canViewCfm));
  renderFamilyOptions();
  setAccountEmail(session.user);
  daySelect.innerHTML = '<option value="all">All dates</option>' + [...new Set(tickets.map((ticket) => ticket.day))].sort().reverse().map((day) => `<option value="${day}">${day}</option>`).join('');
  daySelect.value = state.day;
  renderAll();
}

function renderFamilyOptions() {
  const select = document.getElementById('family');
  if (!select) return;
  const current = select.value;
  const names = state.families
    .filter((name) => name !== 'Ban Văn Hóa')
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
    applyState(boot, boot.tickets || [], boot.families || []);
    return Promise.resolve();
  }
  return Promise.allSettled([api('/api/session'), api('/api/tickets'), api('/api/families')]).then((results) => {
    const sessionResult = results[0];
    if (sessionResult.status !== 'fulfilled') throw sessionResult.reason;
    applyState(sessionResult.value, results[1].status === 'fulfilled' ? results[1].value : [], results[2].status === 'fulfilled' ? results[2].value : []);
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

async function createTicket() {
  if (!state.canCreateTicket) {
    showToast('Your account is not allowed to create tickets.', 'error');
    return;
  }
  if (ticketSubmitting) return;
  const button = document.querySelector('#create .leader-actions .btn.primary');
  ticketSubmitting = true;
  if (button) { button.disabled = true; button.textContent = 'SENDING...'; }
  try {
    const ticket = await api('/api/tickets', { method: 'POST', body: JSON.stringify({ title: title.value, content: content.value, family: family.value, cause: 'General', media: state.media }) });
    clearForm();
    await load();
    showPage('dashboard');
    showToast(`Gửi ticket thành công: ${ticket.id}`, 'success');
  } catch (error) { showToast(error.message || 'Không thể tạo ticket', 'error'); }
  finally { ticketSubmitting = false; if (button) { button.disabled = false; button.textContent = 'SEND TICKET'; } }
}

function clearForm() {
  title.value = '';
  content.value = '';
  setAccountEmail(state.user);
  state.media = [];
  mediaPreview.innerHTML = '';
}

function patch(id, payload) {
  return api(`/api/tickets/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }).then(load);
}

function markRead(id) { patch(id, { status: 'READ' }); }

function closeTicket(id) { patch(id, { status: 'CLOSED' }); }

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
