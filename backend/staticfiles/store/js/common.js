/**
 * common.js
 * Loaded on every page. Handles shared behaviour:
 *   - Cart storage (scoped per user so guests and logged-in users never share carts)
 *   - Cart badge counter displayed in the navbar
 *   - Account dropdown open/close
 *   - Active nav-link highlighting
 *   - Staggered fade-in animation for info-box cards
 */


// ---------------------------------------------------------------------------
// Cart storage
// The cart is kept in localStorage under a key that changes between
// "cart:guest" and "cart:user:<id>" depending on login state.
// The key is embedded in the navbar element via a Django template attribute.
// ---------------------------------------------------------------------------

/** Returns the localStorage key for the current user's cart. */
function getCartStorageKey() {
  const navbar    = document.querySelector(".navbar");
  const scopedKey = navbar?.dataset?.cartKey;
  return scopedKey || "cart:guest";
}

/**
 * Reads the cart from localStorage.
 * Also handles a one-time migration from the old unsoped "cart" key
 * so that existing guest carts are not lost after a site update.
 */
function getStoredCart() {
  const storageKey = getCartStorageKey();
  const cartJson   = localStorage.getItem(storageKey);

  if (cartJson) {
    try {
      return JSON.parse(cartJson) || [];
    } catch {
      localStorage.removeItem(storageKey);
      return [];
    }
  }

  // One-time migration: move the legacy unsoped "cart" key to the new scoped key.
  const legacyJson = localStorage.getItem("cart");
  if (legacyJson) {
    try {
      const legacyCart = JSON.parse(legacyJson) || [];
      localStorage.setItem(storageKey, JSON.stringify(legacyCart));
      localStorage.removeItem("cart");
      return legacyCart;
    } catch {
      localStorage.removeItem("cart");
    }
  }

  return [];
}

/** Writes the cart array back to localStorage. */
function setStoredCart(cart) {
  localStorage.setItem(getCartStorageKey(), JSON.stringify(cart));
}

/** Removes the cart from localStorage (called after a successful order). */
function clearStoredCart() {
  localStorage.removeItem(getCartStorageKey());
}


// ---------------------------------------------------------------------------
// Cart badge
// The navbar shows a red badge with the total number of items in the cart.
// ---------------------------------------------------------------------------

/** Reads the cart and updates the cart count badge in the navbar. */
function updateCartCount() {
  const cart       = getStoredCart();
  const totalItems = cart.reduce((sum, item) => sum + (item.qty || 1), 0);
  const badge      = document.getElementById("cart-count");
  if (badge) badge.innerText = totalItems;
}


// ---------------------------------------------------------------------------
// Account dropdown
// The user icon in the navbar opens a dropdown with account info and sign-out.
// ---------------------------------------------------------------------------

/** Wires up open/close behaviour for the account dropdown in the navbar. */
function setupAccountMenu() {
  const accountMenu = document.querySelector(".account-menu");
  if (!accountMenu) return;

  const toggle   = accountMenu.querySelector(".account-toggle");
  const dropdown = accountMenu.querySelector(".account-dropdown");
  if (!toggle || !dropdown) return;

  const close = () => {
    accountMenu.classList.remove("is-open");
    dropdown.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  };

  const open = () => {
    accountMenu.classList.add("is-open");
    dropdown.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
  };

  // Toggle on icon click.
  toggle.addEventListener("click", (e) => {
    e.stopPropagation();
    dropdown.hidden ? open() : close();
  });

  // Close when the user clicks anywhere outside the menu.
  document.addEventListener("click", (e) => {
    if (!accountMenu.contains(e.target)) close();
  });

  // Close on Escape key.
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
  });
}


// ---------------------------------------------------------------------------
// Active nav link
// Each page sets data-page="<name>" on <body>.
// Nav links have data-link="<name>" so we can highlight the current page.
// ---------------------------------------------------------------------------

/** Adds the "active" class to the nav link that matches the current page. */
function highlightActiveNavLink() {
  const page = document.body.dataset.page;
  document.querySelectorAll("[data-link]").forEach(a => {
    if (a.dataset.link === page) a.classList.add("active");
  });
}


// ---------------------------------------------------------------------------
// Info-box stagger
// Cards with class .info-box get a small animation-delay offset so they
// appear to cascade in rather than all fading in at once.
// ---------------------------------------------------------------------------

function staggerInfoBoxes() {
  document.querySelectorAll(".info-box").forEach((box, i) => {
    box.style.animationDelay = `${i * 0.12}s`;
  });
}


// ---------------------------------------------------------------------------
// Initialise everything once the DOM is ready.
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  updateCartCount();
  setupAccountMenu();
  highlightActiveNavLink();
  staggerInfoBoxes();
});
