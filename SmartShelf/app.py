from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask import Flask, request, render_template

from database import db
from models import Product, Inventory, Sale
from datetime import date
from datetime import date, datetime
from models import Product, Inventory, Sale, Alert

load_dotenv()

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

@app.route('/')
def home():
    return render_template('record-sale.html')

@app.route('/products', methods=['GET'])
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

@app.route('/products', methods=['POST'])
def add_product():
    data = request.get_json()

    product = Product(
        name=data['name'],
        category=data['category'],
        supplier=data['supplier'],
        unit_price=data['unit_price'],
        expiry_date=data['expiry_date'],
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

print(app.url_map)

@app.route('/inventory', methods=['GET'])
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

@app.route('/sales', methods=['POST'])
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
def run_alert_check():
    check_alerts()
    return {"message": "Alerts checked successfully"}

@app.route('/alerts', methods=['GET'])
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

if __name__ == '__main__':
    app.run(debug=True)