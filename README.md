# GitHub Site Alert Monitor

A lightweight Shopify store inventory monitor that automatically tracks product listings and sends notifications to a Signal group/phone when new items or inventory changes are detected.

## Branch Architecture
To prevent git conflicts between your local edits and the automated script runs, this repository is split into two branches:
* **`main`**: Contains only the code, tests, and configuration files. This is the branch you pull/push to when making code changes.
* **`data`**: Contains only the state files ([last_seen.json](file:///Users/ericraymond/src/quad/github-site-alert/last_seen.json) and [log.yaml](file:///Users/ericraymond/src/quad/github-site-alert/log.yaml)). The GitHub Actions runner checks this branch out to a subdirectory, reads/writes the files, and pushes changes back exclusively to the `data` branch.

## How it Works
1. **Scrapes Shopify**: Fetches products from the target store via its public `products.json` endpoint.
2. **Detects Changes**: Compares current products against a local state file ([last_seen.json](file:///Users/ericraymond/src/quad/github-site-alert/last_seen.json)) and history log ([log.yaml](file:///Users/ericraymond/src/quad/github-site-alert/log.yaml)).
3. **Notifies via Signal**: Sends automated alerts to Signal (via CallMeBot API) when new inventory appears. 
4. **Commits State**: Commits the updated product history state back to the repository using GitHub Actions.

---

## Scheduling & Triggers (Native Cron & Self-Triggering Loop)

This repository uses a hybrid scheduling architecture designed to bypass GitHub Actions cron delays and external trigger limits:

1. **Native GitHub Actions Cron Fallback**: The workflow in [.github/workflows/check.yml](file:///Users/ericraymond/src/quad/github-site-alert/.github/workflows/check.yml) is scheduled natively to trigger every 5 minutes on weekends (expected sale times) and every 20 minutes on weekdays.
2. **Continuous Self-Triggering Loop**: To ensure 100% reliable execution (bypassing any native cron delays), the workflow runs a continuous self-triggering loop (daemon).
   - Once started, the workflow calculates the appropriate interval: 5 minutes during weekends or active sales, and 20 minutes during weekdays.
   - At the end of a run, it sleeps for the calculated duration and dispatches a new workflow run to trigger itself.
   - The native scheduled cron acts as a self-healing fallback to restart the loop if it ever gets cancelled or fails due to network issues.
3. **Pipedream / External Triggers**: No external cron services or tokens are required.
