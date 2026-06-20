from database import db
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("admin", "staff", name="user_roles"), default="staff")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.user_id)
    
    from database import db

class Staff(db.Model):
    __tablename__ = 'staff'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(10))
    status = db.Column(db.String(20))


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

class Prediction(db.Model):
    __tablename__ = "predictions"

    prediction_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id"))
    predicted_demand = db.Column(db.Integer)
    recommended_reorder_qty = db.Column(db.Integer)
    generated_on = db.Column(db.Date)