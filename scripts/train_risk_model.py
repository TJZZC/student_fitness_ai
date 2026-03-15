import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score


def build_risk_flag(row):
    reasons = []

    if row["BMI"] >= 28 or row["BMI"] <= 16:
        reasons.append("BMI风险")

    if row["Run50m"] >= 9.0:
        reasons.append("速度风险")

    if row["LungCapacity"] <= 2600:
        reasons.append("心肺风险")

    if row["Jump"] <= 160:
        reasons.append("力量风险")

    if row["Label"] >= 2:
        reasons.append("等级风险")

    return 1 if len(reasons) > 0 else 0


def main():
    script_dir = os.path.dirname(__file__)
    csv_path = os.path.join(script_dir, "../data/students.csv")
    model_dir = os.path.join(script_dir, "../models")
    os.makedirs(model_dir, exist_ok=True)

    df = pd.read_csv(csv_path)
    df["StudentID"] = df["StudentID"].astype(str).str.zfill(3)

    required_cols = [
        "BMI", "LungCapacity", "Run50m", "Jump",
        "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"缺少必要列: {missing_cols}")

    df["RiskLabel"] = df.apply(build_risk_flag, axis=1)

    X = df[required_cols].copy()
    y = df["RiskLabel"].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=6,
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print("风险预测模型 Accuracy:", round(acc, 4))
    print(classification_report(y_test, y_pred, zero_division=0))

    model_path = os.path.join(model_dir, "risk_predict_model.pkl")
    joblib.dump(model, model_path)
    print(f"模型已保存: {model_path}")


if __name__ == "__main__":
    main()
