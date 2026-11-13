# Restricted MCP server (stdio) for the Legal tools. It exposes THREE tools only - not a general shell:
#   legal_read     read-only actions (find / info / lists)
#   legal_preview  dry-run of a write action; returns a one-time confirmation token
#   legal_apply    executes exactly the previewed action (arguments are fixed by the token, cannot be changed)
# It never exposes the settings file, the setup wizard, MASTMD_CONFIG, -Test or -DbOverride.
$ErrorActionPreference = 'Stop'
$enc = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $enc
$script:reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), $enc)
$script:writer = New-Object System.IO.StreamWriter([Console]::OpenStandardOutput(), $enc); $script:writer.AutoFlush = $true
$root = Split-Path $PSScriptRoot -Parent
$tool = Join-Path $root 'tools\Invoke-MasTmdWrite.ps1'
$psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$serverVersion = '1.0.0'
$pending = @{}      # token -> @{ argv; summary; expires }

$readActions  = @('Find', 'Info', 'ListKinds', 'ListStatuses', 'FindStatus', 'ListStages', 'ShowPaths')
$writeActions = @('AddEvent', 'AddDocument', 'Rename', 'Move', 'Delete', 'NewCase', 'NewSubfolder', 'RenameFolder', 'SetStatus', 'CloseCase', 'ReopenCase', 'AddStatus', 'RemoveStatus')
# argument name (as sent by the client) -> @(tool parameter, type)
$argMap = [ordered]@{
  case = @('Case', 'int'); act = @('Act', 'int'); to_case = @('ToCase', 'int'); customer_id = @('CustomerId', 'int'); sue_kind = @('SueKind', 'int'); color = @('Color', 'int')
  name = @('Name', 'str'); kind = @('Kind', 'str'); text = @('Text', 'str'); new_text = @('NewText', 'str'); date = @('Date', 'str'); start = @('Start', 'str'); end = @('End', 'str')
  amount = @('Amount', 'str'); file = @('File', 'str'); first = @('First', 'str'); last = @('Last', 'str'); phone = @('Phone', 'str')
  move = @('Move', 'switch'); no_alarm = @('NoAlarm', 'switch'); not_similar = @('NotSimilar', 'switch')
}
function Send($obj) { $script:writer.WriteLine((ConvertTo-Json -InputObject $obj -Depth 12 -Compress)) }
function Reply($id, $result) { Send ([ordered]@{ jsonrpc = '2.0'; id = $id; result = $result }) }
function Fail($id, $code, $msg) { Send ([ordered]@{ jsonrpc = '2.0'; id = $id; error = [ordered]@{ code = $code; message = $msg } }) }
function TextResult($text, [bool]$isError = $false) { [ordered]@{ content = @([ordered]@{ type = 'text'; text = $text }); isError = $isError } }
function Prop($type, $desc) { [ordered]@{ type = $type; description = $desc } }
function ArgSchema {
  [ordered]@{
    case = Prop 'integer' 'CaseID (internal id; Find/Info show it) - not the displayed case number'
    act = Prop 'integer' 'ActID of a document or event'
    to_case = Prop 'integer' 'target CaseID (sub-folder case) for Move'
    customer_id = Prop 'integer' 'existing CustomerID for NewCase'
    sue_kind = Prop 'integer' 'case type for NewCase: 24 general, 22/98/20/102 torts'
    color = Prop 'integer' 'calendar colour override (1 red, 4 blue, 7 green, 16 purple)'
    name = Prop 'string' 'client or folder name'
    kind = Prop 'string' 'event kind id or name (14 meeting, 3 pre-trial, 4 hearing, 11 reminder, 7 task, 15 call, 39 event, 66 internal note, 52 damage assessment) or document kind 1/2'
    text = Prop 'string' 'description / status text / title'
    new_text = Prop 'string' 'new title (Rename, RenameFolder)'
    date = Prop 'string' 'date yyyy-MM-dd'
    start = Prop 'string' 'start time HH:mm'
    end = Prop 'string' 'end time HH:mm'
    amount = Prop 'string' 'amount for damage assessment'
    file = Prop 'string' 'path of an existing file to import (AddDocument)'
    first = Prop 'string' 'client first name (NewCase)'
    last = Prop 'string' 'client family name (NewCase)'
    phone = Prop 'string' 'client phone (NewCase)'
    move = Prop 'boolean' 'move the file instead of copying (AddDocument)'
    no_alarm = Prop 'boolean' 'no alarm (AddEvent)'
    not_similar = Prop 'boolean' 'user rejected the similar statuses (AddStatus)'
  }
}
function Tools-Core {
  $actionRead = [ordered]@{ type = 'string'; enum = $readActions; description = 'read-only action' }
  $actionWrite = [ordered]@{ type = 'string'; enum = $writeActions; description = 'write action to preview' }
  $rs = ArgSchema; $ws = ArgSchema
  $rs = [ordered]@{ action = $actionRead } + $rs
  $ws = [ordered]@{ action = $actionWrite } + $ws
  @(
    [ordered]@{ name = 'legal_read'; title = 'Legal: read'; description = 'Read data from the Legal case-management software: Find (clients/cases by name), Info (case summary, folder, acts), ListKinds, ListStatuses, FindStatus, ListStages, ShowPaths. Never writes.'
      inputSchema = [ordered]@{ type = 'object'; properties = $rs; required = @('action') }; annotations = [ordered]@{ readOnlyHint = $true; destructiveHint = $false; idempotentHint = $true; openWorldHint = $false } },
    [ordered]@{ name = 'legal_preview'; title = 'Legal: preview a change'; description = 'Dry-run of a change in Legal (nothing is written). Returns exactly what would be written and a one-time confirmation token. Show the preview to the user and get an explicit yes before calling legal_apply.'
      inputSchema = [ordered]@{ type = 'object'; properties = $ws; required = @('action') }; annotations = [ordered]@{ readOnlyHint = $true; destructiveHint = $false; idempotentHint = $true; openWorldHint = $false } },
    [ordered]@{ name = 'legal_apply'; title = 'Legal: apply the previewed change'; description = 'Writes to Legal exactly the change that legal_preview showed (identified by its token; arguments cannot be changed). Only after the user explicitly approved that preview. The database is backed up automatically first.'
      inputSchema = [ordered]@{ type = 'object'; properties = [ordered]@{ token = Prop 'string' 'confirmation token returned by legal_preview' }; required = @('token') }; annotations = [ordered]@{ readOnlyHint = $false; destructiveHint = $true; idempotentHint = $false; openWorldHint = $false } }
  )
}
function Setup-Tools {
  $sp = [ordered]@{
    mode = [ordered]@{ type = 'string'; enum = @('production', 'test'); description = 'work mode: production (real data only, default) or test (test computer only)' }
    confirm_test = Prop 'string' 'must be exactly TEST, typed or explicitly confirmed by the user, to enable test mode'
    legal_root = Prop 'string' 'folder that contains the Legal database and the documents folder (default C:\Timin)'
    user_name = Prop 'string' 'Legal user name (written as creator/sender of items)'
    vat_percent = Prop 'integer' 'VAT percent 0-30 (default 18)'
    event_location = Prop 'string' 'default location number for calendar events, or empty for none'
    keep = Prop 'integer' 'number of automatic backups to keep (default 15)'
    backup_folder = Prop 'string' 'backup folder (default: the tool folder)'
  }
  @(
    [ordered]@{ name = 'legal_setup_status'; title = 'Legal: setup status'; description = 'Shows whether the first-time setup was completed, the work mode and the Legal folder. If setup is not complete, run the interactive setup: ask the user the questions in the chat (AskUserQuestion), then call legal_setup_apply.'
      inputSchema = [ordered]@{ type = 'object'; properties = [ordered]@{} }; annotations = [ordered]@{ readOnlyHint = $true; destructiveHint = $false; idempotentHint = $true; openWorldHint = $false } },
    [ordered]@{ name = 'legal_setup_apply'; title = 'Legal: save settings'; description = 'Saves the settings the user chose in the chat (first-time setup or a later change). Pass only the values the user answered or changed. The database password is built in - never ask for it. Test mode needs confirm_test = TEST and only if the user explicitly chose it.'
      inputSchema = [ordered]@{ type = 'object'; properties = $sp }; annotations = [ordered]@{ readOnlyHint = $false; destructiveHint = $false; idempotentHint = $true; openWorldHint = $false } }
  )
}
function Tools { @(Tools-Core) + @(Setup-Tools) }
function Run-Setup($a) {
  Remove-Item Env:MASTMD_CONFIG -ErrorAction SilentlyContinue
  $wiz = Join-Path $root 'tools\Setup-MasTmd.ps1'
  if (-not (Test-Path -LiteralPath $wiz)) { return @{ out = "Setup wizard not found: $wiz"; code = 1 } }
  $argv = New-Object System.Collections.ArrayList; [void]$argv.Add('-Auto')
  $map = [ordered]@{ mode = '-Mode'; confirm_test = '-ConfirmTest'; legal_root = '-LegalRoot'; user_name = '-UserName'; vat_percent = '-VatPercent'; event_location = '-EventLocation'; keep = '-Keep'; backup_folder = '-BackupFolder' }
  foreach ($k in $map.Keys) {
    $v = $a.$k; if ($null -eq $v) { continue }
    if ($k -eq 'event_location' -or $k -eq 'backup_folder') { [void]$argv.Add($map[$k]); [void]$argv.Add("$v"); continue }
    if ("$v" -eq '') { continue }
    if ($k -in 'vat_percent', 'keep') { $n = 0; if (-not [int]::TryParse("$v", [ref]$n)) { throw "Argument '$k' must be an integer." }; [void]$argv.Add($map[$k]); [void]$argv.Add("$n"); continue }
    [void]$argv.Add($map[$k]); [void]$argv.Add("$v")
  }
  $out = (& $psExe -NoProfile -ExecutionPolicy Bypass -File $wiz @($argv) 2>&1 | Out-String); $code = $LASTEXITCODE
  @{ out = $out.TrimEnd(); code = $code }
}function Build-Argv($a) {
  $act = "$($a.action)"
  $argv = New-Object System.Collections.ArrayList; [void]$argv.Add('-Action'); [void]$argv.Add($act)
  $summary = New-Object System.Collections.ArrayList; [void]$summary.Add("action=$act")
  foreach ($k in $argMap.Keys) {
    $v = $a.$k; if ($null -eq $v -or "$v" -eq '') { continue }
    $p = $argMap[$k][0]; $t = $argMap[$k][1]
    if ($t -eq 'int') { $n = 0; if (-not [int]::TryParse("$v", [ref]$n)) { throw "Argument '$k' must be an integer." }; [void]$argv.Add("-$p"); [void]$argv.Add("$n"); [void]$summary.Add("$k=$n") }
    elseif ($t -eq 'switch') { if ($v -eq $true -or "$v" -eq 'true') { [void]$argv.Add("-$p"); [void]$summary.Add($k) } }
    else {
      $s = "$v"
      if ($k -eq 'file') {
        if (-not (Test-Path -LiteralPath $s -PathType Leaf)) { throw "File not found: $s" }
        if ($s -match '(?i)MasTmd[\\/]+config\.json') { throw 'This file cannot be imported.' }
      }
      [void]$argv.Add("-$p"); [void]$argv.Add($s); [void]$summary.Add("$k=$s")
    }
  }
  @{ argv = @($argv); summary = ($summary -join '; ') }
}
function Run-Tool([string[]]$argv) {
  Remove-Item Env:MASTMD_CONFIG -ErrorAction SilentlyContinue   # the settings file can never be redirected from here
  if (-not (Test-Path -LiteralPath $tool)) { return @{ out = "Tool not found: $tool"; code = 1 } }
  $out = (& $psExe -NoProfile -ExecutionPolicy Bypass -File $tool @argv 2>&1 | Out-String)
  $code = $LASTEXITCODE
  if ($out.Length -gt 60000) { $out = $out.Substring(0, 60000) + "`n[output truncated]" }
  if ($out -match '\[SETUP REQUIRED\]') { $out += "`n`nStart the interactive first-time setup now: ask the user the setup questions in the chat (AskUserQuestion), then call legal_setup_apply with the answers (the user may instead run the wizard in a terminal: powershell -NoProfile -File `"$(Join-Path $root 'tools\Setup-MasTmd.ps1')`")." }
  @{ out = $out.TrimEnd(); code = $code }
}
function Handle-Call($name, $a) {
  if ($name -eq 'legal_read') {
    if ($readActions -notcontains "$($a.action)") { return TextResult "Action not allowed. Allowed: $($readActions -join ', ')" $true }
    $b = Build-Argv $a; $r = Run-Tool $b.argv
    return TextResult $r.out ($r.code -ne 0)
  }
  if ($name -eq 'legal_preview') {
    if ($writeActions -notcontains "$($a.action)") { return TextResult "Action not allowed. Allowed: $($writeActions -join ', ')" $true }
    $b = Build-Argv $a
    $dry = @($b.argv) + @('-AllowRealData')     # dry-run: nothing is written
    $r = Run-Tool $dry
    if ($r.code -ne 0 -or $r.out -match '\[ERROR\]|\[SETUP REQUIRED\]') { return TextResult $r.out $true }
    $token = [guid]::NewGuid().ToString('N').Substring(0, 12)
    foreach ($k in @($pending.Keys)) { if ($pending[$k].expires -lt (Get-Date)) { $pending.Remove($k) } }
    $pending[$token] = @{ argv = @($b.argv); summary = $b.summary; expires = (Get-Date).AddMinutes(15) }
    return TextResult ($r.out + "`n`nCONFIRMATION TOKEN: $token`n(valid 15 minutes, single use). Nothing was written. Show this preview to the user; call legal_apply with this token only after the user explicitly approves.")
  }
  if ($name -eq 'legal_apply') {
    $t = "$($a.token)"
    if (-not $pending.ContainsKey($t)) { return TextResult 'Unknown or already used token. Run legal_preview again.' $true }
    $p = $pending[$t]; $pending.Remove($t)
    if ($p.expires -lt (Get-Date)) { return TextResult 'The token expired. Run legal_preview again.' $true }
    $r = Run-Tool (@($p.argv) + @('-Apply', '-AllowRealData'))
    return TextResult ("Applied: $($p.summary)`n`n" + $r.out) ($r.code -ne 0)
  }
  if ($name -eq 'legal_setup_status') {
    $r = Run-Tool @('-Action', 'ShowPaths')
    if ($r.out -match '\[SETUP REQUIRED\]') { return TextResult ("SETUP NOT COMPLETE.`n" + $r.out + "`n`nStart the interactive setup now: ask the questions in the chat, then call legal_setup_apply.") $false }
    return TextResult ("Setup is complete.`n" + $r.out) ($r.code -ne 0)
  }
  if ($name -eq 'legal_setup_apply') {
    $r = Run-Setup $a
    return TextResult $r.out ($r.code -ne 0)
  }  TextResult "Unknown tool: $name" $true
}
# ---- main loop
while ($true) {
  $line = $script:reader.ReadLine()
  if ($null -eq $line) { break }
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  try { $msg = $line | ConvertFrom-Json } catch { continue }
  $id = $msg.id; $method = "$($msg.method)"
  try {
    switch ($method) {
      'initialize' {
        $pv = if ($msg.params.protocolVersion) { "$($msg.params.protocolVersion)" } else { '2025-06-18' }
        Reply $id ([ordered]@{ protocolVersion = $pv; capabilities = [ordered]@{ tools = [ordered]@{ listChanged = $false } }; serverInfo = [ordered]@{ name = 'legal-db'; title = 'Legal DB'; version = $serverVersion }
            instructions = 'Tools for the Legal (ליגל) case-management software. Use legal_read to look things up. Every change is two steps: legal_preview (nothing written) then, only after the user explicitly approves the preview, legal_apply with its token. FIRST USE: call legal_setup_status; if setup is not complete, start the setup immediately in the chat - ask the questions with AskUserQuestion (work mode: production by default; Legal folder: default C:\Timin; user name; VAT %: default 18; default event location; backups to keep: default 15) and then call legal_setup_apply with the answers. The database password is built in: never ask for it. Test mode only if the user explicitly chose it (confirm_test = TEST).' })
      }
      'notifications/initialized' { }
      'notifications/cancelled' { }
      'ping' { Reply $id ([ordered]@{}) }
      'tools/list' { Reply $id ([ordered]@{ tools = (Tools) }) }
      'tools/call' {
        $a = $msg.params.arguments; if ($null -eq $a) { $a = [pscustomobject]@{} }
        try { Reply $id (Handle-Call "$($msg.params.name)" $a) } catch { Reply $id (TextResult "Error: $($_.Exception.Message)" $true) }
      }
      default { if ($null -ne $id) { Fail $id -32601 "Method not found: $method" } }
    }
  } catch { if ($null -ne $id) { Fail $id -32603 "Internal error: $($_.Exception.Message)" } }
}
