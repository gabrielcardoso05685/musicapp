document.querySelectorAll('.dropdown').forEach(menu => menu.addEventListener('toggle', () => {
  if (menu.open) document.querySelectorAll('.dropdown').forEach(other => { if (other !== menu) other.open = false; });
}));
document.addEventListener('click', event => document.querySelectorAll('.dropdown').forEach(menu => {
  if (!menu.contains(event.target)) menu.open = false;
}));
document.addEventListener('keydown', event => { if (event.key === 'Escape') document.querySelectorAll('.dropdown').forEach(menu => menu.open = false); });
document.querySelectorAll('.delete-form').forEach(form => form.addEventListener('submit', event => {
  if (!confirm('Deseja excluir este registro?')) event.preventDefault();
}));
