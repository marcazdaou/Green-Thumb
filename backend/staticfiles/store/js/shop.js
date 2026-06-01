const page = document.body.dataset.page;
document.querySelectorAll("[data-link]").forEach(a => {
  if (a.dataset.link === page) a.classList.add("active");
});

const searchInput = document.getElementById("product-search-input");
const searchButton = document.getElementById("product-search-button");
const productsGrid = document.getElementById("products-grid");
const productCard = document.getElementsByClassName("product-card")[0] || null;
const productCards = [];
const emptyState = document.getElementById("search-empty");
const staticRoot = document.body.dataset.staticRoot || "/static/";

//Runs on page load and searches by URL tag
const urlQuery = window.location.hash?.split("search=")[1]?.replaceAll("%20", ' ').split("#")[0];

class ProductCard {
  constructor(product_name, src, desc, price) {
    this.product_name = product_name;
    this.src = src;
    this.desc = desc;
    this.price = price;
  }

  static from(json) {
    return Object.assign(new ProductCard(), json)
  }

  createCard() {
    if (!productCard) return;
    const clone = productCard.cloneNode(true);
    const img = clone.querySelector("img");
    img.src = this.src;
    img.alt = this.product_name;
    clone.querySelector("h2.product-name").innerText = this.product_name;
    clone.querySelector("p.product-desc").innerText = this.desc;
    clone.querySelector("div.product-price").innerText = "$" + this.price.toFixed(2);
const btn = clone.querySelector(".add-btn");

btn.addEventListener("click", () => {
  addToCartWithQty(btn, this.product_name, this.price);
});
    productsGrid.appendChild(clone);
    productCards.push(clone);
  }
}

const products = [
  new ProductCard(
    "Reusable Water Bottle",
    staticRoot + "images/products/waterbottle.png",
    "Lightweight bottle to keep you hydrated while gardening or on the go.",
    18.00
  ),
  new ProductCard(
    "Cotton Tote Bag",
    staticRoot + "images/products/cottonbag.png",
    "Durable everyday tote for groceries, tools, and market finds.",
    14.00
  ),
  new ProductCard(
    "Steel Straw Set",
    staticRoot + "images/products/steelstraw.png",
    "Reusable stainless steel straws with a cleaner, perfect for daily use.",
    9.00
  ),
  new ProductCard(
    "Succulents",
    staticRoot + "images/products/succulet.png",
    "Low-maintenance mini succulents to brighten desks and windowsills.",
    12
  ),
  new ProductCard(
    "Flower Seeds",
    staticRoot + "images/products/flowerseeds.png",
    "Assorted seasonal flower seeds for colorful blooms all season long.",
    6.00
  ),
  new ProductCard("Aloe Vera",
		"https://www.stockvault.net/data/2021/01/03/282191/preview16.jpg",
		"Known for the soothing gel inside its leaves that helps treat burns and skin irritation. It is very easy to grow and requires little water.",
    12.67
	),
	new ProductCard("Snake Plant",
		"https://cdn.shopify.com/s/files/1/0619/1218/7051/files/1661954674-dsc-7058-1.jpg",
		"A hardy houseplant that survives in low light with minimal watering. It is known for helping improve indoor air quality.",
    12.99
	),

	new ProductCard("Peace Lily",
		"https://www.meadowsfarms.com/great-big-greenhouse-gardening-blog/wp-content/uploads/sites/2/2025/03/bonnie-blog-peace-lily.jpg.webp",
		"Known for its elegant white blooms and lush green leaves. It thrives indoors and is valued for helping filter certain pollutants from the air.",
    15.96
	),

	new ProductCard("Lavender",
		"https://www.provenwinners.com/sites/provenwinners.com/files/imagecache/low-resolution/ifa_upload/lavandula_summer_serenade_apj25_3.jpg",
		"Known for its fragrant purple flowers and use in aromatherapy. Its scent helps promote relaxation and reduce stress.",
    11.96
	),

	new ProductCard("Basil",
		"https://aanmc.org/wp-content/uploads/2021/08/987-1024x681.jpg",
		"A popular culinary herb used in many Mediterranean dishes. Growing basil at home promotes sustainable cooking with fresh ingredients.",
    11.96
	),

	new ProductCard("Mint",
		"https://media.post.rvohealth.io/wp-content/uploads/sites/3/2025/06/mint-good-GettyImages-2216675819-Header-1024x575.jpg",
		"Mint is a fast-growing herb known for its refreshing flavor. It is commonly used in teas, desserts, and beverages. It grows easily in home gardens.",
    11.76
	),

	new ProductCard("Rosemary",
		"https://lancaster.unl.edu/sites/unl.edu.ianr.extension.lancaster/files/2024-12/rosemary-gb8cd2e20e_1920.jpg",
		"A fragrant herb widely used in cooking. It grows well in sunny conditions and requires very little water.",
    8.49
	),

	new ProductCard("Monstera",
		"https://cdn.mos.cms.futurecdn.net/w5g9MUrhQ8nRgAhRamAKvX.jpg",
		"A tropical plant known for its large split leaves. It is widely used as a decorative indoor plant.",
    25.76
	),

	new ProductCard("Spider Plant",
		"https://cdn.mos.cms.futurecdn.net/Rw63sJPwqukKneBYZkpjUn.jpg",
		"A resilient houseplant known for its long arching leaves. It is easy to care for and grows quickly indoors. It produces small plantlets that can be replanted.",
    20.06
	),
	new ProductCard("Chamomile",
		"https://cdn.mos.cms.futurecdn.net/v2sQs7MsmECNVGZBqXtwkH.jpg",
		"A flowering herb commonly used to make calming herbal tea. It is known for its relaxing effects.",
    9.50
	),
	new ProductCard("Sunflower",
		"https://www.lunafloral.my/cdn/shop/articles/pexels-pixabay-54267.jpg?v=1724733421&width=2048",
		"A bright plant that supports pollinators like bees. It produces seeds commonly used in food and cooking oil. Its tall stems and large flowers make it popular in gardens.",
    22.55
	)
];

addEventListener("DOMContentLoaded", (event) => {

  if(productCard){
    productCard.remove();
  }

  //Converts json dump into product card.
  django_shop_items.forEach((element) => {
    products.push(ProductCard.from(element))
  });

  products.forEach((element) => element.createCard());

  if(urlQuery != null) {
    searchInput.value = urlQuery;
    filterProducts()
  }
});

function filterProducts() {
  const query = searchInput.value.trim().toLowerCase();
  let visibleCount = 0;

  productsGrid.classList.toggle("search-results", query !== "");

  productCards.forEach(card => {
    const searchableText = card.innerText.toLowerCase();
    const matches = searchableText.includes(query);

    card.hidden = !matches;
    if (matches) {
      visibleCount += 1;
    }
  });

  emptyState.hidden = visibleCount !== 0;
}

searchButton.addEventListener("click", filterProducts);
searchInput.addEventListener("input", filterProducts);
searchInput.addEventListener("keydown", event => {
  if (event.key === "Enter") {
    event.preventDefault();
    filterProducts();
  }
});

function addToCartWithQty(btn, name, price){

  let qty = parseInt(btn.parentElement.querySelector(".qty").innerText);

  let cart = getStoredCart();

let existingItem = cart.find(item => item.name === name);

if(existingItem){
  existingItem.qty += qty;
}else{
cart.push({
  name: name,
  price: price,
  qty: qty,
  image: this.src || btn.closest(".product-card").querySelector("img").src
});
}

  setStoredCart(cart);

  updateCartCount();

  alert(name + " (x" + qty + ") added to cart!");
}

function changeQty(btn, change){
  let qtySpan = btn.parentElement.querySelector(".qty");
  let qty = parseInt(qtySpan.innerText);

  qty += change;
  if(qty < 1) qty = 1;

  qtySpan.innerText = qty;
}


updateCartCount();

document.addEventListener("DOMContentLoaded", updateCartCount);
