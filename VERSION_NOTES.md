# Version History

## v2.4.1 - Amazon.com Research Guardrail
- Added US marketplace and `amazon.com` defaults to competitor research templates and snapshots.
- Added Amazon.com search URLs to generated competitor research templates.
- Updated competitor research reports to show marketplace, search domain, and search URL.

## v2.4 - Competitor Research Builder
- Added keyword-based competitor research CSV template generation.
- Added keyword/search-position fields to competitor snapshots.
- Added threat scoring based on price, review moat, rating, coupon, organic rank, and sponsored rank.
- Added a competitor research report with recommended PPC/listing actions.
- Added Raycast commands for research template generation and research report creation.

## v2.3 - Competitor Tracker
- Added competitor/product config import into the local warehouse.
- Added manual/API-ready competitor snapshot CSV import.
- Added competitor movement report covering price, rating, reviews, coupon, organic rank, and sponsored rank.
- Added Raycast commands for competitor config import, snapshot import, and report generation.
- Added a sample competitor snapshot CSV for repeatable testing.

## v2.2 - Baseline Forecast Engine
- Added a weekly low/base/high forecast generator from local warehouse PPC data.
- Added a `forecasts` table and Raycast command for forecast creation.
- Added a competitor configuration template to prepare ASIN tracking.

## v2.1 - Data Warehouse Foundation
- Added a local SQLite warehouse at `data/farid_os.db` for supported Rubex/Amazon reports.
- Added an importer that scans `~/Downloads/Rubex/Reports`, detects report types, deduplicates files by SHA-256, and loads normalized tables.
- Added warehouse tables for Sponsored Products Search Terms, Campaigns, Targeting, SQP queries, and Search Catalog ASINs.
- Added a Raycast command for one-step warehouse import and clipboard-ready summary output.
- Added warehouse documentation and Git ignores for local business data.

## v1.19 - PPC Action Plan
- Added a combined PPC action-plan generator across Search Term, Campaign, and Targeting reports.
- Added a Raycast command that creates a clipboard-ready action plan from the latest Rubex reports.
- Added a Notion connector contract for saving the PPC action plan to Decision & Report Log.
- Added guarded bid/relevance review recommendations without automatic bid changes.

## v1.18 - Sponsored Products Targeting Report
- Added a Sponsored Products Targeting report analyzer.
- Updated latest-report dispatch to identify targeting-level XLSX exports.
- Added waste, high-ACOS, and harvest/protect target review sections.

## v1.17 - Sponsored Products Campaign Report
- Added a Sponsored Products Campaign report analyzer.
- Updated latest-report dispatch to identify campaign-level CSV exports.
- Added campaign-level spend, ACOS, zero-sales, and strong-campaign review sections.

## v1.16 - PPC Search Term Notion Review
- Added a Notion connector contract for PPC Search Term WBR and RCA creation.
- Created separate WBR and RCA records from the Sponsored Products Search Term report.
- Preserved the guardrail against automatic bid or negative-keyword changes.

## v1.15 - Sponsored Products Search Term XLSX
- Added XLSX support for Amazon Ads Sponsored Products Search Term reports.
- Updated latest-report intake to consider `.xlsx` files in `~/Downloads/Rubex/Reports`.
- Kept parsing dependency-free by using Python standard-library ZIP/XML handling.

## v1.14 - Top Search Terms Intake
- Added a streaming Brand Analytics Top Search Terms analyzer for large files.
- Updated latest-report dispatch so Top Search Terms is not mistaken for an Ads Search Term Report.
- Clarified that Top Search Terms lacks spend, sales, ACOS, CPC, and campaign fields.

## v1.13 - Search Catalog Performance
- Added a Search Catalog Performance analyzer for ASIN-level search funnel exports.
- Updated the latest Rubex report dispatcher to detect metadata-row catalog files.
- Kept Brand Analytics Trends detection explicit but unsupported until a dedicated analyzer is added.

## v1.12 - Latest Rubex Report Intake
- Added a dispatcher that finds the newest CSV in `~/Downloads/Rubex/Reports`.
- Added report-type detection for SQP, Search Term Report, and Brand Analytics Trends.
- Added a Raycast command for one-step latest-report analysis.
- Fixed the SQP analyzer row-count regression introduced during WBR extraction.

## v1.11 - Notion SQP Auto-Write
- Added a connector action contract for SQP WBR records.
- Confirmed the target Decision & Report Log data source for automatic Notion creation.
- Documented the difference between Codex connector auto-write and local Raycast clipboard capture.

## v1.10 - SQP WBR Capture
- Added a Notion-ready WBR output mode to the SQP analyzer.
- Added a Raycast command that turns an SQP CSV path into a clipboard-ready WBR summary.

## v1.9 - Raycast Notion Capture Commands
- Added Raycast script commands for Daily Pulse and RCA capture.
- Commands copy Notion-ready Markdown to the clipboard for reviewed insertion into the Decision & Report Log.

## v1.8 - Notion Operating Templates
- Added Notion-ready Daily Pulse and RCA templates.
- Aligned the new templates with the Raycast Daily Pulse and RCA AI commands.
- Updated README versioning to reflect the current release line.

## v1.7 - Search Query Performance
- Added a standard-library Search Query Performance analyzer for Brand Analytics exports.
- Added a Raycast script command with clipboard and temporary Markdown output.
- Added a labeled synthetic SQP sample for reproducible testing.

## v1.6 - Amazon Data Intake (Current)
- Added a standard-library Search Term Report CSV analyzer.
- Added data-quality checks, PPC metric calculations, and review candidate rules.
- Added a Raycast command with clipboard and temporary Markdown output.
- Added a labeled synthetic CSV for reproducible testing.

## v1.5 - Reviewed Direct Write
- Added a Raycast validation gate for WBR records.
- Added a direct link to Decision & Report Log.
- Added a connector-ready WBR property and content contract.
- Added a reviewed WBR AI command with strict missing-data rules.

## v1.4 - Notion Automation
- Added the Notion Automation Hub inside the Knowledge Vault.
- Added Raycast commands for WBR, decision, and metric-diagnostic capture.
- Added Notion-ready templates and the Decision & Report Log data contract.
- Kept credentials out of Git and preserved a review step before writes.

## v1.3 - Decision Engine & Report Factory
- Added new AI Commands and Snippets for comprehensive business reporting and diagnostics:
  - ACOS/TACoS Diagnostic
  - Daily Pulse Report
  - WBR (Weekly Business Review) Report Generator
  - QBR (Quarterly Business Review) Strategy Builder
  - RCA (Root Cause Analysis) Framework
- Consolidated Snippets (!ppcaudit, !wbr, !star, !qbr, !acos) for fast operational execution.

## v1.2 - Raycast Native
- Migrated core tools to native Raycast Script Commands
- Packaged Knowledge Vault and Quicklinks for rapid deployment

## v1.1 - The Command Center
- First iteration of structured prompts and search integration
- Amazon workflows standardized

## v1.0 - Genesis
- Foundational Knowledge Vault setup and basic AI interaction models
