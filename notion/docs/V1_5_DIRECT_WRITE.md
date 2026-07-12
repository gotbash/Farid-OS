# v1.5 Reviewed Direct Write

v1.5 connects the Raycast preparation workflow to the authenticated Notion connector while retaining an explicit review gate. SQP WBR records now also support Codex-side automatic creation in the Decision & Report Log when the user asks for direct Notion write.

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
- SQP WBR payload contract: `notion/connector-actions/create-sqp-wbr.json`
- PPC Search Term WBR/RCA payload contract: `notion/connector-actions/create-ppc-search-term-review.json`

## Why validation is separate

Raycast Script Commands cannot call the Codex Notion connector directly. Keeping validation local and submission connector-side avoids tokens in shell scripts and prevents unreviewed drafts from being written.

For SQP WBR, Codex can write directly through the connected Notion MCP connector. The local Raycast command still copies Markdown to the clipboard and does not store Notion credentials.

For PPC Search Term review, Codex creates two records: one WBR and one RCA. This separates the executive readout from the root-cause workflow.

## Submission policy

- Never submit content containing `[MISSING]` or `[VERIFY]`.
- Exception: SQP WBR may include explicit `[MISSING]` notes for fields that the SQP export cannot contain, such as TACoS.
- Exception: PPC Search Term records may include explicit TACoS missing notes because Search Term Reports do not contain total Amazon sales.
- Never infer owners, dates, sources, or performance figures.
- Create one record per reporting period.
- Preserve source links inside the page body.
