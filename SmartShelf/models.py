from database import db

class Product(db.Model):
    __tablename__ = "products"

    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(80))
    supplier = db.Column(db.String(100))
    unit_price = db.Column(db.Numeric(10, 2))
    expiry_date = db.Column(db.Date)
    reorder_level = db.Column(db.Integer, default=10)


class Inventory(db.Model):
    __tablename__ = "inventory"

    inventory_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id"))
    quantity = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime)


class Sale(db.Model):
    __tablename__ = "sales"

    sale_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id"))
    quantity = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.Date)

class Alert(db.Model):
    __tablename__ = "alerts"

    alert_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id"))
    alert_type = db.Column(db.String(50))
    message = db.Column(db.String(255))
    status = db.Column(db.String(30), default="active")
    created_at = db.Column(db.DateTime)