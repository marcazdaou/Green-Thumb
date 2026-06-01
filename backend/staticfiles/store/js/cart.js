/**
 * cart.js
 * Manages the cart page UI and checkout flow.
 *
 * The cart is stored in localStorage (via common.js helpers).
 * This file reads that data, builds the product card HTML, handles
 * quantity changes and item removal, and submits the order to the server.
 */


// Highlight the active nav link for this page (data-page="cart" on <body>).
// common.js runs highlightActiveNavLink() on DOMContentLoaded, so no call needed here.


// ---------------------------------------------------------------------------
// Render cart items
// ---------------------------------------------------------------------------

/**
 * Reads the cart from localStorage and rebuilds the cart items section.
 * Also updates both total price elements (subtotal + order total).
 */
function loadCart() {
    const cart     = getStoredCart();
    const cartDiv  = document.getElementById("cart-items");
    const emptyMsg = document.getElementById("cart-empty-msg");
    let total      = 0;

    cartDiv.innerHTML = "";

    if (cart.length === 0) {
        // Show the empty-cart message and zero out the totals.
        if (emptyMsg) emptyMsg.hidden = false;
        syncTotals(0);
        return;
    }

    if (emptyMsg) emptyMsg.hidden = true;

    // Build one product card element per cart item.
    cart.forEach((item, index) => {
        const qty       = item.qty || 1;
        const itemTotal = item.price * qty;
        total += itemTotal;

        cartDiv.innerHTML += `
            <article class="product-card">
                <img src="${item.image || ''}" alt="${item.name}">
                <div class="product-info">
                    <h2 class="product-name">${item.name}</h2>
                    <div class="cart-controls">
                        <button onclick="updateQty(${index}, -1)">-</button>
                        <span class="qty">${qty}</span>
                        <button onclick="updateQty(${index}, 1)">+</button>
                        <button class="remove-btn" onclick="removeItem(${index})">Remove</button>
                    </div>
                    <div class="product-price">$${itemTotal.toFixed(2)}</div>
                </div>
            </article>
        `;
    });

    syncTotals(total);
}

/**
 * Updates both the subtotal and the order-total displays.
 * There are two separate elements showing the same value (one in the
 * summary breakdown, one in the bold total line).
 */
function syncTotals(total) {
    const fmt = total.toFixed(2);
    const el1 = document.getElementById("cart-total");
    const el2 = document.getElementById("cart-total-final");
    if (el1) el1.innerText = fmt;
    if (el2) el2.innerText = fmt;
}


// ---------------------------------------------------------------------------
// Cart mutations
// ---------------------------------------------------------------------------

/**
 * Removes the item at the given index from the cart and re-renders.
 * @param {number} index - position in the cart array
 */
function removeItem(index) {
    const cart = getStoredCart();
    cart.splice(index, 1);
    setStoredCart(cart);
    loadCart();
    updateCartCount();
}

/**
 * Increments or decrements the quantity of an item.
 * If quantity drops below 1 the item is removed entirely.
 * @param {number} index  - position in the cart array
 * @param {number} change - +1 or -1
 */
function updateQty(index, change) {
    const cart = getStoredCart();
    cart[index].qty += change;
    if (cart[index].qty < 1) cart.splice(index, 1);
    setStoredCart(cart);
    loadCart();
    updateCartCount();
}


// ---------------------------------------------------------------------------
// Checkout
// ---------------------------------------------------------------------------

/** Reads the CSRF token from the browser cookie (required for Django POST). */
function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
}

/**
 * Handles the Place Order button:
 *   1. POSTs the current cart to the server so it can be recorded in the DB.
 *   2. Shows the success popup.
 *   3. Clears the cart and reloads the page after a short delay.
 *
 * The fetch is fire-and-forget (.catch(() => {})) so a network failure does
 * not prevent the UI from completing the flow.
 */
function simulatePayment() {
    const cart  = getStoredCart();
    const popup = document.getElementById("success-popup");

    // Send cart data to the server for analytics tracking.
    fetch('/orders/submit/', {
        method: 'POST',
        headers: {
            'Content-Type':  'application/json',
            'X-CSRFToken':   getCsrfToken(),
        },
        body: JSON.stringify({ items: cart }),
    }).catch(() => {});  // silent fail — the order confirmation still shows

    popup.classList.add("show");
    clearStoredCart();

    setTimeout(() => {
        popup.classList.remove("show");
        location.reload();
    }, 2000);
}


// ---------------------------------------------------------------------------
// Payment method toggle
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    loadCart();
    updateCartCount();

    const paymentSelect = document.getElementById("payment-method");
    const cardForm      = document.getElementById("card-form");

    if (!paymentSelect || !cardForm) return;

    /**
     * Shows the card input fields only when "Credit / Debit Card" is selected.
     * Other payment methods (PayPal, Apple Pay, COD) have no extra fields.
     */
    function togglePaymentUI() {
        cardForm.style.display = paymentSelect.value === "card" ? "flex" : "none";
    }

    paymentSelect.addEventListener("change", togglePaymentUI);
    togglePaymentUI();  // set correct state on initial render
});
