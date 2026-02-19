# Zava Retail - Order Simulator Instructions

## Overview

The `simulate_orders.py` script generates realistic new orders to simulate a live retail business. It inserts orders and order items into the Azure PostgreSQL database, which Fabric Mirroring picks up via CDC in near real-time.

Each batch generates orders with:

- 🏪 Store-weighted distribution (Seattle & Online get the most traffic)
- 📅 Seasonal product demand (Garden peaks in summer, Paint in spring, etc.)
- 💰 Realistic pricing with 15% chance of discounts
- 📦 Inventory decrements
- 👤 Customer-store affinity (70% of orders go to the customer's primary store)

## Prerequisites

1. **Python 3** installed on your machine
2. **psycopg2-binary** package installed:

   ```powershell
   py -m pip install psycopg2-binary
   ```

3. **Azure PostgreSQL server** running and accessible (firewall rules allow your IP)

## Connection Details

| Setting  | Value                                          |
| -------- | ---------------------------------------------- |
| Host     | `zava-pg-server.postgres.database.azure.com`   |
| Port     | `5432`                                         |
| Database | `zava`                                         |
| User     | `postgresadmin`                                |
| SSL      | Required                                       |

> **Note:** If you change the server password, update it in `simulate_orders.py` under `DB_CONFIG`.

## Usage

Open a terminal and navigate to the repo:

```powershell
cd "C:\Users\edaavar\OneDrive - Microsoft\Documents\Repos\ai-tour-26-zava-diy-dataset-plus-mcp"
```

### Single Batch (Quick Test)

Generates ~10 orders and exits. Good for testing the connection.

```powershell
py simulate_orders.py
```

Example output:

```
🏪 Zava Retail Order Simulator
   Server: zava-pg-server.postgres.database.azure.com
   Batch size: ~10 orders

✅ Generated 13 orders with 23 line items
   Total orders in DB: 197,678
   Orders today: 117
```

### Continuous Mode

Generates new orders at regular intervals to simulate ongoing business activity.

```powershell
py simulate_orders.py --continuous
```

This runs every **60 seconds** by default. Press **Ctrl+C** to stop.

### Custom Interval and Batch Size

```powershell
py simulate_orders.py --continuous --interval 30 --batch-size 20
```

| Flag           | Default | Description                          |
| -------------- | ------- | ------------------------------------ |
| `--continuous` | off     | Run continuously instead of one batch|
| `--interval`   | 60      | Seconds between batches              |
| `--batch-size` | 10      | Approximate number of orders per batch|

### Recommended Settings for Demos

| Scenario                    | Command                                                        | Orders/hour |
| --------------------------- | -------------------------------------------------------------- | ----------- |
| Light background activity   | `py simulate_orders.py --continuous --interval 120 --batch-size 5`  | ~150        |
| Normal business day         | `py simulate_orders.py --continuous --interval 60 --batch-size 10`  | ~600        |
| Busy day / stress test      | `py simulate_orders.py --continuous --interval 30 --batch-size 20`  | ~2,400      |
| Quick demo burst            | `py simulate_orders.py --batch-size 50`                             | One-off     |

## Troubleshooting

### "psycopg2 not found"

```powershell
py -m pip install psycopg2-binary
```

### "connection refused" or timeout

- Check your Azure PostgreSQL firewall rules include your current IP
- Go to Azure Portal → your server → Networking → add your IP

### "password authentication failed"

- Verify the password in `simulate_orders.py` matches your Azure PostgreSQL admin password

### "psql / py not recognised"

- Ensure Python is installed and on your PATH
- Try `python` or `python3` instead of `py`
