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

@app.route('/')
@app.route('/dashboard')
@app.route('/')
@app.route('/dashboard')
def home():
    products = Product.query.all()
    reorder_needed = 0
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
    return render_template(
        'dashboard.html',
        total_products=total_products,
        low_stock=low_stock,
        expiring=expiring,
        recent_products=recent_products[:5],
        expiring_products=expiring_products[:5],
        reorder_needed=reorder_needed,
        ai_summary=ai_summary,
        smart_recommendation=smart_recommendation,
        recommendation_level=recommendation_level,
        urgent_actions=urgent_actions[ :3],
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
@app.route('/api/predictions', methods=['GET'])
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

    return render_template("ai-predictions.html", predictions=predictions)

if __name__ == '__main__':
    app.run(debug=True)
    
