"""Build the procurement spend and master-data analysis outputs.

Usage:
    python src/build_analysis.py

Expected input:
    data/raw/Spend Analytics.xlsx
"""

from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "Spend Analytics.xlsx"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"


SOURCE_COLUMNS = [
    "Purch.Doc.", "Item", "Changed On", "Short Text", "Material", "CoCd",
    "Plnt", "SLoc", "Matl Group", "PO Quantity", "OUn", "Net Price",
    "Per", "Net Value", "Gross value", "NCM Code", "Requested By",
    "Requirement Urgency", "Ordered By", "Approved By", "Priority",
    "Section", "Indenter ID", "Input Tax Credit", "Spend_Class",
]


def snake_case(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    return value.strip("_").lower()


def canonical_text(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9]+", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def suggested_category(text: str) -> str:
    rules = {
        "Animal feed and nutrition": ["feed", "broiler", "poultry", "chick", "vitamin", "mineral"],
        "Packaging materials": ["pouch", "cup", "carton", "label", "pack", "film", "bag", "bottle"],
        "Maintenance and spares": ["bearing", "shaft", "gear", "bolt", "nut", "hinge", "spare", "pump", "motor"],
        "Electrical and automation": ["relay", "cable", "switch", "sensor", "electrical", "heater", "panel"],
        "IT and telecom": ["router", "computer", "laptop", "printer", "network", "server", "airgrid"],
        "Chemicals and laboratory": ["chemical", "reagent", "acid", "solvent", "laboratory", "test kit"],
        "Construction and facilities": ["cement", "steel", "paint", "brick", "civil", "construction"],
        "Services and logistics": ["service", "freight", "transport", "repair", "consulting", "labour"],
    }
    for category, keywords in rules.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "Unclassified"


def load_data() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing source workbook: {INPUT}. See data/raw/README.md."
        )
    df = pd.read_excel(INPUT, sheet_name="Data", usecols=SOURCE_COLUMNS)
    df.columns = [snake_case(column) for column in df.columns]

    numeric = ["po_quantity", "net_price", "per", "net_value", "gross_value"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["changed_on"] = pd.to_datetime(df["changed_on"], errors="coerce")
    df["year"] = df["changed_on"].dt.year
    df["month"] = df["changed_on"].dt.to_period("M").astype("string")
    df["purchase_order_id"] = df["purch_doc"].astype("string")
    df["material_id"] = df["material"].astype("string").replace("<NA>", pd.NA)
    df["material_group"] = df["matl_group"].astype("string")
    df["plant"] = df["plnt"].astype("string")
    df["canonical_description"] = canonical_text(df["short_text"])
    df["unit_price_normalized"] = df["net_price"] / df["per"].replace(0, np.nan)
    df["proposed_internal_category"] = df["canonical_description"].map(suggested_category)
    return df


def build_kpis(df: pd.DataFrame) -> pd.DataFrame:
    po = df.groupby("purchase_order_id").agg(
        po_spend=("gross_value", "sum"),
        line_count=("item", "size"),
    )
    metrics = [
        ("Purchase order lines", len(df)),
        ("Purchase documents", df["purchase_order_id"].nunique()),
        ("Total gross spend", df["gross_value"].sum()),
        ("Average purchase order value", po["po_spend"].mean()),
        ("Median purchase order value", po["po_spend"].median()),
        ("Single-line purchase orders (%)", 100 * (po["line_count"] == 1).mean()),
        ("Material groups", df["material_group"].nunique()),
        ("Plants", df["plant"].nunique()),
        ("Unique materials", df["material_id"].nunique()),
        ("Unique descriptions", df["canonical_description"].nunique()),
    ]
    return pd.DataFrame(metrics, columns=["metric", "value"])


def build_spend_outputs(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    total_spend = df["gross_value"].sum()

    spend_class = (
        df.groupby("spend_class", dropna=False)
        .agg(lines=("item", "size"), purchase_orders=("purchase_order_id", "nunique"), spend=("gross_value", "sum"))
        .reset_index()
    )
    spend_class["spend_share"] = spend_class["spend"] / total_spend

    material_group = (
        df.groupby("material_group", dropna=False)
        .agg(lines=("item", "size"), purchase_orders=("purchase_order_id", "nunique"), spend=("gross_value", "sum"))
        .reset_index()
        .sort_values("spend", ascending=False)
    )
    material_group["spend_share"] = material_group["spend"] / total_spend
    material_group["cumulative_spend_share"] = material_group["spend_share"].cumsum()

    plant = (
        df.groupby("plant", dropna=False)
        .agg(lines=("item", "size"), purchase_orders=("purchase_order_id", "nunique"), spend=("gross_value", "sum"))
        .reset_index()
        .sort_values("spend", ascending=False)
    )
    plant["spend_share"] = plant["spend"] / total_spend

    descriptions = (
        df.groupby(["canonical_description", "short_text"], dropna=False)
        .agg(lines=("item", "size"), purchase_orders=("purchase_order_id", "nunique"), spend=("gross_value", "sum"))
        .reset_index()
        .sort_values("spend", ascending=False)
    )
    descriptions["spend_share"] = descriptions["spend"] / total_spend
    descriptions["cumulative_spend_share"] = descriptions["spend_share"].cumsum()
    descriptions["abc_class"] = np.select(
        [descriptions["cumulative_spend_share"] <= 0.80, descriptions["cumulative_spend_share"] <= 0.95],
        ["A", "B"],
        default="C",
    )

    po = (
        df.groupby("purchase_order_id")
        .agg(po_spend=("gross_value", "sum"), line_count=("item", "size"))
        .reset_index()
    )
    bands = [-np.inf, 1_000, 5_000, 10_000, 25_000, 50_000, 100_000, np.inf]
    labels = ["<=1K", "1K-5K", "5K-10K", "10K-25K", "25K-50K", "50K-100K", ">100K"]
    po["value_band"] = pd.cut(po["po_spend"], bins=bands, labels=labels)
    fragmentation = (
        po.groupby("value_band", observed=True)
        .agg(purchase_orders=("purchase_order_id", "size"), spend=("po_spend", "sum"))
        .reset_index()
    )
    fragmentation["po_share"] = fragmentation["purchase_orders"] / len(po)
    fragmentation["spend_share"] = fragmentation["spend"] / total_spend

    return {
        "spend_class_summary": spend_class,
        "material_group_summary": material_group,
        "plant_summary": plant,
        "description_pareto": descriptions,
        "po_fragmentation": fragmentation,
    }


def build_quality_outputs(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    fields = [
        "material_id", "short_text", "material_group", "ncm_code", "requested_by",
        "priority", "sloc", "input_tax_credit", "ordered_by", "approved_by",
    ]
    quality_rows = []
    for field in fields:
        missing = df[field].isna() | df[field].astype("string").str.strip().eq("")
        quality_rows.append({
            "field": field,
            "missing_records": int(missing.sum()),
            "missing_rate": float(missing.mean()),
            "distinct_values": int(df[field].nunique(dropna=True)),
        })
    quality = pd.DataFrame(quality_rows).sort_values("missing_rate", ascending=False)

    material_consistency = (
        df.dropna(subset=["material_id"])
        .groupby("material_id")
        .agg(
            description_count=("canonical_description", "nunique"),
            uom_count=("oun", "nunique"),
            material_group_count=("material_group", "nunique"),
            line_count=("item", "size"),
            spend=("gross_value", "sum"),
        )
        .reset_index()
    )
    material_consistency["issue_flag"] = (
        (material_consistency["description_count"] > 1)
        | (material_consistency["uom_count"] > 1)
        | (material_consistency["material_group_count"] > 1)
    )
    material_consistency = material_consistency.sort_values(["issue_flag", "spend"], ascending=[False, False])

    price = (
        df.dropna(subset=["material_id", "unit_price_normalized"])
        .query("unit_price_normalized > 0")
        .groupby(["material_id", "oun"])
        .agg(
            transaction_count=("unit_price_normalized", "size"),
            median_unit_price=("unit_price_normalized", "median"),
            minimum_unit_price=("unit_price_normalized", "min"),
            maximum_unit_price=("unit_price_normalized", "max"),
            average_unit_price=("unit_price_normalized", "mean"),
            spend=("gross_value", "sum"),
        )
        .reset_index()
    )
    price = price[price["transaction_count"] >= 5].copy()
    price["price_spread_pct"] = (
        (price["maximum_unit_price"] - price["minimum_unit_price"])
        / price["median_unit_price"].replace(0, np.nan)
    )
    price["review_flag"] = np.where(price["price_spread_pct"] > 0.50, "Review", "Monitor")
    price = price.sort_values(["review_flag", "spend"], ascending=[False, False])

    taxonomy = (
        df.groupby(["material_group", "proposed_internal_category"], dropna=False)
        .agg(lines=("item", "size"), spend=("gross_value", "sum"))
        .reset_index()
        .sort_values("spend", ascending=False)
    )
    taxonomy["unspsc_code"] = ""
    taxonomy["unspsc_title"] = ""
    taxonomy["mapping_status"] = "Requires procurement review"

    return {
        "master_data_quality": quality,
        "material_consistency_issues": material_consistency,
        "price_variance_candidates": price,
        "taxonomy_mapping_template": taxonomy,
    }


def create_figures(outputs: dict[str, pd.DataFrame]) -> None:
    sns.set_theme(style="whitegrid")
    FIGURES.mkdir(parents=True, exist_ok=True)

    top_groups = outputs["material_group_summary"].head(10).sort_values("spend")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top_groups["material_group"].astype(str), top_groups["spend"] / 1e9, color="#3F7CAC")
    ax.set(title="Top material groups by gross spend", xlabel="Gross spend (billions, source currency)", ylabel="Material group")
    fig.tight_layout(); fig.savefig(FIGURES / "top_material_groups.png", dpi=180); plt.close(fig)

    pareto = outputs["description_pareto"].head(50).copy()
    fig, ax1 = plt.subplots(figsize=(10, 5))
    x = np.arange(1, len(pareto) + 1)
    ax1.bar(x, pareto["spend"] / 1e9, color="#7DB7D8")
    ax1.set(xlabel="Ranked purchase descriptions", ylabel="Gross spend (billions)", title="Purchase-description Pareto analysis")
    ax2 = ax1.twinx(); ax2.plot(x, pareto["cumulative_spend_share"] * 100, color="#17365D", linewidth=2)
    ax2.axhline(80, color="#B23A48", linestyle="--", linewidth=1); ax2.set_ylabel("Cumulative spend share (%)")
    fig.tight_layout(); fig.savefig(FIGURES / "description_pareto.png", dpi=180); plt.close(fig)

    q = outputs["master_data_quality"].sort_values("missing_rate")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(q["field"], q["missing_rate"] * 100, color="#D88C5A")
    ax.set(title="Master-data completeness gaps", xlabel="Missing records (%)", ylabel="Field")
    fig.tight_layout(); fig.savefig(FIGURES / "master_data_completeness.png", dpi=180); plt.close(fig)

    frag = outputs["po_fragmentation"]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(frag["value_band"].astype(str), frag["purchase_orders"], color="#5E8C61")
    ax.set(title="Purchase-order fragmentation by value band", xlabel="PO value band", ylabel="Purchase orders")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout(); fig.savefig(FIGURES / "po_fragmentation.png", dpi=180); plt.close(fig)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    df = load_data()
    outputs = {"kpi_summary": build_kpis(df)}
    outputs.update(build_spend_outputs(df))
    outputs.update(build_quality_outputs(df))

    for name, table in outputs.items():
        table.to_csv(TABLES / f"{name}.csv", index=False)

    create_figures(outputs)
    print(f"Built {len(outputs)} tables and 4 figures from {len(df):,} purchase-order lines.")


if __name__ == "__main__":
    main()

