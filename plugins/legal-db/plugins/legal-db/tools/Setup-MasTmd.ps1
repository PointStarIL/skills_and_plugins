<#
  First-run setup and later settings editor for the Legal (MasTmd) tools.
  Two ways to run it:
   1) By a person in a terminal (asks the questions one by one):
      powershell -NoProfile -File "<...>\db-tools\Setup-MasTmd.ps1"
   2) By the assistant, AFTER the user answered the questions in the chat (no prompts), with the user's answers as parameters:
      powershell -NoProfile -File "<...>\db-tools\Setup-MasTmd.ps1" -Auto [-Mode production|test -ConfirmTest TEST] [-LegalRoot <path>] [-UserName <name>] [-VatPercent <n>] [-EventLocation <n>] [-Keep <n>] [-BackupFolder <path>]
      Test mode is accepted only together with -ConfirmTest TEST (an explicit confirmation by the user).
  First run (no settings file yet): asks the questions one by one. Later runs: shows the current settings and lets you change any of them.
  Writes the settings to %APPDATA%\MasTmd\config.json (per Windows user, outside the project folder). The database password is the same for every Legal installation and is built into the tools (not asked).
#>
param(
  [string]$ConfigPath = $(if ($env:MASTMD_CONFIG) { $env:MASTMD_CONFIG } else { Join-Path $env:APPDATA 'MasTmd\config.json' }),
  [string[]]$ScriptedAnswers,   # for automated tests only; refused for the real settings file
  [switch]$Auto,                # no prompts: apply the parameters below (the assistant uses this after the user answered in the chat)
  [ValidateSet('production', 'test')][string]$Mode,
  [string]$ConfirmTest,         # must be exactly TEST to enable test mode
  [string]$LegalRoot,
  [string]$UserName,
  [int]$VatPercent = -1,
  [string]$EventLocation,
  [int]$Keep = 0,
  [string]$BackupFolder
)
$script:FixedDbPassword = 'laroche'   # the Legal database password is the same for every installation
$ErrorActionPreference = 'Stop'
$realConfig = Join-Path $env:APPDATA 'MasTmd\config.json'
$isReal = ([IO.Path]::GetFullPath($ConfigPath) -eq [IO.Path]::GetFullPath($realConfig))
if ($ScriptedAnswers -and $isReal) { Write-Host 'Scripted answers are not allowed for the real settings file. Run this setup yourself in a terminal.' -ForegroundColor Red; exit 1 }
if (-not $ScriptedAnswers -and -not $Auto -and ([Console]::IsInputRedirected -or -not [Environment]::UserInteractive)) { Write-Host 'No keyboard input is available here: run this setup in an interactive terminal, or use -Auto with the answers as parameters.' -ForegroundColor Red; exit 1 }
$ps32 = Join-Path $env:WINDIR 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
$script:queue = New-Object System.Collections.Queue; if ($ScriptedAnswers) { foreach ($a in $ScriptedAnswers) { $script:queue.Enqueue($a) } }
function Ask($prompt, $default = '') {
  $label = if ($default -ne '') { "$prompt [$default]" } else { $prompt }
  if ($script:queue.Count -gt 0 -or $ScriptedAnswers) { $v = if ($script:queue.Count) { $script:queue.Dequeue() } else { '' }; Write-Host "$label : $v" } else { $v = Read-Host $label }
  if ([string]::IsNullOrWhiteSpace($v)) { $default } else { $v.Trim() }
}
function AskSecret($prompt) {
  if ($ScriptedAnswers) { $v = if ($script:queue.Count) { $script:queue.Dequeue() } else { '' }; Write-Host "$prompt : ********"; return (ConvertTo-SecureString $v -AsPlainText -Force) }
  Read-Host $prompt -AsSecureString
}
function Plain($ss) { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($ss)) }
function Test-Db($root, $dbFile, $secure) {
  $db = Join-Path $root $dbFile
  $pw = Plain $secure
  $cmd = "`$c=New-Object System.Data.OleDb.OleDbConnection('Provider=Microsoft.Jet.OLEDB.4.0;Data Source=' + `$env:MASTMD_DB + ';Mode=Read;Jet OLEDB:Database Password=' + `$env:MASTMD_PW); try { `$c.Open(); 'OK' } catch { 'FAIL: ' + `$_.Exception.Message } finally { `$c.Close() }"
  $env:MASTMD_DB = $db; $env:MASTMD_PW = $pw
  try { (& $ps32 -NoProfile -Command $cmd) -join '' } finally { Remove-Item Env:MASTMD_DB, Env:MASTMD_PW -ErrorAction SilentlyContinue }
}
# ---- load current settings (if any)
$cur = $null; $firstRun = $true
if (Test-Path -LiteralPath $ConfigPath) { try { $cur = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json; $firstRun = ($cur.SetupComplete -ne $true) } catch { $cur = $null } }
function Cv($name, $def) { if ($cur -and $null -ne $cur.PSObject.Properties[$name] -and "$($cur.$name)".Trim() -ne '') { "$($cur.$name)" } else { $def } }
$S = [ordered]@{
  TestMode = ((Cv 'TestMode' 'false') -in 'true','True'); LegalRoot = (Cv 'LegalRoot' 'C:\Timin'); DbFileName = (Cv 'DbFileName' 'MasTmd.mdb')
  DocsFolder = (Cv 'DocsFolder' 'tmpDocs'); DeletedFolder = (Cv 'DeletedFolder' 'DeletedFiles'); User = (Cv 'User' ''); Vat = [int](Cv 'Vat' '18')
  EventLocationId = (Cv 'EventLocationId' ''); BackupsToKeep = [int](Cv 'BackupsToKeep' '15'); BackupDir = (Cv 'BackupDir' '')
  PasswordProtected = (Cv 'PasswordProtected' ''); Password = (Cv 'Password' '')
}
$defaultRoot = 'C:\Timin'
function Step-Mode {
  Write-Host ''; Write-Host '--- Work mode ---'
  Write-Host '  1) Production (real data only) - recommended for every customer'
  Write-Host '  2) Test mode (allows dummy data and test shortcuts) - for a test computer only'
  $cur1 = if ($S.TestMode) { '2' } else { '1' }
  $a = Ask 'Choose 1 or 2' $cur1
  if ($a -eq '2') {
    Write-Host 'WARNING: test mode lets the tool create dummy customers/cases and work without the real-data protections.' -ForegroundColor Yellow
    $c = Ask 'Type TEST to confirm test mode, or press Enter to stay in production mode' ''
    $S.TestMode = ($c -ceq 'TEST')
  } else { $S.TestMode = $false }
  Write-Host ("Mode: " + $(if ($S.TestMode) { 'TEST' } else { 'PRODUCTION' }))
}
function Step-Path {
  Write-Host ''; Write-Host '--- Legal folder (the folder that contains the database and the documents) ---'
  Write-Host "  Default: $defaultRoot"
  while ($true) {
    $p = (Ask 'Path (Enter = keep/default)' $S.LegalRoot).TrimEnd('\')
    $dbOk = Test-Path -LiteralPath (Join-Path $p $S.DbFileName); $docsOk = Test-Path -LiteralPath (Join-Path $p $S.DocsFolder)
    if ($dbOk -and $docsOk) { $S.LegalRoot = $p; Write-Host "OK: found $($S.DbFileName) and $($S.DocsFolder) in $p"; return }
    if (-not $dbOk) { Write-Host "Not found: database '$($S.DbFileName)' in $p" -ForegroundColor Yellow }
    if (-not $docsOk) { Write-Host "Not found: documents folder '$($S.DocsFolder)' in $p" -ForegroundColor Yellow }
    if ($ScriptedAnswers -and $script:queue.Count -eq 0) { throw 'Scripted path invalid' }
    $again = Ask 'Try another path? (y = yes, n = save this path anyway)' 'y'
    if ($again -eq 'n') { $S.LegalRoot = $p; return }
  }
}
function Step-Password {
  Write-Host ''; Write-Host '--- Database password (built-in, the same for every Legal installation - nothing to enter) ---'
  $res = Test-Db $S.LegalRoot $S.DbFileName (ConvertTo-SecureString $script:FixedDbPassword -AsPlainText -Force)
  $S.PasswordProtected = ''; $S.Password = ''
  if ($res -eq 'OK') { Write-Host 'OK: the database opens with the built-in password.' } else { Write-Host "Could not open the database with the built-in password: $res" -ForegroundColor Yellow }
}
function Step-User {
  Write-Host ''; Write-Host '--- User name (written as the creator/sender of items; use the name of the Legal user) ---'
  while ($true) { $u = Ask 'User name' $S.User; if ($u) { $S.User = $u; return }; Write-Host 'A user name is required.' -ForegroundColor Yellow }
}
function Step-Vat {
  Write-Host ''; Write-Host '--- VAT rate in percent (used for billed events) ---'
  while ($true) { $v = Ask 'VAT %' "$($S.Vat)"; $n = 0; if ([int]::TryParse($v, [ref]$n) -and $n -ge 0 -and $n -le 30) { $S.Vat = $n; return }; Write-Host 'Enter a whole number between 0 and 30.' -ForegroundColor Yellow }
}
function Step-Location {
  Write-Host ''; Write-Host '--- Default location number for calendar events (meeting / hearing / reminder) ---'
  Write-Host '  A number from the Legal locations list. Leave empty to write no location.'
  while ($true) { $l = Ask 'Location number (Enter = none/keep)' $S.EventLocationId; $n = 0; if ($l -eq '' -or [int]::TryParse($l, [ref]$n)) { $S.EventLocationId = $l; return }; Write-Host 'Enter a number or leave empty.' -ForegroundColor Yellow }
}
function Step-Backups {
  Write-Host ''; Write-Host '--- Automatic backups (a full copy of the database before every write) ---'
  Write-Host '  Backups contain all client data: keep them on a protected disk.'
  while ($true) { $k = Ask 'How many backups to keep' "$($S.BackupsToKeep)"; $n = 0; if ([int]::TryParse($k, [ref]$n) -and $n -ge 1 -and $n -le 200) { $S.BackupsToKeep = $n; break }; Write-Host 'Enter a number between 1 and 200.' -ForegroundColor Yellow }
  $d = Ask 'Backup folder (Enter = the tool folder\backups)' $S.BackupDir
  if ($d) { if (-not (Test-Path -LiteralPath $d)) { try { New-Item -ItemType Directory -Force $d | Out-Null } catch { Write-Host "Could not create $d - keeping the default." -ForegroundColor Yellow; $d = '' } } }
  $S.BackupDir = $d
}
function Save {
  $o = [ordered]@{
    SetupComplete = $true; TestMode = $S.TestMode; LegalRoot = $S.LegalRoot; DbFileName = $S.DbFileName; DocsFolder = $S.DocsFolder; DeletedFolder = $S.DeletedFolder
    User = $S.User; Vat = $S.Vat; EventLocationId = $S.EventLocationId; BackupsToKeep = $S.BackupsToKeep; BackupDir = $S.BackupDir
    PasswordProtected = $S.PasswordProtected
  }
  if ($S.Password) { $o['Password'] = $S.Password }
  $o['TestCaseIds'] = $(if ($cur -and $cur.TestCaseIds) { @($cur.TestCaseIds) } else { @() })
  $o['Notes'] = 'Created by Setup-MasTmd.ps1. TestMode false = production (real data only); true = test computer. Change settings by running Setup-MasTmd.ps1 again.'
  New-Item -ItemType Directory -Force (Split-Path $ConfigPath -Parent) | Out-Null
  [IO.File]::WriteAllText($ConfigPath, ($o | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding($true)))
  Write-Host ''; Write-Host "Settings saved to $ConfigPath" -ForegroundColor Green
}
function Show-Summary {
  Write-Host ''; Write-Host '=== Current settings ==='
  Write-Host ("  1) Mode              : " + $(if ($S.TestMode) { 'TEST' } else { 'PRODUCTION' }))
  Write-Host ("  2) Legal folder      : $($S.LegalRoot)")
  Write-Host ("  3) Database password : " + 'built-in')
  Write-Host ("  4) User name         : $($S.User)")
  Write-Host ("  5) VAT %             : $($S.Vat)")
  Write-Host ("  6) Event location    : " + $(if ($S.EventLocationId -ne '') { $S.EventLocationId } else { '(none)' }))
  Write-Host ("  7) Backups           : keep $($S.BackupsToKeep) in " + $(if ($S.BackupDir) { $S.BackupDir } else { '<tool folder>\backups' }))
}
if ($Auto) {
  function Fail($m) { Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }
  if ($Mode -eq 'test') { if ($ConfirmTest -ceq 'TEST') { $S.TestMode = $true } else { Fail 'Test mode needs -ConfirmTest TEST (an explicit confirmation by the user).' } }
  elseif ($Mode -eq 'production') { $S.TestMode = $false }
  if ($LegalRoot) { $S.LegalRoot = $LegalRoot.TrimEnd('\') }
  if ($UserName) { $S.User = $UserName.Trim() }
  if ($VatPercent -ge 0) { if ($VatPercent -gt 30) { Fail 'VAT must be between 0 and 30.' }; $S.Vat = $VatPercent }
  if ($PSBoundParameters.ContainsKey('EventLocation')) { $n = 0; if ($EventLocation -ne '' -and -not [int]::TryParse($EventLocation, [ref]$n)) { Fail 'Event location must be a number or empty.' }; $S.EventLocationId = $EventLocation }
  if ($Keep -gt 0) { if ($Keep -gt 200) { Fail 'Backups to keep must be between 1 and 200.' }; $S.BackupsToKeep = $Keep }
  if ($PSBoundParameters.ContainsKey('BackupFolder')) { if ($BackupFolder -and -not (Test-Path -LiteralPath $BackupFolder)) { try { New-Item -ItemType Directory -Force $BackupFolder | Out-Null } catch { Fail "Could not create the backup folder $BackupFolder" } }; $S.BackupDir = $BackupFolder }
  if (-not $S.User) { Fail 'A user name is required (-UserName).' }
  if (-not (Test-Path -LiteralPath (Join-Path $S.LegalRoot $S.DbFileName))) { Fail "Database '$($S.DbFileName)' not found in $($S.LegalRoot)" }
  if (-not (Test-Path -LiteralPath (Join-Path $S.LegalRoot $S.DocsFolder))) { Fail "Documents folder '$($S.DocsFolder)' not found in $($S.LegalRoot)" }
  $res = Test-Db $S.LegalRoot $S.DbFileName (ConvertTo-SecureString $script:FixedDbPassword -AsPlainText -Force)
  if ($res -ne 'OK') { Fail "Could not open the database: $res" }
  $S.PasswordProtected = ''; $S.Password = ''
  Save; Show-Summary; exit 0
}
if ($firstRun) {
  Write-Host '=== First-time setup of the Legal tools ===' -ForegroundColor Cyan
  Step-Mode; Step-Path; Step-Password; Step-User; Step-Vat; Step-Location; Step-Backups
  Show-Summary
  $ok = Ask 'Save these settings? (y/n)' 'y'
  if ($ok -eq 'y') { Save } else { Write-Host 'Nothing saved.' }
} else {
  Write-Host '=== Legal tools settings ===' -ForegroundColor Cyan
  while ($true) {
    Show-Summary
    Write-Host '  s) Save and exit      q) Exit without saving'
    $c = Ask 'Which setting to change?' 's'
    switch ($c) {
      '1' { Step-Mode } '2' { Step-Path } '3' { Step-Password } '4' { Step-User } '5' { Step-Vat } '6' { Step-Location } '7' { Step-Backups }
      's' { Save; break } 'q' { Write-Host 'Nothing saved.'; break }
      default { Write-Host 'Choose 1-7, s or q.' -ForegroundColor Yellow; continue }
    }
    if ($c -in 's','q') { break }
  }
}
