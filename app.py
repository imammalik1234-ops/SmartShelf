from datetime import date, datetime
import os

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request
from flask_cors import CORS

from database import db
from models import Alert, Inventory, Product, Sale


load_dotenv(override=True)

app = Flask(__name__)
CORS(app)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def form_int(name, default=0):
    value = request.form.get(name)
    return int(value) if value not in (None, "") else default


def form_float(name, default=0):
    value = request.form.get(name)
    return float(value) if value not in (None, "") else default


def inventory_for_product(product_id):
    return Inventory.query.filter_by(product_id=product_id).first()


def stock_status(product, quantity):
    if quantity <= 0:
        return "Out of Stock"
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
        return

    days_left = (product.expiry_date - date.today()).days
    if days_left <= 7:
        upsert_alert(
            product,
            "EXPIRY",
            f"{product.name} is expiring soon. Days left: {days_left}.",
        )
    else:
        resolve_alert(product, "EXPIRY")


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
@app.route("/dashboard")
def dashboard():
    check_alerts()

    products = product_inventory_rows()
    total_products = len(products)
    low_stock = 0
    expiring = 0
    today = date.today()
    recent_products = []
    expiring_products = []

    for product in products:
        quantity = product["quantity"]
        status = product["stock_status"]

        recent_products.append({
            "name": product["name"],
            "category": product["category"],
            "quantity": quantity,
            "stock_status": status,
        })

        if status in ("Low Stock", "Out of Stock"):
            low_stock += 1

        if product["expiry_date"]:
            days_left = (product["expiry_date"] - today).days
            if days_left <= 7:
                expiring += 1
                expiring_products.append({
                    "name": product["name"],
                    "category": product["category"],
                    "quantity": quantity,
                    "days_left": days_left,
                })

    return render_template(
        "dashboard.html",
        total_products=total_products,
        low_stock=low_stock,
        expiring=expiring,
        recent_products=recent_products[:5],
        expiring_products=expiring_products[:5],
    )


@app.route("/products", methods=["GET"])
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
def add_product_api():
    data = request.get_json()

    product = Product(
        name=data["name"],
        category=data.get("category"),
        supplier=data.get("supplier"),
        unit_price=float(data.get("unit_price") or 0),
        expiry_date=parse_date(data.get("expiry_date")),
        reorder_level=int(data.get("reorder_level") or 0),
    )
    db.session.add(product)
    db.session.flush()

    inventory = Inventory(
        product_id=product.product_id,
        quantity=int(data.get("quantity") or 0),
        last_updated=datetime.now(),
    )
    db.session.add(inventory)

    create_low_stock_alert(product, inventory)
    create_expiry_alert(product)
    db.session.commit()

    return {"message": "Product added successfully", "product_id": product.product_id}, 201


@app.route("/products/<int:product_id>", methods=["PUT"])
def update_product_api(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return {"error": "Product not found"}, 404

    data = request.get_json()
    inventory = inventory_for_product(product_id)

    product.name = data["name"]
    product.category = data.get("category")
    product.supplier = data.get("supplier")
    product.unit_price = float(data.get("unit_price") or 0)
    product.expiry_date = parse_date(data.get("expiry_date"))
    product.reorder_level = int(data.get("reorder_level") or 0)

    if inventory is None:
        inventory = Inventory(product_id=product_id)
        db.session.add(inventory)

    inventory.quantity = int(data.get("quantity") or 0)
    inventory.last_updated = datetime.now()

    create_low_stock_alert(product, inventory)
    create_expiry_alert(product)
    db.session.commit()

    return {"message": "Product updated successfully"}


@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product_api(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return {"error": "Product not found"}, 404

    delete_product_records(product_id)
    return {"message": "Product deleted successfully"}


@app.route("/inventory", methods=["GET"])
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
def inventory_page():
    check_alerts()
    return render_template("inventory.html", products=product_inventory_rows())


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        product = Product(
            name=request.form["name"],
            category=request.form["category"],
            supplier=request.form["supplier"],
            unit_price=form_float("unit_price"),
            expiry_date=parse_date(request.form.get("expiry_date")),
            reorder_level=form_int("reorder_level"),
        )
        db.session.add(product)
        db.session.flush()

        inventory = Inventory(
            product_id=product.product_id,
            quantity=form_int("quantity"),
            last_updated=datetime.now(),
        )
        db.session.add(inventory)

        create_low_stock_alert(product, inventory)
        create_expiry_alert(product)
        db.session.commit()

        return redirect("/inventory-page")

    return render_template("add-product.html")


@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return redirect("/inventory-page")

    inventory = inventory_for_product(product_id)

    if request.method == "POST":
        product.name = request.form["name"]
        product.category = request.form["category"]
        product.supplier = request.form["supplier"]
        product.unit_price = form_float("unit_price")
        product.expiry_date = parse_date(request.form.get("expiry_date"))
        product.reorder_level = form_int("reorder_level")

        if inventory is None:
            inventory = Inventory(product_id=product_id)
            db.session.add(inventory)

        inventory.quantity = form_int("quantity")
        inventory.last_updated = datetime.now()

        create_low_stock_alert(product, inventory)
        create_expiry_alert(product)
        db.session.commit()

        return redirect("/inventory-page")

    return render_template(
        "edit-product.html",
        product=product,
        quantity=inventory.quantity if inventory else 0,
    )


@app.route("/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    delete_product_records(product_id)
    return redirect("/inventory-page")


@app.route("/remove-stock/<int:product_id>", methods=["POST"])
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
def record_sale_page():
    return render_template("record-sale.html")


@app.route("/check-alerts", methods=["GET"])
def run_alert_check():
    check_alerts()
    return {"message": "Alerts checked successfully"}


@app.route("/alerts", methods=["GET"])
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
def expiry_alerts_page():
    check_alerts()
    return render_template("alerts.html")


@app.route("/admin-alerts")
def admin_alerts_page():
    check_alerts()
    return render_template("admin-alerts.html")


@app.route("/api/predictions", methods=["GET"])
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

    return render_template("ai-predictions.html", predictions=predictions)


if __name__ == "__main__":
    app.run(debug=True)
