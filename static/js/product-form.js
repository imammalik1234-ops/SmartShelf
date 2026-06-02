const categorySelect = document.getElementById("category");
const productSelect = document.getElementById("product");
const variantSelect = document.getElementById("variant");
const supplierSelect = document.getElementById("supplier");
const productForm = document.getElementById("productForm");

function setOptions(select, values, placeholder, selectedValue) {
  select.innerHTML = `<option value="">${placeholder}</option>`;

  values.forEach(value => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    option.selected = value === selectedValue;
    select.appendChild(option);
  });
}

function selectedProductInfo() {
  const category = categorySelect.value;
  const product = productSelect.value;

  if (!category || !product || !catalog[category] || !catalog[category][product]) {
    return null;
  }

  return catalog[category][product];
}

function populateProducts() {
  const category = categorySelect.value;
  const products = category && catalog[category] ? Object.keys(catalog[category]) : [];

  setOptions(productSelect, products, "Select a product", selectedValues.product);
  populateProductDetails();
}

function populateProductDetails() {
  const info = selectedProductInfo();

  setOptions(
    variantSelect,
    info ? info.variants : [],
    "Select a variant",
    selectedValues.variant
  );

  setOptions(
    supplierSelect,
    info ? info.suppliers : [],
    "Select a supplier",
    selectedValues.supplier
  );
}

function showValidationErrors(errors) {
  let summary = document.querySelector(".validation-summary");

  if (!summary) {
    summary = document.createElement("div");
    summary.className = "message error validation-summary";
    productForm.parentElement.insertBefore(summary, productForm);
  }

  summary.innerHTML = errors.map(error => `<div>${error}</div>`).join("");
  summary.style.display = "block";
}

function validateForm(event) {
  const errors = [];
  const quantity = Number(document.getElementById("quantity").value);
  const unitPrice = Number(document.getElementById("unit_price").value);
  const reorderLevel = Number(document.getElementById("reorder_level").value);
  const expiryInput = document.getElementById("expiry_date");

  if (!categorySelect.value) errors.push("Please select a category.");
  if (!productSelect.value) errors.push("Please select a product.");
  if (!variantSelect.value) errors.push("Please select a product variant.");
  if (!supplierSelect.value) errors.push("Please select a supplier.");
  if (!Number.isInteger(quantity) || quantity < 0) errors.push("Quantity must be greater than or equal to 0.");
  if (!unitPrice || unitPrice <= 0) errors.push("Selling price must be greater than 0.");
  if (!Number.isInteger(reorderLevel) || reorderLevel < 0) errors.push("Reorder level must be greater than or equal to 0.");
  if (!expiryInput.value) errors.push("Please select an expiry date.");

  if (expiryInput.min && expiryInput.value && expiryInput.value < expiryInput.min) {
    errors.push("Expiry date must be a future date after today.");
  }

  if (errors.length > 0) {
    event.preventDefault();
    showValidationErrors(errors);
  }
}

categorySelect.addEventListener("change", () => {
  selectedValues.product = "";
  selectedValues.variant = "";
  selectedValues.supplier = "";
  populateProducts();
});

productSelect.addEventListener("change", () => {
  selectedValues.variant = "";
  selectedValues.supplier = "";
  populateProductDetails();
});

productForm.addEventListener("submit", validateForm);
populateProducts();
