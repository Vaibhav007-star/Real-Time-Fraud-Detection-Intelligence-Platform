# Real-Time Fraud Detection Intelligence Platform

[![Live Demo](https://img.shields.io/badge/Live_Demo-GitHub_Pages-2ea44f.svg?style=for-the-badge&logo=github&logoColor=white)](https://vaibhav007-star.github.io/Real-Time-Fraud-Detection-Intelligence-Platform/)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Vaibhav007-star/Real-Time-Fraud-Detection-Intelligence-Platform)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-Cost--Sensitive-red.svg)](https://xgboost.readthedocs.io/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.4+-orange.svg)](https://scikit-learn.org/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38bdf8.svg)](https://tailwindcss.com/)
[![Kaggle Benchmark](https://img.shields.io/badge/Kaggle-284k%20European%20Cardholders-20beff.svg)](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
[![PR-AUC](https://img.shields.io/badge/PR--AUC-0.7834-success.svg)](#benchmark)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🌐 **Live Web Application**: [https://vaibhav007-star.github.io/Real-Time-Fraud-Detection-Intelligence-Platform/](https://vaibhav007-star.github.io/Real-Time-Fraud-Detection-Intelligence-Platform/)  
> ⚡ **Deploy to Vercel (1-Click)**: [Click to Deploy on Vercel](https://vercel.com/new/clone?repository-url=https://github.com/Vaibhav007-star/Real-Time-Fraud-Detection-Intelligence-Platform)

**An enterprise-grade, testable real-time financial fraud detection and investigation platform built with FastAPI, XGBoost, Graph Fraud Analytics, 24-feature streaming engine, and an interactive 6-page operations console.**

Trained & benchmarked on the official **Kaggle Credit Card Fraud Detection dataset (284,807 transactions, 492 frauds, 0.17% class imbalance)** with strict out-of-time chronological evaluation.

---

## 📌 Executive Architecture & Highlights

Modern financial institutions (Stripe, PayPal, Adyen, Capital One) combat sophisticated fraud through defense-in-depth:
1. **Real-Time Streaming Feature Engine (`backend/app/features/`)**:
   - Computes 24 rolling velocity and behavioral metrics across 1m, 5m, 15m, and 60m windows using bounded per-account in-memory state (`AccountRollingState`).
   - Guarantees zero temporal target leakage by computing features *before* appending transactions to history.
2. **Interactive Graph Fraud Topology Engine (`backend/app/graph/`)**:
   - Discovers shared-device clusters, IP proxy networks, repeated transfers, and circular money-mule rings ($A \to B \to C \to A$) that tabular ML models cannot detect.
   - Interactive SVG canvas with concentric orbital shells, pulsing risk halos, and 1-click pivot exploration.
3. **Calibrated Machine Learning Engine (`backend/app/ml/`)**:
   - Chronological 80/20 train/test split on 284,807 real European cardholder transactions.
   - Evaluates **Cost-Sensitive XGBoost (`scale_pos_weight`)**, **Balanced Random Forest**, and **Balanced Logistic Regression**.
   - Computes Precision-Recall AUC (PR-AUC), ROC-AUC, Recall @ 0.1% FPR, and banking financial ROI.
4. **Hybrid Risk Scoring & Live WebSocket Alerts (`backend/app/scoring/`, `backend/app/alerts/`)**:
   - Aggregates Supervised ML ($0.45$), Graph Risk ($0.30$), and Deterministic Rules ($0.25$) with correlation dampening into `LOW_RISK`, `REVIEW`, and `HIGH_RISK` tiers.
   - Real-time WebSocket push (`/ws/live`), duplicate suppression cooldown, analyst assignment, notes, and immutable audit logs.
5. **Interactive 6-Page Fraud Operations Console (`frontend/`)**:
   - **Overview Console**: Live KPIs, throughput, latency, and 1-click scenario & Kaggle burst triggers.
   - **Live Transaction Monitor**: Searchable, filterable ledger with full 24-feature SHAP attribution inspector.
   - **Alert Investigation**: Prioritized alert queue with analyst workflows (`IN_REVIEW`, `ACKNOWLEDGED`, `RESOLVED`).
   - **Graph Explorer**: SVG network visualizer with node pivot and hop depth selection (1-3 hops).
   - **Model Performance**: Multi-model leaderboard, financial ROI cards, top XGBoost feature importances, and an **Interactive Decision Threshold Sensitivity Optimizer**.
   - **System Health & Config**: Live scoring weight editor, CSV dataset validator, and Dead-Letter Queue (DLQ).

---

## 📊 Real Kaggle Model Benchmark & Financial ROI

<a name="benchmark"></a>

### Out-of-Time Test Set Performance (56,962 Unseen Real Transactions)

| Model Architecture | PR-AUC (Avg Precision) | ROC-AUC | Recall (Fraud Capture) | Precision | F1 Score | Recall @ 0.1% FPR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Class-Balanced)** | `0.7620` | `0.9863` | 89.3% | 7.1% | `0.1311` | 54.7% |
| **Balanced Random Forest (50 Trees)** | **`0.8202`** | `0.9714` | 73.3% | **96.5%** | **`0.8333`** | 73.3% |
| **XGBoost (Cost-Sensitive `scale_pos_weight`)** | `0.7834` | **`0.9811`** | **77.3%** | 63.0% | `0.6946` | **76.0%** |

### Financial ROI & Operational Cost Equation
$$\text{Net Financial Savings} = \text{Fraud Prevented} - (\text{Customer Friction Cost}) - (\text{Chargeback Penalties})$$
- **Customer Friction Cost**: \$20.00 per false positive alert.
- **Chargeback Penalties**: \$50.00 penalty fee + lost transaction value per missed fraud.

| Model Architecture | Fraud Prevented | Customer Friction Cost | Chargeback Penalties | Net Financial ROI |
| :--- | :---: | :---: | :---: | :---: |
| **Logistic Regression Baseline** | \$5,380.37 | -\$17,600.00 | -\$400.00 | **-\$12,619.63 (Net Loss)** |
| **Balanced Random Forest** | \$3,846.86 | -\$40.00 | -\$1,000.00 | **+\$2,806.86** |
| **XGBoost (Recommended)** | **\$5,093.21** | -\$680.00 | -\$850.00 | **+\$3,563.21 (Highest Net Savings)** |

---

## 🚀 Quick Start Guide

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/Vaibhav007-star/Real-Time-Fraud-Detection-Intelligence-Platform.git
cd Real-Time-Fraud-Detection-Intelligence-Platform

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install backend dependencies & ML libraries
pip install -r backend/requirements.txt scikit-learn xgboost kagglehub requests
```

### 2. Fetch Kaggle Dataset & Run Multi-Model Training

```bash
# 1. Fetch official real-world Kaggle creditcard.csv (284k transactions):
python scripts/fetch_kaggle_dataset.py

# 2. Run multi-model benchmark & produce models/kaggle_benchmark_report.json:
PYTHONPATH=backend python scripts/train_kaggle_real_model.py
```

### 3. Run Automated Test Suite (23 Tests)

```bash
cd backend
PYTHONPATH=. python -m unittest discover -s tests -p "test_*.py" -v
# Run end-to-end integration test runner:
PYTHONPATH=. python ../scripts/test_all_features.py
```

### 4. Start the Application Server

```bash
cd backend
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Open **`http://localhost:8000/`** in your browser to access the **Interactive Operations Console**.
- Open **`http://localhost:8000/docs`** for interactive Swagger API documentation.

---

## 📁 Repository Structure

```text
├── backend/
│   ├── app/
│   │   ├── alerts/         # Cooldown suppression & persistent alert manager
│   │   ├── api/            # REST routes (transactions, alerts, graph, models, stream)
│   │   ├── core/           # Settings, logging, and security config
│   │   ├── database/       # SQLite / PostgreSQL foreign-key relational manager
│   │   ├── features/       # 24-feature streaming rolling velocity engine
│   │   ├── graph/          # Typed graph intelligence & cycle detection engine
│   │   ├── ingestion/      # Validators, CSV loader, and synthetic stream generator
│   │   ├── ml/             # XGBoost & real Kaggle multi-model benchmark engine
│   │   ├── rules/          # Deterministic banking heuristics engine
│   │   ├── schemas/        # Pydantic v2 transaction & alert data models
│   │   ├── scoring/        # Hybrid risk aggregator with correlation dampening
│   │   └── services/       # Stateful platform orchestrator
│   └── tests/              # 23 unit & integration tests
├── frontend/
│   ├── src/
│   │   ├── components/     # Metric cards, risk badges, navigation
│   │   ├── pages/          # 6 console pages (Overview, Monitor, Alerts, Graph, Model, Health)
│   │   ├── services/       # Typed REST & WebSocket API client
│   │   └── types/          # TypeScript domain interfaces
│   └── dist/               # Compiled production assets
├── data/
│   ├── kaggle/             # Real Kaggle benchmark samples (5,000 rows)
│   └── sample/             # Canonical synthetic replay streams
├── models/                 # Serialized XGBoost model artifacts & metadata reports
├── scripts/                # CLI automation (train_kaggle_real_model.py, test_all_features.py)
└── docs/                   # Internship Portfolio & Technical Interview Guide
```

---

## 👤 Author & Contact

**Vaibhav Lohchab**  
- **GitHub**: [@Vaibhav007-star](https://github.com/Vaibhav007-star)  
- **Email**: [Vaibhavlohchab1@gmail.com](mailto:Vaibhavlohchab1@gmail.com)  

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
