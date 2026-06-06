import time  # <--- Make sure 'import time' is at the top of your check.py file

def main(max_retries=3, delay=5):
    data = None

    # Retry loop configuration
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"Fetching data (Attempt {attempt} of {max_retries})...")
            response = requests.get(SHOPIFY_URL, timeout=5) # 5 second network timeout limit
            response.raise_for_status()
            data = response.json()
            break # Success! Break out of the retry loop immediately.
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print(f"Waiting {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                print("All configuration retries exhausted. Exiting script execution.")
                return # Give up completely to keep execution well under 1-minute threshold

    # Safety catch if data wasn't successfully populated
    if not data:
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