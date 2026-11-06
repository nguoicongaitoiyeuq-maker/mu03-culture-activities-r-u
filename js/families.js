let configuredMembers = [];

function renderFamilies() {
  family.innerHTML = state.families.map((item) => `<option>${esc(item)}</option>`).join('');
  families.innerHTML = state.families.map((item) => `<span class="family">${esc(item)} <button onclick="removeFamily('${esc(item)}')">×</button></span>`).join('');
  if (typeof familyManage === 'undefined') return;
  const previous = familyManage.value;
  familyManage.innerHTML = state.families.map((item) => `<option>${esc(item)}</option>`).join('');
  familyManage.value = state.families.includes(previous) ? previous : (state.families[0] || '');
  loadMembers();
}

function renderMembers() {
  if (typeof familyMembers === 'undefined') return;
  const roleLabel = (role) => role === 'SHIFT_LEADER' ? 'Shift leader' : 'Leader khu vực';
  familyMembers.innerHTML = configuredMembers.length
    ? configuredMembers.map((member) => `<span class="family">${esc(member.display_name || member.email)} · ${esc(member.email)} · ${roleLabel(member.role)} <button onclick="removeMember('${esc(member.email)}')">×</button></span>`).join('')
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
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members`, { method: 'POST', body: JSON.stringify({ email, display_name: memberProfile.dataset.displayName || '', role: memberRole.value }) })
    .then(() => { memberEmail.value = ''; loadMembers(); })
    .catch((error) => showToast(error.message || 'Cannot add member', 'error'));
}

function removeMember(email) {
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members/${encodeURIComponent(email)}`, { method: 'DELETE' }).then(loadMembers);
}

if (typeof familyManage !== 'undefined') familyManage.onchange = loadMembers;

async function lookupMemberProfile() {
  const email = memberEmail.value.trim().toLowerCase();
  if (!email || !email.includes('@')) return;
  try {
    const profile = await api(`/api/directory/lookup?email=${encodeURIComponent(email)}`);
    memberProfile.dataset.displayName = profile.display_name || email;
    memberProfile.textContent = `Teams profile: ${profile.display_name || email}`;
  } catch (error) {
    memberProfile.dataset.displayName = '';
    memberProfile.textContent = error.message || 'Profile not found';
  }
}

if (typeof memberEmail !== 'undefined') memberEmail.addEventListener('blur', lookupMemberProfile);
