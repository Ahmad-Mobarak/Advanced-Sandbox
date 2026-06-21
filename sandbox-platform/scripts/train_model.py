#!/usr/bin/env python3
"""
Advanced Cybersecurity Sandbox Platform
ML Model Training Script

Generates synthetic training data and trains the XGBoost false-positive
classifier. Saves the model to models/false_positive_classifier.json.

Usage:
    python scripts/train_model.py
    python scripts/train_model.py --samples 10000
"""

import sys
import os
import argparse

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ml.training_data_generator import generate_training_data, save_to_csv
from src.ml.false_positive_classifier import FalsePositiveClassifier

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import numpy as np


def main():
    parser = argparse.ArgumentParser(description="Train the ML false-positive classifier")
    parser.add_argument("--samples", type=int, default=5000, help="Number of training samples")
    parser.add_argument("--malicious-ratio", type=float, default=0.4, help="Fraction of malicious samples")
    parser.add_argument("--model-dir", type=str, default="./models", help="Directory to save the model")
    args = parser.parse_args()

    print("=" * 60)
    print("  ML False-Positive Classifier — Training Pipeline")
    print("=" * 60)

    # Step 1: Generate training data
    print(f"\n[1/4] Generating {args.samples} synthetic training samples...")
    X, y = generate_training_data(
        n_samples=args.samples,
        malicious_ratio=args.malicious_ratio,
    )

    # Save to CSV for reference
    csv_path = save_to_csv(X, y, "./storage/training_data.csv")
    print(f"       Training data saved to: {csv_path}")

    # Step 2: Train/test split
    print("\n[2/4] Splitting data into train/test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )
    print(f"       Train: {len(X_train)} samples | Test: {len(X_test)} samples")

    # Step 3: Train the model
    print("\n[3/4] Training XGBoost classifier...")
    classifier = FalsePositiveClassifier(model_path=args.model_dir)
    classifier.train(X_train, y_train, eval_set=(X_test, y_test))

    # Step 4: Evaluate
    print("\n[4/4] Evaluating model performance...")
    y_pred = classifier.model.predict(X_test)
    y_proba = classifier.model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 60)
    print("  MODEL EVALUATION RESULTS")
    print("=" * 60)
    print(f"\nClassification Report:\n{classification_report(y_test, y_pred, target_names=['Benign', 'Malicious'])}")
    print(f"Confusion Matrix:\n{confusion_matrix(y_test, y_pred)}")

    auc = roc_auc_score(y_test, y_proba)
    print(f"\nROC AUC Score: {auc:.4f}")

    # Summary
    precision = float(classification_report(y_test, y_pred, output_dict=True)["weighted avg"]["precision"])
    recall = float(classification_report(y_test, y_pred, output_dict=True)["weighted avg"]["recall"])
    f1 = float(classification_report(y_test, y_pred, output_dict=True)["weighted avg"]["f1-score"])

    print(f"\n{'='*60}")
    print(f"  MODEL SAVED: {args.model_dir}/false_positive_classifier.json")
    print(f"  Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f} | AUC: {auc:.4f}")
    print(f"{'='*60}")

    if auc > 0.9:
        print("\n[+] Model quality: EXCELLENT -- ready for production!")
    elif auc > 0.8:
        print("\n[+] Model quality: GOOD -- suitable for deployment.")
    else:
        print("\n[!] Model quality: FAIR -- consider adding more training data.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
