from datetime import date, datetime, timedelta
import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from flask_cors import CORS
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from database import db
from models import Alert, Inventory, Product, Sale, User


load_dotenv(override=True)


app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'role_selection'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role != role:
                return redirect(url_for("dashboard"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


@app.context_processor
def inject_user_profile():
    if current_user.is_authenticated:
        name = current_user.name or "Staff Member"
        initials = "".join([part[0].upper() for part in name.split() if part])[:2] or "SM"
        return {
            "profile_name": name,
            "profile_email": current_user.email,
            "profile_initials": initials,
        }
    return {}


PRODUCT_CATALOG = {
    "Dairy": {
        "Milk": {
            "suppliers": ["Nestle", "Fresh Farms Co.", "Farmhouse Dairy"],
            "variants": ["Full Cream Milk", "Low Fat Milk", "Chocolate Milk"],
        },
        "Cheese": {
            "suppliers": ["Fresh Farms Co.", "Dairy Best"],
            "variants": ["Cheddar Cheese", "Mozzarella Cheese", "Cheese Slices"],
        },
        "Yogurt": {
            "suppliers": ["Dairy Best", "Farmhouse Dairy"],
            "variants": ["Plain Yogurt", "Strawberry Yogurt", "Greek Yogurt"],
        },
    },
    "Beverages": {
        "Coke": {
            "suppliers": ["Coca-Cola", "Local Beverage Distributor"],
            "variants": ["Coke 200ml", "Coke 500ml", "Coke 1.5L", "Diet Coke", "Coke Zero"],
        },
        "Pepsi": {
            "suppliers": ["PepsiCo", "Local Beverage Distributor"],
            "variants": ["Pepsi 200ml", "Pepsi 500ml", "Pepsi 1.5L", "Pepsi Max"],
        },
        "Sprite": {
            "suppliers": ["Coca-Cola", "Local Beverage Distributor"],
            "variants": ["Sprite 200ml", "Sprite 500ml", "Sprite 1.5L"],
        },
    },
    "Bakery": {
        "Bread": {
            "suppliers": ["Gardenia", "Sunshine Bakery", "Local Bakery"],
            "variants": ["White Bread", "Wholemeal Bread", "Multigrain Bread"],
        },
        "Bun": {
            "suppliers": ["Sunshine Bakery", "Local Bakery"],
            "variants": ["Plain Bun", "Cream Bun", "Red Bean Bun"],
        },
        "Croissant": {
            "suppliers": ["Local Bakery", "French Bakehouse"],
            "variants": ["Butter Croissant", "Chocolate Croissant"],
        },
    },
    "Produce": {
        "Apple": {
            "suppliers": ["Fresh Farms Co.", "Green Harvest"],
            "variants": ["Red Apple", "Green Apple", "Fuji Apple"],
        },
        "Banana": {
            "suppliers": ["Green Harvest", "Fresh Farms Co."],
            "variants": ["Cavendish Banana", "Mini Banana"],
        },
        "Lettuce": {
            "suppliers": ["Green Harvest", "Local Farm"],
            "variants": ["Romaine Lettuce", "Butterhead Lettuce"],
        },
    },
    "Pantry": {
        "Rice": {
            "suppliers": ["Golden Grain", "Pantry Supply Co."],
            "variants": ["White Rice 5kg", "Brown Rice 5kg", "Basmati Rice 5kg"],
        },
        "Pasta": {
            "suppliers": ["Pantry Supply Co.", "Italian Foods"],
            "variants": ["Spaghetti", "Macaroni", "Penne"],
        },
        "Cereal": {
            "suppliers": ["Nestle", "Kellogg's"],
            "variants": ["Corn Flakes", "Oat Cereal", "Chocolate Cereal"],
        },
    },
}


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def form_int(name, default=0):
    value = request.form.get(name)
    return int(value) if value not in (None, "") else default


def form_float(name, default=0):
    value = request.form.get(name)
    return float(value) if value not in (None, "") else default


def catalog_selection_for_name(name, category=None):
    categories = [category] if category in PRODUCT_CATALOG else PRODUCT_CATALOG.keys()

    for category_name in categories:
        for product_name, product_info in PRODUCT_CATALOG[category_name].items():
            if name == product_name or name in product_info["variants"]:
                return {
                    "category": category_name,
                    "product": product_name,
                    "variant": name if name in product_info["variants"] else "",
                }

    return {
        "category": category or "",
        "product": name or "",
        "variant": "",
    }


def product_form_defaults(product=None, inventory=None):
    selection = catalog_selection_for_name(product.name, product.category) if product else {}

    return {
        "category": selection.get("category", ""),
        "product": selection.get("product", ""),
        "variant": selection.get("variant", ""),
        "name": product.name if product else "",
        "supplier": product.supplier if product else "",
        "quantity": str(inventory.quantity) if inventory else "",
        "expiry_date": product.expiry_date.isoformat() if product and product.expiry_date else "",
        "unit_price": str(product.unit_price) if product and product.unit_price is not None else "",
        "reorder_level": str(product.reorder_level) if product and product.reorder_level is not None else "",
    }


def form_data_from_request():
    return {
        "category": request.form.get("category", "").strip(),
        "product": request.form.get("product", "").strip(),
        "variant": request.form.get("variant", "").strip(),
        "name": request.form.get("name", "").strip(),
        "supplier": request.form.get("supplier", "").strip(),
        "quantity": request.form.get("quantity", "").strip(),
        "expiry_date": request.form.get("expiry_date", "").strip(),
        "unit_price": request.form.get("unit_price", "").strip(),
        "reorder_level": request.form.get("reorder_level", "").strip(),
    }


def validation_data_from_json(data):
    category = str(data.get("category", "")).strip()
    name = str(data.get("name", "")).strip()
    product = str(data.get("product", "")).strip()
    variant = str(data.get("variant", "")).strip()

    if name and not product:
        selection = catalog_selection_for_name(name, category)
        product = selection["product"]
        variant = selection["variant"]

    return {
        "category": category,
        "product": product,
        "variant": variant,
        "name": name,
        "supplier": str(data.get("supplier", "")).strip(),
        "quantity": str(data.get("quantity", "")).strip(),
        "expiry_date": str(data.get("expiry_date", "")).strip(),
        "unit_price": str(data.get("unit_price", "")).strip(),
        "reorder_level": str(data.get("reorder_level", "")).strip(),
    }


def validate_product_form(data, require_future_expiry=False):
    errors = []
    category = data.get("category", "").strip()
    product = data.get("product", "").strip()
    variant = data.get("variant", "").strip()
    supplier = data.get("supplier", "").strip()

    if not category:
        errors.append("Please select a category.")
    elif category not in PRODUCT_CATALOG:
        errors.append("Please select a valid category.")

    product_info = None
    if category in PRODUCT_CATALOG:
        product_info = PRODUCT_CATALOG[category].get(product)

    if not product:
        errors.append("Please select a product.")
    elif product_info is None:
        errors.append("Please select a product that belongs to the chosen category.")

    product_name = product
    if product_info:
        variants = product_info.get("variants", [])
        suppliers = product_info.get("suppliers", [])

        if variants:
            if not variant:
                errors.append("Please select a product variant.")
            elif variant not in variants:
                errors.append("Please select a valid variant for the chosen product.")
            else:
                product_name = variant

        if not supplier:
            errors.append("Please select a supplier.")
        elif supplier not in suppliers:
            errors.append("Please select a supplier available for the chosen product.")
    elif not supplier:
        errors.append("Supplier cannot be empty.")

    try:
        quantity = int(data.get("quantity", ""))
        if quantity < 0:
            errors.append("Quantity must be greater than or equal to 0.")
    except ValueError:
        quantity = 0
        errors.append("Quantity must be a whole number.")

    try:
        unit_price = float(data.get("unit_price", ""))
        if unit_price <= 0:
            errors.append("Selling price must be greater than 0.")
    except ValueError:
        unit_price = 0
        errors.append("Selling price must be a valid number greater than 0.")

    try:
        reorder_level = int(data.get("reorder_level", ""))
        if reorder_level < 0:
            errors.append("Reorder level must be greater than or equal to 0.")
    except ValueError:
        reorder_level = 0
        errors.append("Reorder level must be a whole number.")

    expiry_date = parse_date(data.get("expiry_date", ""))
    if expiry_date is None:
        errors.append("Please select an expiry date.")
    elif require_future_expiry and expiry_date <= date.today():
        errors.append("Expiry date must be a future date after today.")

    if not product_name.strip():
        errors.append("Product name cannot be empty.")

    return errors, {
        "name": product_name.strip(),
        "category": category,
        "supplier": supplier,
        "quantity": quantity,
        "unit_price": unit_price,
        "reorder_level": reorder_level,
        "expiry_date": expiry_date,
    }


def render_product_form(template_name, form_data=None, errors=None, **context):
    return render_template(
        template_name,
        catalog=PRODUCT_CATALOG,
        form_data=form_data or product_form_defaults(),
        errors=errors or [],
        today=date.today().isoformat(),
        tomorrow=(date.today() + timedelta(days=1)).isoformat(),
        **context,
    )


def inventory_for_product(product_id):
    return Inventory.query.filter_by(product_id=product_id).first()


def stock_status(product, quantity):
    if product.expiry_date and product.expiry_date < date.today():
        return "Expired"
    if quantity <= (product.reorder_level or 0):
        return "Low Stock"
    return "In Stock"


def upsert_alert(product, alert_type, message):
    alert = Alert.query.filter_by(
        product_id=product.product_id,
        alert_type=alert_type,
        status="active",
    ).first()

    if alert is None:
        alert = Alert(
            product_id=product.product_id,
            alert_type=alert_type,
            status="active",
            created_at=datetime.now(),
        )
        db.session.add(alert)

    alert.message = message
    alert.created_at = datetime.now()
    return alert


def resolve_alert(product, alert_type):
    Alert.query.filter_by(
        product_id=product.product_id,
        alert_type=alert_type,
        status="active",
    ).update({"status": "resolved"})


def create_low_stock_alert(product, inventory):
    quantity = inventory.quantity if inventory else 0

    if product.expiry_date and product.expiry_date < date.today():
        resolve_alert(product, "LOW_STOCK")
        return

    if quantity <= (product.reorder_level or 0):
        upsert_alert(
            product,
            "LOW_STOCK",
            f"{product.name} is low in stock. Current quantity: {quantity}.",
        )
    else:
        resolve_alert(product, "LOW_STOCK")


def create_expiry_alert(product):
    if not product.expiry_date:
        resolve_alert(product, "EXPIRY")
        resolve_alert(product, "EXPIRED")
        return

    days_left = (product.expiry_date - date.today()).days
    if days_left < 0:
        resolve_alert(product, "EXPIRY")
        upsert_alert(
            product,
            "EXPIRED",
            f"{product.name} has expired. Days expired: {abs(days_left)}.",
        )
    elif days_left <= 7:
        resolve_alert(product, "EXPIRED")
        upsert_alert(
            product,
            "EXPIRY",
            f"{product.name} is expiring soon. Days left: {days_left}.",
        )
    else:
        resolve_alert(product, "EXPIRY")
        resolve_alert(product, "EXPIRED")


def check_alerts():
    product_ids = [row.product_id for row in Product.query.with_entities(Product.product_id).all()]
    if product_ids:
        Alert.query.filter(~Alert.product_id.in_(product_ids)).delete(synchronize_session=False)
    else:
        Alert.query.delete()

    for product in Product.query.all():
        inventory = inventory_for_product(product.product_id)
        if inventory is None:
            inventory = Inventory(
                product_id=product.product_id,
                quantity=0,
                last_updated=datetime.now(),
            )
            db.session.add(inventory)
            db.session.flush()

        create_low_stock_alert(product, inventory)
        create_expiry_alert(product)

    db.session.commit()


def delete_product_records(product_id):
    Inventory.query.filter_by(product_id=product_id).delete()
    Alert.query.filter_by(product_id=product_id).delete()
    Sale.query.filter_by(product_id=product_id).delete()
    Product.query.filter_by(product_id=product_id).delete()
    db.session.commit()


def predict_demand_for_product(product_id):
    sales = Sale.query.filter_by(product_id=product_id).order_by(Sale.sale_date.asc()).all()

    if not sales:
        return 0

    quantities = [sale.quantity for sale in sales]
    if len(quantities) < 3:
        return round(sum(quantities) / len(quantities))

    last_3 = quantities[-3:]
    return round(sum(last_3) / len(last_3))


def calculate_reorder_qty(predicted_demand, current_stock):
    reorder_qty = predicted_demand - current_stock
    return reorder_qty if reorder_qty > 0 else 0


def product_inventory_rows():
    rows = []

    products = Product.query.outerjoin(
        Inventory,
        Product.product_id == Inventory.product_id,
    ).order_by(Product.product_id.desc()).all()

    for product in products:
        inventory = inventory_for_product(product.product_id)
        quantity = inventory.quantity if inventory else 0

        rows.append({
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "supplier": product.supplier,
            "unit_price": product.unit_price,
            "expiry_date": product.expiry_date,
            "quantity": quantity,
            "stock_status": stock_status(product, quantity),
        })

    return rows

@app.route("/")
@app.route("/roles")
def role_selection():
    
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard") if current_user.role == "admin" else url_for("dashboard"))
    return render_template("role_selection.html")

@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard") if current_user.role == "admin" else url_for("dashboard"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "") 

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.role == "admin":
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page if next_page and next_page.startswith("/") else url_for("admin_dashboard"))
        
        error = "Invalid admin credentials."

    return render_template("admin_login.html", error=error)


@app.route("/login/staff", methods=["GET", "POST"])
def staff_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard") if current_user.role == "admin" else url_for("dashboard"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.role == "staff":
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page if next_page and next_page.startswith("/") else url_for("dashboard"))
        
        error = "Invalid staff credentials."

    return render_template("staff_login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("role_selection"))


@app.route("/admin-dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    check_alerts()

    products = product_inventory_rows()
    total_products = len(products)
    low_stock = 0
    expiring = 0
    expired = 0
    today = date.today()

    recent_products = []
    expiring_products = []
    expired_products = []

    for product in products:
        quantity = product["quantity"]
        status = product["stock_status"]

        recent_products.append({
            "name": product["name"],
            "category": product["category"],
            "quantity": quantity,
            "stock_status": status,
        })

        if status == "Low Stock":
            low_stock += 1

        if product["expiry_date"]:
            days_left = (product["expiry_date"] - today).days

            if days_left < 0:
                expired += 1
                expired_products.append({
                    "name": product["name"],
                    "category": product["category"],
                    "quantity": quantity,
                    "days_expired": abs(days_left),
                })

            elif days_left <= 7:
                expiring += 1
                expiring_products.append({
                    "name": product["name"],
                    "category": product["category"],
                    "quantity": quantity,
                    "days_left": days_left,
                })

    reorder_needed = low_stock

    return render_template(
        "admin-dashboard.html",
        total_products=total_products,
        low_stock=low_stock,
        expiring=expiring,
        expired=expired,
        reorder_needed=reorder_needed,
        recent_products=recent_products[:5],
        expiring_products=expiring_products[:5],
        expired_products=expired_products[:5],
        active_page="dashboard",
    )


@app.route("/dashboard")
@login_required
def dashboard():
    check_alerts()

    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))

    products = product_inventory_rows()
    total_products = len(products)
    low_stock = 0
    expiring = 0
    expired = 0
    today = date.today()
    recent_products = []
    expiring_products = []
    expired_products = []

    for product in products:
        quantity = product["quantity"]
        status = product["stock_status"]

        recent_products.append({
            "name": product["name"],
            "category": product["category"],
            "quantity": quantity,
            "stock_status": status,
        })

        if status == "Low Stock":
            low_stock += 1

        if product["expiry_date"]:
            days_left = (product["expiry_date"] - today).days
            if days_left < 0:
                expired += 1
                expired_products.append({
                    "name": product["name"],
                    "category": product["category"],
                    "quantity": quantity,
                    "days_expired": abs(days_left),
                })
            elif days_left <= 7:
                expiring += 1
                expiring_products.append({
                    "name": product["name"],
                    "category": product["category"],
                    "quantity": quantity,
                    "days_left": days_left,
                })

    reorder_needed = low_stock

    return render_template(
        "dashboard.html",
        total_products=total_products,
        low_stock=low_stock,
        expiring=expiring,
        expired=expired,
        reorder_needed=reorder_needed,
        recent_products=recent_products[:5],
        expiring_products=expiring_products[:5],
        expired_products=expired_products[:5],
    )


@app.route("/products", methods=["GET"])
@login_required
def get_products():
    result = []

    for product in Product.query.all():
        result.append({
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "supplier": product.supplier,
            "unit_price": float(product.unit_price) if product.unit_price else 0,
            "expiry_date": str(product.expiry_date) if product.expiry_date else "",
            "reorder_level": product.reorder_level,
        })

    return result


@app.route("/products", methods=["POST"])
@login_required
def add_product_api():
    data = request.get_json() or {}
    errors, cleaned = validate_product_form(
        validation_data_from_json(data),
        require_future_expiry=True,
    )

    if errors:
        return {"errors": errors}, 400

    product = Product(
        name=cleaned["name"],
        category=cleaned["category"],
        supplier=cleaned["supplier"],
        unit_price=cleaned["unit_price"],
        expiry_date=cleaned["expiry_date"],
        reorder_level=cleaned["reorder_level"],
    )
    db.session.add(product)
    db.session.flush()

    inventory = Inventory(
        product_id=product.product_id,
        quantity=cleaned["quantity"],
        last_updated=datetime.now(),
    )
    db.session.add(inventory)

    create_low_stock_alert(product, inventory)
    create_expiry_alert(product)
    db.session.commit()

    return {"message": "Product added successfully", "product_id": product.product_id}, 201


@app.route("/products/<int:product_id>", methods=["PUT"])
@login_required
def update_product_api(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return {"error": "Product not found"}, 404

    data = request.get_json() or {}
    errors, cleaned = validate_product_form(validation_data_from_json(data))
    if errors:
        return {"errors": errors}, 400

    inventory = inventory_for_product(product_id)

    product.name = cleaned["name"]
    product.category = cleaned["category"]
    product.supplier = cleaned["supplier"]
    product.unit_price = cleaned["unit_price"]
    product.expiry_date = cleaned["expiry_date"]
    product.reorder_level = cleaned["reorder_level"]

    if inventory is None:
        inventory = Inventory(product_id=product_id)
        db.session.add(inventory)

    inventory.quantity = cleaned["quantity"]
    inventory.last_updated = datetime.now()

    create_low_stock_alert(product, inventory)
    create_expiry_alert(product)
    db.session.commit()

    return {"message": "Product updated successfully"}


@app.route("/products/<int:product_id>", methods=["DELETE"])
@login_required
def delete_product_api(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return {"error": "Product not found"}, 404

    delete_product_records(product_id)
    return {"message": "Product deleted successfully"}

@app.route("/inventory", methods=["GET"])
@login_required
def get_inventory():
    result = []

    for item in product_inventory_rows():
        result.append({
            "product_id": item["product_id"],
            "product_name": item["name"],
            "category": item["category"],
            "quantity": item["quantity"],
            "expiry_date": str(item["expiry_date"]) if item["expiry_date"] else "",
            "stock_status": item["stock_status"],
        })

    return result


@app.route("/inventory-page")
@login_required
def inventory_page():
    check_alerts()
    return render_template("inventory.html", products=product_inventory_rows())


@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        form_data = form_data_from_request()
        errors, cleaned = validate_product_form(form_data, require_future_expiry=True)

        if errors:
            return render_product_form(
                "add-product.html",
                form_data=form_data,
                errors=errors,
            ), 400

        product = Product(
            name=cleaned["name"],
            category=cleaned["category"],
            supplier=cleaned["supplier"],
            unit_price=cleaned["unit_price"],
            expiry_date=cleaned["expiry_date"],
            reorder_level=cleaned["reorder_level"],
        )
        db.session.add(product)
        db.session.flush()

        inventory = Inventory(
            product_id=product.product_id,
            quantity=cleaned["quantity"],
            last_updated=datetime.now(),
        )
        db.session.add(inventory)

        create_low_stock_alert(product, inventory)
        create_expiry_alert(product)
        db.session.commit()

        return redirect("/inventory-page")

    return render_product_form("add-product.html")


@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return redirect("/inventory-page")

    inventory = inventory_for_product(product_id)

    if request.method == "POST":
        form_data = form_data_from_request()
        errors, cleaned = validate_product_form(form_data)

        if errors:
            return render_product_form(
                "edit-product.html",
                form_data=form_data,
                errors=errors,
                product=product,
                quantity=inventory.quantity if inventory else 0,
            ), 400

        product.name = cleaned["name"]
        product.category = cleaned["category"]
        product.supplier = cleaned["supplier"]
        product.unit_price = cleaned["unit_price"]
        product.expiry_date = cleaned["expiry_date"]
        product.reorder_level = cleaned["reorder_level"]

        if inventory is None:
            inventory = Inventory(product_id=product_id)
            db.session.add(inventory)

        inventory.quantity = cleaned["quantity"]
        inventory.last_updated = datetime.now()

        create_low_stock_alert(product, inventory)
        create_expiry_alert(product)
        db.session.commit()

        return redirect("/inventory-page")

    return render_template(
        "edit-product.html",
        catalog=PRODUCT_CATALOG,
        form_data=product_form_defaults(product, inventory),
        errors=[],
        today=date.today().isoformat(),
        product=product,
        quantity=inventory.quantity if inventory else 0,
    )


@app.route("/delete-product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    delete_product_records(product_id)
    return redirect("/inventory-page")


@app.route("/remove-stock/<int:product_id>", methods=["POST"])
@login_required
def remove_stock(product_id):
    product = Product.query.get(product_id)
    inventory = inventory_for_product(product_id)

    if product is None or inventory is None:
        return redirect("/inventory-page")

    quantity_to_remove = form_int("quantity_to_remove", 0)
    if quantity_to_remove > 0:
        inventory.quantity = max((inventory.quantity or 0) - quantity_to_remove, 0)
        inventory.last_updated = datetime.now()
        create_low_stock_alert(product, inventory)
        create_expiry_alert(product)
        db.session.commit()

    return redirect("/inventory-page")


@app.route("/sales", methods=["POST"])
@login_required
def record_sale():
    data = request.get_json()
    product_id = int(data["product_id"])
    quantity_sold = int(data["quantity"])

    product = Product.query.get(product_id)
    inventory = inventory_for_product(product_id)

    if product is None:
        return {"error": "Product not found"}, 404

    if inventory is None:
        return {"error": "Inventory record not found"}, 404

    if inventory.quantity < quantity_sold:
        return {"error": "Not enough stock"}, 400

    inventory.quantity -= quantity_sold
    inventory.last_updated = datetime.now()

    sale = Sale(
        product_id=product_id,
        quantity=quantity_sold,
        sale_date=date.today(),
    )
    db.session.add(sale)

    create_low_stock_alert(product, inventory)
    create_expiry_alert(product)
    db.session.commit()

    return {
        "message": "Sale recorded successfully",
        "product_id": product_id,
        "quantity_sold": quantity_sold,
        "remaining_stock": inventory.quantity,
    }


@app.route("/record-sale")
@login_required
def record_sale_page():
    return render_template("record-sale.html")

@app.route('/admin-record-sale')
@login_required
def admin_record_sale_page():
    return render_template('admin-record-sale.html')


@app.route("/check-alerts", methods=["GET"])
@login_required
def run_alert_check():
    check_alerts()
    return {"message": "Alerts checked successfully"}


@app.route("/alerts", methods=["GET"])
@login_required
def get_alerts():
    check_alerts()
    result = []

    for alert in Alert.query.filter_by(status="active").order_by(Alert.created_at.desc()).all():
        product = Product.query.get(alert.product_id)
        result.append({
            "alert_id": alert.alert_id,
            "product_name": product.name if product else None,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "status": alert.status,
            "created_at": str(alert.created_at) if alert.created_at else "",
        })

    return result


@app.route("/expiry-alerts")
@login_required
def expiry_alerts_page():
    check_alerts()
    return render_template("alerts.html")

@app.route("/admin-inventory")
@login_required
@role_required("admin")
def admin_inventory():

    products = []

    for item in product_inventory_rows():
        products.append({
            "product_id": item["product_id"],
            "product_name": item["name"],
            "category": item["category"],
            "quantity": item["quantity"],
            "expiry_date": str(item["expiry_date"]) if item["expiry_date"] else "",
            "stock_status": item["stock_status"],
            "supplier": item.get("supplier", "")
        })

    return render_template(
        "admin-inventory.html",
        active_page="inventory",
        products=products
    )

@app.route("/admin-edit-product/<int:product_id>")
@login_required
@role_required("admin")
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    inventory = Inventory.query.filter_by(product_id=product_id).first()
    print("INVENTORY:", inventory)


    return render_template(
    "admin-edit-product.html",
    product=product,
    inventory=inventory,
    active_page="inventory"
)
@app.route('/admin-alerts')
@login_required
@role_required("admin")
def admin_alerts():
    check_alerts()

    alerts = Alert.query.filter_by(status="active").all()

    expiring = [a for a in alerts if a.alert_type == "EXPIRY"]
    low_stock = [a for a in alerts if a.alert_type == "LOW_STOCK"]
    expired = [a for a in alerts if a.alert_type == "EXPIRED"]

    return render_template(
        "admin-alerts.html",
        expiring=expiring,
        low_stock=low_stock,
        expired=expired
    )


@app.route("/api/predictions", methods=["GET"])
@login_required
def api_predictions():
    products = Product.query.all()
    result = []

    for product in products:
        inventory = inventory_for_product(product.product_id)
        current_stock = inventory.quantity if inventory else 0
        predicted_demand = predict_demand_for_product(product.product_id)
        reorder_qty = calculate_reorder_qty(predicted_demand, current_stock)

        result.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "current_stock": current_stock,
            "predicted_demand": predicted_demand,
            "recommended_reorder_qty": reorder_qty,
        })

    return result


@app.route("/ai-predictions")
@login_required
def ai_predictions_page():
    predictions = []

    for product in Product.query.all():
        inventory = inventory_for_product(product.product_id)
        current_stock = inventory.quantity if inventory else 0
        predicted_demand = predict_demand_for_product(product.product_id)
        reorder_qty = calculate_reorder_qty(predicted_demand, current_stock)

        predictions.append({
            "product_name": product.name,
            "current_stock": current_stock,
            "predicted_demand": predicted_demand,
            "recommended_reorder_qty": reorder_qty,
            "status": "Restock Soon" if reorder_qty > 0 else "Sufficient",
        })

    return render_template("ai_predictions.html", predictions=predictions)


if __name__ == "__main__":
    app.run(debug=True)
