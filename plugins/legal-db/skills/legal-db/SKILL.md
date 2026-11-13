---
name: legal-db
description: Work with the Legal (ליגל) law-office case-management software through its database (MasTmd.mdb) - find clients and cases, open a client/case, add calendar events (meeting, pre-trial, hearing, reminder, task, call, notes, damage assessment), add/rename/move/delete case documents and sub-folders, change case status, close or reopen a case. Use whenever the user asks to open or organise a client file, create events/documents/sub-folders, normalise file names, change a case status, or read case data from Legal. Also triggers on "ליגל", "תכתוב לליגל", "תיצור בליגל".
compatibility: Requires Windows with local PowerShell and the Legal software (Access/Jet database). Works in Claude Code and in the Code tab of the Claude desktop app; not in plain chat or Cowork sandboxes.
---

# Legal DB skill

## Where things are
`${CLAUDE_PLUGIN_ROOT}` is replaced by the plugin's installation folder when this skill loads (if you ever see it literally, use the path from the session-start message `[Legal plugin] root: ...`). The tools are in `${CLAUDE_PLUGIN_ROOT}\tools\`, the reference in `${CLAUDE_PLUGIN_ROOT}\docs\reference.md` (read it before acting on anything you are unsure about). The session-start message `[Legal plugin] root: ...` also shows the plugin root.

| file | what |
|---|---|
| `tools\Invoke-MasTmdWrite.ps1` | THE write tool: dry-run by default, `-Apply` to write. Also read-only actions `Find`, `Info`, `ListKinds`, `ListStatuses`, `FindStatus`, `ShowPaths` |
| `tools\Invoke-MasTmd.ps1` | read-only database queries (`-Action Query -Sql "..."`, Tables, Columns, Test) |
| `tools\Setup-MasTmd.ps1` | settings wizard (see "First-run setup") |
| `%APPDATA%\MasTmd\config.json` | settings file (per Windows user): mode, Legal folder, user name, VAT, event location, backups |

## Vocabulary rule: "ליגל" / "Legal" = the software we work against
When the user says "תכתוב לליגל", "תשאל את ליגל", "תיצור בליגל", "בדוק בליגל", they mean: do it **through this tool**, the way the software itself would store it. It is not a request to contact a company or an external service. Answer in Hebrew and call the system "ליגל". If a request is outside what the tool does safely, say so instead of improvising.

## How to run the tool
**Prefer the plugin's MCP tools when they are available** (`legal_read`, `legal_preview`, `legal_apply`, `legal_setup_status`, `legal_setup_apply`; the plugin starts this restricted server itself through `.mcp.json`, and the Desktop extension offers the same tools). They enforce the two steps for you: `legal_preview` writes nothing and returns a one-time token, `legal_apply` writes exactly what was previewed and only with that token. Use the PowerShell script directly only when these tools are not present.

From PowerShell (any version; it relaunches itself in 32-bit Windows PowerShell), with a quoted full path:
`& "${CLAUDE_PLUGIN_ROOT}\tools\Invoke-MasTmdWrite.ps1" -Action <Action> ...`
Actions: `ListKinds`, `Find -Name`, `Info -Case`, `AddEvent -Case -Kind -Text [-Date yyyy-MM-dd -Start HH:mm -End HH:mm -Color -Amount -NoAlarm]`, `AddDocument -Case -File [-Kind 1|2 -Text -Date -Move]`, `Rename -Act -NewText`, `Move -Act -ToCase`, `Delete -Act`, `NewCase -First -Last [-SueKind 24|22|98|20|102 -Phone -CustomerId]`, `NewSubfolder -Case -Name`, `RenameFolder -Case -NewText`, `SetStatus -Case -Text`, `CloseCase -Case [-Date]`, `ReopenCase -Case [-Text]`, `ListStatuses`, `FindStatus -Text`, `AddStatus -Text [-NotSimilar]`, `RemoveStatus -Text`, `ShowPaths`, `SetRoot -Path`.
Case ids are `CaseID` (not the displayed case number); `Find`/`Info` show both. Sub-folders are cases with `SueKind=77`. Never write the `.mdb` or the documents folder by any other route (no raw SQL writes, no manual file moves): the tool keeps rows, file names and paths consistent.
**Concurrency rule:** if the case card is open in Legal when the tool writes to that case, Legal fails on its next save of that card ("Row cannot be located for updating"). Ask the user to close the card first and reopen it afterwards.

## Status vs. closing a case
- **Close the case** => `CloseCase`: status "סגור" **and** the close date (default today), always together.
- **Any other status** (e.g. "ממתין לתשובת חברת ביטוח") => `SetStatus`: only the status, **no close date**. `SetStatus` refuses "סגור" (use `CloseCase`), closed cases (use `ReopenCase`) and statuses that do not exist.
- **Open a case** (status AND close date empty) => `ReopenCase` with no `-Text`. With `-Text <status>`: reopen into that existing status.
- **New status procedure - never create a status straight away:** (1) `FindStatus` / `ListStatuses`; the tool matches by wording only, **you also judge by meaning**. (2) Exact match -> use it. Similar -> offer it first (AskUserQuestion: use the similar one / create a new one). (3) If a different wording would fit the existing style better, offer it as another option. (4) Only if the user says nothing fits -> `AddStatus -Text <name> -NotSimilar -AllowRealData`, then `SetStatus`. The catalog is shared and appears in Legal's status list, so get the exact final name approved first. `RemoveStatus` removes a catalog status no case uses.

## Interactive protocol (guided, Hebrew, RTL)
Never ask free text when choices exist.
1. **Understand the goal.** Missing details -> `AskUserQuestion`: one question per item, 2-4 short options, recommended first; `multiSelect: true` (checkboxes) when several items may apply.
2. **Resolve the target** with `Find`/`Info`; confirm only if ambiguous.
3. **Dry-run** (no `-Apply`) and present the plan as a clean visual card (`mcp__visualize__show_widget` after `read_me` with modules `interactive`, `mockup`): before -> after for names, dates, folders. Templates: `cards\plan-card.html` (one action) and `cards\batch-card.html` (many items with a checkbox each, "select all", live count) in this skill's folder. A button click arrives as a normal user message: treat it as the decision.
4. **Approval** with `AskUserQuestion` (first option = approve). Never apply without an explicit yes in this turn.
5. **Apply** with `-Apply -AllowRealData` for the approved change only (the tool backs up the database first), then **verify** (`[VERIFY]` line; `Info` for batches) and report briefly what changed and what to check in Legal.
6. Short messages in Hebrew; show CaseID/ActID so the user can find items.

## First-run setup (starts by itself, interactive in the chat)
**When the session-start message says FIRST-TIME SETUP NOT DONE, or any tool prints `[SETUP REQUIRED]`, start the setup immediately - before doing whatever else the user asked, and without waiting for a slash command.** Tell the user in one Hebrew sentence that this is the first use and a short setup follows, then run the flow of `commands\legal-setup.md` (same as `/legal-db:legal-setup`):
1. Ask the questions in the chat with `AskUserQuestion`, two short rounds, every question showing its default as the first option marked "(Recommended)" (the user can also type another value): work mode (Production = default / Test), Legal folder (default `C:\Timin`), user name (required, no default), VAT % (default 18), default event location (or none), number of backups to keep (default 15) and backup folder (default: the tool's `backups` folder).
2. Run `powershell -NoProfile -File "${CLAUDE_PLUGIN_ROOT}\tools\Setup-MasTmd.ps1" -Auto -Mode production -LegalRoot "..." -UserName "..." -VatPercent N [-EventLocation N] [-Keep N] [-BackupFolder "..."]` with the answers, through `device_bash` (or a local PowerShell/Bash tool when the session already runs on the user's computer). Test mode only with `-Mode test -ConfirmTest TEST` and only if the user explicitly chose it in this conversation.
3. On `ERROR` explain in Hebrew what to fix and ask again. Otherwise run `Invoke-MasTmdWrite.ps1 -Action ShowPaths`, report the mode, the Legal folder and whether the database was found, and continue with the user's original request.
The database password is built into the tools (the same for every Legal installation): never ask for it. **Never create/edit the settings file (`config.json`) or set `MASTMD_CONFIG`**; settings change only through the wizard. Later changes of settings: run the same flow, asking only what the user wants to change. `SetRoot` (Legal folder) is the only setting the tool itself may change, and only when the user asks. These tools need the `device_bash` tool (the chat linked to the user's computer through the Claude desktop app); without it, tell the user to open the chat in the desktop app, or to run `Setup-MasTmd.ps1` in a terminal.
## Mode rule: TestMode (set by the user, never by Claude)
Every run prints `[MODE] ...`.
- **PRODUCTION** (`TestMode=false`, also when missing): real data only. The tool refuses `-Test`/`-DbOverride` and ignores test-case lists. Do not create dummy customers, cases, documents or events, do not look for ways around a refusal. If the user wants test data, say it needs a separate test installation.
- **TEST MODE**: test machines only.
- **Never edit the settings file or `TestMode`, never set or use the `MASTMD_CONFIG` environment variable, never copy the tool to run it under another configuration, never suggest flipping the mode.** The plugin also blocks such tool calls. If the banner says PRODUCTION treat everything as the customer's real data.

## Safety rules
- Every real change needs the user's explicit approval of the exact change (client, case, what changes).
- Not covered, tell the user it is outside the tool: invoices, payments, bookkeeping, enforcement modules, clients' personal data edits, passwords/owners tables, process-model editing and automation rules.
- Deleting moves files to `DeletedFiles\` and logs to `tblBankDeletes` (like Legal). Do not delete unless asked.
- If a result looks wrong, stop and report. Automatic backups are in the tool's `backups` folder (restore only on explicit request, with Legal closed).
- Never print or paste the database password.

## Known limits
- NewCase supports types 24 (general) and 22/98/20/102 (torts); other types are not verified.
- Events: kinds in `ListKinds` have verified templates; other hearing/meeting kinds use a generic template.
- Legal may need a refresh to show changes made by the tool.
