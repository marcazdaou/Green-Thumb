/**
 * common.js: loaded on every page.
 *
 *  - Cart storage. The cart lives in localStorage as [{id, qty}] only; names
 *    and prices are always fetched from the server, so nothing the browser
 *    stores can change what an order costs. The key is scoped per account
 *    ("cart:guest" or "cart:user:<id>") so carts are never shared.
 *  - Navbar: cart badge, account dropdown, active link.
 *  - CSRF token helper for POST requests to Django.
 */

const MAX_QTY = 100;

function cartKey() {
  return document.querySelector(".navbar")?.dataset.cartKey || "cart:guest";
}

/** The cart as [{id, qty}]; malformed or legacy entries are dropped. */
function getCart() {
  try {
    const items = JSON.parse(localStorage.getItem(cartKey())) || [];
    return items
      .filter(item => Number.isInteger(item.id) && Number.isInteger(item.qty) && item.qty > 0)
      .map(item => ({ id: item.id, qty: Math.min(item.qty, MAX_QTY) }));
  } catch {
    return [];
  }
}

function setCart(items) {
  localStorage.setItem(cartKey(), JSON.stringify(items));
  updateCartCount();
}

function addToCart(id, qty = 1) {
  const cart = getCart();
  const line = cart.find(item => item.id === id);
  if (line) line.qty = Math.min(line.qty + qty, MAX_QTY);
  else cart.push({ id, qty: Math.min(qty, MAX_QTY) });
  setCart(cart);
}

function updateCartCount() {
  const badge = document.getElementById("cart-count");
  if (badge) badge.textContent = getCart().reduce((sum, item) => sum + item.qty, 0);
}

/** Django's CSRF token (from the csrftoken cookie), required for POST requests. */
function csrfToken() {
  return document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "";
}

/** POST JSON to the server; resolves to the parsed body, rejects with the server's error message. */
async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || "Something went wrong. Please try again.");
  return body;
}

/** Small non-blocking notification (replaces alert()). */
function toast(message) {
  let box = document.querySelector(".toast");
  if (!box) {
    box = document.createElement("div");
    box.className = "toast";
    box.setAttribute("role", "status");
    document.body.appendChild(box);
  }
  box.textContent = message;
  box.classList.add("show");
  clearTimeout(box.hideTimer);
  box.hideTimer = setTimeout(() => box.classList.remove("show"), 2200);
}

function setupAccountMenu() {
  const menu = document.querySelector(".account-menu");
  const toggle = menu?.querySelector(".account-toggle");
  const dropdown = menu?.querySelector(".account-dropdown");
  if (!toggle || !dropdown) return;
  const setOpen = open => {
    dropdown.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
  };
  toggle.addEventListener("click", e => { e.stopPropagation(); setOpen(dropdown.hidden); });
  document.addEventListener("click", e => { if (!menu.contains(e.target)) setOpen(false); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") setOpen(false); });
}

function highlightActiveNavLink() {
  const page = document.body.dataset.page;
  document.querySelectorAll(".navbar [data-link]").forEach(a => {
    a.classList.toggle("active", a.dataset.link === page);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  updateCartCount();
  setupAccountMenu();
  highlightActiveNavLink();
});
