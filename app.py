<<<<<<< HEAD
from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask import Flask, request, render_template
from flask import render_template, request, redirect

from database import db
from models import Product, Inventory, Sale, Alert, Prediction
from datetime import date, timedelta
from datetime import date, datetime
from models import Product, Inventory, Sale, Alert
=======
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

>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714

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

<<<<<<< HEAD
=======
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


>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None

def check_alerts():
    products = Product.query.all()

    for product in products:
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()

        if inventory and inventory.quantity <= product.reorder_level:
            alert = Alert(
                product_id=product.product_id,
                alert_type="LOW_STOCK",
                message=f"{product.name} is low in stock. Current quantity: {inventory.quantity}",
                status="active",
                created_at=datetime.now()
            )
            db.session.add(alert)

        if product.expiry_date:
            days_left = (product.expiry_date - date.today()).days

            if days_left <= 3:
                alert = Alert(
                    product_id=product.product_id,
                    alert_type="EXPIRY",
                    message=f"{product.name} is expiring soon. Days left: {days_left}",
                    status="active",
                    created_at=datetime.now()
                )
                db.session.add(alert)

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

<<<<<<< HEAD
@app.route('/')
@app.route('/dashboard')
@app.route('/')
@app.route('/dashboard')
def home():
    products = Product.query.all()
    reorder_needed = 0
=======
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
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
    total_products = len(products)
    low_stock = 0
    expiring = 0
    today = date.today()
    recent_products = []
    expiring_products = []
    ai_summary = []
    urgent_actions = []

    for product in products:
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0
        stock_status = "Low Stock" if quantity <= product.reorder_level else "In Stock"

        predicted_demand = predict_demand_for_product(product.product_id)
        reorder_qty = calculate_reorder_qty(predicted_demand, quantity)

        if reorder_qty > 0:
            reorder_needed += 1

        recent_products.append({
            "name": product.name,
            "category": product.category,
            "quantity": quantity,
            "stock_status": stock_status
        })

        if inventory and quantity <= product.reorder_level:
            low_stock += 1

        if product.expiry_date:
            days_left = (product.expiry_date - today).days
            if 0 <= days_left <= 7:
                expiring += 1
                expiring_products.append({
                    "name": product.name,
                    "category": product.category,
                    "quantity": quantity,
                    "days_left": days_left
                })

<<<<<<< HEAD
    top_product = None
    top_prediction = 0

    for product in products:
        predicted = predict_demand_for_product(product.product_id)
        if predicted > top_prediction:
            top_prediction = predicted
            top_product = product.name

    if reorder_needed > 0:
        ai_summary.append({
        "level": "urgent",
        "title": "Restocking Priority",
        "message": f"Reorder attention needed for {reorder_needed} product(s)."
    })

    if expiring > 0:
        ai_summary.append({
        "level": "warning",
        "title": "Expiry Attention",
        "message": f"{expiring} product(s) are close to expiry and may need action."
    })

    if low_stock > 0:
        ai_summary.append({
        "level": "info",
        "title": "Low Stock Watch",
        "message": f"{low_stock} product(s) are currently running low."
    })
        recommendation_level = "stable"
    smart_recommendation = "Inventory looks stable today."

    if reorder_needed > 0:
        recommendation_level = "high"
        smart_recommendation = f"Restock priority detected. {reorder_needed} product(s) may affect sales if not replenished soon."
    elif expiring > 0:
        recommendation_level = "watch"
        smart_recommendation = f"Expiry attention needed. {expiring} product(s) may lead to avoidable waste if not reviewed soon."
    elif low_stock > 0:
        recommendation_level = "watch"
        smart_recommendation = f"Low stock risk detected. {low_stock} product(s) may reduce product availability if not monitored."
    elif top_product and top_prediction > 0:
        recommendation_level = "stable"
        smart_recommendation = f"Demand is expected to be highest for {top_product} ({top_prediction}), so stock planning should prioritise this item."

    if reorder_needed > 0:
        urgent_actions.append(f"Restock {reorder_needed} product(s) as a priority.")

    if expiring > 0:
        urgent_actions.append(f"Review {expiring} product(s) nearing expiry.")

    if low_stock > 0:
        urgent_actions.append(f"Monitor {low_stock} low-stock item(s) closely.")

    if top_product and top_prediction > 0:
      urgent_actions.append(f"Prioritise {top_product} in stock planning due to expected demand.") 
=======
    reorder_needed = low_stock

>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
    return render_template(
        'dashboard.html',
        total_products=total_products,
        low_stock=low_stock,
        expiring=expiring,
<<<<<<< HEAD
=======
        expired=expired,
        reorder_needed=reorder_needed,
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
        recent_products=recent_products[:5],
        expiring_products=expiring_products[:5],
        reorder_needed=reorder_needed,
        ai_summary=ai_summary,
        smart_recommendation=smart_recommendation,
        recommendation_level=recommendation_level,
        urgent_actions=urgent_actions[ :3],
    )
<<<<<<< HEAD
@app.route('/products', methods=['GET'])
=======


@app.route("/products", methods=["GET"])
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
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


<<<<<<< HEAD
@app.route('/reports')
def reports():
    products = Product.query.all()
    today = date.today()
=======
@app.route("/products", methods=["POST"])
@login_required
def add_product_api():
    data = request.get_json() or {}
    errors, cleaned = validate_product_form(
        validation_data_from_json(data),
        require_future_expiry=True,
    )
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714

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

<<<<<<< HEAD
@app.route('/products/<int:product_id>', methods=['PUT'])
=======

@app.route("/products/<int:product_id>", methods=["PUT"])
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
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

<<<<<<< HEAD
@app.route('/products/<int:product_id>', methods=['DELETE'])
=======

@app.route("/products/<int:product_id>", methods=["DELETE"])
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
def delete_product_api(product_id):
    product = Product.query.get(product_id)

    if product is None:
        return {"error": "Product not found"}, 404

    delete_product_records(product_id)

    return {"message": "Product deleted successfully"}

<<<<<<< HEAD
@app.route('/inventory', methods=['GET'])
=======
@app.route("/inventory", methods=["GET"])
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
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

<<<<<<< HEAD
@app.route('/inventory-page')
=======

@app.route("/inventory-page")
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
def inventory_page():
    inventory_items = Inventory.query.all()
    products = []

    for item in inventory_items:
        product = Product.query.get(item.product_id)

<<<<<<< HEAD
        if product:
            products.append({
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "supplier": product.supplier,
                "unit_price": product.unit_price,
                "expiry_date": product.expiry_date,
                "quantity": item.quantity
            })
=======
@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        form_data = form_data_from_request()
        errors, cleaned = validate_product_form(form_data, require_future_expiry=True)
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714

    return render_template('inventory.html', products=products)

def delete_product_records(product_id):
    Inventory.query.filter_by(product_id=product_id).delete()
    Alert.query.filter_by(product_id=product_id).delete()
    Sale.query.filter_by(product_id=product_id).delete()
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

<<<<<<< HEAD
@app.route('/sales', methods=['POST'])
=======
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
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
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

<<<<<<< HEAD
@app.route('/check-alerts', methods=['GET'])
=======

@app.route("/record-sale")
@login_required
def record_sale_page():
    return render_template("record-sale.html")


@app.route("/check-alerts", methods=["GET"])
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
def run_alert_check():
    check_alerts()
    return {"message": "Alerts checked successfully"}

<<<<<<< HEAD
@app.route('/alerts', methods=['GET'])
=======

@app.route("/alerts", methods=["GET"])
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
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

<<<<<<< HEAD
@app.route('/expiry-alerts')
=======
@app.route("/expiry-alerts")
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
def expiry_alerts_page():
    return render_template('alerts.html')

<<<<<<< HEAD
@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get(product_id)

    if product is None:
        return redirect('/inventory-page')
=======
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
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714

    inventory = Inventory.query.filter_by(product_id=product_id).first()

    if request.method == 'POST':
        product.name = request.form['name']
        product.category = request.form['category']
        product.supplier = request.form['supplier']
        product.unit_price = request.form['unit_price']
        product.expiry_date = parse_date(request.form['expiry_date'])
        product.reorder_level = request.form['reorder_level']

        if inventory is None:
            inventory = Inventory(product_id=product_id)
            db.session.add(inventory)

        inventory.quantity = request.form['quantity']

        db.session.commit()

        return redirect('/inventory-page')

    return render_template(
        'edit-product.html',
        product=product,
        quantity=inventory.quantity if inventory else 0
    )

@app.route('/delete-product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    delete_product_records(product_id)
    return redirect('/inventory-page')

<<<<<<< HEAD

@app.route('/add-product', methods=['GET', 'POST'])
def add_product():

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
@app.route('/api/predictions', methods=['GET'])
=======
@app.route("/api/predictions", methods=["GET"])
@login_required
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
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

<<<<<<< HEAD
    for product in products:
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
=======

@app.route("/ai-predictions")
@login_required
def ai_predictions_page():
    predictions = []

    for product in Product.query.all():
        inventory = inventory_for_product(product.product_id)
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
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
@app.route('/ai-predictions')
def ai_predictions_page():
    products = Product.query.all()
    predictions = []

    for product in products:
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        current_stock = inventory.quantity if inventory else 0

        predicted_demand = predict_demand_for_product(product.product_id)
        reorder_qty = calculate_reorder_qty(predicted_demand, current_stock)

        status = "Sufficient"
        if reorder_qty > 0:
            status = "Restock Soon"

        predictions.append({
            "product_name": product.name,
            "current_stock": current_stock,
            "predicted_demand": predicted_demand,
            "recommended_reorder_qty": reorder_qty,
            "status": status
        })

    return render_template("ai_predictions.html", predictions=predictions)

<<<<<<< HEAD
if __name__ == '__main__':
    app.run(debug=True)
    
=======

if __name__ == "__main__":
    app.run(debug=True)
>>>>>>> 33567981c1008f637daca387a0d7fc466ed5b714
