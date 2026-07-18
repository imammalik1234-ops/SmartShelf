import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from models import Product, Sale

SALES_COLUMNS = [
    "product_id",
    "date",
    "category",
    "product",
    "variant",
    "supplier",
    "unit_price_rm",
    "quantity_sold",
    "total_sales_rm",
]

def load_sales_dataframe():
    rows = (
        Sale.query
        .join(Product, Sale.product_id == Product.product_id)
        .with_entities(
            Product.product_id,
            Sale.sale_date,
            Product.category,
            Product.name,
            Product.supplier,
            Product.unit_price,
            Sale.quantity
        )
        .order_by(Sale.sale_date.asc(), Sale.sale_id.asc())
        .all()
    )

    records = []

    for product_id, sale_date, category, product, supplier, unit_price, quantity in rows:
        quantity_sold = int(quantity)
        unit_price_rm = float(unit_price) if unit_price is not None else 0.0

        records.append({
            "product_id": product_id,
            "date": f"{sale_date.day}/{sale_date.month}/{sale_date.year}",
            "category": category,
            "product": product,
            "variant": product,
            "supplier": supplier,
            "unit_price_rm": unit_price_rm,
            "quantity_sold": quantity_sold,
            "total_sales_rm": float(round(quantity_sold * unit_price_rm, 2)),
        })

    df = pd.DataFrame(records, columns=SALES_COLUMNS)

    return df.astype({
        "product_id": "int64",
        "date": "object",
        "category": "object",
        "product": "object",
        "variant": "object",
        "supplier": "object",
        "unit_price_rm": "float64",
        "quantity_sold": "int64",
        "total_sales_rm": "float64",
    })

def get_predictions():
    # Load live sales data from MySQL using actual database products as the prediction unit.
    df = load_sales_dataframe()
    df["product_variant"] = df["product"] + " (" + df["variant"] + ")"
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)

    predictions = []

    grouped = df.groupby("product_id")

    for product_id, group in grouped:
        # Sort by date
        group = group.sort_values(by="date")
        product_name = group["product"].iloc[0]
        supplier = group["supplier"].iloc[0]

        # X = time steps
        X = np.arange(len(group)).reshape(-1, 1)

        # y = quantity sold
        y = group["quantity_sold"].values

        if len(y) < 2:
            continue

                # Split data into training (80%) and testing (20%)
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42
        )

        # Train the model
        model = LinearRegression()
        model.fit(X_train, y_train)

        # Test the model
        y_pred = model.predict(X_test)

        # Calculate MAE
        mae = mean_absolute_error(y_test, y_pred)

        print(f"{product_name} ({supplier}) -> MAE: {mae:.2f}")

        # Predict future demand
        future_step = np.array([[len(group)]])
        predicted = model.predict(future_step)[0]

        predictions.append({
            "product_id": int(product_id),
            "name": product_name,
            "supplier": supplier,
            "predicted": int(max(predicted, 0))
        })

    predictions = sorted(predictions, key=lambda x: x["predicted"], reverse=True)

    return predictions


if __name__ == "__main__":
    from app import app

    with app.app_context():
        result = get_predictions()
        for item in result:
            print(item)
