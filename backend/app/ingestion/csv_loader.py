import io
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


CANONICAL_COLUMNS = [
    "transaction_id",
    "timestamp",
    "source_account_id",
    "destination_account_id",
    "merchant_id",
    "merchant_category",
    "device_id",
    "ip_address",
    "transaction_amount",
    "currency",
    "transaction_type",
    "location",
    "transaction_status",
    "fraud_label",
]


class CSVDatasetInspector:
    """Handles CSV dataset preview, schema validation, column mapping, class distribution, and canonical conversion.

    Explicitly separates original public dataset columns (e.g., Kaggle Credit Card Fraud `Time, V1..V28, Amount, Class`)
    from simulated graph entities when a dataset does not natively include account/device/IP/merchant IDs.
    """

    @staticmethod
    def analyze_and_convert(
        csv_bytes: bytes,
        filename: str = "uploaded.csv",
        column_mapping: Optional[Dict[str, str]] = None,
        inject_synthetic_graph: bool = True,
        max_rows: int = 500,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        total_rows = int(len(df))
        if total_rows == 0:
            raise ValueError("Uploaded CSV dataset contains 0 rows.")

        mapping = column_mapping or {}
        if mapping:
            df = df.rename(columns=mapping)

        cols_lower = {c.lower(): c for c in df.columns}
        # Auto-map standard Kaggle Credit Card Fraud dataset columns if present
        auto_mapped: Dict[str, str] = {}
        if "amount" in cols_lower and "transaction_amount" not in df.columns:
            src_col = cols_lower["amount"]
            df["transaction_amount"] = df[src_col].apply(lambda x: max(0.01, float(x)) if pd.notnull(x) else 1.0)
            auto_mapped[src_col] = "transaction_amount"
        if "class" in cols_lower and "fraud_label" not in df.columns:
            src_col = cols_lower["class"]
            df["fraud_label"] = df[src_col].apply(lambda x: int(x) if pd.notnull(x) and int(x) in (0, 1) else None)
            auto_mapped[src_col] = "fraud_label"

        # Determine which canonical fields are genuine vs simulated
        genuine_fields: List[str] = [c for c in CANONICAL_COLUMNS if c in df.columns]
        simulated_fields: List[str] = []

        missing_value_report: Dict[str, int] = {
            str(col): int(df[col].isna().sum()) for col in df.columns
        }

        # Class distribution analysis
        class_distribution: Dict[str, Any] = {"labeled": False, "legitimate_0": 0, "fraud_1": 0, "unlabeled": total_rows, "fraud_ratio": None}
        if "fraud_label" in df.columns:
            vc = df["fraud_label"].value_counts(dropna=True).to_dict()
            legit_cnt = int(vc.get(0, 0))
            fraud_cnt = int(vc.get(1, 0))
            labeled_cnt = legit_cnt + fraud_cnt
            if labeled_cnt > 0:
                class_distribution = {
                    "labeled": True,
                    "legitimate_0": legit_cnt,
                    "fraud_1": fraud_cnt,
                    "unlabeled": total_rows - labeled_cnt,
                    "fraud_ratio": round(fraud_cnt / labeled_cnt, 6),
                }

        # Convert up to max_rows into canonical transactions
        subset = df.head(max_rows).copy()
        base_dt = datetime.now(timezone.utc) - timedelta(minutes=len(subset))
        converted_records: List[Dict[str, Any]] = []

        for idx, row in subset.iterrows():
            row_dict = row.to_dict()
            is_fraud_row = int(row_dict.get("fraud_label", 0) or 0) == 1

            tx_id = str(row_dict.get("transaction_id") or f"CSV-{filename.split('.')[0]}-{idx:05d}")
            if "transaction_id" not in genuine_fields and "transaction_id" not in simulated_fields:
                simulated_fields.append("transaction_id")

            # Timestamp handling
            raw_ts = row_dict.get("timestamp")
            if pd.isna(raw_ts) or not raw_ts:
                if "Time" in row_dict and pd.notna(row_dict["Time"]):
                    ts_iso = (base_dt + timedelta(seconds=float(row_dict["Time"]))).isoformat()
                else:
                    ts_iso = (base_dt + timedelta(seconds=int(idx) * 15)).isoformat()
                if "timestamp" not in simulated_fields:
                    simulated_fields.append("timestamp")
            else:
                ts_iso = str(raw_ts)

            # Graph entity fields
            if "source_account_id" in genuine_fields and pd.notna(row_dict.get("source_account_id")):
                src_acc = str(row_dict["source_account_id"])
            else:
                if "source_account_id" not in simulated_fields:
                    simulated_fields.append("source_account_id")
                src_acc = f"SIM-ACC-RING-{int(idx) % 4}" if (inject_synthetic_graph and is_fraud_row) else f"SIM-ACC-{int(idx) % 40:03d}"

            if "device_id" in genuine_fields and pd.notna(row_dict.get("device_id")):
                dev_id = str(row_dict["device_id"])
            else:
                if "device_id" not in simulated_fields:
                    simulated_fields.append("device_id")
                dev_id = "SIM-DEV-SHARED-FRAUD-99" if (inject_synthetic_graph and is_fraud_row) else f"SIM-DEV-{int(idx) % 40:03d}"

            if "ip_address" in genuine_fields and pd.notna(row_dict.get("ip_address")):
                ip_addr = str(row_dict["ip_address"])
            else:
                if "ip_address" not in simulated_fields:
                    simulated_fields.append("ip_address")
                ip_addr = "subnet-185.220.sim.x" if (inject_synthetic_graph and is_fraud_row) else f"subnet-10.0.{int(idx) % 16}.x"

            if "merchant_id" in genuine_fields and pd.notna(row_dict.get("merchant_id")):
                merch_id = str(row_dict["merchant_id"])
            else:
                if "merchant_id" not in simulated_fields:
                    simulated_fields.append("merchant_id")
                merch_id = "SIM-MERCH-CRYP-91" if (inject_synthetic_graph and is_fraud_row) else f"SIM-MERCH-{int(idx) % 10:02d}"

            merch_cat = str(row_dict.get("merchant_category") or ("CRYPTO_EXCHANGE" if is_fraud_row else "ECOMMERCE"))
            tx_amount = float(row_dict.get("transaction_amount") or 10.0)
            tx_amount = max(0.01, round(tx_amount, 2))

            converted_records.append(
                {
                    "transaction_id": tx_id,
                    "timestamp": ts_iso,
                    "source_account_id": src_acc,
                    "destination_account_id": str(row_dict["destination_account_id"]) if pd.notna(row_dict.get("destination_account_id")) else None,
                    "merchant_id": merch_id,
                    "merchant_category": merch_cat,
                    "device_id": dev_id,
                    "ip_address": ip_addr,
                    "transaction_amount": tx_amount,
                    "currency": str(row_dict.get("currency") or "USD"),
                    "transaction_type": str(row_dict.get("transaction_type") or "PURCHASE"),
                    "location": str(row_dict.get("location") or "US-NY"),
                    "transaction_status": str(row_dict.get("transaction_status") or "COMPLETED"),
                    "fraud_label": int(row_dict["fraud_label"]) if pd.notna(row_dict.get("fraud_label")) else None,
                    "is_demo": bool(simulated_fields),
                    "scenario_tag": "CSV_IMPORT_WITH_SYNTHETIC_GRAPH" if simulated_fields else "CSV_IMPORT_NATIVE",
                }
            )

        summary = {
            "filename": filename,
            "total_rows": total_rows,
            "rows_prepared": len(converted_records),
            "original_columns": [str(c) for c in df.columns],
            "auto_mapped_columns": auto_mapped,
            "genuine_canonical_fields": genuine_fields,
            "simulated_graph_fields": simulated_fields,
            "provenance_notice": (
                "Original dataset lacked native graph identifiers; synthetic DEMO graph entities (prefixed 'SIM-') were generated separately for relationship demonstration."
                if simulated_fields
                else "All canonical and graph fields were natively present in the uploaded dataset."
            ),
            "missing_value_report": missing_value_report,
            "class_distribution": class_distribution,
            "preview_rows": df.head(5).fillna("").to_dict(orient="records"),
        }
        return summary, converted_records
