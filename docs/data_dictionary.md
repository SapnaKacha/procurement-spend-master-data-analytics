# Data dictionary

The project uses selected fields from the `Data` sheet in the Kaggle workbook.

| Field | Meaning in this project |
|---|---|
| `purchase_order_id` | Purchase document identifier |
| `item` | Purchase-order line number |
| `changed_on` | Transaction/change date from the source |
| `short_text` | Free-text purchase description |
| `material_id` | Material master identifier |
| `material_group` | Source material-group code |
| `plant` | Source plant code |
| `sloc` | Storage-location code |
| `po_quantity` | Ordered quantity |
| `oun` | Order unit of measure |
| `net_price` | Source net price |
| `per` | Price-unit denominator |
| `gross_value` | Gross transaction value used for spend KPIs |
| `ncm_code` | Source commodity/customs code |
| `requested_by` | Requisition requester, when populated |
| `ordered_by` | Ordering person or group |
| `approved_by` | Approver field |
| `priority` | Source priority value |
| `spend_class` | Major/Tail spend classification included in the source |
| `canonical_description` | Lowercase, punctuation-normalized description created by the pipeline |
| `unit_price_normalized` | `net_price / per`, calculated when `per` is non-zero |
| `proposed_internal_category` | Keyword-based category suggestion for analyst review; not an official taxonomy |

## Important limitation

The source does not contain supplier identifiers or verified UNSPSC/eClass mappings. The project therefore assesses taxonomy readiness and creates a review template. It does not invent official taxonomy codes or perform supplier-concentration analysis.

