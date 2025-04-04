import argparse
import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Training entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR"))
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN"))
    parser.add_argument("--test", type=str, default=os.environ.get("SM_CHANNEL_TEST"))
    args = parser.parse_args()

    train_df = pd.read_csv(os.path.join(args.train, "train.csv"))
    test_df = pd.read_csv(os.path.join(args.test, "test.csv"))

    features = [
        'venue_code', 'team', 'opp_code', 'hour', 'day_code',
        'gf_rolling', 'ga_rolling', 'sh_rolling', 'sot_rolling',
        'dist_rolling', 'fk_rolling', 'pk_rolling', 'pkatt_rolling',
        'opp_gf_rolling', 'opp_ga_rolling', 'opp_sh_rolling', 'opp_sot_rolling',
        'opp_dist_rolling', 'opp_fk_rolling', 'opp_pk_rolling', 'opp_pkatt_rolling'
    ]
    target = "target"

    X_train, y_train = train_df[features], train_df[target]
    X_test, y_test = test_df[features], test_df[target]

    model = RandomForestClassifier(n_estimators=100, random_state=2526)
    model.fit(X_train, y_train)

    joblib.dump(model, os.path.join(args.model_dir, "randomforest_model.pkl"))

    y_pred = model.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred))