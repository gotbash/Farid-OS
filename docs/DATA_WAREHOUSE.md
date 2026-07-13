# Farid OS Data Warehouse

The warehouse is the local foundation for automated reporting, competitor tracking, forecasting, and alerts.

## Location

Default database:

```text
data/farid_os.db
```

The database is intentionally ignored by Git because it contains local business data exported from Amazon.

## Import command

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/warehouse_importer.py
```

From Raycast:

```text
Import Rubex Warehouse
```

The importer scans:

```text
~/Downloads/Rubex/Reports
```

## Supported reports

- Sponsored Products Search Term reports
- Sponsored Products Campaign reports
- Sponsored Products Targeting reports
- Brand Analytics Search Query Performance reports
- Brand Analytics Search Catalog Performance reports

Unsupported reports are skipped until a dedicated parser is added.

## Current tables

- `report_files`
- `ppc_search_terms`
- `ppc_campaigns`
- `ppc_targets`
- `sqp_queries`
- `catalog_asins`
- `products`
- `competitors`
- `competitor_snapshots`
- `forecasts`
- `alerts`
- `latest_report_files` view

## Design rules

- Files are deduplicated by SHA-256 hash.
- Raw report files remain in `~/Downloads/Rubex/Reports`.
- The warehouse stores normalized metrics, not credentials.
- Bid recommendations are review-ready only; no automatic Amazon Ads changes are executed.

## Next layers

1. Weekly PPC WBR generated from warehouse tables.
2. Product margin and target ACOS values populated in `products`.
3. Competitor ASIN snapshots populated in `competitor_snapshots`.
4. Forecast rows generated in `forecasts`.
5. Alert generation for ACOS, CTR, CVR, CPC, competitor price, and rank movement.

## Forecast command

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/forecast_engine.py
```

From Raycast:

```text
Create Weekly Forecast
```

The current forecast is a baseline low/base/high scenario from the latest PPC targeting report. It becomes a stronger trend forecast after several weekly snapshots exist in the warehouse.

## Competitor tracker commands

Import product and competitor definitions:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/competitor_tracker.py import-config
```

The command reads `config/competitors.local.json` if present. If it is missing, it falls back to `config/competitors.example.json`.

Import the latest manual/API snapshot CSV from `~/Downloads/Rubex/Competitors`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/competitor_tracker.py import-snapshot
```

Create a competitor report:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/competitor_tracker.py report
```

Raycast commands:

```text
Import Competitors Config
Import Competitor Snapshot
Create Competitor Report
```

Snapshot CSV columns:

```text
competitor_asin, competitor_name, product_asin, brand, price, rating, reviews, coupon, organic_rank, sponsored_rank, captured_at, raw_source
```

Example:

```text
examples/competitor-snapshot-sample.csv
```

The current tracker is source-agnostic. Manual CSV, browser automation, Keepa, Helium10, or API collectors can all write the same snapshot format.
