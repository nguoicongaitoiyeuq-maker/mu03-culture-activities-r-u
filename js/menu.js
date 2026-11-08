function showPage(id) {
  if (id === 'confirmation' && !state.canViewCfm) id = 'dashboard';
  if (id === 'data' && !state.canViewData) id = 'dashboard';
  document.querySelectorAll('.page').forEach((page) => page.classList.toggle('hidden', page.id !== id));
  document.querySelectorAll('.nav button').forEach((button) => button.classList.toggle('active', button.dataset.page === id));
  if (typeof renderAll === 'function') renderAll();
}

document.querySelectorAll('.nav button').forEach((button) => {
  button.addEventListener('click', () => showPage(button.dataset.page));
});
