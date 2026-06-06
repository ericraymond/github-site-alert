import os
import json
import requests

# Target Endpoint configuration
SHOPIFY_URL = "https://lovepedalcustomeffects.myshopify.com/products.json"
STATE_FILE = "last_seen.json"

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
    alerts = []

    # Parse through inventory entries
    for product in data.get("products", []):
        p_id = str(product.get("id"))
        current_ids.add(p_id)

        # Evaluate if item is newly surfaced or updated
        if p_id not in old_ids:
            title = product.get("title", "")

            # Check individual variants for zero pricing markers
            for variant in product.get("variants", []):
                price_str = variant.get("price", "999")
                try:
                    price = float(price_str)
                except ValueError:
                    price = 999.0

                # Check criteria: price is exactly 0 OR string implies free
                if "free" in title.lower() or price == 0.0:
                    handle = product.get("handle", "")
                    item_url = f"https://lovepedalcustomeffects.myshopify.com/products/{handle}"
                    alerts.append(f"- **{title}** is currently listed for **${price:,.2f}**!\n  [View Item on Storefront]({item_url})")
                    break # Alert once per product structure

    # If matches surface, dispatch an Issue to prompt mobile application ping
    if alerts:
        print(f"Found {len(alerts)} item matches. Dispatching GitHub Issue alert...")
        if GITHUB_TOKEN and GITHUB_REPO:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+v3+json"
            }
            payload = {
                "title": "🚨 Deal Alert: Free Items Detected!",
                "body": "The tracking script discovered free entries on the Shopify inventory endpoint:\n\n" + "\n".join(alerts),
                "labels": ["alert"]
            }
            try:
                res = requests.post(url, json=payload, headers=headers)
                res.raise_for_status()
                print("Notification issue dispatched successfully.")
            except Exception as e:
                print(f"Failed to submit issue alert: {e}")
        else:
            print("Missing GITHUB_TOKEN or GITHUB_REPOSITORY environment variables.")
    else:
        print("Scan complete. No free items or pricing anomalies detected.")

    # Write current snapshot to maintain state continuity
    save_current_products(current_ids)

if __name__ == "__main__":
    main()