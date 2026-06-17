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
    """Loads previously seen product IDs and sentinel presence/state from local state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data), None, None
                elif isinstance(data, dict):
                    # Load sentinel state (with fallback to legacy key)
                    sentinel_seen = data.get("sentinel_seen")
                    if sentinel_seen is None:
                        legacy_key = SENTINEL_KEYWORD.replace(" ", "_") + "_seen"
                        sentinel_seen = data.get(legacy_key)
                    state = data.get("state")
                    return set(data.get("product_ids", [])), sentinel_seen, state
        except Exception:
            return set(), None, None
    return set(), None, None

def save_current_products(product_ids, sentinel_seen, state):
    """Saves current product IDs, sentinel presence, and state to local state file."""
    with open(STATE_FILE, "w") as f:
        json.dump({
            "product_ids": list(product_ids),
            "sentinel_seen": sentinel_seen,
            "state": state
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

    old_ids, sentinel_previously_seen, previous_state = load_old_products()
    current_ids = set()
    sentinel_currently_seen = False
    current_other_items_present = False

    signal_alerts = []

    historical_logs = load_history_logs()

    if sentinel_previously_seen is None:
        sentinel_id = None
        for entry in reversed(historical_logs):
            if SENTINEL_KEYWORD in entry.get("title", "").lower():
                sentinel_id = entry.get("id")
                break
        sentinel_previously_seen = (sentinel_id in old_ids) if sentinel_id is not None else False

    if previous_state is None:
        if not sentinel_previously_seen:
            previous_state = "sns_active"
        else:
            if len(old_ids) > 1:
                previous_state = "end_in_sight"
            else:
                previous_state = "idle"

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
        else:
            current_other_items_present = True
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
                signal_alerts.append(f"🔥 FREE DROP: {title} is listed for ＄0.00! {item_url}")
            else:
                signal_alerts.append(f"📦 New Inventory: {title} listed for ＄{price:,.2f}. {item_url}")
        else:
            if previous_snapshot is not None:
                old_price = previous_snapshot.get("price")
                old_available = previous_snapshot.get("available")
                if old_available != is_available:
                    if not is_available:
                        signal_alerts.append(f"🔴 SOLD OUT: {title} is now sold out. {item_url}")
                    else:
                        signal_alerts.append(f"🟢 Back in Stock: {title} is now available for ＄{price:,.2f}! {item_url}")
                if old_price != price:
                    signal_alerts.append(f"💰 Price Change: {title} is now ＄{price:,.2f} (was ＄{old_price:,.2f}). {item_url}")

    if not sentinel_currently_seen:
        current_state = "sns_active"
    elif current_other_items_present:
        current_state = "end_in_sight"
    else:
        current_state = "idle"

    if previous_state != current_state:
        if current_state == "sns_active":
            if previous_state == "end_in_sight":
                signal_alerts.append("Just Kidding")
            else:
                signal_alerts.append("SNS Starting")
        elif previous_state == "sns_active" and current_state == "end_in_sight":
            signal_alerts.append("End in Sight")
        elif current_state == "idle":
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

    save_current_products(current_ids, sentinel_currently_seen, current_state)

    if log_changed:
        print("Inventory changes saved to log.")
        save_history_logs(historical_logs)

if __name__ == "__main__":
    main()