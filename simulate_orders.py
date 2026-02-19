"""
Zava Retail - Live Order Simulator
Generates realistic new orders at regular intervals to simulate a live business.
Fabric Mirroring will pick up changes via CDC in near real-time.

Usage:
    python simulate_orders.py                    # Generate 1 batch (5-15 orders)
    python simulate_orders.py --continuous       # Run continuously every 60 seconds
    python simulate_orders.py --interval 30      # Run every 30 seconds
    python simulate_orders.py --batch-size 20    # Generate ~20 orders per batch
"""

import psycopg2
import random
import argparse
import time
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

# === CONNECTION CONFIG ===
DB_CONFIG = {
    "host": "zava-pg-server.postgres.database.azure.com",
    "port": 5432,
    "dbname": "zava",
    "user": "postgresadmin",
    "password": "zavagoose9785!",
    "sslmode": "require",
}

# === STORE WEIGHTS (from reference_data.json) ===
STORE_WEIGHTS = {
    1: {"name": "Seattle",  "weight": 30, "freq": 3.0, "value": 1.3},
    2: {"name": "Bellevue", "weight": 25, "freq": 2.6, "value": 1.2},
    3: {"name": "Tacoma",   "weight": 20, "freq": 2.4, "value": 1.1},
    4: {"name": "Spokane",  "weight":  8, "freq": 2.0, "value": 1.0},
    5: {"name": "Everett",  "weight":  7, "freq": 1.8, "value": 0.95},
    6: {"name": "Redmond",  "weight":  6, "freq": 1.6, "value": 0.9},
    7: {"name": "Kirkland", "weight":  4, "freq": 1.4, "value": 0.85},
    8: {"name": "Online",   "weight": 30, "freq": 3.0, "value": 1.5},
}

# === SEASONAL MULTIPLIERS BY CATEGORY (Jan=0 to Dec=11) ===
SEASONAL = {
    "Hand Tools":              [1.0, 1.0, 1.2, 1.4, 1.6, 1.5, 1.5, 1.4, 1.2, 1.1, 1.0, 0.9],
    "Power Tools":             [0.8, 0.9, 1.2, 1.5, 1.8, 2.1, 2.1, 1.8, 1.5, 1.2, 1.0, 1.5],
    "Paint & Finishes":        [0.6, 0.7, 1.5, 2.2, 2.0, 1.8, 1.6, 1.5, 1.3, 1.0, 0.7, 0.5],
    "Hardware":                [1.0, 1.0, 1.1, 1.2, 1.3, 1.3, 1.3, 1.2, 1.1, 1.0, 1.0, 1.1],
    "Lumber & Building Materials": [0.5, 0.6, 1.2, 1.8, 2.0, 2.0, 1.8, 1.6, 1.4, 1.0, 0.6, 0.4],
    "Electrical":              [1.0, 1.0, 1.1, 1.2, 1.3, 1.2, 1.2, 1.1, 1.0, 1.0, 1.1, 1.2],
    "Plumbing":                [1.2, 1.1, 1.0, 1.0, 1.1, 1.2, 1.2, 1.1, 1.0, 1.0, 1.1, 1.2],
    "Garden & Outdoor":        [0.3, 0.4, 1.2, 1.8, 2.2, 2.5, 2.5, 2.2, 1.8, 1.2, 0.5, 0.3],
    "Storage & Organization":  [1.5, 1.3, 1.0, 0.9, 0.8, 0.8, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6],
}


def get_weighted_store():
    """Pick a store weighted by customer distribution."""
    stores = list(STORE_WEIGHTS.keys())
    weights = [STORE_WEIGHTS[s]["weight"] for s in stores]
    return random.choices(stores, weights=weights, k=1)[0]


def get_seasonal_category(month, categories):
    """Pick a product category weighted by seasonal demand."""
    weights = []
    for cat in categories:
        cat_name = cat["category_name"]
        mult = SEASONAL.get(cat_name, [1.0] * 12)[month]
        weights.append(mult)
    return random.choices(categories, weights=weights, k=1)[0]


def generate_order_items(products_by_category, categories, store_id, month):
    """Generate 1-5 items for an order."""
    num_items = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5], k=1)[0]
    items = []
    value_mult = STORE_WEIGHTS[store_id]["value"]

    for _ in range(num_items):
        # 90% seasonal, 10% random category
        if random.random() < 0.9:
            cat = get_seasonal_category(month, categories)
        else:
            cat = random.choice(categories)

        cat_id = cat["category_id"]
        if cat_id not in products_by_category or not products_by_category[cat_id]:
            continue

        product = random.choice(products_by_category[cat_id])
        quantity = random.choices([1, 2, 3, 4, 5], weights=[60, 25, 10, 3, 2], k=1)[0]
        unit_price = Decimal(str(float(product["base_price"]) * random.uniform(0.8, 1.2) * value_mult)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 15% chance of discount
        if random.random() < 0.15:
            discount_percent = random.choice([5, 10, 15, 20, 25])
        else:
            discount_percent = 0

        discount_amount = (unit_price * quantity * discount_percent / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_amount = (unit_price * quantity - discount_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        items.append({
            "store_id": store_id,
            "product_id": product["product_id"],
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_percent": discount_percent,
            "discount_amount": discount_amount,
            "total_amount": total_amount,
        })

    return items


def generate_batch(conn, batch_size=10):
    """Generate a batch of realistic orders."""
    cur = conn.cursor()

    # Load reference data
    cur.execute("SELECT customer_id, primary_store_id FROM retail.customers")
    customers = cur.fetchall()

    cur.execute("SELECT category_id, category_name FROM retail.categories")
    categories = [{"category_id": r[0], "category_name": r[1]} for r in cur.fetchall()]

    cur.execute("SELECT product_id, category_id, base_price FROM retail.products")
    products = cur.fetchall()
    products_by_category = {}
    for p in products:
        cat_id = p[1]
        if cat_id not in products_by_category:
            products_by_category[cat_id] = []
        products_by_category[cat_id].append({"product_id": p[0], "category_id": p[1], "base_price": p[2]})

    today = date.today()
    month = today.month - 1  # 0-indexed for seasonal array
    orders_created = 0
    items_created = 0

    # Generate orders
    num_orders = random.randint(max(1, batch_size - 5), batch_size + 5)

    for _ in range(num_orders):
        customer = random.choice(customers)
        customer_id = customer[0]

        # 70% chance order goes to customer's primary store, 30% random
        if random.random() < 0.7 and customer[1]:
            store_id = customer[1]
        else:
            store_id = get_weighted_store()

        # Insert order
        cur.execute(
            "INSERT INTO retail.orders (customer_id, store_id, order_date) VALUES (%s, %s, %s) RETURNING order_id",
            (customer_id, store_id, today),
        )
        order_id = cur.fetchone()[0]

        # Generate and insert items
        items = generate_order_items(products_by_category, categories, store_id, month)
        for item in items:
            cur.execute(
                """INSERT INTO retail.order_items 
                   (order_id, store_id, product_id, quantity, unit_price, discount_percent, discount_amount, total_amount)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (order_id, item["store_id"], item["product_id"], item["quantity"],
                 item["unit_price"], item["discount_percent"], item["discount_amount"], item["total_amount"]),
            )
            items_created += 1

        # Optionally decrease inventory
        for item in items:
            cur.execute(
                """UPDATE retail.inventory 
                   SET stock_level = GREATEST(stock_level - %s, 0) 
                   WHERE store_id = %s AND product_id = %s""",
                (item["quantity"], item["store_id"], item["product_id"]),
            )

        orders_created += 1

    conn.commit()
    cur.close()
    return orders_created, items_created


def main():
    parser = argparse.ArgumentParser(description="Zava Retail - Live Order Simulator")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between batches (default: 60)")
    parser.add_argument("--batch-size", type=int, default=10, help="Approx orders per batch (default: 10)")
    args = parser.parse_args()

    print("🏪 Zava Retail Order Simulator")
    print(f"   Server: {DB_CONFIG['host']}")
    print(f"   Batch size: ~{args.batch_size} orders")
    if args.continuous:
        print(f"   Interval: every {args.interval}s")
    print()

    conn = psycopg2.connect(**DB_CONFIG)

    try:
        if args.continuous:
            batch_num = 0
            while True:
                batch_num += 1
                orders, items = generate_batch(conn, args.batch_size)
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] Batch #{batch_num}: +{orders} orders, +{items} items")
                time.sleep(args.interval)
        else:
            orders, items = generate_batch(conn, args.batch_size)
            print(f"✅ Generated {orders} orders with {items} line items")

            # Show a summary
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM retail.orders")
            total = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM retail.orders WHERE order_date = %s", (date.today(),))
            today_count = cur.fetchone()[0]
            print(f"   Total orders in DB: {total:,}")
            print(f"   Orders today: {today_count:,}")
            cur.close()
    except KeyboardInterrupt:
        print("\n⏹️  Stopped.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
