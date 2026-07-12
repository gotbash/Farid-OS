# Farid OS v1.5

Personal Raycast operating system for Amazon operations, executive reporting, interviews, and a Notion-backed knowledge vault.

## Included

- `raycast/quicklinks/` — importable Raycast Quicklinks
- `raycast/snippets/` — reusable prompt and report snippets
- `raycast/ai-commands/` — AI command definitions in Markdown (plus a portable JSON catalog)
- `raycast/script-commands/` — executable Raycast shell commands
- `notion/docs/` — Knowledge Vault map and operating guidance
- `prompts/` — longer reusable Amazon and interview prompts
- `notion/templates/` — reviewed WBR, decision, and metric-diagnostic records

## Install

1. In Raycast, search for **Import Quicklinks** and select `raycast/quicklinks/quicklinks.json`.
2. Search for **Import Snippets** and select `raycast/snippets/snippets.json`.
3. Open **Raycast Settings → Extensions → Script Commands → Add Directories** and add `raycast/script-commands`.
4. Create AI Commands from the Markdown files in `raycast/ai-commands/`. Raycast import formats can vary by app version, so `AI_COMMANDS.json` is supplied as a readable catalog and the Markdown files are the source of truth.
5. Open the Notion Knowledge Vault from Raycast with the `vault` command.
6. Use the v1.4 `Prepare Notion…` commands to copy review-ready Markdown into your workflow.
7. Run `Validate Notion Record` before a reviewed connector write.

No API keys or credentials are stored in this repository. Seller Central links may require sign-in and can vary by marketplace/account.

## Recommended aliases

| Command | Alias |
|---|---|
| Knowledge Vault | `vault` |
| Amazon Playbooks | `pb` |
| Experience Library | `cases` |
| Interview Bank | `ib` |
| Decision Log | `dec` |
| Search Notion | `ns` |
| Amazon Search | `amz` |

## Versions

- **v1.0 — Amazon Core:** Amazon dashboards, analysis prompts, interview and executive workflows.
- **v1.1 — Notion Knowledge Vault:** Notion-first playbooks, experience library, interview bank, and decision/report log.
- **v1.2 — Raycast ↔ Notion Copilot:** Vault launch/search commands, Notion-oriented AI commands, and structured capture templates.
- **v1.3 — Decision Engine + Report Factory:** ACOS/TACoS diagnostics, Daily Pulse, WBR, QBR, and RCA workflows.
- **v1.4 — Notion Automation:** reviewed data contract, Automation Hub, and Raycast capture commands.
- **v1.5 — Reviewed Direct Write:** local validation plus an authenticated Notion connector contract.

See [VERSION_NOTES.md](VERSION_NOTES.md) for details.
