import os
import json
import yaml
import requests
from datetime import datetime

# Target Endpoint configurations
SHOPIFY_URL = "https://lovepedalcustomeffects.myshopify.com/products.json"
STATE_FILE = "last_seen.json"
LOG_FILE = "log.yaml"

# Injected automatically by the GitHub Actions workflow environment
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def load_old_products():
    """Loads previously seen product IDs from local state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_current_products(product_ids):
    """Saves current product IDs to local state file."""
    with open(STATE_FILE, "w") as f:
        json.dump(list(product_ids), f, indent=2)

def load_history_logs():
    """Loads existing log events from the historical YAML file."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return yaml.safe_load(f) or []
        except Exception:
            return []
    return []

def save_history_logs(logs):
    """Writes updated history logs back to the repository in clean YAML format."""
    with open(LOG_FILE, "w") as f:
        # sort_keys=False keeps the fields in the exact order we built them
        yaml.safe_dump(logs, f, default_flow_style=False, sort_keys=False)

def main():
    try:
        # Request data from shopify backend API
        response = requests.get(SHOPIFY_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching Shopify data: {e}")
        return

    old_ids = load_old_products()
    current_ids = set()

    # Alert queues
    free_alerts = []
    standard_alerts = []

    # Log management variables
    historical_logs = load_history_logs()
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_changed = False

    # Map the absolute latest log record for every item ID to prevent duplications
    latest_snapshots = {}
    for entry in historical_logs:
        latest_snapshots[entry.get("id")] = entry

    # Parse through inventory entries
    for product in data.get("products", []):
        p_id = str(product.get("id"))
        current_ids.add(p_id)

        title = product.get("title", "")
        handle = product.get("handle", "")
        item_url = f"https://lovepedalcustomeffects.myshopify.com/products/{handle}"

        # Strip out basic HTML markers and clean up whitespaces in description
        raw_body = product.get("body_html", "") or ""
        clean_desc = " ".join(raw_body.replace("<br>", " ").split())[:120]
        if len(raw_body) > 120:
            clean_desc += "..."

        # Isolate the core pricing and stock parameters from variants
        variants = product.get("variants", [])
        first_variant = variants[0] if variants else {}

        price_str = first_variant.get("price", "999")
        try:
            price = float(price_str)
        except ValueError:
            price = 999.0

        is_available = first_variant.get("available", False)

        # Assemble current item object schema
        current_snapshot = {
            "timestamp": current_timestamp,
            "id": p_id,
            "title": title.split(" - ")[0][:35],
            "price": price,
            "available": is_available,
            "url": item_url,
            "description": clean_desc if clean_desc else "No description provided."
        }

        # DEDUPLICATED HISTORY LOGGING ENGINE
        previous_snapshot = latest_snapshots.get(p_id)
        if previous_snapshot is None:
            historical_logs.append(current_snapshot)
            log_changed = True
        else:
            if previous_snapshot.get("price") != price or previous_snapshot.get("available") != is_available:
                historical_logs.append(current_snapshot)
                log_changed = True

        # NEW ITEM ALERT ENGINE
        if p_id not in old_ids:
            if "free" in title.lower() or price == 0.0:
                free_alerts.append(f"- 🔥 **FREE DROP:** {title} is listed for **$0.00**!\n  [Link]({item_url})")
            else:
                standard_alerts.append(f"- 📦 **New Inventory:** {title} listed for **${price:,.2f}**\n  [Link]({item_url})")

    # Evaluate dynamic notification structure
    all_alerts = free_alerts + standard_alerts
    if all_alerts:
        if free_alerts:
            issue_title = "🚨 CRITICAL FREE ITEM DETECTED 🚨"
        else:
            issue_title = f"📦 [NEW ITEM] {data['products'][0]['title'][:30]}..." if len(all_alerts) == 1 else f"📦 {len(all_alerts)} New Items Added to Store"

        print(f"Inventory changes found. Dispatching GitHub Issue alert: '{issue_title}'")

        if GITHUB_TOKEN and GITHUB_REPO:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+v3+json"
            }

            body_content = "### 🔔 Storefront Inventory Update Found!\n\n"
            if free_alerts:
                body_content += "#### ⚠️ FREE ITEMS FOUND:\n" + "\n".join(free_alerts) + "\n\n"
            if standard_alerts:
                body_content += "#### Standard New Items:\n" + "\n".join(standard_alerts)

            payload = {
                "title": issue_title,
                "body": body_content,
                "labels": ["alert", "free"] if free_alerts else ["new-item"]
            }

            try:
                res = requests.post(url, json=payload, headers=headers)
                res.raise_for_status()
            except Exception as e:
                print(f"Failed to submit issue alert: {e}")
        else:
            print("Missing GITHUB_TOKEN or GITHUB_REPOSITORY environment variables.")
    else:
        print("Scan complete. No new items detected on the storefront.")

    # Write data targets
    save_current_products(current_ids)

    if log_changed:
        print("Inventory changes detected. Committing snapshots to YAML log file.")
        save_history_logs(historical_logs)
    else:
        print("No changes across inventory fields. Skipping log update.")

if __name__ == "__main__":
    main()