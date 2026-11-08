const dayPicker = document.getElementById('dayPicker');
const clearDateBtn = document.getElementById('clearDateBtn');

function updateDateFilterUI() {
  const active = state.day && state.day !== 'all';
  const status = document.getElementById('dateFilterState');
  if (status) status.textContent = active ? state.day.split('-').reverse().join('/') : 'Any date';
  if (dayPicker) dayPicker.value = active ? state.day : '';
  if (clearDateBtn) clearDateBtn.disabled = !active;
}

dayPicker?.addEventListener('change', () => {
  state.day = dayPicker.value || 'all';
  updateDateFilterUI();
  renderAll();
});

clearDateBtn?.addEventListener('click', () => {
  state.day = 'all';
  updateDateFilterUI();
  renderAll();
});

updateDateFilterUI();

document.getElementById('dataExportBtn')?.addEventListener('click', () => {
  const day = encodeURIComponent(state.day || 'all');
  window.location.href = `/api/tickets/export?day=${day}`;
});

let galleryIndex = 0;
setInterval(() => {
  const track = document.getElementById('galleryTrack');
  if (!track) return;
  galleryIndex = (galleryIndex + 1) % 6;
  track.style.transform = `translateX(-${galleryIndex * (100 / 5 + 2.4)}%)`;
}, 2200);

let dashIndex = 0;
setInterval(() => {
  const track = document.getElementById('dashboardTrack');
  if (!track) return;
  dashIndex = 0;
  track.style.transform = `translateX(-${dashIndex * 100}%)`;
}, 3000);

setInterval(refreshSla, 1000);
load().catch((error) => {
  userPill.textContent = 'Connection unavailable';
  console.error(error);
});
