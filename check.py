import os
import json
import yaml
import time
import requests
from datetime import datetime

SHOPIFY_URL = "https://lovepedalcustomeffects.myshopify.com/products.json"
STATE_FILE = "last_seen.json"
LOG_FILE = "log.yaml"
SENTINEL_KEYWORD = "super stud"

SIGNAL_PHONE = os.environ.get("SIGNAL_PHONE")
SIGNAL_API_KEY = os.environ.get("SIGNAL_API_KEY")

def load_old_products():
    """Loads previously seen product IDs and sentinel presence from local state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data), None
                elif isinstance(data, dict):
                    # Load sentinel state (with fallback to legacy key)
                    sentinel_seen = data.get("sentinel_seen")
                    if sentinel_seen is None:
                        legacy_key = SENTINEL_KEYWORD.replace(" ", "_") + "_seen"
                        sentinel_seen = data.get(legacy_key)
                    return set(data.get("product_ids", [])), sentinel_seen
        except Exception:
            return set(), None
    return set(), None

def save_current_products(product_ids, sentinel_seen):
    """Saves current product IDs and sentinel presence to local state file."""
    with open(STATE_FILE, "w") as f:
        json.dump({
            "product_ids": list(product_ids),
            "sentinel_seen": sentinel_seen
        }, f, indent=2)

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
        yaml.safe_dump(logs, f, default_flow_style=False, sort_keys=False)

def main(max_retries=3, delay=5):
    data = None

    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"Retrying backend fetch (Attempt {attempt}/{max_retries})...")
            response = requests.get(SHOPIFY_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            break
        except Exception as e:
            if attempt < max_retries:
                time.sleep(delay)
            else:
                print(f"All fetch attempts failed: {e}")
                return

    if not data:
        return

    old_ids, sentinel_previously_seen = load_old_products()
    current_ids = set()
    sentinel_currently_seen = False

    signal_alerts = []

    historical_logs = load_history_logs()
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_changed = False

    latest_snapshots = {}
    for entry in historical_logs:
        latest_snapshots[entry.get("id")] = entry

    for product in data.get("products", []):
        p_id = str(product.get("id"))
        current_ids.add(p_id)

        title = product.get("title", "")
        if SENTINEL_KEYWORD in title.lower():
            sentinel_currently_seen = True
        handle = product.get("handle", "")
        item_url = f"https://lovepedalcustomeffects.myshopify.com/products/{handle}"

        raw_body = product.get("body_html", "") or ""
        clean_desc = " ".join(raw_body.replace("<br>", " ").split())[:120]
        if len(raw_body) > 120:
            clean_desc += "..."

        variants = product.get("variants", [])
        first_variant = variants[0] if variants else {}

        price_str = first_variant.get("price", "999")
        try:
            price = float(price_str)
        except ValueError:
            price = 999.0

        is_available = first_variant.get("available", False)

        current_snapshot = {
            "timestamp": current_timestamp,
            "id": p_id,
            "title": title.split(" - ")[0][:35],
            "price": price,
            "available": is_available,
            "url": item_url,
            "description": clean_desc if clean_desc else "No description provided."
        }

        previous_snapshot = latest_snapshots.get(p_id)
        if previous_snapshot is None:
            historical_logs.append(current_snapshot)
            log_changed = True
        else:
            if previous_snapshot.get("price") != price or previous_snapshot.get("available") != is_available:
                historical_logs.append(current_snapshot)
                log_changed = True

        if p_id not in old_ids:
            if "free" in title.lower() or price == 0.0:
                signal_alerts.append(f"🔥 FREE DROP: {title} is listed for $0.00! {item_url}")
            else:
                signal_alerts.append(f"📦 New Inventory: {title} listed for ${price:,.2f}. {item_url}")

    if sentinel_previously_seen is not None:
        if sentinel_previously_seen and not sentinel_currently_seen:
            signal_alerts.append("SNS Starting")
        elif not sentinel_previously_seen and sentinel_currently_seen:
            signal_alerts.append("SNS Over")

    if signal_alerts:
        print("Signal alerts detected.")
        if SIGNAL_PHONE and SIGNAL_API_KEY:
            print("Sending Signal notification...")
            signal_text = "\n\n".join(signal_alerts)
            signal_url = "https://api.callmebot.com/signal/send.php"
            signal_payload = {
                "phone": SIGNAL_PHONE,
                "apikey": SIGNAL_API_KEY,
                "text": signal_text
            }
            try:
                sig_res = requests.get(signal_url, params=signal_payload, timeout=5)
                sig_res.raise_for_status()
            except Exception as e:
                print(f"Failed to submit Signal notification: {e}")
        else:
            print("Signal notification skipped: SIGNAL_PHONE or SIGNAL_API_KEY not configured.")

    save_current_products(current_ids, sentinel_currently_seen)

    if log_changed:
        print("Inventory changes saved to log.")
        save_history_logs(historical_logs)

if __name__ == "__main__":
    main()