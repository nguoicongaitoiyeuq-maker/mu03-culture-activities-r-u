function renderFamilies() {
  family.innerHTML = '<option>ALL MU03</option>' + state.families.map((item) => `<option>${esc(item)}</option>`).join('');
  families.innerHTML = state.families.map((item) => `<span class="family">${esc(item)} <button onclick="removeFamily('${esc(item)}')">×</button></span>`).join('');
}

function addFamily() {
  if (!newFamily.value.trim()) return;
  api('/api/families', { method: 'POST', body: JSON.stringify({ name: newFamily.value }) }).then(() => { newFamily.value = ''; load(); });
}

function removeFamily(name) {
  api(`/api/families/${encodeURIComponent(name)}`, { method: 'DELETE' }).then(load);
}
