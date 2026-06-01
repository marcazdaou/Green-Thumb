const page = document.body.dataset.page;
document.querySelectorAll("[data-link]").forEach(a => {
    if (a.dataset.link === page) a.classList.add("active");
});

document.addEventListener("DOMContentLoaded", function () {
    if (typeof updateCartCount === "function") {
        updateCartCount();
    }
});
