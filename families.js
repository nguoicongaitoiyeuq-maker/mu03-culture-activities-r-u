let configuredMembers = [];

function memberName(member) {
  return member.display_name && member.display_name.toLowerCase() !== member.email.toLowerCase() ? member.display_name : member.email;
}

function roleLabel(role) {
  return role === 'SHIFT_LEADER' ? 'Shift leader' : 'Leader';
}

function renderFamilies() {
  if (typeof memberEmail !== 'undefined') memberEmail.value = '';
  if (typeof managedBy !== 'undefined') managedBy.value = '';
  if (typeof memberProfile !== 'undefined') { memberProfile.textContent = ''; memberProfile.dataset.displayName = ''; }
  const visibleFamilies = state.families.filter((item) => item !== 'ALL MU03');
  family.innerHTML = visibleFamilies.map((item) => `<option value="${esc(item)}">${esc(item)}</option>`).join('') + '<option value="ALL MU03">All groups (MU03)</option>';
  families.innerHTML = visibleFamilies.map((item) => `<span class="family">${esc(item)} <button onclick="removeFamily('${esc(item)}')">×</button></span>`).join('');
  if (typeof familyManage === 'undefined') return;
  const previous = familyManage.value;
  familyManage.innerHTML = visibleFamilies.map((item) => `<option>${esc(item)}</option>`).join('');
  familyManage.value = visibleFamilies.includes(previous) ? previous : (visibleFamilies[0] || '');
  loadMembers();
  loadFamilyOverview();
}

async function loadFamilyOverview() {
  if (typeof familyOverview === 'undefined') return;
  const groups = await Promise.all(state.families.filter((name) => name !== 'ALL MU03').map(async (name) => ({ name, members: await api(`/api/families/${encodeURIComponent(name)}/members`).catch(() => []) })));
  familyOverview.innerHTML = groups.map((group) => {
    const shifts = group.members.filter((member) => member.role === 'SHIFT_LEADER');
    const leaders = group.members.filter((member) => member.role === 'AREA_LEADER');
    const shiftCards = shifts.map((shift) => `<div class="group-member"><b>${esc(memberName(shift))}</b><small>${esc(shift.email)}</small><em>${esc(shift.title || 'Shift leader')}</em><div class="reports">${leaders.filter((leader) => (leader.managed_by || '').toLowerCase() === shift.email.toLowerCase()).map((leader) => `<span>${esc(memberName(leader))} · ${esc(leader.title || 'Leader')}</span>`).join('') || '<span>No area leaders assigned</span>'}</div></div>`).join('');
    const unassigned = leaders.filter((leader) => !(leader.managed_by || '').trim()).map((leader) => `<div class="group-member"><b>${esc(memberName(leader))}</b><small>${esc(leader.email)}</small><em>${esc(leader.title || 'Leader')}</em></div>`).join('');
    return `<article class="group-card"><h4>${esc(group.name)}</h4><div class="group-count">${group.members.length} configured leader${group.members.length === 1 ? '' : 's'}</div><div class="group-members">${shiftCards}${unassigned || (!shiftCards ? '<span class="meta">No leaders configured</span>' : '')}</div></article>`;
  }).join('');
}

function renderMembers() {
  if (typeof familyMembers === 'undefined') return;
  familyMembers.innerHTML = configuredMembers.length
    ? configuredMembers.map((member) => `<span class="family"><b>${esc(memberName(member))}</b> · ${esc(member.email)} · ${esc(member.title || roleLabel(member.role))}${member.role === 'AREA_LEADER' ? ` · managed by ${esc(member.managed_by || 'not assigned')}` : ''} <button onclick="removeMember('${esc(member.email)}')">×</button></span>`).join('')
    : '<span class="meta">No leaders configured for this group.</span>';
  renderManagedByOptions();
}

function renderManagedByOptions() {
  if (typeof managedBy === 'undefined') return;
  if (typeof managedByField !== 'undefined') managedByField.classList.toggle('hidden', memberRole.value === 'SHIFT_LEADER');
  if (memberRole.value === 'SHIFT_LEADER') {
    managedBy.value = '';
    if (typeof managedByProfile !== 'undefined') managedByProfile.textContent = '';
  }
  if (typeof memberEmail !== 'undefined') {
    memberEmail.value = '';
    memberEmail.removeAttribute('readonly');
    memberEmail.placeholder = memberRole.value === 'SHIFT_LEADER' ? 'Shift leader company email' : 'Leader company email';
  }
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
  if (memberRole.value === 'AREA_LEADER' && !managedBy.value.trim()) { showToast('Enter the Shift Leader email', 'error'); return; }
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members`, { method: 'POST', body: JSON.stringify({ email, display_name: memberProfile.dataset.displayName || '', role: memberRole.value, managed_by: managedBy.value.trim().toLowerCase() }) })
    .then(() => { memberEmail.value = ''; memberProfile.textContent = ''; memberProfile.dataset.displayName = ''; loadMembers(); })
    .catch((error) => showToast(error.message || 'Cannot add leader', 'error'));
}

function removeMember(email) {
  api(`/api/families/${encodeURIComponent(familyManage.value)}/members/${encodeURIComponent(email)}`, { method: 'DELETE' }).then(loadMembers);
}

if (typeof familyManage !== 'undefined') familyManage.onchange = loadMembers;
if (typeof memberRole !== 'undefined') memberRole.onchange = renderManagedByOptions;

async function lookupProfile(email, target) {
  if (!email || !email.includes('@')) return;
  try {
    const profile = await api(`/api/directory/lookup?email=${encodeURIComponent(email)}`);
    target.dataset.displayName = profile.display_name || email;
    target.textContent = `${profile.display_name || email}${profile.title ? ` · ${profile.title}` : ''}`;
  } catch (error) {
    target.dataset.displayName = '';
    target.textContent = error.message || 'Profile not found';
  }
}

async function lookupMemberProfile() {
  const email = memberEmail.value.trim().toLowerCase();
  lookupProfile(email, memberProfile);
}

if (typeof memberEmail !== 'undefined') memberEmail.addEventListener('blur', lookupMemberProfile);
if (typeof managedBy !== 'undefined') managedBy.addEventListener('blur', () => lookupProfile(managedBy.value.trim().toLowerCase(), managedByProfile));
