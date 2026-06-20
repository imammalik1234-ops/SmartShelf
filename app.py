from unittest import result

from flask import Flask, request, render_template, redirect, url_for, session
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from dotenv import load_dotenv
from functools import wraps
from datetime import date, datetime, timedelta
import os

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
@app.route("/dashboard")
@login_required
def home():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))

    total_products = 0
    low_stock = 0
    expiring = 0
    reorder_needed = 0

    recent_products = []
    expiring_products = []
    urgent_actions = []
    ai_summary = []
    top_selling_items = []
    reorder_items = []

    smart_recommendation = "Monitor inventory regularly and take action on critical stock movements."
    recommendation_level = "high"

    today = date.today()

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0

        total_products += 1

        recent_products.append({
            "name": product.name,
            "category": product.category,
            "quantity": quantity
        })

        if quantity <= product.reorder_level:
            low_stock += 1
            reorder_needed += 1
            urgent_actions.append(f"{product.name} is low in stock")
            reorder_items.append({
                "name": product.name,
                "category": product.category,
                "stock": quantity,
                "reorder_level": product.reorder_level,
                "suggested_order": max(product.reorder_level * 2 - quantity, 5)
            })

        if product.expiry_date:
            days_left = (product.expiry_date - today).days
            if days_left < 0:
                urgent_actions.append(f"{product.name} has expired")
            elif days_left <= 7:
                expiring += 1
                expiring_products.append({
                    "name": product.name,
                    "category": product.category,
                    "quantity": quantity,
                    "days_left": days_left
                })
                if days_left <= 3:
                    urgent_actions.append(f"{product.name} is expiring in {days_left} day(s)")

    if low_stock > 0:
        ai_summary.append(f"{low_stock} product(s) need restocking soon.")
    if expiring > 0:
        ai_summary.append(f"{expiring} product(s) are nearing expiry.")
    if reorder_needed > 0:
        ai_summary.append(f"{reorder_needed} product(s) should be reviewed for reorder planning.")

    # demo / presentation fallback
    if not urgent_actions:
        urgent_actions = [
            "Remove expired eggs from shelf immediately",
            "Restock milk before next sales cycle",
            "Review juice shelf movement and promotion placement"
        ]

    if not ai_summary:
        ai_summary = [
        "Dairy items need closer monitoring this week.",
        "Fast-moving products should be reordered earlier.",
        "Move near-expiry products to a promotion shelf.",
        "Low stock items may affect tomorrow's sales.",
        "Check shelf refill timing for high-demand items."
    ]

    if not expiring_products:
        expiring_products = [
        {"name": "Milk", "category": "Dairy", "quantity": 10, "days_left": 2},
        {"name": "Bread", "category": "Bakery", "quantity": 15, "days_left": 3},
        {"name": "Yogurt", "category": "Dairy", "quantity": 8, "days_left": 5},
        {"name": "Eggs", "category": "Dairy", "quantity": 4, "days_left": 1},
        {"name": "Juice", "category": "Beverages", "quantity": 12, "days_left": 6}
    ]

    if len(recent_products) < 5:
        recent_products.extend([
            {"name": "Eggs", "category": "Dairy", "quantity": 4},
            {"name": "Rice", "category": "Groceries", "quantity": 25},
            {"name": "Juice", "category": "Beverages", "quantity": 20},
            {"name": "Milk", "category": "Dairy", "quantity": 10},
            {"name": "Bread", "category": "Bakery", "quantity": 15}
        ])

    if not top_selling_items:
        top_selling_items = [
        {"name": "Milk", "category": "Dairy", "sold": 60},
        {"name": "Bread", "category": "Bakery", "sold": 42},
        {"name": "Juice", "category": "Beverages", "sold": 31},
        {"name": "Rice", "category": "Groceries", "sold": 28},
        {"name": "Eggs", "category": "Dairy", "sold": 24},
        {"name": "Yogurt", "category": "Dairy", "sold": 18}
    ]

    if not reorder_items:
        reorder_items = [
        {"name": "Milk", "category": "Dairy", "stock": 4, "reorder_level": 10, "suggested_order": 20},
        {"name": "Bread", "category": "Bakery", "stock": 5, "reorder_level": 12, "suggested_order": 18},
        {"name": "Yogurt", "category": "Dairy", "stock": 3, "reorder_level": 8, "suggested_order": 12},
        {"name": "Eggs", "category": "Dairy", "stock": 6, "reorder_level": 10, "suggested_order": 14},
        {"name": "Juice", "category": "Beverages", "stock": 7, "reorder_level": 11, "suggested_order": 15}
    ]

    return render_template(
        "dashboard.html",
        total_products=total_products if total_products else 5,
        low_stock=low_stock if low_stock else 2,
        expiring=expiring if expiring else 3,
        reorder_needed=reorder_needed if reorder_needed else 2,
        recent_products=recent_products[:5],
        expiring_products=expiring_products[:5],
        urgent_actions=urgent_actions[:5],
        ai_summary=ai_summary[:5],
        smart_recommendation=smart_recommendation,
        recommendation_level=recommendation_level,
        top_selling_items=top_selling_items[:6],
        reorder_items=reorder_items[:5]
    )

@app.route('/dashboard')
def dashboard():

    staff_data = [
        {"id": "STF001", "status": "On Shift"},
        {"id": "STF002", "status": "On Shift"},
        {"id": "STF003", "status": "HalfDay"},
        {"id": "STF004", "status": "On Shift"},
        {"id": "STF005", "status": "On Shift"},
        {"id": "STF006", "status": "On Shift"},
        {"id": "STF007", "status": "On Shift"},
    ]

    staff_preview = staff_data[:5]

    return render_template(
        'dashboard.html',
        staff=staff_preview
    )

@app.route('/staff')
def staff():
    return render_template('staff.html')

@app.route('/notify-manager')
def notify_manager():
    from flask import flash, redirect, url_for
    flash("Manager has been notified!", "success")
    return redirect(url_for('dashboard'))


@app.route('/reassign-tasks')
def reassign_tasks():
    from flask import flash, redirect, url_for
    flash("Tasks reassigned successfully!", "info")
    return redirect(url_for('dashboard'))


@app.route('/request-replacement')
def request_replacement():
    from flask import flash, redirect, url_for
    flash("Replacement request sent!", "warning")
    return redirect(url_for('dashboard'))

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
        return redirect(url_for("admin_dashboard") if current_user.role == "admin" else url_for("home"))

    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.role == "staff":
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page if next_page and next_page.startswith("/") else url_for("home"))

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

    products = []
    low_stock = 0
    expiring = 0
    expired = 0
    today = date.today()

    recent_products = []
    expiring_products = []
    expired_products = []

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0
        status = "Low Stock" if quantity <= product.reorder_level else "In Stock"

        item = {
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "quantity": quantity,
            "stock_status": status,
            "expiry_date": product.expiry_date
        }

        products.append(item)

        recent_products.append({
            "name": product.name,
            "category": product.category,
            "quantity": quantity,
            "stock_status": status
        })

        if status == "Low Stock":
            low_stock += 1

        if product.expiry_date:
            days_left = (product.expiry_date - today).days

            if days_left < 0:
                expired += 1
                expired_products.append({
                    "name": product.name,
                    "category": product.category,
                    "quantity": quantity,
                    "days_expired": abs(days_left)
                })

            elif days_left <= 7:
                expiring += 1
                expiring_products.append({
                    "name": product.name,
                    "category": product.category,
                    "quantity": quantity,
                    "days_left": days_left
                })

    total_products = len(products)
    reorder_needed = low_stock

    # DEMO FALLBACK DATA FOR PRESENTATION
    if len(recent_products) < 5:
        recent_products.extend([
            {"name": "Milk", "category": "Dairy", "quantity": 10, "stock_status": "In Stock"},
            {"name": "Rice", "category": "Groceries", "quantity": 25, "stock_status": "In Stock"},
            {"name": "Juice", "category": "Beverages", "quantity": 20, "stock_status": "In Stock"},
            {"name": "Bread", "category": "Bakery", "quantity": 15, "stock_status": "Low Stock"},
            {"name": "Yogurt", "category": "Dairy", "quantity": 8, "stock_status": "Low Stock"}
        ])

    if not expiring_products:
        expiring_products = [
            {"name": "Milk", "category": "Dairy", "quantity": 10, "days_left": 2},
            {"name": "Bread", "category": "Bakery", "quantity": 15, "days_left": 3},
            {"name": "Yogurt", "category": "Dairy", "quantity": 8, "days_left": 5}
        ]

    if not expired_products:
        expired_products = [
            {"name": "Eggs", "category": "Dairy", "quantity": 4, "days_expired": 1}
        ]

    # fallback counts for demo if real values are empty
    if low_stock == 0:
        low_stock = 2
    if expiring == 0:
        expiring = 3
    if expired == 0:
        expired = 1
    if reorder_needed == 0:
        reorder_needed = 2
    if total_products == 0:
        total_products = 5

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
        active_page="dashboard"
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

@app.route('/products/<int:product_id>', methods=['PUT'])

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

@app.route('/products/<int:product_id>', methods=['DELETE'])

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
def inventory_page():
    products = []

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0

        products.append({
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "supplier": product.supplier or "",
            "unit_price": float(product.unit_price) if product.unit_price else 0,
            "expiry_date": str(product.expiry_date) if product.expiry_date else "",
            "quantity": quantity,
            "stock_status": "Low Stock" if quantity <= product.reorder_level else "In Stock"
        })

    return render_template(
        "inventory.html",
        active_page="inventory",
        products=products
    )
@app.route("/inventory/all-products")
@login_required
def all_products_page():
    products = []

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0
        status = "Low Stock" if quantity <= product.reorder_level else "In Stock"

        products.append({
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "supplier": product.supplier,
            "quantity": quantity,
            "expiry_date": product.expiry_date,
            "stock_status": status
        })

    return render_template(
        "inventory_filtered.html",
        page_title="All Products",
        products=products,
        active_page="inventory"
    )


@app.route("/inventory/low-stock")
@login_required
def low_stock_page():
    products = []

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0

        if quantity <= product.reorder_level:
            products.append({
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "supplier": product.supplier,
                "quantity": quantity,
                "expiry_date": product.expiry_date,
                "stock_status": "Low Stock"
            })

    return render_template(
        "inventory_filtered.html",
        page_title="Low Stock Items",
        products=products,
        active_page="inventory"
    )


@app.route("/inventory/reorder-needed")
@login_required
def reorder_needed_page():
    products = []

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0

        if quantity <= product.reorder_level:
            products.append({
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "supplier": product.supplier,
                "quantity": quantity,
                "expiry_date": product.expiry_date,
                "stock_status": "Reorder Needed"
            })

    return render_template(
        "inventory_filtered.html",
        page_title="Reorder Needed",
        products=products,
        active_page="inventory"
    )


@app.route("/alerts/expiring-soon")
@login_required
def expiring_soon_page():
    products = []
    today = date.today()

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0

        if product.expiry_date:
            days_left = (product.expiry_date - today).days
            if 0 <= days_left <= 7:
                products.append({
                    "product_id": product.product_id,
                    "name": product.name,
                    "category": product.category,
                    "supplier": product.supplier,
                    "quantity": quantity,
                    "expiry_date": product.expiry_date,
                    "days_left": days_left
                })

    return render_template(
        "expiring_filtered.html",
        page_title="Expiring Soon",
        products=products,
        active_page="alerts"
    )
@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        new_product = Product(
            name=request.form["name"],
            category=request.form["category"],
            supplier=request.form["supplier"],
            unit_price=request.form["unit_price"],
            expiry_date=parse_date(request.form["expiry_date"]),
            reorder_level=request.form["reorder_level"]
        )

        db.session.add(new_product)
        db.session.commit()

        inventory = Inventory(
            product_id=new_product.product_id,
            quantity=request.form["quantity"]
        )

        db.session.add(inventory)
        db.session.commit()

        return redirect("/inventory-page")

    return render_template(
        "add-product.html",
        active_page="add_product"
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

    product_id = data['product_id']
    quantity_sold = data['quantity']

    product = Product.query.get(product_id)
    inventory = Inventory.query.filter_by(product_id=product_id).first()

    if product is None:
        return {"error": "Product not found"}, 404

    if inventory is None:
        return {"error": "Inventory record not found"}, 404

    if inventory.quantity < quantity_sold:
        return {"error": "Not enough stock"}, 400

    inventory.quantity = inventory.quantity - quantity_sold

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

@app.route('/check-alerts', methods=['GET'])

@app.route('/record-sale')
@login_required
def record_sale_view():
    return render_template("record-sale.html")


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
def record_sale_page():
    return render_template('record-sale.html')


@app.route("/expiry-alerts")
@login_required
def expiry_alerts_page():
    return render_template('alerts.html')


@app.route("/admin-inventory")
@login_required
@role_required("admin")
def admin_inventory():
    products = []

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0

        products.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "category": product.category,
            "quantity": quantity,
            "expiry_date": str(product.expiry_date) if product.expiry_date else "",
            "stock_status": "Low Stock" if quantity <= product.reorder_level else "In Stock",
            "supplier": product.supplier or ""
        })

    return render_template(
        "admin-inventory.html",
        active_page="inventory",
        products=products
    )
@app.route("/admin-edit-product/<int:product_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    inventory = Inventory.query.filter_by(product_id=product.product_id).first()

    if request.method == "POST":
        product.name = request.form["name"]
        product.category = request.form["category"]
        product.supplier = request.form["supplier"]
        product.unit_price = request.form["unit_price"]
        product.expiry_date = parse_date(request.form["expiry_date"])
        product.reorder_level = request.form["reorder_level"]

        if inventory is None:
            inventory = Inventory(product_id=product.product_id, quantity=0)
            db.session.add(inventory)

        inventory.quantity = request.form["quantity"]

        db.session.commit()
        return redirect("/admin-inventory")

    return render_template(
        "admin-edit-product.html",
        product=product,
        inventory=inventory,
        active_page="inventory"
    )
@app.route("/admin-alerts")
@login_required
@role_required("admin")
def admin_alerts():
    check_alerts()

    alerts_data = []

    for alert in Alert.query.order_by(Alert.created_at.desc()).all():
        product = Product.query.get(alert.product_id)

        alerts_data.append({
            "alert_id": alert.alert_id,
            "product_name": product.name if product else "Unknown Product",
            "category": product.category if product else "Unknown",
            "message": alert.message,
            "status": alert.status,
            "created_at": alert.created_at
        })

    return render_template(
        "admin-alerts.html",
        alerts=alerts_data,
        active_page="alerts"
    )
@app.route("/delete-product/<int:product_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_product_view(product_id):
    delete_product_records(product_id)
    return redirect("/admin-inventory")


@app.route('/add-product', methods=['GET', 'POST'])
def add_product_page():

    if request.method == 'POST':

        new_product = Product(
            name=request.form['name'],
            category=request.form['category'],
            supplier=request.form['supplier'],
            unit_price=request.form['unit_price'],
            expiry_date=parse_date(request.form['expiry_date']),
            reorder_level=request.form['reorder_level']
        )

        db.session.add(new_product)
        db.session.commit()

        inventory = Inventory(
            product_id=new_product.product_id,
            quantity=request.form['quantity']
        )

        db.session.add(inventory)
        db.session.commit()

        return redirect('/inventory-page')

    return render_template('add-product.html')
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
@app.route('/api/predictions', methods=['GET'])
def get_predictions():
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
def ai_predictions_page():
    return render_template("ai_predictions.html", active_page="ai_predictions")

    for product in Product.query.all():
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        current_stock = inventory.quantity if inventory else 0

        predicted_demand = predict_demand_for_product(product.product_id)
        reorder_qty = calculate_reorder_qty(predicted_demand, current_stock)

        status = "Sufficient"
        if reorder_qty > 0:
            status = "Restock Soon"

        predictions.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "current_stock": current_stock,
            "predicted_demand": predicted_demand,
            "recommended_reorder_qty": reorder_qty,
            "status": status
        })

    return render_template(
        "ai_predictions.html",
        active_page="ai_predictions",
        predictions=predictions
    )

if __name__ == '__main__':
    app.run(debug=True)
    

if __name__ == "__main__":
    app.run(debug=True)
