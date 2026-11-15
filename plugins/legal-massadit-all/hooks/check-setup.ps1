# SessionStart hook: tells Claude whether the Legal tools are set up and in which mode. Output is added to the session context.
$root = $env:CLAUDE_PLUGIN_ROOT; if (-not $root) { $root = Split-Path $PSScriptRoot -Parent }
$cfgPath = if ($env:MASTMD_CONFIG) { $env:MASTMD_CONFIG } else { Join-Path $env:APPDATA 'MasTmd\config.json' }
Write-Output "[Legal-Massadit plugin] root: $root"
Write-Output "[Legal-Massadit plugin] TOOLS: FIRST check whether the Legal-Connector tools packed inside this plugin are available (full names: mcp__plugin_legal-massadit-all_Legal-Connector__legal_read, mcp__plugin_legal-massadit-all_Legal-Connector__legal_preview, mcp__plugin_legal-massadit-all_Legal-Connector__legal_apply, mcp__plugin_legal-massadit-all_Legal-Connector__legal_setup_status, mcp__plugin_legal-massadit-all_Legal-Connector__legal_list_users, mcp__plugin_legal-massadit-all_Legal-Connector__legal_setup_apply; if they are deferred, load them with ToolSearch: select: and these names, or the keyword query legal_read). If they are, use ONLY them (also for the first-time setup) and do not look for device_bash. Only if they are not available: the PowerShell scripts need the user's Windows computer through the device_bash tool (mcp__remote-devices__device_bash) or a local PowerShell/Bash tool; if none exists either, tell the user in Hebrew to install the Legal-Connector extension (.mcpb) in Claude Desktop, restart Claude Desktop completely and open a new chat."
$cfg = $null
if (Test-Path -LiteralPath $cfgPath) { try { $cfg = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $cfg = $null } }
if ($null -eq $cfg -or $cfg.SetupComplete -ne $true) {
  Write-Output "[Legal-Massadit plugin] FIRST-TIME SETUP NOT DONE. The Legal tools refuse to work until setup is done. START THE SETUP NOW, interactively in the chat, before anything else the user asks (do not wait for a slash command): follow `"$root\commands\legal-setup.md`" - ask the questions with AskUserQuestion, then run Setup-MasTmd.ps1 -Auto with the answers. Fallback for the user: run in a terminal: powershell -NoProfile -File `"$root\tools\Setup-MasTmd.ps1`""
  Write-Output "[Legal-Massadit plugin] Never create/edit the settings file yourself; settings change only through Setup-MasTmd.ps1."
} else {
  $mode = if ("$($cfg.TestMode)" -in 'True','true') { 'TEST MODE' } else { 'PRODUCTION (real data only)' }
  $legal = if ($cfg.LegalRoot) { $cfg.LegalRoot } else { 'C:\Timin' }
  $db = Join-Path $legal $(if ($cfg.DbFileName) { $cfg.DbFileName } else { 'MasTmd.mdb' })
  Write-Output "[Legal-Massadit plugin] settings found. Mode: $mode. Legal folder: $legal (database present: $(Test-Path -LiteralPath $db))."
  Write-Output "[Legal-Massadit plugin] Use the legal-db skill of the Legal-Massadit plugin for any work on Legal. Do not change the mode or the settings file."
}
exit 0
