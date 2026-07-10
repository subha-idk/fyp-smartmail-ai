# E-Commerce Customer Analytics Notebook

This folder contains the machine learning model implementation, statistical evaluations, and dataset generation pipelines for the **SmartMail AI+** project report (specifically supporting the quantitative findings for **Chapter 3: Methodology and Model Design** and **Chapter 4: Implementation and Results**).

## Folder Contents

* **`customer_analytics_model.ipynb`**: The main Jupyter Notebook containing:
  * Synthetic e-commerce user behavior dataset generation (1,000 samples).
  * Descriptive statistics (`df.describe()`, class distributions).
  * Exploratory Data Analysis (EDA) charts (feature distributions, label proportions, correlation heatmap).
  * Train-test partitioning (80/20 stratified split) and Standard Scaling.
  * Churn Prediction modeling using a **Random Forest Classifier**.
  * Purchase Intent modeling using a **Logistic Regression Classifier**.
  * Performance evaluations with statistical tables and matplotlib plots (ROC Curves, Precision-Recall Curves, Confusion Matrices, and Gini Feature Importance).
* **`requirements.txt`**: Python dependencies required to run this notebook locally.

## Setup & Running the Notebook

To set up the environment and run the notebook locally:

1. **Activate the Virtual Environment:**
   ```powershell
   # Windows (PowerShell)
   ..\backend\venv\Scripts\Activate.ps1
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Launch Jupyter:**
   ```bash
   jupyter notebook
   # Or run directly in VS Code / PyCharm / Google Colab
   ```

## Model Configurations

### 1. Customer Churn Predictor
* **Algorithm:** Random Forest Classifier (Ensemble)
* **Configuration:** `n_estimators=100`, `max_depth=10`, `class_weight='balanced'`
* **Features:** 12 behavioral and transactional signals (Recency, Frequency, Monetary value, Clickstream events).
* **Primary Metric:** ROC-AUC and Recall (maximizing detection of churn-prone users).

### 2. Purchase Intent Predictor
* **Algorithm:** Regularized Logistic Regression ($L_2$ Penalty)
* **Configuration:** `C=1.0`, `class_weight='balanced'`, scaled inputs.
* **Features:** Dynamic rolling behavioral events (e.g. 7-day events, 30-day cart additions).
* **Primary Metric:** Precision and F1-Score (minimizing false positives to prevent email spam).
