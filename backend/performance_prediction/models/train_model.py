import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

# Load the preprocessed data
file_path = "../../../data/final_preprocessed_data.csv"
df = pd.read_csv(file_path)

# Separate features and target
X = df.drop(columns=["Result"])
y = df["Result"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=2526)

# Train the RandomForest model
model = RandomForestClassifier(random_state=2526)
model.fit(X_train, y_train)

# Evaluate the model
y_pred = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2f}")
print(classification_report(y_test, y_pred))

# Save the feature names
feature_names_file = "../models/model_features.pkl"
joblib.dump(X_train.columns.tolist(), feature_names_file)
print(f"Feature names saved to {feature_names_file}")

# Save the trained model in the module directory
model_file = "../models/random_forest_model.pkl"
joblib.dump(model, model_file)
print(f"Model saved to {model_file}")