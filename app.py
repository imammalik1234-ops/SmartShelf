from unittest import result

from flask import Flask, request, render_template, redirect, url_for, session
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from dotenv import load_dotenv
from functools import wraps
from datetime import date, datetime, timedelta
import os
import io
import csv
from flask import Response, render_template, request, redirect, url_for
from datetime import date

from database import db
from models import Alert, Inventory, Product, Sale, User


load_dotenv(override=True)


app = Flask(__name__)
app.secret_key = "secret123"
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


from functools import wraps
from flask_login import current_user
from flask import redirect, url_for

from functools import wraps
from flask_login import current_user
from flask import redirect, url_for

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("role_selection"))
            if current_user.role != role:
                if current_user.role == "admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return decorated
    return wrapper


def role_home():
    if not current_user.is_authenticated:
        return redirect(url_for("role_selection"))
    return redirect(url_for("admin_dashboard") if current_user.role == "admin" else url_for("home"))

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

def check_alerts():
    today = date.today()

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0

        # LOW STOCK ALERT
        if quantity <= product.reorder_level:
            existing_low_stock = Alert.query.filter_by(
                product_id=product.product_id,
                alert_type="LOW_STOCK",
                status="active"
            ).first()

            if existing_low_stock is None:
                low_stock_alert = Alert(
                    product_id=product.product_id,
                    alert_type="LOW_STOCK",
                    message=f"{product.name} is low in stock. Current quantity: {quantity}",
                    status="active",
                    created_at=datetime.now()
                )
                db.session.add(low_stock_alert)

        # EXPIRY ALERT
        if product.expiry_date:
            days_left = (product.expiry_date - today).days

            if 0 <= days_left <= 7:
                existing_expiry = Alert.query.filter_by(
                    product_id=product.product_id,
                    alert_type="EXPIRY",
                    status="active"
                ).first()

                if existing_expiry is None:
                    expiry_alert = Alert(
                        product_id=product.product_id,
                        alert_type="EXPIRY",
                        message=f"{product.name} is expiring soon. Days left: {days_left}",
                        status="active",
                        created_at=datetime.now()
                    )
                    db.session.add(expiry_alert)

            elif days_left < 0:
                existing_expired = Alert.query.filter_by(
                    product_id=product.product_id,
                    alert_type="EXPIRED",
                    status="active"
                ).first()

                if existing_expired is None:
                    expired_alert = Alert(
                        product_id=product.product_id,
                        alert_type="EXPIRED",
                        message=f"{product.name} has expired.",
                        status="active",
                        created_at=datetime.now()
                    )
                    db.session.add(expired_alert)

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


def inventory_for_product(product_id):
    return Inventory.query.filter_by(product_id=product_id).first()


def form_int(field_name, default=0):
    try:
        return int(request.form.get(field_name, default))
    except (TypeError, ValueError):
        return default


def product_form_defaults(product=None, inventory=None):
    product_name = product.name if product else ""
    category = product.category if product else ""
    product_value = product_name if category in PRODUCT_CATALOG and product_name in PRODUCT_CATALOG[category] else product_name

    return {
        "category": category,
        "product": product_value,
        "variant": product_name,
        "supplier": product.supplier if product else "",
        "quantity": str(inventory.quantity if inventory else ""),
        "expiry_date": product.expiry_date.isoformat() if product and product.expiry_date else "",
        "unit_price": str(product.unit_price if product and product.unit_price is not None else ""),
        "reorder_level": str(product.reorder_level if product else 10),
    }


def form_data_from_request():
    fields = ["category", "product", "variant", "supplier", "quantity", "expiry_date", "unit_price", "reorder_level"]
    return {field: request.form.get(field, "").strip() for field in fields}


def validate_product_form(form_data, require_catalog=True, existing_product_id=None, require_future_expiry=False):
    errors = []
    cleaned = {}

    category = form_data.get("category", "")
    product = form_data.get("product", "")
    variant = form_data.get("variant", "")
    supplier = form_data.get("supplier", "")

    if require_catalog:
        product_info = PRODUCT_CATALOG.get(category, {}).get(product)
        if product_info is None:
            errors.append("Please select a valid category and product.")
        else:
            if variant not in product_info["variants"]:
                errors.append("Please select a valid product variant.")
            if supplier not in product_info["suppliers"]:
                errors.append("Please select a valid supplier.")
    else:
        if not product:
            errors.append("Product name is required.")
        if not category:
            errors.append("Category is required.")
        if not supplier:
            errors.append("Supplier is required.")

    try:
        quantity = int(form_data.get("quantity", ""))
        if quantity < 0:
            errors.append("Quantity cannot be negative.")
    except ValueError:
        quantity = 0
        errors.append("Quantity must be a whole number.")

    try:
        unit_price = float(form_data.get("unit_price", ""))
        if unit_price <= 0:
            errors.append("Selling price must be greater than 0.")
    except ValueError:
        unit_price = 0
        errors.append("Selling price must be a valid number.")

    try:
        reorder_level = int(form_data.get("reorder_level", ""))
        if reorder_level < 0:
            errors.append("Reorder level cannot be negative.")
    except ValueError:
        reorder_level = 0
        errors.append("Reorder level must be a whole number.")

    try:
        expiry_date = parse_date(form_data.get("expiry_date"))
    except ValueError:
        expiry_date = None
        errors.append("Expiry date must use a valid date.")

    if expiry_date is None:
        errors.append("Expiry date is required.")
    elif require_future_expiry and expiry_date <= date.today():
        errors.append("Expiry date must be a future date.")

    product_name = variant if require_catalog else product
    if product_name:
        duplicate_query = Product.query.filter_by(name=product_name, category=category, supplier=supplier)
        if existing_product_id is not None:
            duplicate_query = duplicate_query.filter(Product.product_id != existing_product_id)
        if duplicate_query.first():
            errors.append("A product with the same name, category, and supplier already exists.")

    cleaned.update({
        "name": product_name,
        "category": category,
        "supplier": supplier,
        "quantity": quantity,
        "unit_price": unit_price,
        "expiry_date": expiry_date,
        "reorder_level": reorder_level,
    })

    return errors, cleaned


def render_product_form(template_name, **context):
    context.setdefault("catalog", PRODUCT_CATALOG)
    context.setdefault("tomorrow", (date.today() + timedelta(days=1)).isoformat())
    context.setdefault("today", date.today().isoformat())
    return render_template(template_name, **context)


def product_inventory_summary(product):
    inventory = inventory_for_product(product.product_id)
    quantity = inventory.quantity if inventory else 0
    reorder_level = product.reorder_level or 0
    days_left = None
    status_labels = []
    reorder_needed = quantity <= reorder_level

    if product.expiry_date:
        days_left = (product.expiry_date - date.today()).days
        if days_left < 0:
            status_labels.append("Expired")
        elif days_left <= 7:
            status_labels.append("Expiring Soon")

    if reorder_needed:
        status_labels.extend(["Low Stock", "Reorder Needed"])

    if not status_labels:
        status_labels.append("In Stock")

    predicted_demand = predict_demand_for_product(product.product_id)
    suggested_reorder = 0
    if reorder_needed:
        suggested_reorder = max(
            calculate_reorder_qty(predicted_demand, quantity),
            (reorder_level * 2) - quantity,
            1
        )

    return {
        "product_id": product.product_id,
        "product_name": product.name,
        "name": product.name,
        "category": product.category or "",
        "supplier": product.supplier or "",
        "unit_price": float(product.unit_price) if product.unit_price else 0,
        "quantity": quantity,
        "reorder_level": reorder_level,
        "expiry_date": product.expiry_date,
        "expiry_date_display": product.expiry_date.isoformat() if product.expiry_date else "",
        "days_left": days_left,
        "stock_status": status_labels[0],
        "status_labels": status_labels,
        "status_filter": " ".join(status_labels),
        "reorder_needed": reorder_needed,
        "predicted_demand": predicted_demand,
        "suggested_reorder": suggested_reorder,
    }


def inventory_summaries():
    return [product_inventory_summary(product) for product in Product.query.order_by(Product.name.asc()).all()]


def top_selling_items(limit=5):
    totals = {}
    for sale in Sale.query.all():
        totals[sale.product_id] = totals.get(sale.product_id, 0) + sale.quantity

    items = []
    for product_id, sold in totals.items():
        product = Product.query.get(product_id)
        if product:
            items.append({"name": product.name, "category": product.category or "", "sold": sold})

    return sorted(items, key=lambda item: item["sold"], reverse=True)[:limit]


def admin_dashboard_data():
    summaries = inventory_summaries()
    low_stock = [item for item in summaries if item["reorder_needed"]]
    expiring = [item for item in summaries if item["days_left"] is not None and 0 <= item["days_left"] <= 7]
    reorder_items = [item for item in summaries if item["reorder_needed"]]

    return {
        "stats": {
            "total_products": len(summaries),
            "low_stock": len(low_stock),
            "expiring": len(expiring),
            "reorder_needed": len(reorder_items),
        },
        "top_selling": top_selling_items(),
        "reorder_items": reorder_items[:5],
        "recent_alerts": recent_admin_alerts(),
    }


def staff_dashboard_data():
    summaries = inventory_summaries()
    low_stock = [item for item in summaries if item["reorder_needed"]]
    expiring = [item for item in summaries if item["days_left"] is not None and 0 <= item["days_left"] <= 7]
    reorder_items = [item for item in summaries if item["reorder_needed"]]

    return {
        "stats": {
            "total_products": len(summaries),
            "low_stock": len(low_stock),
            "expiring": len(expiring),
            "reorder_needed": len(reorder_items),
        },
        "low_stock_items": low_stock[:5],
        "expiring_items": expiring[:5],
        "reorder_items": reorder_items[:5],
        "top_selling": top_selling_items(),
        "recent_alerts": inventory_alert_items(limit=5),
    }


def admin_alert_sections():
    summaries = inventory_summaries()

    low_stock = [
        item for item in summaries
        if item["reorder_needed"]
    ]

    expiring_soon = [
        item for item in summaries
        if item["days_left"] is not None and 0 <= item["days_left"] <= 7
    ]

    reorder_needed = [
        item for item in summaries
        if item["reorder_needed"]
    ]

    return {
        "low_stock": low_stock,
        "expiring_soon": expiring_soon,
        "reorder_needed": reorder_needed,
    }


def recent_admin_alerts(limit=5):
    return inventory_alert_items(limit=limit)


def inventory_alert_items(limit=None):
    alerts = []

    for item in inventory_summaries():
        if item["days_left"] is not None:
            if item["days_left"] < 0:
                alerts.append({
                    "product_name": item["name"],
                    "alert_type": "Expired",
                    "days_remaining": item["days_left"],
                    "detail": "Expired",
                    "priority": "danger",
                    "sort_value": -1000 + item["days_left"],
                })
            elif item["days_left"] <= 7:
                alerts.append({
                    "product_name": item["name"],
                    "alert_type": "Expiring Soon",
                    "days_remaining": item["days_left"],
                    "detail": f"{item['days_left']} day{'s' if item['days_left'] != 1 else ''} remaining",
                    "priority": "danger" if item["days_left"] <= 2 else "warning",
                    "sort_value": item["days_left"],
                })

        if item["reorder_needed"]:
            alerts.append({
                "product_name": item["name"],
                "alert_type": "Reorder Needed",
                "days_remaining": None,
                "detail": f"{item['quantity']} in stock",
                "priority": "warning",
                "sort_value": 20,
            })

    alerts = sorted(alerts, key=lambda alert: (alert["sort_value"], alert["product_name"]))
    return alerts[:limit] if limit else alerts
def create_expiry_alert(product):
    if product.expiry_date:
        days_left = (product.expiry_date - date.today()).days

        if days_left <= 7:
            existing_alert = Alert.query.filter_by(
                product_id=product.product_id,
                alert_type="EXPIRY",
                status="active"
            ).first()

            if existing_alert is None:
                alert = Alert(
                    product_id=product.product_id,
                    alert_type="EXPIRY",
                    message=f"{product.name} is expiring soon. Days left: {days_left}.",
                    status="active",
                    created_at=datetime.now()
                )

                db.session.add(alert)

@app.route("/")
def index():
    return role_home()


@app.route("/dashboard")
@login_required
@role_required("staff")
def home():
    check_alerts()
    dashboard_data = staff_dashboard_data()

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        stats=dashboard_data["stats"],
        low_stock_items=dashboard_data["low_stock_items"],
        expiring_items=dashboard_data["expiring_items"],
        reorder_items=dashboard_data["reorder_items"],
        top_selling_items=dashboard_data["top_selling"],
        recent_alerts=dashboard_data["recent_alerts"]
    )

@app.route('/staff')
@login_required
@role_required("staff")
def staff():
    return render_template('staff.html')

@app.route('/notify-manager')
@login_required
@role_required("staff")
def notify_manager():
    from flask import flash, redirect, url_for
    flash("Manager has been notified!", "success")
    return redirect(url_for('home'))


@app.route('/reassign-tasks')
@login_required
@role_required("staff")
def reassign_tasks():
    from flask import flash, redirect, url_for
    flash("Tasks reassigned successfully!", "info")
    return redirect(url_for('home'))


@app.route('/request-replacement')
@login_required
@role_required("staff")
def request_replacement():
    from flask import flash, redirect, url_for
    flash("Replacement request sent!", "warning")
    return redirect(url_for('home'))

@app.route("/roles")
def role_selection():
    
    if current_user.is_authenticated:
        return role_home()
    return render_template("role_selection.html")

@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return role_home()

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "") 

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.role == "admin":
            login_user(user)
            return redirect(url_for("admin_dashboard"))
        
        error = "Invalid admin credentials."

    return render_template("admin_login.html", error=error)


@app.route("/login/staff", methods=["GET", "POST"])
def staff_login():
    if current_user.is_authenticated:
        return role_home()

    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.role == "staff":
            login_user(user)
            return redirect(url_for("home"))

        error = "Invalid staff credentials."

    return render_template("staff_login.html", error=error)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("role_selection"))


@app.route("/sales")
@login_required
@role_required("admin")
def sales():
    sales_records = [2000, 1500, 3000, 2500, 3000]
    total_sales = sum(sales_records)

    return render_template(
        "sales.html",
        total_sales=total_sales,
        sales_records=sales_records
    )

@app.route("/admin-dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    check_alerts()
    dashboard_data = admin_dashboard_data()

    return render_template(
        "admin-dashboard.html",
        active_page="dashboard",
        stats=dashboard_data["stats"],
        top_selling=dashboard_data["top_selling"],
        reorder_items=dashboard_data["reorder_items"],
        recent_alerts=dashboard_data["recent_alerts"]
    )

  
@app.route("/products", methods=["GET"])
@login_required
def get_products():
    products = Product.query.all()
    result = []

    for product in products:
        result.append({
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "supplier": product.supplier,
            "unit_price": float(product.unit_price) if product.unit_price else 0,
            "expiry_date": str(product.expiry_date),
            "reorder_level": product.reorder_level
        })

    return result


@app.route('/reports')
@login_required
@role_required("admin")
def reports():
    products = Product.query.all()
    today = date.today()

    low_stock_products = []
    expiring_products = []
    reorder_products = []

    for product in products:
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0

        if quantity <= product.reorder_level:
            low_stock_products.append(product)

        if product.expiry_date and product.expiry_date <= today + timedelta(days=7):
            expiring_products.append(product)

        predicted_demand = predict_demand_for_product(product.product_id)
        reorder_qty = calculate_reorder_qty(predicted_demand, quantity)

        if reorder_qty > 0:
            reorder_products.append({
                "product": product,
                "reorder_qty": reorder_qty
            })

    return render_template(
        'reports.html',
        low_stock_products=low_stock_products,
        expiring_products=expiring_products,
        reorder_products=reorder_products
    )


@app.route('/products', methods=['POST'])
@login_required
def add_product_api():
    data = request.get_json()

    product = Product(
        name=data['name'],
        category=data['category'],
        supplier=data['supplier'],
        unit_price=data['unit_price'],
        expiry_date=parse_date(data['expiry_date']),
        reorder_level=data['reorder_level']
    )

    db.session.add(product)
    db.session.commit()

    inventory = Inventory(
        product_id=product.product_id,
        quantity=data['quantity']
    )

    db.session.add(inventory)
    db.session.commit()

    return {
        "message": "Product added successfully",
        "product_id": product.product_id
    }

@app.route("/products/<int:product_id>", methods=["PUT"])
@login_required
def update_product_api(product_id):
    product = Product.query.get(product_id)

    if product is None:
        return {"error": "Product not found"}, 404

    data = request.get_json()
    inventory = Inventory.query.filter_by(product_id=product_id).first()

    product.name = data['name']
    product.category = data['category']
    product.supplier = data['supplier']
    product.unit_price = data['unit_price']
    product.expiry_date = parse_date(data['expiry_date'])
    product.reorder_level = data['reorder_level']

    if inventory is None:
        inventory = Inventory(product_id=product_id)
        db.session.add(inventory)

    inventory.quantity = data['quantity']

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
    inventory_items = Inventory.query.all()
    result = []

    for item in inventory_items:
        product = Product.query.get(item.product_id)

        result.append({
            "inventory_id": item.inventory_id,
            "product_id": item.product_id,
            "product_name": product.name if product else None,
            "category": product.category if product else None,
            "quantity": item.quantity,
            "last_updated": str(item.last_updated)
        })

    return result

@app.route('/inventory-page')
@login_required
@role_required("staff")
def inventory_page():
    return render_template(
        "inventory.html",
        active_page="inventory",
        products=inventory_summaries()
    )
@app.route("/inventory/all-products")
@login_required
@role_required("staff")
def all_products_page():
    return render_template(
        "inventory_filtered.html",
        page_title="All Products",
        products=inventory_summaries(),
        active_page="inventory"
    )


@app.route("/inventory/low-stock")
@login_required
@role_required("staff")
def low_stock_page():
    products = [item for item in inventory_summaries() if item["reorder_needed"]]

    return render_template(
        "inventory_filtered.html",
        page_title="Low Stock Items",
        products=products,
        active_page="inventory"
    )


@app.route("/inventory/reorder-needed")
@login_required
@role_required("staff")
def reorder_needed_page():
    products = [item for item in inventory_summaries() if item["reorder_needed"]]

    return render_template(
        "inventory_filtered.html",
        page_title="Reorder Needed",
        products=products,
        active_page="inventory"
    )


@app.route("/alerts/expiring-soon")
@login_required
@role_required("staff")
def expiring_soon_page():
    products = [
        item for item in inventory_summaries()
        if item["days_left"] is not None and 0 <= item["days_left"] <= 7
    ]

    return render_template(
        "expiring_filtered.html",
        page_title="Expiring Soon",
        products=products,
        active_page="alerts"
    )
@app.route("/add-product", methods=["GET", "POST"])
@login_required
@role_required("staff")
def add_product():
    form_defaults = {
        "category": "",
        "product": "",
        "variant": "",
        "supplier": "",
        "quantity": "",
        "expiry_date": "",
        "unit_price": "",
        "reorder_level": "10",
    }

    if request.method == "POST":
        form_data = {key: request.form.get(key, form_defaults[key]).strip() for key in form_defaults}
        errors, cleaned = validate_product_form(form_data)

        if errors:
            return render_template(
                "add-product.html",
                active_page="add_product",
                catalog=PRODUCT_CATALOG,
                form_data=form_data,
                errors=errors,
                tomorrow=(date.today() + timedelta(days=1)).isoformat(),
                is_admin_page=False
            ), 400

        new_product = Product(
            name=cleaned["name"],
            category=cleaned["category"],
            supplier=cleaned["supplier"],
            unit_price=cleaned["unit_price"],
            expiry_date=cleaned["expiry_date"],
            reorder_level=cleaned["reorder_level"]
        )

        db.session.add(new_product)
        db.session.commit()

        inventory = Inventory(
            product_id=new_product.product_id,
            quantity=cleaned["quantity"]
        )

        db.session.add(inventory)
        create_low_stock_alert(new_product, inventory)
        create_expiry_alert(new_product)
        db.session.commit()

        return redirect("/inventory-page")

    return render_template(
        "add-product.html",
        active_page="add_product",
        catalog=PRODUCT_CATALOG,
        form_data=form_defaults,
        errors=[],
        tomorrow=(date.today() + timedelta(days=1)).isoformat(),
        is_admin_page=False
    )


@app.route("/admin-add-product", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_add_product():
    form_defaults = product_form_defaults()

    if request.method == "POST":
        form_data = form_data_from_request()
        errors, cleaned = validate_product_form(form_data, require_future_expiry=True)

        if errors:
            return render_product_form(
                "admin-add-product.html",
                active_page="inventory",
                form_data=form_data,
                errors=errors,
                is_admin_page=True
            ), 400

        new_product = Product(
            name=cleaned["name"],
            category=cleaned["category"],
            supplier=cleaned["supplier"],
            unit_price=cleaned["unit_price"],
            expiry_date=cleaned["expiry_date"],
            reorder_level=cleaned["reorder_level"]
        )

        db.session.add(new_product)
        db.session.commit()

        inventory = Inventory(
            product_id=new_product.product_id,
            quantity=cleaned["quantity"],
            last_updated=datetime.now()
        )

        db.session.add(inventory)
        create_low_stock_alert(new_product, inventory)
        create_expiry_alert(new_product)
        db.session.commit()

        return redirect(url_for("admin_inventory", added=new_product.product_id))

    return render_product_form(
        "admin-add-product.html",
        active_page="inventory",
        form_data=form_defaults,
        errors=[],
        is_admin_page=True
    )

def delete_product_records(product_id):
    Inventory.query.filter_by(product_id=product_id).delete()
    Sale.query.filter_by(product_id=product_id).delete()
    Alert.query.filter_by(product_id=product_id).delete()
    Product.query.filter_by(product_id=product_id).delete()
    db.session.commit()

def create_low_stock_alert(product, inventory):
    if inventory.quantity <= product.reorder_level:
        existing_alert = Alert.query.filter_by(
            product_id=product.product_id,
            alert_type="LOW_STOCK",
            status="active"
        ).first()

        if existing_alert is None:
            alert = Alert(
                product_id=product.product_id,
                alert_type="LOW_STOCK",
                message=f"{product.name} is low in stock. Current quantity: {inventory.quantity}.",
                status="active",
                created_at=datetime.now()
            )

            db.session.add(alert)
@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
@login_required
@role_required("staff")
def edit_product(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return redirect("/inventory-page")

    inventory = inventory_for_product(product_id)

    if request.method == "POST":
        form_data = form_data_from_request()
        errors, cleaned = validate_product_form(form_data, existing_product_id=product_id)

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
@role_required("staff")
def delete_product(product_id):
    delete_product_records(product_id)
    return redirect("/inventory-page")


@app.route("/remove-stock/<int:product_id>", methods=["POST"])
@login_required
@role_required("staff")
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

    try:
        product_id = int(data.get('product_id'))
        quantity_sold = int(data.get('quantity'))
    except (TypeError, ValueError, AttributeError):
        return {"error": "Product and quantity are required"}, 400

    if quantity_sold <= 0:
        return {"error": "Quantity sold must be greater than 0"}, 400

    product = Product.query.get(product_id)
    inventory = Inventory.query.filter_by(product_id=product_id).first()

    if product is None:
        return {"error": "Product not found"}, 404

    if inventory is None:
        return {"error": "Inventory record not found"}, 404

    if inventory.quantity < quantity_sold:
        return {"error": "Not enough stock"}, 400

    inventory.quantity = inventory.quantity - quantity_sold
    inventory.last_updated = datetime.now()

    create_low_stock_alert(product, inventory)
    create_expiry_alert(product)

    sale = Sale(
        product_id=product_id,
        quantity=quantity_sold,
        sale_date=date.today()
    )

    db.session.add(sale)
    db.session.commit()

    return {
        "message": "Sale recorded successfully",
        "product_id": product_id,
        "quantity_sold": quantity_sold,
        "remaining_stock": inventory.quantity
    }


@app.route('/admin-record-sale')
@login_required
@role_required("admin")
def admin_record_sale():
    return render_template("admin-record-sale.html")


@app.route("/check-alerts", methods=["GET"])
@login_required
def run_alert_check():
    check_alerts()
    return {"message": "Alerts checked successfully"}



@app.route("/alerts", methods=["GET"])
@login_required
def get_alerts():
    alerts = Alert.query.all()
    result = []

    for alert in alerts:
        product = Product.query.get(alert.product_id)

        result.append({
            "alert_id": alert.alert_id,
            "product_name": product.name if product else None,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "status": alert.status,
            "created_at": str(alert.created_at)
        })

    return result

@app.route('/record-sale')
@login_required
@role_required("staff")
def record_sale_page():
    return render_template('record-sale.html')


@app.route("/expiry-alerts")
@login_required
@role_required("staff")
def expiry_alerts_page():
    check_alerts()
    sections = admin_alert_sections()

    return render_template(
        'alerts.html',
        low_stock_items=sections["low_stock"],
        expiring_items=sections["expiring_soon"],
        reorder_items=sections["reorder_needed"],
        active_page="alerts"
    )


@app.route("/admin-inventory")
@login_required
@role_required("admin")
def admin_inventory():
    success_message = None
    if request.args.get("added"):
        success_message = "Product added successfully."

    return render_template(
        "admin-inventory.html",
        active_page="inventory",
        products=inventory_summaries(),
        success_message=success_message
    )
@app.route("/admin-edit-product/<int:product_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    inventory = Inventory.query.filter_by(product_id=product.product_id).first()

    if request.method == "POST":
        form_data = {
            "product": request.form.get("name", "").strip(),
            "category": request.form.get("category", "").strip(),
            "supplier": request.form.get("supplier", "").strip(),
            "unit_price": request.form.get("unit_price", "").strip(),
            "expiry_date": request.form.get("expiry_date", "").strip(),
            "reorder_level": request.form.get("reorder_level", "").strip(),
            "quantity": request.form.get("quantity", "").strip(),
            "variant": request.form.get("name", "").strip(),
        }
        errors, cleaned = validate_product_form(form_data, require_catalog=False, existing_product_id=product_id)

        if errors:
            return render_template(
                "admin-edit-product.html",
                product=product,
                inventory=inventory,
                active_page="inventory",
                errors=errors
            ), 400

        product.name = cleaned["name"]
        product.category = cleaned["category"]
        product.supplier = cleaned["supplier"]
        product.unit_price = cleaned["unit_price"]
        product.expiry_date = cleaned["expiry_date"]
        product.reorder_level = cleaned["reorder_level"]

        if inventory is None:
            inventory = Inventory(product_id=product.product_id, quantity=0)
            db.session.add(inventory)

        inventory.quantity = cleaned["quantity"]
        inventory.last_updated = datetime.now()

        create_low_stock_alert(product, inventory)
        create_expiry_alert(product)
        db.session.commit()
        return redirect("/admin-inventory")

    return render_template(
        "admin-edit-product.html",
        product=product,
        inventory=inventory,
        active_page="inventory",
        errors=[]
    )
@app.route("/admin-alerts")
@login_required
@role_required("admin")
def admin_alerts():
    check_alerts()
    sections = admin_alert_sections()

    return render_template(
        "admin-alerts.html",
        low_stock_items=sections["low_stock"],
        expiring_items=sections["expiring_soon"],
        reorder_items=sections["reorder_needed"],
        active_page="alerts"
    )
@app.route("/admin-delete-product/<int:product_id>", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_product(product_id):
    delete_product_records(product_id)
    return redirect("/admin-inventory")


@app.route("/api/predictions", methods=["GET"])
@login_required
def api_predictions():
    products = Product.query.all()
    result = []

    for product in products:
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        current_stock = inventory.quantity if inventory else 0

        predicted_demand = predict_demand_for_product(product.product_id)
        reorder_qty = calculate_reorder_qty(predicted_demand, current_stock)

        result.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "current_stock": current_stock,
            "predicted_demand": predicted_demand,
            "recommended_reorder_qty": reorder_qty
        })

    return result


@app.route("/ai-predictions")
@login_required
@role_required("admin")
def ai_predictions():
    predictions = []

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        current_stock = inventory.quantity if inventory else 0

        predicted_demand = predict_demand_for_product(product.product_id)
        reorder_qty = calculate_reorder_qty(predicted_demand, current_stock)

        status = "Restock Soon" if reorder_qty > 0 else "Sufficient"

        predictions.append({
            "product_name": product.name,
            "current_stock": current_stock,
            "predicted_demand": predicted_demand,
            "recommended_reorder_qty": reorder_qty,
            "status": status   
        })

    return render_template(
    "ai_predictions.html",
    predictions=predictions,
    active_page="ai"   
)

@app.route("/admin-settings", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_settings():
    success_message = None
    error_message = None

    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_profile":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            
            if name and email:
                existing_user = User.query.filter(User.email == email, User.user_id != current_user.user_id).first()
                if existing_user:
                    error_message = "This email address is already registered to another account."
                else:
                    current_user.name = name
                    current_user.email = email
                    db.session.commit()
                    success_message = "Profile settings saved and updated successfully!"

    return render_template(
        "admin-settings.html",
        active_page="settings",
        success_message=success_message,
        error_message=error_message,
        profile_name=current_user.name,
        profile_email=current_user.email
    )


@app.route("/admin-settings/export-data")
@login_required
@role_required("admin")
def export_data():
    products = Product.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Product ID", "Product Name", "Category", "Supplier", "Unit Price", "Current Stock", "Expiry Date", "Reorder Level"])
    
    for product in products:
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        current_stock = inventory.quantity if inventory else 0
        
        writer.writerow([
            product.product_id,
            product.name,
            product.category or "N/A",
            product.supplier or "N/A",
            f"{product.unit_price:.2f}" if product.unit_price else "0.00",
            current_stock,
            product.expiry_date if product.expiry_date else "N/A",
            product.reorder_level
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=smartshelf_inventory_{date.today()}.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)
