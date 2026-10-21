import csv
import random
from datetime import datetime, timedelta

# ── Shop definitions ──────────────────────────────────────────────
SOUVENIR_SHOPS = [
    {"name": "Budget Treasures",   "price_bracket": "budget",    "price_range": (2, 15)},
    {"name": "Island Keepsakes",  "price_bracket": "mid-range", "price_range": (15, 60)},
    {"name": "Luxury Souvenirs",   "price_bracket": "premium",   "price_range": (60, 250)},
]

TRAVEL_NECESSITY_SHOPS = [
    {"name": "Travel Essentials",  "price_range": (5, 40)},
    {"name": "Wanderlust Supplies","price_range": (8, 55)},
]

COFFEE_SHOPS = [
    {"name": "Bean There Café",   "price_range": (3, 8)},
    {"name": "Morning Brew",      "price_range": (3, 9)},
    {"name": "Caffeine Corner",   "price_range": (2, 7)},
    {"name": "The Daily Grind",   "price_range": (4, 10)},
    {"name": "Espresso Express",  "price_range": (3, 8)},
]

# ── Configuration ─────────────────────────────────────────────────
START_DATE   = datetime(2025, 5, 1, 0, 0)    # May 1 2025, midnight
END_DATE     = datetime(2025, 5, 31, 23, 59) # May 31 2025, 11:59 PM
OUTPUT_FILE  = "synthetic_sales.csv"
RANDOM_SEED  = 42

random.seed(RANDOM_SEED)


def is_coffee_open(dt):
    """Coffee shops are open 08:00–21:00."""
    return 8 <= dt.hour <= 20


def is_rush_hour(dt):
    """Rush hours: 07:30–09:30 and 16:00–20:00."""
    t = dt.hour * 60 + dt.minute  # minutes since midnight
    return (7*60 + 30 <= t <= 9*60 + 30) or (16*60 <= t <= 20*60)


def generate_transactions():
    """Yield one transaction dict per row."""
    current = START_DATE
    transaction_id = 1000

    while current <= END_DATE:
        # Build the pool of active shops for this minute
        active_shops = []
        for shop in SOUVENIR_SHOPS:
            active_shops.append(("souvenir", shop))
        for shop in TRAVEL_NECESSITY_SHOPS:
            active_shops.append(("travel_necessity", shop))
        if is_coffee_open(current):
            for shop in COFFEE_SHOPS:
                active_shops.append(("coffee", shop))

        rush = is_rush_hour(current)

        for shop_type, shop in active_shops:
            # Probability of generating a transaction this minute
            if rush:
                # Rush hour: high activity, 1–3 transactions per minute
                if random.random() < 0.80:
                    num_transactions = random.randint(1, 3)
                else:
                    num_transactions = 0
            else:
                # Normal hours: moderate activity, 0–1 transactions per minute
                if random.random() < 0.30:
                    num_transactions = 1
                else:
                    num_transactions = 0

            for _ in range(num_transactions):
                unit_price = round(random.uniform(*shop["price_range"]), 2)
                items_sold = random.randint(1, 5)
                total_revenue = round(unit_price * items_sold, 2)

                row = {
                    "transaction_id": transaction_id,
                    "timestamp": current.strftime("%Y-%m-%d %H:%M:%S"),
                    "shop_name": shop["name"],
                    "shop_type": shop_type,
                    "price_bracket": shop.get("price_bracket", ""),
                    "items_sold": items_sold,
                    "unit_price": unit_price,
                    "total_revenue": total_revenue,
                }
                yield row
                transaction_id += 1

        # Advance time by one minute
        current += timedelta(minutes=1)


def main():
    fieldnames = [
        "transaction_id",
        "timestamp",
        "shop_name",
        "shop_type",
        "price_bracket",
        "items_sold",
        "unit_price",
        "total_revenue",
    ]

    row_count = 0
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in generate_transactions():
            writer.writerow(row)
            row_count += 1

    print(f"✅ Generated {row_count:,} transactions → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()