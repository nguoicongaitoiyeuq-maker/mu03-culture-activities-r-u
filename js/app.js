daySelect.onchange = () => {
  state.day = daySelect.value;
  renderAll();
};

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
