let selectedFamily = '';
let familyMemberCache = {};
let familyLoadToken = 0;

function memberName(member) {
  const name = String(member.display_name || '').trim();
  return name && name.toLowerCase() !== String(member.email || '').toLowerCase() ? name : member.email;
}

function roleLabel(role) {
  return role === 'SHIFT_LEADER' ? 'Shift leader' : 'Leader';
}

function initials(name) {
  return String(name || '?').split(/\s+/).filter(Boolean).slice(-2).map((part) => part[0]).join('').toUpperCase() || '?';
}

function familyNames() {
  return state.families.filter((name) => name !== 'ALL MU03');
}

function renderFamilies() {
  if (typeof familyOverview === 'undefined') return;
  loadFamilyOverview();
}

function renderGroupCards(groups) {
  if (!groups.length) {
    familyOverview.innerHTML = '<div class="panel empty">No groups configured.</div>';
    return;
  }
  familyOverview.innerHTML = groups.map((group, index) => {
    const shifts = group.members.filter((member) => member.role === 'SHIFT_LEADER');
    const preview = shifts.length
      ? shifts.slice(0, 2).map((shift) => `<span><b>Owner</b>${esc(memberName(shift))}</span>`).join('')
      : '<span>No shift leader assigned</span>';
    return `<button type="button" class="group-card" onclick="selectFamily('${esc(group.name)}')"><div class="group-card-top"><span>Group ${String(index + 1).padStart(2, '0')}</span><span class="group-open">Open roster →</span></div><h4>${esc(group.name)}</h4><div class="group-count">${group.members.length} configured members</div><div class="group-roster-preview">${preview}</div></button>`;
  }).join('');
}

function renderFamilyDetail(name, members) {
  if (typeof familyDetail === 'undefined') return;
  const shifts = members.filter((member) => member.role === 'SHIFT_LEADER');
  const leaders = members.filter((member) => member.role !== 'SHIFT_LEADER');
  const assigned = new Set();
  const tree = shifts.map((shift) => {
    const reports = leaders.filter((leader) => (leader.managed_by || '').toLowerCase() === shift.email.toLowerCase());
    reports.forEach((leader) => assigned.add(leader.email.toLowerCase()));
    return `<article class="owner-card"><div class="owner-card-head"><span class="owner-avatar">${esc(initials(memberName(shift)))}</span><div><h4>${esc(memberName(shift))}</h4><div class="meta">${esc(shift.email)}</div><span class="owner-title">${esc(shift.title || roleLabel(shift.role))}</span></div></div><div class="report-list">${reports.length ? reports.map((leader) => `<div class="report-row"><div><b>${esc(memberName(leader))}</b><small>${esc(leader.email)}</small><em>${esc(leader.title || roleLabel(leader.role))}</em></div></div>`).join('') : '<div class="unassigned-note">No leaders assigned to this owner.</div>'}</div></article>`;
  }).join('');
  const unassigned = leaders.filter((leader) => !assigned.has(leader.email.toLowerCase()) && !(leader.managed_by || '').trim());
  familyDetail.innerHTML = `<div class="group-detail-head"><div><h3>${esc(name)}</h3><p>Member roster and reporting ownership</p></div><span class="group-detail-badge">${members.length} members · ${shifts.length} owners</span></div><div class="group-tree">${tree || '<div class="unassigned-note">No shift leader configured for this group.</div>'}</div>${unassigned.length ? `<div class="unassigned-note">Unassigned leaders: ${unassigned.map((leader) => esc(memberName(leader))).join(', ')}</div>` : ''}`;
  familyDetail.classList.remove('hidden');
}

async function selectFamily(name) {
  selectedFamily = name;
  const cached = familyMemberCache[name];
  if (cached) {
    renderFamilyDetail(name, cached);
    familyDetail.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }
  if (typeof familyDetail !== 'undefined') {
    familyDetail.classList.remove('hidden');
    familyDetail.innerHTML = '<div class="unassigned-note">Loading group roster...</div>';
  }
  try {
    const members = await api(`/api/families/${encodeURIComponent(name)}/members`);
    familyMemberCache[name] = members;
    if (selectedFamily === name) renderFamilyDetail(name, members);
  } catch (error) {
    if (typeof familyDetail !== 'undefined') familyDetail.innerHTML = `<div class="unassigned-note">${esc(error.message || 'Unable to load this group.')}</div>`;
  }
  if (typeof familyDetail !== 'undefined') familyDetail.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadFamilyOverview() {
  if (typeof familyOverview === 'undefined') return;
  const token = ++familyLoadToken;
  const names = familyNames();
  const status = typeof groupsStatus !== 'undefined' ? groupsStatus : null;
  if (status) status.textContent = 'Loading groups';
  familyOverview.innerHTML = names.map(() => '<div class="group-card"><div class="group-card-top"><span>Loading</span></div><h4>Loading group...</h4><div class="group-count">Preparing member roster</div></div>').join('');
  const groups = await Promise.all(names.map(async (name) => {
    try {
      const members = await api(`/api/families/${encodeURIComponent(name)}/members`);
      familyMemberCache[name] = members;
      return { name, members };
    } catch (error) {
      return { name, members: [] };
    }
  }));
  if (token !== familyLoadToken) return;
  renderGroupCards(groups);
  if (status) status.textContent = `${groups.length} groups ready`;
  if (selectedFamily && familyMemberCache[selectedFamily]) renderFamilyDetail(selectedFamily, familyMemberCache[selectedFamily]);
}
