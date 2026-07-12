const categorySelect = document.getElementById("category");
const productSelect = document.getElementById("product");
const variantSelect = document.getElementById("variant");
const supplierSelect = document.getElementById("supplier");
const productForm = document.getElementById("productForm");
const unitPriceInput = document.getElementById("unit_price");
const productPriceLookup = typeof priceLookup !== "undefined" ? priceLookup : {};
let priceManuallyEdited = Boolean(unitPriceInput && unitPriceInput.value);

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
    "Select a brand",
    selectedValues.supplier
  );

  updatePriceField();
}

function priceLookupKey() {
  return [
    categorySelect.value,
    productSelect.value,
    variantSelect.value,
    supplierSelect.value
  ].join("|");
}

function updatePriceField(force = false) {
  if (Object.keys(productPriceLookup).length === 0) return;
  if (!unitPriceInput || priceManuallyEdited && !force) return;

  const key = priceLookupKey();

  if (key && Object.prototype.hasOwnProperty.call(productPriceLookup, key) && productPriceLookup[key] !== "") {
    unitPriceInput.value = Number(productPriceLookup[key]).toFixed(2);
  } else {
    unitPriceInput.value = "";
  }
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
  const unitPriceValue = unitPriceInput ? unitPriceInput.value.trim() : "";
  const unitPrice = Number(unitPriceValue);
  const reorderLevel = Number(document.getElementById("reorder_level").value);
  const expiryInput = document.getElementById("expiry_date");

  if (!categorySelect.value) errors.push("Please select a category.");
  if (!productSelect.value) errors.push("Please select a product.");
  if (!variantSelect.value) errors.push("Please select a product variant.");
  if (!supplierSelect.value) errors.push("Please select a brand.");
  if (!Number.isInteger(quantity) || quantity < 0) errors.push("Quantity must be greater than or equal to 0.");
  if (!unitPriceValue) errors.push("Please enter a price.");
  if (unitPriceValue && (Number.isNaN(unitPrice) || unitPrice < 0)) errors.push("Price must be a valid non-negative number.");
  if (!Number.isInteger(reorderLevel) || reorderLevel < 0) errors.push("Restock level must be greater than or equal to 0.");
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
  priceManuallyEdited = false;
  populateProducts();
});

productSelect.addEventListener("change", () => {
  selectedValues.variant = "";
  selectedValues.supplier = "";
  priceManuallyEdited = false;
  populateProductDetails();
});

variantSelect.addEventListener("change", () => {
  priceManuallyEdited = false;
  updatePriceField(true);
});

supplierSelect.addEventListener("change", () => {
  priceManuallyEdited = false;
  updatePriceField(true);
});

if (unitPriceInput) {
  unitPriceInput.addEventListener("input", () => {
    priceManuallyEdited = true;
  });
}

productForm.addEventListener("submit", validateForm);
populateProducts();
