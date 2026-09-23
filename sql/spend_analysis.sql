-- Procurement spend and master-data analysis
-- Expected table: spend_fact

-- 1. Core procurement KPIs
SELECT
    COUNT(*) AS po_lines,
    COUNT(DISTINCT purchase_order_id) AS purchase_orders,
    SUM(gross_value) AS total_gross_spend,
    AVG(gross_value) AS average_line_spend
FROM spend_fact;

-- 2. Spend by material group with cumulative contribution
WITH category_spend AS (
    SELECT
        material_group,
        SUM(gross_value) AS spend
    FROM spend_fact
    GROUP BY material_group
), ranked AS (
    SELECT
        material_group,
        spend,
        spend / SUM(spend) OVER () AS spend_share,
        SUM(spend) OVER (ORDER BY spend DESC)
            / SUM(spend) OVER () AS cumulative_spend_share
    FROM category_spend
)
SELECT *
FROM ranked
ORDER BY spend DESC;

-- 3. Purchase-order fragmentation
WITH po_value AS (
    SELECT purchase_order_id, SUM(gross_value) AS po_spend
    FROM spend_fact
    GROUP BY purchase_order_id
)
SELECT
    CASE
        WHEN po_spend <= 1000 THEN '<=1K'
        WHEN po_spend <= 5000 THEN '1K-5K'
        WHEN po_spend <= 10000 THEN '5K-10K'
        WHEN po_spend <= 25000 THEN '10K-25K'
        WHEN po_spend <= 50000 THEN '25K-50K'
        WHEN po_spend <= 100000 THEN '50K-100K'
        ELSE '>100K'
    END AS value_band,
    COUNT(*) AS purchase_orders,
    SUM(po_spend) AS spend
FROM po_value
GROUP BY 1
ORDER BY MIN(po_spend);

-- 4. Material-master consistency issues
SELECT
    material_id,
    COUNT(DISTINCT canonical_description) AS description_count,
    COUNT(DISTINCT oun) AS uom_count,
    COUNT(DISTINCT material_group) AS material_group_count,
    COUNT(*) AS line_count,
    SUM(gross_value) AS spend
FROM spend_fact
WHERE material_id IS NOT NULL
GROUP BY material_id
HAVING COUNT(DISTINCT canonical_description) > 1
    OR COUNT(DISTINCT oun) > 1
    OR COUNT(DISTINCT material_group) > 1
ORDER BY spend DESC;

-- 5. Unit-price variation candidates
SELECT
    material_id,
    oun,
    COUNT(*) AS transaction_count,
    MIN(unit_price_normalized) AS minimum_unit_price,
    AVG(unit_price_normalized) AS average_unit_price,
    MAX(unit_price_normalized) AS maximum_unit_price,
    SUM(gross_value) AS spend
FROM spend_fact
WHERE material_id IS NOT NULL
  AND unit_price_normalized > 0
GROUP BY material_id, oun
HAVING COUNT(*) >= 5
ORDER BY spend DESC;

