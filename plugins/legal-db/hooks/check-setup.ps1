# SessionStart hook: tells Claude whether the Legal tools are set up and in which mode. Output is added to the session context.
$root = $env:CLAUDE_PLUGIN_ROOT; if (-not $root) { $root = Split-Path $PSScriptRoot -Parent }
$cfgPath = if ($env:MASTMD_CONFIG) { $env:MASTMD_CONFIG } else { Join-Path $env:APPDATA 'MasTmd\config.json' }
Write-Output "[Legal plugin] root: $root"
Write-Output "[Legal plugin] REQUIRED: this plugin works on the user's Windows computer and needs the device_bash tool (mcp__remote-devices__device_bash; load it with ToolSearch if deferred). If it is not available, tell the user (in Hebrew) to open this chat in the Claude desktop app on the computer that has Legal and send a message there."
$cfg = $null
if (Test-Path -LiteralPath $cfgPath) { try { $cfg = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $cfg = $null } }
if ($null -eq $cfg -or $cfg.SetupComplete -ne $true) {
  Write-Output "[Legal plugin] FIRST-TIME SETUP NOT DONE. The Legal tools refuse to work until setup is done. START THE SETUP NOW, interactively in the chat, before anything else the user asks (do not wait for a slash command): follow `"$root\commands\legal-setup.md`" - ask the questions with AskUserQuestion, then run Setup-MasTmd.ps1 -Auto with the answers. Fallback for the user: run in a terminal: powershell -NoProfile -File `"$root\tools\Setup-MasTmd.ps1`""
  Write-Output "[Legal plugin] Never create/edit the settings file yourself; settings change only through Setup-MasTmd.ps1."
} else {
  $mode = if ("$($cfg.TestMode)" -in 'True','true') { 'TEST MODE' } else { 'PRODUCTION (real data only)' }
  $legal = if ($cfg.LegalRoot) { $cfg.LegalRoot } else { 'C:\Timin' }
  $db = Join-Path $legal $(if ($cfg.DbFileName) { $cfg.DbFileName } else { 'MasTmd.mdb' })
  Write-Output "[Legal plugin] settings found. Mode: $mode. Legal folder: $legal (database present: $(Test-Path -LiteralPath $db))."
  Write-Output "[Legal plugin] Use the legal-db skill for any work on Legal. Do not change the mode or the settings file."
}
exit 0
