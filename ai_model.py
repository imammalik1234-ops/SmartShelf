import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

def get_predictions():
    # Load your actual sales data
    df = pd.read_csv("sales_data.csv")
    df["product_variant"] = df["product"] + " (" + df["variant"] + ")"
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)

    predictions = []

    grouped = df.groupby("product_variant")

    for product, group in grouped:
        # Sort by date
        group = group.sort_values(by="date")

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

        print(f"{product} -> MAE: {mae:.2f}")

        # Predict future demand
        future_step = np.array([[len(group)]])
        predicted = model.predict(future_step)[0]

        predictions.append({
            "name": product,
            "predicted": int(max(predicted, 0))
        })

    predictions = sorted(predictions, key=lambda x: x["predicted"], reverse=True)

    return predictions


if __name__ == "__main__":
    result = get_predictions()
    for item in result:
        print(item)