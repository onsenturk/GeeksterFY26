from pathlib import Path
import sqlite3

import pandas as pd

from .db import DB_PATH

BASE_DIR = Path(__file__).resolve().parent
DATA_ROOT = BASE_DIR.parent / "data"

DATASETS = {
    "dim_customer": DATA_ROOT / "cupid_chocolate_global" / "data" / "DimCustomer.csv",
    "dim_date": DATA_ROOT / "cupid_chocolate_global" / "data" / "DimDate.csv",
    "dim_product": DATA_ROOT / "cupid_chocolate_global" / "data" / "DimProduct.csv",
    "dim_promotion": DATA_ROOT / "cupid_chocolate_global" / "data" / "DimPromotion.csv",
    "dim_store": DATA_ROOT / "cupid_chocolate_global" / "data" / "DimStore.csv",
    "dim_supplier": DATA_ROOT / "cupid_chocolate_global" / "data" / "DimSupplier.csv",
    "fact_sales": DATA_ROOT / "cupid_chocolate_global" / "data" / "FactSales.csv",
    "gift_recommender": DATA_ROOT / "gifts" / "data" / "GiftRecommender.csv",
    "supply_chain": DATA_ROOT / "cupid_supply_chain" / "data" / "dataset_cupid_supply_chain.csv",
    "matchmaking": DATA_ROOT / "cupid_matchmaking" / "data" / "dataset_cupid_matchmaking.csv",
    "behavior_edges": DATA_ROOT / "cupid_behavior_graph_edges" / "data" / "dataset_cupid_behavior_graph_edges.csv",
    "broken_hearts_security": DATA_ROOT / "broken_hearts_security" / "data" / "dataset_broken_hearts_security.csv",
    "trust_safety": DATA_ROOT / "cupid_trust_safety" / "data" / "dataset_cupid_trust_safety.csv",
    "global_routing": DATA_ROOT / "cupid_global_routing" / "data" / "dataset_cupid_global_routing.csv",
    "love_notes_telemetry": DATA_ROOT / "love_notes_telemetry" / "data" / "dataset_love_notes_telemetry.csv",
    "work_dynamics": DATA_ROOT / "modern_work_dynamics" / "data" / "dataset_modern_work_dynamics.csv",
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_id ON fact_sales(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_sales_product_id ON fact_sales(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_sales_date_id ON fact_sales(date_id)",
    "CREATE INDEX IF NOT EXISTS idx_gift_recommender_customer_id ON gift_recommender(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_supply_chain_product_id ON supply_chain(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_matchmaking_user_id ON matchmaking(user_id)",
]


def _table_exists(conn, table_name):
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    return cur.fetchone() is not None


def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        for table_name, csv_path in DATASETS.items():
            if _table_exists(conn, table_name):
                continue
            df = pd.read_csv(csv_path)
            df.to_sql(table_name, conn, if_exists="replace", index=False)

        for statement in INDEXES:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()