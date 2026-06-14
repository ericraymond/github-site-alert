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

## Scheduling & Triggers (External Cron)

### ⚠️ GitHub Actions Cron Limitation
GitHub Actions scheduled workflows (`cron`) run on a best-effort basis and are subject to massive queueing delays in free/public repositories (often delayed by minutes to hours, or skipped entirely).

### Recommended Setup: External Cron (Pipedream)
To ensure the monitor runs reliably on a precise schedule (e.g. every 5 minutes):
* **Pipedream (or other external cron services)** is used to trigger the workflow externally.
* This is done by scheduling a Pipedream workflow to run every 5 minutes, which triggers the **`workflow_dispatch`** or **`repository_dispatch`** event in this repository.
* The internal GitHub `schedule:` cron in [.github/workflows/check.yml](file:///Users/ericraymond/src/quad/github-site-alert/.github/workflows/check.yml) has been commented out to prevent redundant/delayed runs.

### How to trigger it externally:
Create a Pipedream workflow on a 5-minute schedule using the **GitHub - Create Workflow Dispatch** action pointing to:
- **Workflow**: `check.yml`
- **Ref**: `main`
