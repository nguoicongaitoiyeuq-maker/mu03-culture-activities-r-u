const dayPicker = document.getElementById('dayPicker');
const clearDateBtn = document.getElementById('clearDateBtn');

function vietnamToday() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date()).reduce((result, part) => {
    if (part.type !== 'literal') result[part.type] = part.value;
    return result;
  }, {});
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function updateDateFilterUI() {
  const today = vietnamToday();
  if (dayPicker) {
    dayPicker.min = today;
    dayPicker.max = today;
  }
  if (state.day !== 'all' && state.day !== today) state.day = 'all';
  const active = state.day === today;
  if (dayPicker) dayPicker.value = active ? state.day : '';
  if (clearDateBtn) clearDateBtn.disabled = !active;
}

dayPicker?.addEventListener('change', () => {
  const today = vietnamToday();
  state.day = dayPicker.value === today ? today : 'all';
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
