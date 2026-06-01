const page = document.body.dataset.page;
document.querySelectorAll("[data-link]").forEach(a => {
  if (a.dataset.link === page) a.classList.add("active");
});

// Hardcoded base reviews (always shown, not in DB)
const baseReviews = [
  { name: "Raneem A.",  product: "Cotton Tote Bag",       stars: 4, text: "Love your product. The quality is amazing.",                  date: "Feb 2026" },
  { name: "Shrinal D.", product: "Reusable Water Bottle", stars: 5, text: "This is so nicely packaged. I think I'm in love!",           date: "Jan 2026" },
  { name: "David G.",   product: "Succulents",             stars: 5, text: "I am very happy with my purchase!",                          date: "Jan 2026" },
  { name: "Tien L.",    product: "Steel Straw Set",        stars: 5, text: "I love this. I've already convinced my friends to get one!", date: "Dec 2025" },
  { name: "Grey",       product: "Flower Seeds",           stars: 5, text: "This is one of the best products I have bought!",            date: "Dec 2025" },
];

// Reviews from DB (injected by Django)
const dbReviews = typeof django_reviews !== 'undefined' ? django_reviews : [];

let ratingData = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };

function getAllReviews() {
  return [...dbReviews, ...baseReviews];
}

function buildRatingData() {
  ratingData = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
  getAllReviews().forEach(r => { ratingData[r.stars]++; });
}

function getTotalReviews() {
  return Object.values(ratingData).reduce((a, b) => a + b, 0);
}

function getAverageScore() {
  const total = getTotalReviews();
  if (total === 0) return 0;
  const weighted = Object.entries(ratingData).reduce((sum, [stars, count]) => sum + parseInt(stars) * count, 0);
  return (weighted / total).toFixed(1);
}

function updateAverageScore() {
  const total = getTotalReviews();
  document.getElementById('avg-number').textContent = getAverageScore();
  document.getElementById('avg-label').textContent = `Based on ${total} review${total !== 1 ? 's' : ''}`;
}

function updateRatingDistribution() {
  const total = getTotalReviews();
  for (let s = 1; s <= 5; s++) {
    const count = ratingData[s];
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    document.getElementById(`count-${s}`).textContent = count;
    document.getElementById(`percent-${s}`).textContent = pct + '%';
    document.getElementById(`bar-${s}`).style.width = pct + '%';
  }
  updateAverageScore();
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function renderCard(review, prepend = false) {
  const card = document.createElement("div");
  card.className = "review-card";
  let starDisplay = "";
  for (let i = 1; i <= 5; i++) starDisplay += i <= review.stars ? "&#9733;" : "&#9734;";
  const isOwner = current_user_id && review.user_id && review.user_id === current_user_id;
  const deleteBtn = isOwner
    ? `<button class="delete-btn" data-id="${review.id}">&#10005; Remove</button>`
    : "";
  card.innerHTML = `
    <span class="review-product">&#128230; ${escapeHtml(review.product)}</span>
    <div class="stars">${starDisplay}</div>
    <div class="review-text">"${escapeHtml(review.text)}"</div>
    <div class="reviewer-name">${escapeHtml(review.name)}</div>
    <div class="review-date">${escapeHtml(review.date)}</div>
    ${deleteBtn}
  `;
  const container = document.getElementById("reviews-container");
  if (prepend) container.insertBefore(card, container.firstChild);
  else container.appendChild(card);
}

function loadReviews() {
  document.getElementById("reviews-container").innerHTML = "";
  dbReviews.forEach(r => renderCard(r));
  baseReviews.forEach(r => renderCard(r));
}

// Delete a DB review by its id
document.addEventListener("click", function(e) {
  if (!e.target.classList.contains("delete-btn")) return;
  const reviewId = parseInt(e.target.dataset.id);

  fetch(`/reviews/delete/${reviewId}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      const idx = dbReviews.findIndex(r => r.id === reviewId);
      if (idx !== -1) dbReviews.splice(idx, 1);
      buildRatingData();
      loadReviews();
      updateRatingDistribution();
    }
  });
});

function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

// STAR PICKER
const ratingLabels = { 1: "Poor", 2: "Fair", 3: "Good", 4: "Very Good", 5: "Excellent" };
let selectedStars = 0;
const stars = document.querySelectorAll("#star-picker span");

stars.forEach(star => {
  star.addEventListener("click", function() {
    selectedStars = parseInt(this.dataset.val);
    stars.forEach(s => s.classList.toggle("selected", parseInt(s.dataset.val) <= selectedStars));
    document.getElementById("rating-label").textContent = ratingLabels[selectedStars];
  });
  star.addEventListener("mouseover", function() {
    const val = parseInt(this.dataset.val);
    stars.forEach(s => { s.style.color = parseInt(s.dataset.val) <= val ? "#52b788" : "#ddd"; });
  });
  star.addEventListener("mouseout", function() {
    stars.forEach(s => { s.style.color = parseInt(s.dataset.val) <= selectedStars ? "#52b788" : "#ddd"; });
  });
});

// SUBMIT REVIEW
function submitReview() {
  const name    = document.getElementById("input-name").value.trim();
  const product = document.getElementById("input-product").value;
  const text    = document.getElementById("input-review").value.trim();

  if (!name || !product || !text || selectedStars === 0) {
    alert("Please fill in all fields and select a rating!");
    return;
  }

  fetch('/reviews/submit/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
    body: JSON.stringify({ name, product, stars: selectedStars, text }),
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      const review = data.review;
      dbReviews.unshift(review);
      buildRatingData();
      loadReviews();
      updateRatingDistribution();

      document.getElementById("input-name").value    = "";
      document.getElementById("input-review").value  = "";
      document.getElementById("input-product").value = "";
      selectedStars = 0;
      stars.forEach(s => s.classList.remove("selected"));
      document.getElementById("rating-label").textContent = "Select a rating";
    } else {
      alert("Something went wrong. Please try again.");
    }
  });
}

// INIT
document.addEventListener("DOMContentLoaded", function() {
  buildRatingData();
  loadReviews();
  updateRatingDistribution();
  if (typeof updateCartCount === "function") updateCartCount();
});
