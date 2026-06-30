import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

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

        model = LinearRegression()
        model.fit(X, y)

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