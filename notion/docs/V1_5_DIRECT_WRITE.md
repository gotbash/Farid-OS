# v1.5 Reviewed Direct Write

v1.5 connects the Raycast preparation workflow to the authenticated Notion connector while retaining an explicit review gate.

## Flow

1. Run `Prepare Notion WBR`.
2. Complete the record with `Create Reviewed Notion WBR`.
3. Copy the final record.
4. Run `Validate Notion Record`.
5. Only after `READY FOR NOTION`, create the page in Decision & Report Log through the official connector.

## Target

- Database: Decision & Report Log
- Data source: `collection://6ac3e2fe-3d17-49c4-877f-5a0d2ea4e4b3`
- Connector payload contract: `notion/connector-actions/create-wbr.json`

## Why validation is separate

Raycast Script Commands cannot call the Codex Notion connector directly. Keeping validation local and submission connector-side avoids tokens in shell scripts and prevents unreviewed drafts from being written.

## Submission policy

- Never submit content containing `[MISSING]` or `[VERIFY]`.
- Never infer owners, dates, sources, or performance figures.
- Create one record per reporting period.
- Preserve source links inside the page body.

