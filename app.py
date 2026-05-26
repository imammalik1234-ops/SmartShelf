from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask import Flask, request, render_template
from flask import render_template, request, redirect

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
@app.route('/dashboard')
def home():
    products = Product.query.all()
    total_products = len(products)
    low_stock = 0
    expiring = 0
    today = date.today()
    recent_products = []
    expiring_products = []

    for product in products:
        inventory = Inventory.query.filter_by(product_id=product.product_id).first()
        quantity = inventory.quantity if inventory else 0
        stock_status = "Low Stock" if quantity <= product.reorder_level else "In Stock"

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

    return render_template(
        'dashboard.html',
        total_products=total_products,
        low_stock=low_stock,
        expiring=expiring,
        recent_products=recent_products[:5],
        expiring_products=expiring_products[:5]
    )

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
def delete_product_api(product_id):
    product = Product.query.get(product_id)

    if product is None:
        return {"error": "Product not found"}, 404

    delete_product_records(product_id)

    return {"message": "Product deleted successfully"}

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

@app.route('/inventory-page')
def inventory_page():
    inventory_items = Inventory.query.all()
    products = []

    for item in inventory_items:
        product = Product.query.get(item.product_id)

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

@app.route('/expiry-alerts')
def expiry_alerts_page():
    return render_template('alerts.html')

@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get(product_id)

    if product is None:
        return redirect('/inventory-page')

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

if __name__ == '__main__':
    app.run(debug=True)
    
