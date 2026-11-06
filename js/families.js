let configuredMembers = [];

function memberName(member) {
  return member.display_name && member.display_name.toLowerCase() !== member.email.toLowerCase() ? member.display_name : member.email;
}

function roleLabel(role) {
  return role === 'SHIFT_LEADER' ? 'Shift leader' : 'Leader khu vực';
}

function renderFamilies() {
  family.innerHTML = state.families.map((item) => `<option>${esc(item)}</option>`).join('');
  families.innerHTML = state.families.map((item) => `<span class="family">${esc(item)} <button onclick="removeFamily('${esc(item)}')">×</button></span>`).join('');
  if (typeof familyManage === 'undefined') return;
  const previous = familyManage.value;
  familyManage.innerHTML = state.families.map((item) => `<option>${esc(item)}</option>`).join('');
  familyManage.value = state.families.includes(previous) ? previous : (state.families[0] || '');
  loadMembers();
  loadFamilyOverview();
}

async function loadFamilyOverview() {
  if (typeof familyOverview === 'undefined') return;
  const groups = await Promise.all(state.families.map(async (name) => ({ name, members: await api(`/api/families/${encodeURIComponent(name)}/members`).catch(() => []) })));
  familyOverview.innerHTML = groups.map((group) => {
    const shifts = group.members.filter((member) => member.role === 'SHIFT_LEADER');
    const leaders = group.members.filter((member) => member.role === 'AREA_LEADER');
    const shiftCards = shifts.map((shift) => `<div class="group-member"><b>${esc(memberName(shift))}</b><small>${esc(shift.email)}</small><em>Shift leader</em><div class="reports">${leaders.filter((leader) => (leader.managed_by || '').toLowerCase() === shift.email.toLowerCase()).map((leader) => `<span>${esc(memberName(leader))}</span>`).join('') || '<span>No area leaders assigned</span>'}</div></div>`).join('');
    const unassigned = leaders.filter((leader) => !(leader.managed_by || '').trim()).map((leader) => `<div class="group-member"><b>${esc(memberName(leader))}</b><small>${esc(leader.email)}</small><em>Unassigned area leader</em></div>`).join('');
    return `<article class="group-card"><h4>${esc(group.name)}</h4><div class="group-count">${group.members.length} configured leader${group.members.length === 1 ? '' : 's'}</div><div class="group-members">${shiftCards}${unassigned || (!shiftCards ? '<span class="meta">No leaders configured</span>' : '')}</div></article>`;
  }).join('');
}

function renderMembers() {
  if (typeof familyMembers === 'undefined') return;
  familyMembers.innerHTML = configuredMembers.length
    ? configuredMembers.map((member) => `<span class="family"><b>${esc(memberName(member))}</b> · ${esc(member.email)} · ${roleLabel(member.role)}${member.role === 'AREA_LEADER' ? ` · managed by ${esc(member.managed_by || 'not assigned')}` : ''} <button onclick="removeMember('${esc(member.email)}')">×</button></span>`).join('')
    : '<span class="meta">No leaders configured for this group.</span>';
  renderManagedByOptions();
}

function renderManagedByOptions() {
  if (typeof managedBy === 'undefined') return;
  const shifts = configuredMembers.filter((member) => member.role === 'SHIFT_LEADER');
  managedBy.innerHTML = shifts.length ? shifts.map((member) => `<option value="${esc(member.email)}">${esc(memberName(member))} · ${esc(member.email)}</option>`).join('') : '<option value="">Add a Shift Leader first</option>';
  if (typeof managedByField !== 'undefined') managedByField.classList.toggle('hidden', memberRole.value === 'SHIFT_LEADER');
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
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members`, { method: 'POST', body: JSON.stringify({ email, display_name: memberProfile.dataset.displayName || '', role: memberRole.value, managed_by: managedBy.value }) })
    .then(() => { memberEmail.value = ''; memberProfile.textContent = 'Enter a company email to look up the Teams profile.'; loadMembers(); })
    .catch((error) => showToast(error.message || 'Cannot add leader', 'error'));
}

function removeMember(email) {
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members/${encodeURIComponent(email)}`, { method: 'DELETE' }).then(loadMembers);
}

if (typeof familyManage !== 'undefined') familyManage.onchange = loadMembers;
if (typeof memberRole !== 'undefined') memberRole.onchange = renderManagedByOptions;

async function lookupMemberProfile() {
  const email = memberEmail.value.trim().toLowerCase();
  if (!email || !email.includes('@')) return;
  try {
    const profile = await api(`/api/directory/lookup?email=${encodeURIComponent(email)}`);
    memberProfile.dataset.displayName = profile.display_name || email;
    memberProfile.textContent = profile.source === 'microsoft-graph' ? `Teams profile: ${profile.display_name || email}` : `Teams profile pending: ${profile.display_name || email} (Microsoft Graph permission required for the official name)`;
  } catch (error) {
    memberProfile.dataset.displayName = '';
    memberProfile.textContent = error.message || 'Profile not found';
  }
}

if (typeof memberEmail !== 'undefined') memberEmail.addEventListener('blur', lookupMemberProfile);
