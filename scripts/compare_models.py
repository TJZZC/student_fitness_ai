import os
import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier


def load_data():
    script_dir = os.path.dirname(__file__)
    csv_path = os.path.join(script_dir, "../data/students.csv")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"未找到数据文件：{csv_path}")

    df = pd.read_csv(csv_path)
    df["Date"] = pd.to_datetime(df["Date"])
    df["StudentID"] = df["StudentID"].astype(str).str.zfill(3)

    # 如果这些特征不存在，就自动补默认值，保证脚本能跑
    if "Gender" not in df.columns:
        df["Gender"] = "未知"
    if "Age" not in df.columns:
        df["Age"] = 15
    if "TrainFreq" not in df.columns:
        df["TrainFreq"] = 3
    if "SportType" not in df.columns:
        df["SportType"] = "综合训练"

    return df


def build_next_label_dataset(df, window_size=3):
    """
    用前3次记录预测下一次综合体质等级 Label
    """
    df = df.sort_values(["StudentID", "Date"]).reset_index(drop=True)

    rows = []

    for student_id, group in df.groupby("StudentID"):
        group = group.sort_values("Date").reset_index(drop=True)

        if len(group) <= window_size:
            continue

        for i in range(len(group) - window_size):
            history = group.iloc[i:i + window_size]
            target = group.iloc[i + window_size]

            row = {
                "StudentID": student_id,
                "TargetDate": target["Date"],
                "TargetLabel": target["Label"],

                # 静态/背景特征（取目标这一条或历史最后一条都可以）
                "Gender": target["Gender"],
                "Age": target["Age"],
                "TrainFreq": target["TrainFreq"],
                "SportType": target["SportType"],

                # 历史均值特征
                "BMI_mean": history["BMI"].mean(),
                "Lung_mean": history["LungCapacity"].mean(),
                "Run50m_mean": history["Run50m"].mean(),
                "Jump_mean": history["Jump"].mean(),
                "Label_mean": history["Label"].mean(),

                # 历史最后一次特征
                "BMI_last": history.iloc[-1]["BMI"],
                "Lung_last": history.iloc[-1]["LungCapacity"],
                "Run50m_last": history.iloc[-1]["Run50m"],
                "Jump_last": history.iloc[-1]["Jump"],
                "Label_last": history.iloc[-1]["Label"],

                # 趋势特征
                "BMI_trend": history.iloc[-1]["BMI"] - history.iloc[0]["BMI"],
                "Lung_trend": history.iloc[-1]["LungCapacity"] - history.iloc[0]["LungCapacity"],
                "Run50m_trend": history.iloc[-1]["Run50m"] - history.iloc[0]["Run50m"],
                "Jump_trend": history.iloc[-1]["Jump"] - history.iloc[0]["Jump"],
                "Label_trend": history.iloc[-1]["Label"] - history.iloc[0]["Label"],
            }

            rows.append(row)

    dataset = pd.DataFrame(rows)
    if dataset.empty:
        raise ValueError("样本不足，无法构建训练集。")

    return dataset


def build_preprocessor(X):
    numeric_features = [
        "Age", "TrainFreq",
        "BMI_mean", "Lung_mean", "Run50m_mean", "Jump_mean", "Label_mean",
        "BMI_last", "Lung_last", "Run50m_last", "Jump_last", "Label_last",
        "BMI_trend", "Lung_trend", "Run50m_trend", "Jump_trend", "Label_trend"
    ]

    categorical_features = [
        "Gender", "SportType"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler())
                ]),
                numeric_features
            ),
            (
                "cat",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore"))
                ]),
                categorical_features
            )
        ]
    )

    return preprocessor


def compare_models(X_train, X_test, y_train, y_test):
    preprocessor = build_preprocessor(X_train)

    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "RandomForest": RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            random_state=42
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=3,
            random_state=42
        ),
    }

    results = {}
    best_name = None
    best_score = -1
    best_pipeline = None

    for name, model in models.items():
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model)
        ])

        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        results[name] = {
            "accuracy": acc,
            "report": classification_report(y_test, y_pred, zero_division=0)
        }

        if acc > best_score:
            best_score = acc
            best_name = name
            best_pipeline = pipeline

    return results, best_name, best_score, best_pipeline


def main():
    df = load_data()
    dataset = build_next_label_dataset(df, window_size=3)

    feature_cols = [
        "Gender", "Age", "TrainFreq", "SportType",
        "BMI_mean", "Lung_mean", "Run50m_mean", "Jump_mean", "Label_mean",
        "BMI_last", "Lung_last", "Run50m_last", "Jump_last", "Label_last",
        "BMI_trend", "Lung_trend", "Run50m_trend", "Jump_trend", "Label_trend"
    ]

    X = dataset[feature_cols].copy()
    y = dataset["TargetLabel"].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y if y.nunique() > 1 else None
    )

    results, best_name, best_score, best_pipeline = compare_models(
        X_train, X_test, y_train, y_test
    )

    print("=== 模型对比结果 ===")
    for name, info in results.items():
        print(f"\n{name}")
        print("Accuracy:", round(info["accuracy"], 4))
        print(info["report"])

    print(f"\n最佳模型：{best_name} | Accuracy={best_score:.4f}")

    script_dir = os.path.dirname(__file__)
    model_dir = os.path.join(script_dir, "../models")
    os.makedirs(model_dir, exist_ok=True)

    model_path = os.path.join(model_dir, "best_next_label_model.pkl")
    joblib.dump(best_pipeline, model_path)

    print(f"最佳模型已保存：{model_path}")


if __name__ == "__main__":
    main()
