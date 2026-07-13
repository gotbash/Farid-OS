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
