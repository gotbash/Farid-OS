# Version History

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
