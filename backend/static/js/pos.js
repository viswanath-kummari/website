/**
 * Fresh Cut Meat Shop - Point of Sale (POS) Billing Engine
 * Fast shop-counter operations, real-time calculations, touch-friendly
 */

class POSBillingSystem {
  constructor(productsData = []) {
    this.products = productsData;
    this.cart = []; // [{product_id, name, category, unit, rate, qty, max_stock, total}]
    this.activeCategory = 'All';
    this.searchQuery = '';
    this.paymentMethod = 'Cash';
    this.discount = 0.00;
    this.isSubmitting = false;

    this.initElements();
    this.bindEvents();
    this.renderCatalog();
    this.renderCart();
  }

  initElements() {
    this.catalogContainer = document.getElementById('posProductGrid');
    this.cartTableBody = document.getElementById('posCartTableBody');
    this.searchInput = document.getElementById('posSearchInput');
    this.categoryTabs = document.querySelectorAll('.pos-cat-filter');
    this.subtotalDisplay = document.getElementById('posSubtotal');
    this.discountInput = document.getElementById('posDiscountInput');
    this.grandTotalDisplay = document.getElementById('posGrandTotal');
    this.itemCountDisplay = document.getElementById('posItemCount');
    this.customerPhoneInput = document.getElementById('posCustomerPhone');
    this.customerNameInput = document.getElementById('posCustomerName');
    this.paymentButtons = document.querySelectorAll('.payment-btn');
    this.btnCompleteSale = document.getElementById('btnCompleteSale');
    this.btnClearCart = document.getElementById('btnClearCart');
  }

  bindEvents() {
    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.renderCatalog();
      });
    }

    if (this.categoryTabs) {
      this.categoryTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
          this.categoryTabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          this.activeCategory = tab.getAttribute('data-category') || 'All';
          this.renderCatalog();
        });
      });
    }

    if (this.discountInput) {
      this.discountInput.addEventListener('input', (e) => {
        this.discount = parseFloat(e.target.value) || 0.00;
        this.calculateTotals();
      });
    }

    if (this.paymentButtons) {
      this.paymentButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          this.paymentButtons.forEach(b => b.classList.remove('active', 'btn-primary-fc'));
          this.paymentButtons.forEach(b => b.classList.add('btn-outline-fc'));
          btn.classList.remove('btn-outline-fc');
          btn.classList.add('active', 'btn-primary-fc');
          this.paymentMethod = btn.getAttribute('data-method') || 'Cash';
        });
      });
    }

    if (this.btnClearCart) {
      this.btnClearCart.addEventListener('click', () => {
        if (this.cart.length > 0 && confirm('Are you sure you want to clear this bill?')) {
          this.cart = [];
          this.discount = 0.00;
          if (this.discountInput) this.discountInput.value = '';
          this.renderCart();
        }
      });
    }

    if (this.btnCompleteSale) {
      this.btnCompleteSale.addEventListener('click', () => this.submitSale());
    }
  }

  renderCatalog() {
    if (!this.catalogContainer) return;
    this.catalogContainer.innerHTML = '';

    const filtered = this.products.filter(p => {
      const matchCat = this.activeCategory === 'All' || p.category === this.activeCategory;
      const matchSearch = !this.searchQuery || p.name.toLowerCase().includes(this.searchQuery);
      return matchCat && matchSearch;
    });

    if (filtered.length === 0) {
      this.catalogContainer.innerHTML = `
        <div class="col-12 text-center py-5 text-muted">
          <i class="bi bi-search display-6 d-block mb-2"></i>
          <p>No products found matching your filter.</p>
        </div>
      `;
      return;
    }

    filtered.forEach(p => {
      const col = document.createElement('div');
      col.className = 'col-6 col-md-4 col-xl-3 mb-3';

      const isOut = parseFloat(p.available_stock) <= 0;
      const cardClass = isOut ? 'pos-product-item out-of-stock' : 'pos-product-item';

      col.innerHTML = `
        <div class="${cardClass}" data-id="${p.id}">
          <div class="d-flex justify-content-between align-items-start mb-1">
            <span class="badge ${p.unit === 'KG' ? 'bg-secondary' : 'bg-info'} text-white" style="font-size: 0.7rem;">
              ${p.unit}
            </span>
            <small class="${parseFloat(p.available_stock) <= p.min_stock_alert ? 'text-danger font-weight-bold' : 'text-muted'}">
              Stock: ${parseFloat(p.available_stock).toFixed(p.unit === 'KG' ? 2 : 0)}
            </small>
          </div>
          <div class="fw-bold text-charcoal mb-2" style="font-size: 0.92rem; min-height: 2.7rem; line-height: 1.35;">
            ${p.name}
          </div>
          <div class="d-flex justify-content-between align-items-center mt-auto pt-2 border-top">
            <span class="fw-bold text-orange" style="font-size: 1.15rem;">
              ₹${parseFloat(p.selling_price).toFixed(2)}
            </span>
            <button class="btn btn-sm btn-primary-fc py-1 px-2" ${isOut ? 'disabled' : ''}>
              <i class="bi bi-plus-lg"></i> Add
            </button>
          </div>
        </div>
      `;

      col.querySelector('.pos-product-item').addEventListener('click', (e) => {
        if (!isOut) {
          this.addToCart(p);
        }
      });

      this.catalogContainer.appendChild(col);
    });
  }

  addToCart(product) {
    const existing = this.cart.find(it => it.product_id === product.id);
    const defaultIncrement = product.unit === 'KG' ? 0.500 : 1.000;

    if (existing) {
      const newQty = existing.qty + defaultIncrement;
      if (newQty > existing.max_stock) {
        alert(`Cannot add more. Available stock for '${product.name}' is only ${existing.max_stock} ${product.unit}.`);
        return;
      }
      existing.qty = newQty;
      existing.total = parseFloat((existing.qty * existing.rate).toFixed(2));
    } else {
      this.cart.push({
        product_id: product.id,
        name: product.name,
        category: product.category,
        unit: product.unit,
        rate: parseFloat(product.selling_price),
        qty: defaultIncrement,
        max_stock: parseFloat(product.available_stock),
        total: parseFloat((defaultIncrement * parseFloat(product.selling_price)).toFixed(2))
      });
    }

    this.renderCart();
  }

  updateQuantity(productId, delta) {
    const item = this.cart.find(it => it.product_id === productId);
    if (!item) return;

    const step = item.unit === 'KG' ? 0.250 : 1.000;
    const newQty = Math.round((item.qty + (delta * step)) * 1000) / 1000;

    if (newQty <= 0) {
      this.removeItem(productId);
      return;
    }

    if (newQty > item.max_stock) {
      alert(`Requested quantity exceeds available stock (${item.max_stock} ${item.unit}).`);
      return;
    }

    item.qty = newQty;
    item.total = parseFloat((item.qty * item.rate).toFixed(2));
    this.renderCart();
  }

  setExactQuantity(productId, val) {
    const item = this.cart.find(it => it.product_id === productId);
    if (!item) return;

    let qty = parseFloat(val);
    if (isNaN(qty) || qty <= 0) {
      this.removeItem(productId);
      return;
    }

    if (item.unit === 'PCS') {
      qty = Math.round(qty);
    }

    if (qty > item.max_stock) {
      alert(`Maximum stock available: ${item.max_stock} ${item.unit}`);
      qty = item.max_stock;
    }

    item.qty = qty;
    item.total = parseFloat((item.qty * item.rate).toFixed(2));
    this.renderCart();
  }

  removeItem(productId) {
    this.cart = this.cart.filter(it => it.product_id !== productId);
    this.renderCart();
  }

  renderCart() {
    if (!this.cartTableBody) return;
    this.cartTableBody.innerHTML = '';

    if (this.cart.length === 0) {
      this.cartTableBody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center py-5 text-muted">
            <i class="bi bi-basket display-5 d-block mb-2"></i>
            Cart is empty. Click items on the left to add.
          </td>
        </tr>
      `;
      this.calculateTotals();
      if (this.btnCompleteSale) this.btnCompleteSale.disabled = true;
      return;
    }

    if (this.btnCompleteSale) this.btnCompleteSale.disabled = false;

    this.cart.forEach(it => {
      const tr = document.createElement('tr');
      const isKg = it.unit === 'KG';

      tr.innerHTML = `
        <td class="align-middle">
          <div class="fw-bold text-charcoal" style="font-size: 0.9rem;">${it.name}</div>
          <small class="text-muted">₹${it.rate.toFixed(2)} / ${it.unit}</small>
        </td>
        <td class="align-middle" style="width: 140px;">
          <div class="input-group input-group-sm">
            <button class="btn btn-outline-secondary px-2 btn-qty-minus" type="button">-</button>
            <input type="number" step="${isKg ? '0.05' : '1'}" min="${isKg ? '0.05' : '1'}" 
                   class="form-control text-center p-1 font-weight-bold input-qty" value="${it.qty}">
            <button class="btn btn-outline-secondary px-2 btn-qty-plus" type="button">+</button>
          </div>
          <small class="text-muted d-block text-center mt-1">${it.unit}</small>
        </td>
        <td class="align-middle text-end fw-bold text-charcoal" style="width: 85px;">
          ₹${it.total.toFixed(2)}
        </td>
        <td class="align-middle text-center" style="width: 35px;">
          <button class="btn btn-link text-danger p-0 btn-remove" title="Remove">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      `;

      tr.querySelector('.btn-qty-minus').addEventListener('click', () => this.updateQuantity(it.product_id, -1));
      tr.querySelector('.btn-qty-plus').addEventListener('click', () => this.updateQuantity(it.product_id, 1));
      tr.querySelector('.input-qty').addEventListener('change', (e) => this.setExactQuantity(it.product_id, e.target.value));
      tr.querySelector('.btn-remove').addEventListener('click', () => this.removeItem(it.product_id));

      this.cartTableBody.appendChild(tr);
    });

    this.calculateTotals();
  }

  calculateTotals() {
    const subtotal = this.cart.reduce((sum, it) => sum + it.total, 0.00);
    const count = this.cart.length;

    let discount = this.discount;
    if (discount < 0) discount = 0;
    if (discount > subtotal) discount = subtotal;

    const grandTotal = subtotal - discount;

    if (this.subtotalDisplay) this.subtotalDisplay.innerText = `₹${subtotal.toFixed(2)}`;
    if (this.grandTotalDisplay) this.grandTotalDisplay.innerText = `₹${grandTotal.toFixed(2)}`;
    if (this.itemCountDisplay) this.itemCountDisplay.innerText = `${count} ${count === 1 ? 'item' : 'items'}`;
  }

  async submitSale() {
    if (this.cart.length === 0) {
      alert('Cart is empty.');
      return;
    }

    if (this.isSubmitting) return;
    this.isSubmitting = true;

    if (this.btnCompleteSale) {
      this.btnCompleteSale.disabled = true;
      this.btnCompleteSale.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Processing...';
    }

    const payload = {
      customer_name: this.customerNameInput ? this.customerNameInput.value.trim() : '',
      customer_phone: this.customerPhoneInput ? this.customerPhoneInput.value.trim() : '',
      payment_method: this.paymentMethod,
      discount: this.discount,
      items: this.cart.map(it => ({
        product_id: it.product_id,
        quantity: it.qty
      }))
    };

    try {
      const resp = await fetch('/api/v1/pos/bill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (!resp.ok || !data.success) {
        alert(data.message || 'Billing failed. Please try again.');
        this.resetSubmitButton();
        return;
      }

      // Success! Open invoice modal or print dialog
      const invoice = data.data;
      this.showInvoiceSuccessModal(invoice);

      // Clear cart
      this.cart = [];
      this.discount = 0.00;
      if (this.discountInput) this.discountInput.value = '';
      if (this.customerNameInput) this.customerNameInput.value = '';
      if (this.customerPhoneInput) this.customerPhoneInput.value = '';
      this.renderCart();

      // Refresh product stock quantities in local state
      payload.items.forEach(sold => {
        const p = this.products.find(x => x.id === sold.product_id);
        if (p) {
          p.available_stock = Math.max(0, parseFloat(p.available_stock) - sold.quantity);
        }
      });
      this.renderCatalog();

    } catch (err) {
      console.error('POS billing error:', err);
      alert('Network or server error during billing.');
    } finally {
      this.resetSubmitButton();
    }
  }

  resetSubmitButton() {
    this.isSubmitting = false;
    if (this.btnCompleteSale) {
      this.btnCompleteSale.disabled = this.cart.length === 0;
      this.btnCompleteSale.innerHTML = '<i class="bi bi-check2-circle me-1"></i> Complete & Print Bill';
    }
  }

  showInvoiceSuccessModal(invoice) {
    const modalEl = document.getElementById('posInvoiceModal');
    if (!modalEl) {
      window.location.href = `/admin/invoice/${invoice.invoice_number}/print`;
      return;
    }

    document.getElementById('modalInvoiceNum').innerText = invoice.invoice_number;
    document.getElementById('modalGrandTotal').innerText = `₹${parseFloat(invoice.grand_total).toFixed(2)}`;
    document.getElementById('modalCustName').innerText = invoice.customer_name || 'Counter Customer';
    document.getElementById('modalPayMethod').innerText = invoice.payment_method;

    const printBtn = document.getElementById('btnModalPrint');
    const pdfBtn = document.getElementById('btnModalPdf');

    if (printBtn) {
      printBtn.onclick = () => window.open(`/admin/invoice/${invoice.invoice_number}/print`, '_blank');
    }
    if (pdfBtn) {
      pdfBtn.onclick = () => window.location.href = `/admin/invoice/${invoice.invoice_number}/pdf`;
    }

    const bsModal = new bootstrap.Modal(modalEl);
    bsModal.show();
  }
}
