/**
 * Fresh Cut Meat Shop - Customer Storefront Shopping Cart
 */

const StorefrontCart = {
  CART_KEY: 'freshcut_customer_cart',

  getCart() {
    try {
      return JSON.parse(localStorage.getItem(this.CART_KEY)) || [];
    } catch (e) {
      return [];
    }
  },

  saveCart(cart) {
    localStorage.setItem(this.CART_KEY, JSON.stringify(cart));
    this.updateBadge();
  },

  addItem(product, quantity = null) {
    const cart = this.getCart();
    const existing = cart.find(it => it.product_id === product.id);
    const defaultQty = quantity !== null ? quantity : (product.unit === 'KG' ? 1.0 : 1.0);

    if (existing) {
      existing.quantity += defaultQty;
    } else {
      cart.push({
        product_id: product.id,
        product_name: product.name,
        category: product.category,
        unit: product.unit,
        unit_price: parseFloat(product.selling_price),
        quantity: defaultQty,
        image_url: product.image_url || '/static/images/default_product.jpg'
      });
    }

    this.saveCart(cart);
    this.showToast(`Added ${product.name} to cart!`);
  },

  updateQuantity(productId, newQty) {
    let cart = this.getCart();
    const item = cart.find(it => it.product_id === productId);
    if (!item) return;

    const val = parseFloat(newQty);
    if (isNaN(val) || val <= 0) {
      this.removeItem(productId);
      return;
    }

    item.quantity = val;
    this.saveCart(cart);
    this.renderCartPage();
  },

  removeItem(productId) {
    let cart = this.getCart();
    cart = cart.filter(it => it.product_id !== productId);
    this.saveCart(cart);
    this.renderCartPage();
  },

  clearCart() {
    localStorage.removeItem(this.CART_KEY);
    this.updateBadge();
    this.renderCartPage();
  },

  updateBadge() {
    const badge = document.getElementById('navbarCartBadge');
    if (!badge) return;
    const cart = this.getCart();
    const totalCount = cart.length;
    badge.innerText = totalCount;
    badge.style.display = totalCount > 0 ? 'inline-block' : 'none';
  },

  renderCartPage() {
    const tableBody = document.getElementById('customerCartTableBody');
    const subtotalEl = document.getElementById('cartSubtotalDisplay');
    const grandTotalEl = document.getElementById('cartGrandTotalDisplay');
    const emptyState = document.getElementById('cartEmptyState');
    const cartContent = document.getElementById('cartContentSection');

    if (!tableBody) return;

    const cart = this.getCart();

    if (cart.length === 0) {
      if (emptyState) emptyState.style.display = 'block';
      if (cartContent) cartContent.style.display = 'none';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (cartContent) cartContent.style.display = 'block';

    tableBody.innerHTML = '';
    let subtotal = 0;

    cart.forEach(it => {
      const lineTotal = it.quantity * it.unit_price;
      subtotal += lineTotal;
      const isKg = it.unit === 'KG';

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="align-middle">
          <div class="d-flex align-items-center gap-3">
            <img src="${it.image_url}" class="rounded" style="width: 55px; height: 55px; object-fit: cover;" onerror="this.src='/static/images/default_product.jpg'">
            <div>
              <div class="fw-bold text-charcoal">${it.product_name}</div>
              <small class="badge bg-secondary">${it.category}</small>
            </div>
          </div>
        </td>
        <td class="align-middle">₹${it.unit_price.toFixed(2)} / ${it.unit}</td>
        <td class="align-middle" style="width: 140px;">
          <div class="input-group input-group-sm">
            <input type="number" step="${isKg ? '0.25' : '1'}" min="${isKg ? '0.25' : '1'}"
                   class="form-control text-center cart-item-qty" value="${it.quantity}">
            <span class="input-group-text">${it.unit}</span>
          </div>
        </td>
        <td class="align-middle text-end fw-bold">₹${lineTotal.toFixed(2)}</td>
        <td class="align-middle text-center">
          <button class="btn btn-sm text-danger p-0 cart-item-delete" title="Remove">
            <i class="bi bi-trash fs-5"></i>
          </button>
        </td>
      `;

      tr.querySelector('.cart-item-qty').addEventListener('change', (e) => {
        this.updateQuantity(it.product_id, e.target.value);
      });
      tr.querySelector('.cart-item-delete').addEventListener('click', () => {
        this.removeItem(it.product_id);
      });

      tableBody.appendChild(tr);
    });

    if (subtotalEl) subtotalEl.innerText = `₹${subtotal.toFixed(2)}`;
    if (grandTotalEl) grandTotalEl.innerText = `₹${subtotal.toFixed(2)}`;
  },

  showToast(msg) {
    const toastEl = document.getElementById('cartActionToast');
    if (!toastEl) return;
    document.getElementById('cartToastMessage').innerText = msg;
    const toast = new bootstrap.Toast(toastEl, { delay: 2500 });
    toast.show();
  }
};

document.addEventListener('DOMContentLoaded', () => {
  StorefrontCart.updateBadge();
  StorefrontCart.renderCartPage();

  // Bind Add to Cart buttons on product cards
  document.querySelectorAll('.btn-add-to-cart').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = {
        id: btn.getAttribute('data-id'),
        name: btn.getAttribute('data-name'),
        category: btn.getAttribute('data-category'),
        unit: btn.getAttribute('data-unit'),
        selling_price: btn.getAttribute('data-price'),
        image_url: btn.getAttribute('data-img')
      };
      StorefrontCart.addItem(p);
    });
  });
});

