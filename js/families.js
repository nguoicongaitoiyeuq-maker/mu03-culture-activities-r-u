let configuredMembers = [];

function renderFamilies() {
  family.innerHTML = '<option>ALL MU03</option>' + state.families.map((item) => `<option>${esc(item)}</option>`).join('');
  families.innerHTML = state.families.map((item) => `<span class="family">${esc(item)} <button onclick="removeFamily('${esc(item)}')">×</button></span>`).join('');
  if (typeof familyManage === 'undefined') return;
  const previous = familyManage.value;
  familyManage.innerHTML = state.families.map((item) => `<option>${esc(item)}</option>`).join('');
  familyManage.value = state.families.includes(previous) ? previous : (state.families[0] || '');
  loadMembers();
}

function renderMembers() {
  if (typeof familyMembers === 'undefined') return;
  familyMembers.innerHTML = configuredMembers.length
    ? configuredMembers.map((member) => `<span class="family">${esc(member.email)} · ${esc(member.role)} <button onclick="removeMember('${esc(member.email)}')">×</button></span>`).join('')
    : '<span class="meta">No members configured for this family.</span>';
}

function loadMembers() {
  if (typeof familyManage === 'undefined' || !familyManage.value) return;
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members`).then((members) => { configuredMembers = members; renderMembers(); }).catch(() => { configuredMembers = []; renderMembers(); });
}

function addFamily() {
  if (!newFamily.value.trim()) return;
  api('/api/families', { method: 'POST', body: JSON.stringify({ name: newFamily.value }) }).then(() => { newFamily.value = ''; load(); });
}

function removeFamily(name) {
  api(`/api/families/${encodeURIComponent(name)}`, { method: 'DELETE' }).then(load);
}

function addMember() {
  const email = memberEmail.value.trim().toLowerCase();
  if (!familyManage.value || !email) return;
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members`, { method: 'POST', body: JSON.stringify({ email, role: memberRole.value }) })
    .then(() => { memberEmail.value = ''; loadMembers(); })
    .catch((error) => showToast(error.message || 'Cannot add member', 'error'));
}

function removeMember(email) {
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members/${encodeURIComponent(email)}`, { method: 'DELETE' }).then(loadMembers);
}

if (typeof familyManage !== 'undefined') familyManage.onchange = loadMembers;
