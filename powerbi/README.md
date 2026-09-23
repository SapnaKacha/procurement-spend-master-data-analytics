# Power BI build specification

## Recommended model

Use a star schema:

- `FactSpend`: cleaned purchase-order lines.
- `DimDate`: one row per date with year, quarter, month and month-sort fields.
- `DimMaterial`: material ID, canonical description, material group, proposed category and approved taxonomy fields.
- `DimPlant`: plant and company-code attributes.
- `DimRequester`: requester/indenter attributes when available.

Relationships should be one-to-many from each dimension to `FactSpend`, with single-direction filtering.

## Core measures

```DAX
Total Gross Spend =
SUM ( FactSpend[gross_value] )

Purchase Orders =
DISTINCTCOUNT ( FactSpend[purchase_order_id] )

PO Lines =
COUNTROWS ( FactSpend )

Average PO Value =
DIVIDE ( [Total Gross Spend], [Purchase Orders] )

Tail Spend =
CALCULATE (
    [Total Gross Spend],
    FactSpend[spend_class] = "Tail Spend"
)

Tail Spend Percent =
DIVIDE ( [Tail Spend], [Total Gross Spend] )

Missing Requester Lines =
CALCULATE (
    [PO Lines],
    ISBLANK ( FactSpend[requested_by] )
)

Missing Requester Percent =
DIVIDE ( [Missing Requester Lines], [PO Lines] )
```

## Dashboard pages

### Executive Spend Overview

- Cards: Total Gross Spend, Purchase Orders, PO Lines, Average PO Value, Tail Spend Percent.
- Column chart: Spend by material group.
- Line chart: Spend over time.
- Bar chart: Spend by plant.
- Slicers: Year, company code, plant, material group and spend class.

### Category and Pareto Analysis

- Pareto chart using ranked purchase descriptions.
- Matrix: material group, lines, POs, spend, spend share and cumulative share.
- ABC class distribution.
- Drill-through from material group to material descriptions.

### Tail Spend and Fragmentation

- PO count and spend by value band.
- Single-line versus multi-line POs.
- Tail-spend descriptions and material groups.
- Detail table for consolidation review.

### Master Data Quality

- Missing-field rate by attribute.
- Materials with multiple descriptions, UOMs or material groups.
- Price-variance review candidates.
- Taxonomy mapping status and unclassified spend.

## Validation checks

- Reconcile Power BI total gross spend to `kpi_summary.csv`.
- Confirm spend-class totals equal total gross spend.
- Confirm each PO is counted once in PO-level visuals.
- Treat missing text values consistently as blank or `Unknown`.
- Do not present price spread as realized savings without procurement validation.

