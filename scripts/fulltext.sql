SELECT 
    p.product_id,
    p.sku,
    p.product_name,
    p.product_description,
    ts_rank(
        to_tsvector('english', p.product_name || ' ' || p.product_description),
        to_tsquery('english', 'garden | watering | supplies')
    ) as relevance_score
FROM retail.products p
WHERE to_tsvector('english', p.product_name || ' ' || p.product_description) 
@@ to_tsquery('english', 'garden | watering | supplies')
ORDER BY relevance_score DESC, p.product_name
LIMIT 5;