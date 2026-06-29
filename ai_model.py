print("STARTING...")

import pandas as pd
from sklearn.linear_model import LinearRegression

# Load dataset
data = pd.read_csv("sales_data.csv").head(200)
print("DATA LOADED")

# Convert date
data['date'] = pd.to_datetime(data['date'], dayfirst=True, errors='coerce')
data = data.dropna(subset=['date'])

# Create day number
data['day_number'] = (data['date'] - data['date'].min()).dt.days

# Clean numeric column
data['quantity_sold'] = pd.to_numeric(data['quantity_sold'], errors='coerce')
data = data.dropna()

print("TRAINING DONE")

# Group data by product
product_data = data.groupby('product')['quantity_sold'].sum().reset_index()

# Convert product names to numbers
from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
product_data['product_encoded'] = le.fit_transform(product_data['product'])

# Train model again for products
X = product_data[['product_encoded']]
y = product_data['quantity_sold']

model = LinearRegression()
model.fit(X, y)

def get_predictions():
    predictions = []

    for i, product in enumerate(product_data['product']):
        pred = model.predict([[i]])
        predictions.append({
            "name": product,
            "predicted": int(pred[0])
        })

    return predictions

if __name__ == "__main__":
    print("Running AI model...")

    predictions = get_predictions()

    for p in predictions:
        print(p)