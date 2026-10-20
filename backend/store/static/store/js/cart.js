/**
 * cart.js: the cart page.
 *
 * Sends the stored [{id, qty}] to /api/cart/ and renders the lines and totals
 * the server returns. Checkout posts the same ids and quantities to
 * /api/checkout/; the server prices the order from the database. If Stripe
 * test mode is on, the server answers with a checkout_url and we go there to pay.
 * All text is inserted with textContent (never innerHTML) to avoid XSS.
 */
const money = value => `£${Number(value).toFixed(2)}`;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function changeQty(id, delta) {
  const cart = getCart();
  const line = cart.find(item => item.id === id);
  if (!line) return;
  line.qty = Math.min(line.qty + delta, MAX_QTY);
  setCart(cart.filter(item => item.qty > 0));
  renderCart();
}

function removeLine(id) {
  setCart(getCart().filter(item => item.id !== id));
  renderCart();
}

function showError(message) {
  const box = document.getElementById("cart-error");
  box.textContent = message;
  box.hidden = !message;
}

function renderLine(line) {
  const row = el("article", "cart-line card");
  const img = el("img");
  img.src = line.image_url;
  img.alt = "";
  const info = el("div", "cart-line-info");
  const name = el("a", "cart-line-name", line.name);
  name.href = line.url;
  info.append(name, el("span", "muted", `${money(line.unit_price)} each`));

  const controls = el("div", "qty-group");
  const minus = el("button", "qty-step", "−");
  const plus = el("button", "qty-step", "+");
  minus.setAttribute("aria-label", `Decrease ${line.name}`);
  plus.setAttribute("aria-label", `Increase ${line.name}`);
  minus.addEventListener("click", () => changeQty(line.id, -1));
  plus.addEventListener("click", () => changeQty(line.id, 1));
  controls.append(minus, el("span", "qty", line.quantity), plus);

  const remove = el("button", "link-button", "Remove");
  remove.addEventListener("click", () => removeLine(line.id));

  row.append(img, info, controls, el("span", "cart-line-total", money(line.line_total)), remove);
  return row;
}

async function renderCart() {
  const container = document.getElementById("cart-lines");
  const button = document.getElementById("checkout-button");
  const cart = getCart();
  showError("");

  if (cart.length === 0) {
    container.replaceChildren(el("p", "empty", "Your cart is empty."));
    const link = el("a", "btn", "Browse the shop");
    link.href = "/shop/";
    container.append(link);
    document.getElementById("cart-subtotal").textContent = money(0);
    document.getElementById("cart-total").textContent = money(0);
    button.disabled = true;
    return;
  }

  try {
    const data = await postJson("/api/cart/", { items: cart });
    container.replaceChildren(...data.lines.map(renderLine));
    document.getElementById("cart-subtotal").textContent = money(data.total);
    document.getElementById("cart-total").textContent = money(data.total);
    button.disabled = false;
  } catch (error) {
    // A product may have been removed from the catalog: drop unknown items and retry once.
    if (/Unknown product/.test(error.message)) {
      const unknown = new Set((error.message.match(/\d+/g) || []).map(Number));
      setCart(cart.filter(item => !unknown.has(item.id)));
      return renderCart();
    }
    container.replaceChildren(el("p", "form-error", error.message));
    button.disabled = true;
  }
}

async function checkout() {
  const button = document.getElementById("checkout-button");
  button.disabled = true;
  try {
    const order = await postJson("/api/checkout/", { items: getCart() });
    if (order.checkout_url) {
      // Stripe test mode: continue on Stripe's payment page. The cart is kept until
      // the payment is confirmed (order_paid.js empties it), so cancelling loses nothing.
      window.location.assign(order.checkout_url);
      return;
    }
    setCart([]);
    document.getElementById("order-detail").textContent =
      `Order #${order.order_id} for ${money(order.total)} was recorded. No payment was taken and nothing will be shipped.`;
    document.getElementById("order-modal").hidden = false;
    renderCart();
  } catch (error) {
    showError(error.message);
    button.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("checkout-button").addEventListener("click", checkout);
  renderCart();
});
