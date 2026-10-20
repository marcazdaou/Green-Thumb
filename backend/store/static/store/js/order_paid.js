/**
 * order_paid.js: loaded only on the confirmation page after Stripe confirms a payment.
 * The cart is kept while the shopper is on Stripe (so cancelling loses nothing)
 * and emptied here, once the order is actually paid.
 */
setCart([]);
