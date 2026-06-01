/**const page = document.body.dataset.page;
document.querySelectorAll("[data-link]").forEach(a => {
  if (a.dataset.link === page) a.classList.add("active");
});
**/
const page = document.body.dataset.page;

document.querySelectorAll("[data-link]").forEach(a => {
  if (a.dataset.link === page) a.classList.add("active");
});

document.querySelectorAll(".info-box").forEach((box, index) => {
  box.style.animationDelay = `${index * 0.15}s`;
});