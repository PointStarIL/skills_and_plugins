# PreToolUse hook: blocks tool calls that would touch the Legal tools' settings file directly or redirect it (MASTMD_CONFIG).
# Settings change only through the setup wizard (Setup-MasTmd.ps1, run by the user or by the assistant with the user's answers); the assistant must not edit the file itself. Exit code 2 blocks the call and shows the message.
$raw = [Console]::In.ReadToEnd()
if (-not $raw) { exit 0 }
try { $j = $raw | ConvertFrom-Json } catch { exit 0 }
function Flatten($o) {
  if ($null -eq $o) { return @() }
  if ($o -is [string]) { return @($o) }
  if ($o -is [System.Collections.IEnumerable] -and $o -isnot [string]) { return @($o | ForEach-Object { Flatten $_ }) }
  if ($o -is [psobject] -and $o.PSObject.Properties.Count -gt 0 -and $o -isnot [ValueType]) { return @($o.PSObject.Properties | ForEach-Object { Flatten $_.Value }) }
  @("$o")
}
$text = (Flatten $j.tool_input) -join "`n"
$patterns = @('(?i)MasTmd[\\/]+config\.json', 'MASTMD_CONFIG')
foreach ($p in $patterns) {
  if ($text -match $p) {
    [Console]::Error.WriteLine("Blocked by the Legal plugin: this call touches the Legal tools' settings file directly (file / MASTMD_CONFIG). Settings change only through Setup-MasTmd.ps1 (/legal-db:legal-setup) with the user's answers. Do not try another way around it.")
    exit 2
  }
}
exit 0
