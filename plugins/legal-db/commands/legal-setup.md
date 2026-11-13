---
description: Legal setup wizard (ליגל) - first-time setup or change of the Legal tools settings
allowed-tools: AskUserQuestion, ToolSearch, Bash, PowerShell, mcp__remote-devices__device_bash
---
The user wants to set up or change the settings of the Legal tools (work mode, Legal folder, user name, VAT, default event location, backups). Talk to the user in Hebrew. (This flow also starts by itself on the first use, when no settings exist yet - the session-start message says so.)

1. The tools run on the user's Windows computer, so this needs the `device_bash` tool (`mcp__remote-devices__device_bash`; load it with ToolSearch if it is deferred) or a local Bash/PowerShell tool. If none is available, tell the user that this chat must be opened in the Claude desktop app on the computer that has Legal, and that she should send a message there; meanwhile give the manual fallback: run `powershell -NoProfile -File "<plugin root>\tools\Setup-MasTmd.ps1"` in a terminal (it then asks the questions itself). The plugin root is in the session-start message `[Legal plugin] root: ...`.
2. If settings already exist, first run `Invoke-MasTmdWrite.ps1 -Action ShowPaths` and show the current mode and Legal folder.
3. Ask the setup questions in the chat with AskUserQuestion (two rounds, every question shows its default as the first option marked "(Recommended)" and the user can type another value):
   - Work mode: Production (real data only, default) / Test (test computer only; only if the user explicitly chooses it).
   - Legal folder (default `C:\Timin`).
   - User name (the Legal user; required, no default) and VAT % (default 18).
   - Default event location number (or none), number of backups to keep (default 15), backup folder (default: the tool's `backups` folder).
   The database password is built into the tools: never ask for it. On later runs ask only what the user wants to change.
4. Run the wizard with the answers, through device_bash:
   `powershell -NoProfile -File "<plugin root>\tools\Setup-MasTmd.ps1" -Auto -Mode production -LegalRoot "C:\Timin" -UserName "<name>" -VatPercent 18 [-EventLocation <n>] [-Keep <n>] [-BackupFolder "<path>"]`
   Pass `-Mode test -ConfirmTest TEST` only if the user explicitly chose test mode in this conversation. Pass only the parameters the user answered or changed.
5. If it prints `ERROR`, explain in Hebrew what to fix and ask again. Otherwise run `Invoke-MasTmdWrite.ps1 -Action ShowPaths` and report the mode, the Legal folder and whether the database was found.
6. Never create or edit `config.json` yourself and never set `MASTMD_CONFIG`; the settings change only through `Setup-MasTmd.ps1`.
