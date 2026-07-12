# v1.4 Notion Automation

Automation Hub: https://app.notion.com/p/39b5ac9e528581158966d37ec4e0e864

Target database: **Decision & Report Log** (`collection://6ac3e2fe-3d17-49c4-877f-5a0d2ea4e4b3`).

## Raycast workflow

1. Run `Prepare Notion WBR`, `Prepare Notion Decision`, or `Prepare Metric Diagnostic`.
2. Complete the copied Markdown using the relevant Farid OS AI command.
3. Review every `[VERIFY]` and `[MISSING]` marker.
4. Save the reviewed record in Decision & Report Log.

## Database contract

- `Record` — required title
- `Type` — Decision, Root Cause Analysis, Daily Pulse, WBR, QBR, or Risk
- `Decision Date` — record date
- `Area` — Amazon Ads, Marketplace, Inventory, Pricing, Content, or Career
- `Impact` — High, Medium, or Low
- `Owner` — accountable person
- `Status` — Not started, In progress, or Done
- `Review Date` — required for decisions and open risks

## Direct-write guardrail

The repository intentionally contains no Notion token. Direct API submission should be added only through an authenticated n8n credential or the official Notion connector, and should preserve a review step before writing.

