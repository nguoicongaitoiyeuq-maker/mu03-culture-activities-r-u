let selectedFamily = '';
let familyMemberCache = {};
let familyLoadToken = 0;
let groupsVisible = true;
let familyDetailOpen = true;

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
  if (!document.getElementById('familyOverview')) return;
  loadFamilyOverview();
}

function renderGroupCards(groups) {
  const overview = document.getElementById('familyOverview');
  if (!overview) return;
  if (!groups.length) {
    overview.innerHTML = '<div class="panel empty">No groups configured.</div>';
    return;
  }
  overview.innerHTML = groups.map((group, index) => {
    const shifts = group.members.filter((member) => member.role === 'SHIFT_LEADER');
    const preview = shifts.length
      ? shifts.slice(0, 2).map((shift) => `<span><b>Owner</b>${esc(memberName(shift))}</span>`).join('')
      : '<span>No shift leader assigned</span>';
    return `<button type="button" class="group-card" onclick="selectFamily('${esc(group.name)}')"><div class="group-card-top"><span>Group ${String(index + 1).padStart(2, '0')}</span><span class="group-open">Open roster →</span></div><h4>${esc(group.name)}</h4><div class="group-count">${group.members.length} configured members</div><div class="group-roster-preview">${preview}</div></button>`;
  }).join('');
}

function renderFamilyDetail(name, members) {
  const detail = document.getElementById('familyDetail');
  if (!detail) return;
  familyDetailOpen = true;
  const shifts = members.filter((member) => member.role === 'SHIFT_LEADER');
  const leaders = members.filter((member) => member.role !== 'SHIFT_LEADER');
  if (!shifts.length) {
    detail.innerHTML = `<div class="group-detail-head"><div><h3>${esc(name)}</h3><p>Member roster</p></div><div class="group-detail-head-actions"><span class="group-detail-badge">${members.length} members</span><button type="button" class="btn detail-toggle" onclick="toggleFamilyDetail()" aria-expanded="true" title="Hide or show members"><span aria-hidden="true">⌃</span><span>Hide members</span></button></div></div><div id="familyDetailBody" class="member-roster">${members.map((member) => `<div class="report-row"><div><b>${esc(memberName(member))}</b><small>${esc(member.email)}</small><em>${esc(member.title || roleLabel(member.role))}</em></div></div>`).join('')}</div>`;
    detail.classList.remove('hidden');
    return;
  }
  const assigned = new Set();
  const tree = shifts.map((shift) => {
    const reports = leaders.filter((leader) => (leader.managed_by || '').toLowerCase() === shift.email.toLowerCase());
    reports.forEach((leader) => assigned.add(leader.email.toLowerCase()));
    return `<article class="owner-card"><div class="owner-card-head"><span class="owner-avatar">${esc(initials(memberName(shift)))}</span><div><h4>${esc(memberName(shift))}</h4><div class="meta">${esc(shift.email)}</div><span class="owner-title">${esc(shift.title || roleLabel(shift.role))}</span></div></div><div class="report-list">${reports.length ? reports.map((leader) => `<div class="report-row"><div><b>${esc(memberName(leader))}</b><small>${esc(leader.email)}</small><em>${esc(leader.title || roleLabel(leader.role))}</em></div></div>`).join('') : '<div class="unassigned-note">No leaders assigned to this owner.</div>'}</div></article>`;
  }).join('');
  const unassigned = leaders.filter((leader) => !assigned.has(leader.email.toLowerCase()) && !(leader.managed_by || '').trim());
  detail.innerHTML = `<div class="group-detail-head"><div><h3>${esc(name)}</h3><p>Member roster and reporting ownership</p></div><div class="group-detail-head-actions"><span class="group-detail-badge">${members.length} members · ${shifts.length} owners</span><button type="button" class="btn detail-toggle" onclick="toggleFamilyDetail()" aria-expanded="true" title="Hide or show members"><span aria-hidden="true">⌃</span><span>Hide members</span></button></div></div><div id="familyDetailBody" class="group-tree">${tree || '<div class="unassigned-note">No shift leader configured for this group.</div>'}</div>${unassigned.length ? `<div id="familyDetailUnassigned" class="unassigned-note">Unassigned leaders: ${unassigned.map((leader) => esc(memberName(leader))).join(', ')}</div>` : ''}`;
  detail.classList.remove('hidden');
}

function toggleGroups() {
  const overview = document.getElementById('familyOverview');
  const detail = document.getElementById('familyDetail');
  const button = document.getElementById('toggleGroupsBtn');
  groupsVisible = !groupsVisible;
  overview?.classList.toggle('hidden', !groupsVisible);
  if (!groupsVisible) detail?.classList.add('hidden');
  if (button) {
    button.setAttribute('aria-expanded', String(groupsVisible));
    button.innerHTML = `<span aria-hidden="true">${groupsVisible ? '⌃' : '⌄'}</span><span>${groupsVisible ? 'Hide groups' : 'Show groups'}</span>`;
  }
}

function toggleFamilyDetail() {
  const body = document.getElementById('familyDetailBody');
  const unassigned = document.getElementById('familyDetailUnassigned');
  const button = document.querySelector('.detail-toggle');
  familyDetailOpen = !familyDetailOpen;
  body?.classList.toggle('hidden', !familyDetailOpen);
  unassigned?.classList.toggle('hidden', !familyDetailOpen);
  if (button) {
    button.setAttribute('aria-expanded', String(familyDetailOpen));
    button.innerHTML = `<span aria-hidden="true">${familyDetailOpen ? '⌃' : '⌄'}</span><span>${familyDetailOpen ? 'Hide members' : 'Show members'}</span>`;
  }
}

async function selectFamily(name) {
  selectedFamily = name;
  const cached = familyMemberCache[name];
  const detail = document.getElementById('familyDetail');
  if (cached) {
    renderFamilyDetail(name, cached);
    detail?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }
  if (detail) {
    detail.classList.remove('hidden');
    detail.innerHTML = '<div class="unassigned-note">Loading group roster...</div>';
  }
  try {
    const members = await api(`/api/families/${encodeURIComponent(name)}/members`);
    familyMemberCache[name] = members;
    if (selectedFamily === name) renderFamilyDetail(name, members);
  } catch (error) {
    if (detail) detail.innerHTML = `<div class="unassigned-note">${esc(error.message || 'Unable to load this group.')}</div>`;
  }
  detail?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadFamilyOverview() {
  const overview = document.getElementById('familyOverview');
  if (!overview) return;
  const token = ++familyLoadToken;
  const names = familyNames();
  const status = document.getElementById('groupsStatus');
  if (status) status.textContent = 'Loading groups';
  overview.innerHTML = names.map(() => '<div class="group-card"><div class="group-card-top"><span>Loading</span></div><h4>Loading group...</h4><div class="group-count">Preparing member roster</div></div>').join('');
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
  if (!selectedFamily && groups.length) selectedFamily = groups[0].name;
  if (selectedFamily && familyMemberCache[selectedFamily]) renderFamilyDetail(selectedFamily, familyMemberCache[selectedFamily]);
}
