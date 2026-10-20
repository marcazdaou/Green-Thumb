/**
 * shop.js: "Add to cart" buttons (shop grid, home page, product page) and the
 * quantity picker on the product page. Only the product id and quantity are
 * stored; see common.js.
 */
document.addEventListener("DOMContentLoaded", () => {
  const qtyLabel = document.querySelector(".qty-group .qty");

  // Quantity +/- on the product page.
  document.querySelectorAll(".qty-step").forEach(button => {
    button.addEventListener("click", () => {
      const next = Number(qtyLabel.textContent) + Number(button.dataset.step);
      qtyLabel.textContent = Math.min(Math.max(next, 1), MAX_QTY);
    });
  });

  document.querySelectorAll(".add-to-cart").forEach(button => {
    button.addEventListener("click", () => {
      const qty = qtyLabel && button.closest(".product-detail") ? Number(qtyLabel.textContent) : 1;
      addToCart(Number(button.dataset.id), qty);
      toast(`Added ${qty} × ${button.dataset.name} to your cart`);
    });
  });
});
