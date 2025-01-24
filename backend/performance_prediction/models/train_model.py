import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# Load the preprocessed data
file_path = "../../../data/cleaned_laliga_matches.csv"
df = pd.read_csv(file_path)


# Ensure the date column is in datetime format
df['date'] = pd.to_datetime(df['date'])

# Split the data into train and test sets based on time
train = df[df['date'] < '2023-06-04']  # Train on matches before the cutoff date
test = df[df['date'] > '2023-06-04']   # Test on matches after the cutoff date

# Define predictors (columns to use as features)
predictors = [
    'venue_code', 'team', 'opp_code', 'hour', 'day_code',
    'gf_rolling', 'ga_rolling', 'sh_rolling', 'sot_rolling',
    'dist_rolling', 'fk_rolling', 'pk_rolling', 'pkatt_rolling',
    'opp_gf_rolling', 'opp_ga_rolling', 'opp_sh_rolling', 'opp_sot_rolling',
    'opp_dist_rolling', 'opp_fk_rolling', 'opp_pk_rolling', 'opp_pkatt_rolling'
]

# Define the target variable
target = 'target'


# Separate features (X) and target (y) for train and test sets
X_train = train[predictors]
y_train = train[target]
X_test = test[predictors]
y_test = test[target]

# Initialize models
models = {
    "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=10, random_state=2526, class_weight='balanced'),
    "LogisticRegression": LogisticRegression(max_iter=1000, multi_class='multinomial'),
    "SVM": SVC(probability=True, kernel='rbf', random_state=2526),
    "DecisionTree": DecisionTreeClassifier(max_depth=10, random_state=2526),
    "NaiveBayes": GaussianNB(),
    "XGBoost": XGBClassifier(objective="multi:softprob", eval_metric="mlogloss", use_label_encoder=False, num_class=3),
    "LightGBM": LGBMClassifier(objective="multiclass", random_state=2526)

}

# Dictionary to store model scores and probabilities
model_scores = {}

# Train and evaluate each model
for name, model in models.items():
    print(f"Training {name}...")
    model.fit(X_train, y_train)  # Train the model
    y_pred = model.predict(X_test)  # Make predictions
    y_proba = model.predict_proba(X_test)  # Predict probabilities

    # Calculate accuracy
    accuracy = accuracy_score(y_test, y_pred)
    print(f"{name} Accuracy: {accuracy:.4f}")
    print(f"{name} Classification Report:")
    print(classification_report(y_test, y_pred))
    model_scores[name] = accuracy  # Store the accuracy score

    # Show class probabilities for the first few predictions
    print(f"\n{name} Predicted Probabilities (First 5):")
    for idx, probs in enumerate(y_proba[:5]):
        prob_dict = {f"Class {cls}": f"{prob*100:.2f}%" for cls, prob in enumerate(probs)}
        print(f"Match {idx+1}: {prob_dict}")

    # Save the model
    model_path = f"../models/{name.lower()}_model.pkl"
    joblib.dump(model, model_path)
    print(f"{name} model saved to {model_path}")

# Compare model scores
print("\nModel Performance Comparison:")
for name, score in model_scores.items():
    print(f"{name}: {score:.4f}")