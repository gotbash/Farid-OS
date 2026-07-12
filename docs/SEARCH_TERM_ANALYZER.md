# Search Term Report Analyzer

## Run from Raycast

1. Export an Amazon Ads Search Term Report as CSV.
2. Run `Analyze Search Term Report`.
3. Paste the absolute CSV path.
4. Review the report displayed by Raycast and copied to the clipboard.

## Required columns

The analyzer accepts common Amazon names for:

- Customer Search Term
- Impressions
- Clicks
- Spend
- 7-day or 14-day Total Sales
- 7-day or 14-day Total Orders

Currency symbols and thousands separators are removed before calculation.

## Metrics

- CTR = clicks / impressions
- CVR = orders / clicks
- CPC = spend / clicks
- ACOS = spend / attributed sales
- TACoS is deliberately not calculated because Search Term Reports do not contain total Amazon sales.

## Review rules

- Waste candidate: at least 8 clicks and zero attributed sales.
- High ACOS: ACOS above 40%.
- Harvest candidate: at least 2 orders and ACOS at or below 30%.

These rules create review candidates only. They do not change bids, targets, or negative keywords.

