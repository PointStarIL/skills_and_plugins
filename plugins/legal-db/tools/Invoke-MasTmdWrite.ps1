<#
  Write tool for MasTmd.mdb (documents + calendar events). Dry-run by default; add -Apply to write.
  Runs only in 32-bit Windows PowerShell (relaunches itself if started in 64-bit / PowerShell 7).

  Actions:
    ListKinds                                   supported event kinds and what they create
    Find   -Name <text>                         find cases by client name
    Info   -Case <CaseID>                       case summary, folder, acts
    AddEvent -Case <id> -Kind <id|name> -Text <t> [-Date yyyy-MM-dd] [-Start HH:mm] [-End HH:mm] [-Color n] [-Amount n] [-NoAlarm]
    AddDocument -Case <id> -File <path> [-Kind 1|2] [-Text <title>] [-Date yyyy-MM-dd] [-Move]
    Rename -Act <id> -NewText <title>           renames description + file name (ActTeur + DocPath + file)
    Move   -Act <id> -ToCase <id>               moves a document to another case / sub-folder case
    Delete -Act <id>                            deletes like the app (row + tblBankDeletes + file -> DeletedFiles [+ Outlook bin])
    NewCase -First <first name> -Last <family name> [-SueKind 24|22|98|20|102] [-Phone n] [-CustomerId id] (-Test | -AllowRealData)
                                                creates customer (unless -CustomerId) + case + stage + details (+4 value rows for torts)
    SetStatus -Case <id> -Text <status>         changes ONLY the status text (CaseStatus). Refuses "סגור", closed cases and statuses that do not exist yet
    CloseCase -Case <id> [-Date yyyy-MM-dd]     closing = status "סגור" AND CaseCloseDate (default today) together
    ReopenCase -Case <id> [-Text <new status>]  opens a case: clears CaseCloseDate; status becomes empty (or -Text, which must exist)
    ListStages -Case <id>                       stages of the case's process model, current stage marked
    SetStage -Case <id> -Text <stage name|NodeID>   moves the case to a stage like Legal does: new tblCaseNodeFlow row + tblCase.CurrentFlowID + NodeCaption
    RemoveStatus -Text <status>                 removes a catalog status that no case uses (never 9999); needs -AllowRealData
    DeleteFlow -Case <id> -Flow <FlowID>        deletes a stage-history row of the case (never the current stage, never one referenced by acts)
    ListStatuses                                statuses that exist (catalog tblBankStatusText + values already used in cases)
    FindStatus -Text <status>                   exact match or similar existing statuses (use BEFORE creating a new one)
    AddStatus -Text <status> [-NotSimilar]      adds a status to the catalog; refuses if a similar one exists unless the user rejected the similar ones (-NotSimilar). Needs -AllowRealData
    NewSubfolder -Case <parent case or sub-folder id> -Name <folder name>   creates a sub-folder (case type 77) + empty directory
    RenameFolder -Case <sub-folder case id> -NewText <name>                 renames sub-folder (CaseSubject, directory, DocPath of everything inside)
  Safety: dry-run unless -Apply; DB backup before every -Apply; only cases listed in mastmd.config.json
  (TestCaseIds) unless -AllowRealData; every run is logged to write-log.jsonl.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)][ValidateSet('ListKinds','Find','Info','AddEvent','AddDocument','Rename','Move','Delete','NewCase','NewSubfolder','RenameFolder','SetStatus','CloseCase','ReopenCase','ListStatuses','FindStatus','AddStatus','RemoveStatus','ListStages','SetStage','DeleteFlow','ShowPaths','SetRoot')][string]$Action,
  [int]$Case, [int]$Act, [int]$ToCase, [string]$Name,
  [string]$Kind, [string]$Text, [string]$NewText, [string]$Date, [string]$Start, [string]$End,
  [string]$File, [string]$Amount, [int]$Color,
  [string]$First, [string]$Last, [string]$Phone, [int]$CustomerId, [int]$SueKind,
  [string]$DbOverride, [string]$LegalRoot, [string]$Path, [int]$Flow, [switch]$NotSimilar,
  [switch]$Test, [switch]$Move, [switch]$NoAlarm, [switch]$Apply, [switch]$AllowRealData
)
if ([Environment]::Is64BitProcess) {
  $ps32 = Join-Path $env:WINDIR 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
  $a = @('-NoProfile','-File',$PSCommandPath)
  foreach ($k in $PSBoundParameters.Keys) { $v = $PSBoundParameters[$k]; if ($v -is [switch]) { if ($v.IsPresent) { $a += "-$k" } } else { $a += "-$k"; $a += "$v" } }
  & $ps32 @a
  exit $LASTEXITCODE
}
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$script:Here = $PSScriptRoot
$cfgFile = $(if ($env:MASTMD_CONFIG) { $env:MASTMD_CONFIG } else { Join-Path $env:APPDATA 'MasTmd\config.json' })
$script:CfgFile = $cfgFile
$script:Cfg = $null
if (Test-Path -LiteralPath $cfgFile) { try { $script:Cfg = Get-Content -LiteralPath $cfgFile -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $script:CfgFile = $cfgFile
$script:Cfg = $null } }
if ($null -eq $script:Cfg -or $script:Cfg.SetupComplete -ne $true) {
  Write-Output '[SETUP REQUIRED] First-time setup has not been completed on this computer. Run the Legal setup (/legal-db:legal-setup): ask the user the setup questions in the chat, then run Setup-MasTmd.ps1 -Auto with the user''s answers (the user may also run Setup-MasTmd.ps1 in a terminal). Settings are saved in %APPDATA%\MasTmd\config.json. Never edit that file directly.'
  exit 2
}
function Get-DbPassword {
  if ($script:Cfg.PasswordProtected) { $ss = ConvertTo-SecureString "$($script:Cfg.PasswordProtected)"; return [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($ss)) }
  if ("$($script:Cfg.Password)" -ne '') { return "$($script:Cfg.Password)" }
  'laroche'   # built-in: the Legal database password is the same for every installation
}
function Cfg($n,$d) { $v = $script:Cfg.$n; if ($null -ne $v -and "$v".Trim() -ne '') { "$v" } else { $d } }
# Legal partition root: -LegalRoot parameter > LegalRoot in mastmd.config.json > default C:\Timin
$script:RootSource = 'default C:\Timin'
$script:Root = 'C:\Timin'
if ($LegalRoot) { $script:Root = $LegalRoot; $script:RootSource = '-LegalRoot parameter' }
elseif (Cfg 'LegalRoot' '') { $script:Root = Cfg 'LegalRoot' ''; $script:RootSource = 'LegalRoot in the settings file' }
$script:DbPath = $(if ($DbOverride) { $DbOverride } else { Join-Path $script:Root (Cfg 'DbFileName' 'MasTmd.mdb') })
$script:DocBase = Join-Path $script:Root (Cfg 'DocsFolder' 'tmpDocs')
$script:DelDir  = Join-Path $script:Root (Cfg 'DeletedFolder' 'DeletedFiles')
$script:User = $script:Cfg.User
$script:Vat  = [int]$script:Cfg.Vat
# TestMode (mastmd.config.json): true = test shortcuts allowed; false/missing = PRODUCTION, real data only.
# Only the user edits this flag; the tool has no action that changes it.
$script:TestMode = ((Cfg 'TestMode' 'false') -in 'true','True','TRUE','1')
function Get-TestIds { if ($script:TestMode) { @($script:Cfg.TestCaseIds) } else { @() } }
if (-not $script:TestMode -and ($Test -or $DbOverride)) {
  Write-Output '[ERROR] TEST MODE IS OFF (TestMode=false in mastmd.config.json): -Test and -DbOverride are not allowed. This installation works with real data only.'
  exit 1
}
$script:Apply = [bool]$Apply
$script:Undo = New-Object System.Collections.ArrayList
$script:Results = New-Object System.Collections.ArrayList

function Say($m)  { Write-Host $m }
function Plan($m) { if ($script:Apply) { Write-Host "[DO]   $m" } else { Write-Host "[PLAN] $m" } }
function Nz($v,$d=$null) { if ($v -is [DBNull] -or $null -eq $v) { $d } else { $v } }
function Tm($h,$m) { [datetime]::new(1899,12,30,$h,$m,0) }
function Sanitize($s) { $t = ("$s" -replace '"',[string][char]0x05F4); $t = ($t -replace '[\\/:*?<>|\r\n]+',' ').Trim(); $t = $t -replace '\s{2,}',' '; if ($t.Length -gt 99) { $t = $t.Substring(0,99).Trim() }; $t }
function ParseDate($s) {
  if (-not $s) { return (Get-Date).Date }
  foreach ($f in 'yyyy-MM-dd','dd/MM/yyyy','d/M/yyyy') { $r = [datetime]::MinValue; if ([datetime]::TryParseExact($s,$f,$null,'None',[ref]$r)) { return $r } }
  throw "Bad date '$s' (use yyyy-MM-dd)"
}
function ParseTime($s,$def) {
  if (-not $s) { return $def }
  $r = [datetime]::MinValue; if ([datetime]::TryParseExact($s,'H:mm',$null,'None',[ref]$r)) { return (Tm $r.Hour $r.Minute) }
  throw "Bad time '$s' (use HH:mm)"
}

# ---------------- DB ----------------
$script:Conn = $null; $script:Tx = $null
function Open-Db {
  $script:Conn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.Jet.OLEDB.4.0;Data Source=$($script:DbPath);Mode=Share Deny None;Jet OLEDB:Database Password=$(Get-DbPassword)")
  $script:Conn.Open()
}
function Q($sql) {
  $cmd = $script:Conn.CreateCommand(); $cmd.CommandText = $sql; if ($script:Tx) { $cmd.Transaction = $script:Tx }
  $dt = New-Object System.Data.DataTable; $da = New-Object System.Data.OleDb.OleDbDataAdapter($cmd); [void]$da.Fill($dt); ,$dt
}
function Add-Param($cmd,$name,$v) {
  $p = $cmd.Parameters.Add((New-Object System.Data.OleDb.OleDbParameter($name,$(if ($null -eq $v) { [DBNull]::Value } else { $v }))))
  if ($v -is [datetime]) { $p.OleDbType = [System.Data.OleDb.OleDbType]::Date }
}
function Do-Insert($table,$vals,[switch]$Identity) {
  $c = [ordered]@{}; foreach ($k in $vals.Keys) { if ($null -ne $vals[$k]) { $c[$k] = $vals[$k] } }
  Plan ("INSERT $table : " + (($c.Keys | ForEach-Object { "$_=$($c[$_])" }) -join '; '))
  if (-not $script:Apply) { return -1 }
  $cmd = $script:Conn.CreateCommand(); $cmd.Transaction = $script:Tx
  $cols = @($c.Keys)
  $cmd.CommandText = "INSERT INTO [$table] (" + (($cols | ForEach-Object { "[$_]" }) -join ',') + ") VALUES (" + (($cols | ForEach-Object { '?' }) -join ',') + ")"
  foreach ($k in $cols) { Add-Param $cmd "p_$k" $c[$k] }
  [void]$cmd.ExecuteNonQuery()
  $id = $null
  if ($Identity) { $c2 = $script:Conn.CreateCommand(); $c2.Transaction = $script:Tx; $c2.CommandText = 'SELECT @@IDENTITY'; $id = [int]$c2.ExecuteScalar() }
  [void]$script:Results.Add([pscustomobject]@{ op = 'insert'; table = $table; id = $id })
  $id
}
function Do-Update($table,$set,$keyCol,$keyVal) {
  Plan ("UPDATE $table SET " + (($set.Keys | ForEach-Object { "$_=$($set[$_])" }) -join '; ') + " WHERE $keyCol=$keyVal")
  if (-not $script:Apply) { return }
  $cmd = $script:Conn.CreateCommand(); $cmd.Transaction = $script:Tx; $cols = @($set.Keys)
  $cmd.CommandText = "UPDATE [$table] SET " + (($cols | ForEach-Object { "[$_]=?" }) -join ',') + " WHERE [$keyCol]=?"
  foreach ($k in $cols) { Add-Param $cmd "s_$k" $set[$k] }
  Add-Param $cmd 'k' $keyVal
  [void]$cmd.ExecuteNonQuery()
  [void]$script:Results.Add([pscustomobject]@{ op = 'update'; table = $table; key = $keyVal })
}
function Do-Delete($table,$keyCol,$keyVal) {
  Plan "DELETE FROM $table WHERE $keyCol=$keyVal"
  if (-not $script:Apply) { return }
  $cmd = $script:Conn.CreateCommand(); $cmd.Transaction = $script:Tx
  $cmd.CommandText = "DELETE FROM [$table] WHERE [$keyCol]=?"; Add-Param $cmd 'k' $keyVal
  [void]$cmd.ExecuteNonQuery()
  [void]$script:Results.Add([pscustomobject]@{ op = 'delete'; table = $table; key = $keyVal })
}
# ---------------- files ----------------
function Do-FileMove($from,$to,[switch]$Copy) {
  Plan ("FILE " + $(if ($Copy) { 'copy' } else { 'move' }) + " : $from -> $to")
  if (-not $script:Apply) { return }
  $dir = Split-Path $to -Parent; if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
  if (Test-Path -LiteralPath $to) { throw "Target file already exists: $to" }
  if ($Copy) { Copy-Item -LiteralPath $from -Destination $to; $script:UndoArgs += ,$to }
  else { Move-Item -LiteralPath $from -Destination $to; $script:UndoMoves += ,@($to,$from) }
}
$script:UndoArgs = @(); $script:UndoMoves = @()
function Undo-Files {
  foreach ($t in $script:UndoArgs) { Remove-Item -LiteralPath $t -ErrorAction SilentlyContinue }
  foreach ($m in $script:UndoMoves) { if (Test-Path -LiteralPath $m[0]) { Move-Item -LiteralPath $m[0] -Destination $m[1] -ErrorAction SilentlyContinue } }
}
function Backup-Db {
  $dir = $(if (Cfg 'BackupDir' '') { Cfg 'BackupDir' '' } else { Join-Path $script:Here 'backups' }); if (-not (Test-Path $dir)) { New-Item -ItemType Directory $dir | Out-Null }
  $b = Join-Path $dir ("auto-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + ".mdb")
  Copy-Item -LiteralPath $script:DbPath -Destination $b
  Get-ChildItem $dir -Filter 'auto-*.mdb' | Sort-Object LastWriteTime -Descending | Select-Object -Skip ([int]$script:Cfg.BackupsToKeep) | Remove-Item -ErrorAction SilentlyContinue
  Say "[BACKUP] $b"; $b
}
# ---------------- domain helpers ----------------
function Get-CaseRow($id) { $r = (Q "SELECT * FROM tblCase WHERE CaseID=$id").Rows; if ($r.Count -eq 0) { throw "Case $id not found" }; $r[0] }
function Get-Chain($id) {
  $subs = New-Object System.Collections.ArrayList; $row = Get-CaseRow $id; $n = 0
  while ((Nz $row.SueKind 0) -eq 77 -and (Nz $row.CaseParentID 0) -gt 0 -and $n -lt 12) { [void]$subs.Insert(0, "$($row.CaseSubject)"); $row = Get-CaseRow $row.CaseParentID; $n++ }
  [pscustomobject]@{ Root = $row; Subs = @($subs) }
}
function Get-DocDir($id) {
  $ch = Get-Chain $id
  $p = Join-Path $script:DocBase ("$($ch.Root.CaseCustName) $($ch.Root.CaseNum)")
  foreach ($s in $ch.Subs) { $p = Join-Path $p $s }
  $p
}
function Get-Client($id) {
  $ch = Get-Chain $id; $c = (Q "SELECT Pname,Lname FROM tblCustomer WHERE CustomerID=$($ch.Root.CustomerID)").Rows
  if ($c.Count -eq 0) { return '' }
  (("$(Nz $c[0].Pname '') $(Nz $c[0].Lname '')").Trim())
}
function Get-Pname($id) { $ch = Get-Chain $id; $c = (Q "SELECT Pname FROM tblCustomer WHERE CustomerID=$($ch.Root.CustomerID)").Rows; if ($c.Count) { "$(Nz $c[0].Pname '')" } else { '' } }
function Assert-Allowed($caseId) {
  if ($AllowRealData) { return }
  $rootId = [int]((Get-Chain $caseId).Root.CaseID)
  if (@(Get-TestIds) -notcontains [int]$caseId -and @(Get-TestIds) -notcontains $rootId) { throw "Case $caseId is not in TestCaseIds (mastmd.config.json). Use -AllowRealData only with explicit user approval for real data." }
}
function Get-ActRow($id) { $r = (Q "SELECT * FROM tblCaseAct WHERE ActID=$id").Rows; if ($r.Count -eq 0) { throw "Act $id not found" }; $r[0] }
function Get-KindName($k) { $r = (Q "SELECT ActKindTeur,ActKindSugID FROM tblBankActKind WHERE ActKindID=$k").Rows; if ($r.Count) { @{ Name = "$($r[0].ActKindTeur)"; Sug = [int](Nz $r[0].ActKindSugID 0) } } else { @{ Name = ''; Sug = 0 } } }
$script:Templates = @{
  14 = @{ Type = 'cal';  Prod = 3; Color = 7;  Alarm = 30; Loc = $true  }
  3  = @{ Type = 'cal';  Prod = 4; Color = 16; Alarm = 0;  Loc = $false }
  4  = @{ Type = 'cal';  Prod = 3; Color = 4;  Alarm = 30; Loc = $true  }
  11 = @{ Type = 'cal';  Prod = 3; Color = 1;  Alarm = 0;  Loc = $true  }
  7  = @{ Type = 'task'; Prod = 2 }
  15 = @{ Type = 'call'; Prod = 5 }
  39 = @{ Type = 'note' }
  66 = @{ Type = 'note' }
  52 = @{ Type = 'damage'; Prod = 8 }
}
function Resolve-Kind($s) {
  if (-not $s) { throw 'Kind required (see ListKinds)' }
  $id = 0; if ([int]::TryParse($s,[ref]$id)) { return $id }
  $r = (Q "SELECT ActKindID,ActKindTeur FROM tblBankActKind").Rows | Where-Object { "$($_.ActKindTeur)".Trim() -eq $s.Trim() }
  $r = @($r)
  if ($r.Count -ne 1) { throw "Kind '$s' not found / ambiguous (use the numeric id; see ListKinds)" }
  [int]$r[0].ActKindID
}
function Log-Run($extra) {
  $o = [ordered]@{ time = (Get-Date).ToString('s'); action = $Action; applied = $script:Apply; user = $script:User; results = @($script:Results) }
  foreach ($k in $extra.Keys) { $o[$k] = $extra[$k] }
  ($o | ConvertTo-Json -Depth 5 -Compress) | Add-Content -Path (Join-Path $script:Here 'write-log.jsonl') -Encoding UTF8
}
function Is-Calendar($kindId) { $t = $script:Templates[[int]$kindId]; if ($t) { return $t.Type -eq 'cal' }; $s = (Get-KindName $kindId).Sug; return ($s -eq 2 -or $s -eq 5) }

# ---------------- actions ----------------
function Do-ListKinds {
  Say 'Event kinds with a verified template (ActKindID | name | creates):'
  foreach ($k in ($script:Templates.Keys | Sort-Object)) { $t = $script:Templates[$k]; Say ("  {0,-3} | {1,-14} | {2}{3}" -f $k,(Get-KindName $k).Name,$t.Type,$(if ($t.Type -eq 'cal') { " (+tblBasket, color $($t.Color), product $($t.Prod))" } else { " (product $($t.Prod))" })) }
  Say 'Other kinds in group 2 (court hearings) use the "hearing" template (untested); group 5 (meetings) use the "meeting" template (untested).'
  Say 'Document kinds: 1 outgoing letter, 2 incoming letter (AddDocument).'
}
function Do-Find {
  if (-not $Name) { throw '-Name required' }
  $n = $Name.Replace("'","''")
  (Q "SELECT CaseID,CaseNum,CaseCustName,SueKind,CaseParentID FROM tblCase WHERE CaseCustName LIKE '%$n%' OR CaseSubject LIKE '%$n%'").Rows | ForEach-Object { Say ("case {0} | num {1} | {2} | sueKind {3} | parent {4}" -f $_.CaseID,$_.CaseNum,$_.CaseCustName,$_.SueKind,(Nz $_.CaseParentID '')) }
}
function Do-Info {
  if (-not $Case) { throw '-Case required' }
  $r = Get-CaseRow $Case; $ch = Get-Chain $Case
  Say ("Case {0} | num {1} | {2} | sueKind {3} | parent {4}" -f $r.CaseID,$r.CaseNum,$r.CaseCustName,$r.SueKind,(Nz $r.CaseParentID ''))
  Say "Folder: $(Get-DocDir $Case)  (exists: $(Test-Path -LiteralPath (Get-DocDir $Case)))"
  Say "Client (LReciver format): $(Get-Client $Case) | allowed for writes: $([bool]($AllowRealData -or (@(Get-TestIds) -contains $Case) -or (@(Get-TestIds) -contains [int]$ch.Root.CaseID)))"
  $kids = (Q "SELECT CaseID,CaseSubject FROM tblCase WHERE CaseParentID=$Case AND SueKind=77").Rows
  foreach ($k in $kids) { Say ("  sub-folder case {0}: {1}" -f $k.CaseID,$k.CaseSubject) }
  Say 'Acts (ActID | kind | due | text | file):'
  (Q "SELECT ActID,ActKindID,ActDueDate,ActTeur,DocPath FROM tblCaseAct WHERE CaseID=$Case ORDER BY ActID").Rows | ForEach-Object {
    $f = ''; if ($_.DocPath -isnot [DBNull] -and $_.DocPath) { $f = $(if (Test-Path -LiteralPath (Resolve-DocPath $_.DocPath)) { 'file OK' } else { 'FILE MISSING' }) }
    Say ("  {0} | {1} {2} | {3:yyyy-MM-dd} | {4} | {5}" -f $_.ActID,$_.ActKindID,(Get-KindName $_.ActKindID).Name,(Nz $_.ActDueDate (Get-Date '2000-01-01')),(("$($_.ActTeur)" -replace "\r?\n",' ⏎ ')),$f)
  }
}
function Do-AddEvent {
  if (-not $Case) { throw '-Case required' }; if (-not $Text) { throw '-Text required' }
  Assert-Allowed $Case; [void](Get-CaseRow $Case)
  $k = Resolve-Kind $Kind; $kn = Get-KindName $k; $t = $script:Templates[$k]
  if (-not $t) {
    if ($kn.Sug -eq 2) { $t = @{ Type = 'cal'; Prod = 3; Color = 4; Alarm = 30; Loc = $true }; Say "[NOTE] kind $k ($($kn.Name)) uses the generic hearing template (untested in the app)" }
    elseif ($kn.Sug -eq 5) { $t = @{ Type = 'cal'; Prod = 3; Color = 7; Alarm = 30; Loc = $true }; Say "[NOTE] kind $k ($($kn.Name)) uses the generic meeting template (untested in the app)" }
    else { throw "Kind $k ($($kn.Name)) has no template. Supported: see ListKinds" }
  }
  $now = Get-Date; $today = $now.Date; $d = ParseDate $Date; $client = Get-Client $Case; $u = $script:User
  $row = [ordered]@{ CaseID = $Case; ActKindID = $k; ActDate = $today; Lsender = $u; ActTeur = $Text; InputUser = $u }
  switch ($t.Type) {
    'cal' {
      $s = ParseTime $Start (Tm 9 0); $e = ParseTime $End $s.AddMinutes(30)
      $row['LReciver'] = $client; $row['ActDueDate'] = $d; $row['ActDueEndDate'] = $d; $row['ActStartTime'] = $s; $row['ActEndTime'] = $e
      $row['BillProductID'] = $t.Prod; $row['BillIvaValue'] = $script:Vat; $row['ActChange'] = $now; $row['SlipRegMail'] = $u
      $row['ActColor'] = $(if ($Color) { $Color } else { $t.Color })
      if ($t.Alarm -gt 0 -and -not $NoAlarm) { $row['ActAlarm'] = $true; $row['ActAlarmTime'] = $s.AddMinutes(-$t.Alarm); $row['ActAlarmDate'] = $d }
      if ($t.Loc -and (Cfg 'EventLocationId' '') -ne '') { $row['LocationID'] = [int](Cfg 'EventLocationId' '') }
    }
    'task' {
      $s = ParseTime $Start (Tm 8 0)
      $row['LReciver'] = $u; $row['ActDueDate'] = $d; $row['ActStartTime'] = $s; $row['BillProductID'] = $t.Prod; $row['BillIvaValue'] = $script:Vat
      if (-not $NoAlarm) { $row['ActAlarm'] = $true; $row['ActAlarmTime'] = $s.AddMinutes(-10); $row['ActAlarmDate'] = $d }
    }
    'call' {
      $s = ParseTime $Start (Tm $now.Hour $now.Minute)
      $row['LReciver'] = $client; $row['ActDueDate'] = $d; $row['ActStartTime'] = $s; $row['BillProductID'] = $t.Prod; $row['BillIvaValue'] = $script:Vat
      if (-not $NoAlarm) { $row['ActAlarm'] = $true; $row['ActAlarmTime'] = $s.AddMinutes(-10); $row['ActAlarmDate'] = $d }
    }
    'note' {
      $ch = Get-Chain $Case; $row['ActDueDate'] = $d; $row['ActDueEndDate'] = $d
      $row['FlowID'] = $(if ((Nz $ch.Root.CurrentFlowID 0) -ne 0) { [int]$ch.Root.CurrentFlowID } else { $null })
    }
    'damage' {
      $amt = $(if ($Amount) { [double]$Amount } else { 250.0 })
      $row['ActDueDate'] = $d; $row['ActStartTime'] = (Tm $now.Hour $now.Minute); $row['BillProductID'] = $t.Prod; $row['BillUnits'] = 1
      $row['BillCostPerUnit'] = $amt; $row['BillCost'] = $amt; $row['BillSum'] = [math]::Round($amt * (1 + $script:Vat / 100.0),2); $row['BillCoinID'] = 1; $row['BillIvaValue'] = $script:Vat
    }
  }
  $id = Do-Insert 'tblCaseAct' $row -Identity
  if ($t.Type -eq 'cal') { [void](Do-Insert 'tblBasket' ([ordered]@{ CaseID = $Case; BasketDate = $d; BasketOwner = $u; BasketTeur = $kn.Name })) }
  $script:Out = @{ actId = $id; kind = $k; case = $Case }
}
function Do-AddDocument {
  if (-not $Case) { throw '-Case required' }; if (-not $File) { throw '-File required' }
  Assert-Allowed $Case; [void](Get-CaseRow $Case)
  if (-not (Test-Path -LiteralPath $File)) { throw "File not found: $File" }
  $kd = $(if ($Kind) { [int]$Kind } else { 1 }); if ($kd -ne 1 -and $kd -ne 2) { throw 'Document Kind must be 1 (outgoing) or 2 (incoming)' }
  $ext = [IO.Path]::GetExtension($File); $title = Sanitize $(if ($Text) { $Text } else { [IO.Path]::GetFileNameWithoutExtension($File) })
  if (-not $title) { throw 'Empty title' }
  $now = Get-Date; $d = ParseDate $Date; $u = $script:User
  $row = [ordered]@{ CaseID = $Case; ActKindID = $kd; ActDate = $d; ActTeur = $title; ActDueDate = $d; ActStartTime = (Tm $now.Hour $now.Minute); InputUser = $u }
  if ($kd -eq 1) { $row['Lsender'] = $u }
  $id = Do-Insert 'tblCaseAct' $row -Identity
  $dest = Join-Path (Get-DocDir $Case) ("$(if ($id -gt 0) { $id } else { '<ActID>' })$title$ext")
  Do-FileMove $File $dest -Copy:(-not $Move)
  Do-Update 'tblCaseAct' ([ordered]@{ DocPath = $dest }) 'ActID' $id
  $script:Out = @{ actId = $id; docPath = $dest; case = $Case }
}
# DocPath values stored in the database may carry an old prefix (e.g. C:\Timin\tmpDocs\...). Map-DocPath rewrites the part after the
# docs folder name onto the current root; Resolve-DocPath returns the real file when it exists there.
function Map-DocPath($p) {
  if (-not $p) { return $p }
  $m = [regex]::Match($p, '(?i)[\\/]' + [regex]::Escape((Cfg 'DocsFolder' 'tmpDocs')) + '[\\/](.*)$')
  if ($m.Success) { Join-Path $script:DocBase $m.Groups[1].Value } else { $p }
}
function Resolve-DocPath($p) {
  if (-not $p) { return $p }
  if (Test-Path -LiteralPath $p) { return $p }
  $c = Map-DocPath $p; if ($c -ne $p -and (Test-Path -LiteralPath $c)) { return $c }
  $p
}
function Do-Paths {
  function Line($label,$p,$ex) { Say ("  {0,-22} {1}  [{2}]" -f $label,$p,$(if ($ex) { 'exists' } else { 'MISSING' })) }
  Say "Legal partition root: $($script:Root)   (source: $($script:RootSource))"
  Line 'database' $script:DbPath (Test-Path -LiteralPath $script:DbPath)
  Line 'documents folder' $script:DocBase (Test-Path -LiteralPath $script:DocBase)
  Line 'deleted-files folder' $script:DelDir (Test-Path -LiteralPath $script:DelDir)
  Say "  tool folder            $($script:Here)   (backups and log live here)"
  Say "  settings file          $($script:CfgFile)$(if ($env:MASTMD_CONFIG) { '   [OVERRIDDEN by MASTMD_CONFIG]' })"
  if ($Action -eq 'ShowPaths') { return }
  if (-not $Path) { throw '-Path required (the folder that contains the Legal database and the documents folder)' }
  $p = $Path.TrimEnd('\')
  if (-not (Test-Path -LiteralPath (Join-Path $p (Cfg 'DbFileName' 'MasTmd.mdb')))) { throw "Database '$(Cfg 'DbFileName' 'MasTmd.mdb')' not found in $p" }
  if (-not (Test-Path -LiteralPath (Join-Path $p (Cfg 'DocsFolder' 'tmpDocs')))) { throw "Documents folder '$(Cfg 'DocsFolder' 'tmpDocs')' not found in $p" }
  Plan "CONFIG LegalRoot = $p  ($($script:Here)\mastmd.config.json)"
  if (-not $script:Apply) { Say '[DRY-RUN] config not changed. Add -Apply to save.'; return }
  $cp = $script:CfgFile
  $c = Get-Content $cp -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($null -ne $c.PSObject.Properties['LegalRoot']) { $c.LegalRoot = $p } else { Add-Member -InputObject $c -NotePropertyName LegalRoot -NotePropertyValue $p }
  [IO.File]::WriteAllText($cp, ($c | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding($true)))
  Say "[OK] LegalRoot saved. All actions now use: $p"
}function Do-Rename {
  if (-not $Act) { throw '-Act required' }; $new = Sanitize $NewText; if (-not $new) { throw '-NewText required' }
  $a = Get-ActRow $Act; Assert-Allowed $a.CaseID
  $set = [ordered]@{ ActTeur = $new }
  if ($a.DocPath -isnot [DBNull] -and $a.DocPath) {
    $cur = Resolve-DocPath $a.DocPath
    $ext = [IO.Path]::GetExtension($cur); $np = Join-Path (Split-Path $cur -Parent) ("$Act$new$ext")
    if (-not (Test-Path -LiteralPath $cur)) { throw "File missing on disk: $($a.DocPath)" }
    if ($np -ne $cur) { Do-FileMove $cur $np }
    $set['DocPath'] = $np
  }
  Do-Update 'tblCaseAct' $set 'ActID' $Act
  $script:Out = @{ actId = $Act; newText = $new; docPath = $set['DocPath'] }
}
function Do-MoveDoc {
  if (-not $Act -or -not $ToCase) { throw '-Act and -ToCase required' }
  $a = Get-ActRow $Act; Assert-Allowed $a.CaseID; Assert-Allowed $ToCase; [void](Get-CaseRow $ToCase)
  if (-not ($a.DocPath -isnot [DBNull] -and $a.DocPath)) { throw 'Act has no file' }
  $cur = Resolve-DocPath $a.DocPath
  if (-not (Test-Path -LiteralPath $cur)) { throw "File missing on disk: $($a.DocPath)" }
  $np = Join-Path (Get-DocDir $ToCase) (Split-Path $cur -Leaf)
  if ($np -ne $cur) { Do-FileMove $cur $np }
  Do-Update 'tblCaseAct' ([ordered]@{ CaseID = $ToCase; DocPath = $np }) 'ActID' $Act
  $script:Out = @{ actId = $Act; toCase = $ToCase; docPath = $np }
}
$script:Rnd = New-Object System.Random
function RandId { $script:Rnd.Next(-2000000000,2000000000) }
function Do-MkDir($p) {
  Plan "DIR create : $p"
  if (-not $script:Apply) { return }
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Force $p | Out-Null; $script:UndoDirs += ,$p }
}
function Do-DirMove($from,$to) {
  Plan "DIR rename : $from -> $to"
  if (-not $script:Apply) { return }
  if (Test-Path -LiteralPath $to) { throw "Target folder already exists: $to" }
  Move-Item -LiteralPath $from -Destination $to; $script:UndoMoves += ,@($to,$from)
}
$script:UndoDirs = @()
function Do-NewCase {
  $sk = $(if ($SueKind) { $SueKind } else { 24 })
  $map = @{ 22 = @{ Node = 38; Cap = 'פתיחת תיק'; Vals = $true }; 20 = @{ Node = 38; Cap = 'פתיחת תיק'; Vals = $true }; 98 = @{ Node = 38; Cap = 'פתיחת תיק'; Vals = $true }; 102 = @{ Node = 38; Cap = 'פתיחת תיק'; Vals = $true }; 24 = @{ Node = 57; Cap = 'כללי'; Vals = $false } }
  if (-not $map.ContainsKey($sk)) { throw "SueKind $sk is not supported yet (supported: 24 general, 22/98/20/102 torts)" }
  if (-not $Test -and -not $AllowRealData) { throw 'Creating a real client/case needs -AllowRealData after explicit user approval (client name + case type). For dummy data use -Test.' }
  $m = $map[$sk]; $now = Get-Date; $today = $now.Date; $u = $script:User
  if ($CustomerId) {
    $cr = (Q "SELECT Pname,Lname FROM tblCustomer WHERE CustomerID=$CustomerId").Rows; if ($cr.Count -eq 0) { throw "Customer $CustomerId not found" }
    $cid = $CustomerId; $full = ("$(Nz $cr[0].Lname '') $(Nz $cr[0].Pname '')").Trim()
  } else {
    if (-not $First -or -not $Last) { throw '-First (first name) and -Last (family name) required, or -CustomerId' }
    $dup = (Q ("SELECT CustomerID FROM tblCustomer WHERE Pname='" + $Last.Replace("'","''") + "' AND Lname='" + $First.Replace("'","''") + "'")).Rows
    if ($dup.Count -gt 0) { throw "A customer with this name already exists (CustomerID $($dup[0].CustomerID)); use -CustomerId" }
    $cid = Do-Insert 'tblCustomer' ([ordered]@{ CkindID = 1; Pname = $Last; Lname = $First; CellPhone = $Phone; InputUsr = $u; InputDate = $today; ChangeDate = $now }) -Identity
    $full = "$First $Last"
  }
  $full = (($full -replace '"','') -replace '[\\/:*?<>|]',' ' -replace '\s{2,}',' ').Trim()
  $max = 0; foreach ($r in (Q 'SELECT CaseNum FROM tblCase').Rows) { $n = 0; if ([int]::TryParse("$($r.CaseNum)",[ref]$n) -and $n -gt $max) { $max = $n } }
  $num = $max + 1; $flow = RandId; $det = RandId; while ($det -eq $flow) { $det = RandId }
  $caseId = Do-Insert 'tblCase' ([ordered]@{ CustomerID = $cid; CaseNum = "$num"; CaseOpenDate = $today; SueKind = $sk; CurrentFlowID = $flow; NodeCaption = $m.Cap; InputUsr = $u; CaseOwnerMaster = $u; CaseNumSort = ('{0:D8}' -f $num); CaseCustName = $full }) -Identity
  Do-Insert 'tblCaseNodeFlow' ([ordered]@{ FlowID = $flow; CaseID = $caseId; NodeID = $m.Node; ChangeDate = $now }) | Out-Null
  Do-Insert 'tblCaseDetail' ([ordered]@{ CaseDetID = $det; CaseID = $caseId }) | Out-Null
  if ($m.Vals) { foreach ($it in 'nzSueTotal','nzSueReal','nzSueOutcome','nzRisk') { Do-Insert 'tblCaseValues' ([ordered]@{ CaseID = $caseId; ValueItem = $it; ValueDate = $today }) | Out-Null } }
  if ($Test -and $script:Apply) {
    $cfgPath = $script:CfgFile
    $c = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json; $c.TestCaseIds = @($c.TestCaseIds) + [int]$caseId
    ($c | ConvertTo-Json -Depth 5) | Set-Content $cfgPath -Encoding UTF8
    Say "[NOTE] case $caseId added to TestCaseIds"
  }
  $script:Out = @{ customerId = $cid; caseId = $caseId; caseNum = $num; folder = (Join-Path $script:DocBase "$full $num") }
  Say "[NOTE] case folder '$full $num' is created by the app/tool on the first document import"
}
function Do-NewSubfolder {
  if (-not $Case) { throw '-Case required' }; $n = Sanitize $Name; if (-not $n) { throw '-Name required' }
  Assert-Allowed $Case; [void](Get-CaseRow $Case)
  $sib = (Q "SELECT CaseSubject FROM tblCase WHERE CaseParentID=$Case AND SueKind=77").Rows | Where-Object { "$($_.CaseSubject)".Trim() -eq $n }
  if (@($sib).Count -gt 0) { throw "A sub-folder named '$n' already exists under case $Case" }
  $id = Do-Insert 'tblCase' ([ordered]@{ SueKind = 77; CaseParentID = $Case; CaseSubject = $n; CaseNumSort = $n }) -Identity
  Do-MkDir (Join-Path (Get-DocDir $Case) $n)
  $script:Out = @{ caseId = $id; parent = $Case; name = $n }
}
function Do-RenameFolder {
  if (-not $Case) { throw '-Case required' }; $n = Sanitize $NewText; if (-not $n) { throw '-NewText required' }
  $r = Get-CaseRow $Case; if ((Nz $r.SueKind 0) -ne 77) { throw "Case $Case is not a sub-folder (SueKind 77)" }
  Assert-Allowed $Case
  $old = Get-DocDir $Case; $new = Join-Path (Split-Path $old -Parent) $n
  $sib = (Q "SELECT CaseID,CaseSubject FROM tblCase WHERE CaseParentID=$($r.CaseParentID) AND SueKind=77").Rows | Where-Object { $_.CaseID -ne $Case -and "$($_.CaseSubject)".Trim() -eq $n }
  if (@($sib).Count -gt 0) { throw "A sibling sub-folder named '$n' already exists" }
  Do-Update 'tblCase' ([ordered]@{ CaseSubject = $n; CaseNumSort = $n }) 'CaseID' $Case
  if (Test-Path -LiteralPath $old) { Do-DirMove $old $new } else { Say "[NOTE] directory '$old' does not exist yet - only the database name is changed" }
  foreach ($a in (Q 'SELECT ActID,DocPath FROM tblCaseAct WHERE DocPath IS NOT NULL').Rows) {
    $p = Map-DocPath "$($a.DocPath)"; if ($p -and $p.StartsWith($old + '\',[StringComparison]::OrdinalIgnoreCase)) { Do-Update 'tblCaseAct' ([ordered]@{ DocPath = ($new + $p.Substring($old.Length)) }) 'ActID' $a.ActID }
  }
  $script:Out = @{ caseId = $Case; newName = $n }
}
function Norm($s) { (("$s".ToLower() -replace '[^\p{L}\p{N}\s]',' ') -replace '\s+',' ').Trim() }
function Stem($w) { if ($w.Length -gt 3 -and $w -match '^[הבלמכוש]') { $w.Substring(1) } else { $w } }
function Lev($a,$b) {
  $n = $a.Length; $m = $b.Length; if ($n -eq 0) { return $m }; if ($m -eq 0) { return $n }
  $d = New-Object 'int[,]' ($n+1),($m+1)
  for ($i = 0; $i -le $n; $i++) { $d[$i,0] = $i }; for ($j = 0; $j -le $m; $j++) { $d[0,$j] = $j }
  for ($i = 1; $i -le $n; $i++) {
    $im = $i - 1
    for ($j = 1; $j -le $m; $j++) {
      $jm = $j - 1
      $cost = 1; if ($a[$im] -eq $b[$jm]) { $cost = 0 }
      $v1 = $d[$im,$j] + 1; $v2 = $d[$i,$jm] + 1; $v3 = $d[$im,$jm] + $cost
      $d[$i,$j] = [math]::Min([math]::Min($v1,$v2),$v3)
    }
  }
  $d[$n,$m]
}
function Sim($a,$b) {
  $x = Norm $a; $y = Norm $b; if ($x -eq $y) { return 1.0 }; if (-not $x -or -not $y) { return 0.0 }
  $tx = @($x -split ' ' | ForEach-Object { Stem $_ } | Where-Object { $_ }); $ty = @($y -split ' ' | ForEach-Object { Stem $_ } | Where-Object { $_ })
  $inter = @($tx | Where-Object { $ty -contains $_ }).Count; $union = @($tx + $ty | Sort-Object -Unique).Count
  $jac = $(if ($union) { $inter / $union } else { 0 })
  $cont = 0.0; if ($x.Contains($y) -or $y.Contains($x)) { $cont = [math]::Min(1.0, [math]::Min($x.Length,$y.Length) / [double][math]::Max($x.Length,$y.Length) + 0.3) }
  $ed = 1 - (Lev $x $y) / [double][math]::Max($x.Length,$y.Length)
  [math]::Round([math]::Min(1.0, [math]::Max($jac, [math]::Max($cont, $ed))),2)
}
function Get-StatusList {
  $list = New-Object System.Collections.ArrayList
  foreach ($r in (Q 'SELECT BankID,BankName FROM tblBankStatusText').Rows) { $n = "$($r.BankName)".Trim(); if ($n) { [void]$list.Add([pscustomobject]@{ Name = $n; Source = "catalog#$($r.BankID)"; Uses = 0 }) } }
  $used = @{}; foreach ($r in (Q 'SELECT CaseStatus FROM tblCase WHERE CaseStatus IS NOT NULL').Rows) { $s = "$($r.CaseStatus)".Trim(); if ($s) { $used[$s] = 1 + [int]$used[$s] } }
  foreach ($e in $list) { if ($used.ContainsKey($e.Name)) { $e.Uses = $used[$e.Name]; $used.Remove($e.Name) } }
  foreach ($k in $used.Keys) { [void]$list.Add([pscustomobject]@{ Name = $k; Source = 'used-in-cases'; Uses = $used[$k] }) }
  $list.ToArray()
}
function Get-SimilarStatuses($t,$min=0.5) {
  @(Get-StatusList | ForEach-Object { [pscustomobject]@{ Score = (Sim $t $_.Name); Name = $_.Name; Source = $_.Source; Uses = $_.Uses } } | Where-Object { $_.Score -ge $min } | Sort-Object Score -Descending | Select-Object -First 5)
}
function Show-Similar($t,$sim) {
  $sim = @($sim | Where-Object { $_ })
  if ($sim.Count -eq 0) { Say "No similar status found for '$t'."; return }
  Say "Similar existing statuses for '$t' (score 0-1):"
  foreach ($s in $sim) { Say ("  {0} | {1} | {2} | used by {3} case(s)" -f $s.Score,$s.Name,$s.Source,$s.Uses) }
}
function Assert-StatusKnown($t) {
  $ex = @(Get-StatusList | Where-Object { (Norm $_.Name) -eq (Norm $t) })
  if ($ex.Count -gt 0) { return }
  Show-Similar $t (Get-SimilarStatuses $t)
  throw "STATUS_UNKNOWN: '$t' does not exist yet. Offer the user a similar status (or a better wording) first; only if the user rejects them, run AddStatus -Text '$t' -NotSimilar -AllowRealData, then retry."
}
function Do-ListStatuses { foreach ($s in (Get-StatusList | Sort-Object Source,Name)) { Say ("{0} | {1} | used by {2}" -f $s.Name,$s.Source,$s.Uses) } }
function Do-FindStatus {
  $t = "$Text".Trim(); if (-not $t) { throw '-Text required' }
  $ex = @(Get-StatusList | Where-Object { (Norm $_.Name) -eq (Norm $t) })
  if ($ex.Count -gt 0) { Say "EXISTS: '$($ex[0].Name)' ($($ex[0].Source), used by $($ex[0].Uses) case(s))" } else { Say "NOT FOUND: '$t'" }
  Show-Similar $t (@(Get-SimilarStatuses $t) | Where-Object { (Norm $_.Name) -ne (Norm $t) })
}
function Do-AddStatus {
  $t = "$Text".Trim(); if (-not $t) { throw '-Text required' }
  if (-not $AllowRealData) { throw 'AddStatus changes a shared catalog: needs -AllowRealData after the user approved the exact status name' }
  if (@(Get-StatusList | Where-Object { (Norm $_.Name) -eq (Norm $t) }).Count -gt 0) { throw "Status '$t' already exists" }
  $sim = @(Get-SimilarStatuses $t 0.6)
  if ($sim.Count -gt 0 -and -not $NotSimilar) { Show-Similar $t $sim; throw 'Similar statuses exist. Propose them to the user first; if the user says none fits, run again with -NotSimilar.' }
  $dt = New-Object System.Data.DataTable; $da = New-Object System.Data.OleDb.OleDbDataAdapter('SELECT * FROM tblBankStatusText WHERE 1=0',$script:Conn)
  if ($script:Tx) { $da.SelectCommand.Transaction = $script:Tx }
  [void]$da.FillSchema($dt,'Source')
  $row = [ordered]@{ BankName = $t }
  if (-not @($dt.Columns | Where-Object { $_.ColumnName -eq 'BankID' -and $_.AutoIncrement }).Count) {
    $mx = 0; foreach ($r in (Q 'SELECT BankID FROM tblBankStatusText WHERE BankID<9999').Rows) { if ([int]$r.BankID -gt $mx) { $mx = [int]$r.BankID } }
    $row = [ordered]@{ BankID = $mx + 1; BankName = $t }
  }
  Do-Insert 'tblBankStatusText' $row | Out-Null
  $script:Out = @{ status = $t }
}
function Get-ModelStages($caseRow) {
  $mid = (Q "SELECT ModelID FROM tblBankSueKind WHERE SueID=$([int](Nz $caseRow.SueKind 0))").Rows
  if ($mid.Count -eq 0 -or (Nz $mid[0].ModelID 0) -eq 0) { throw "Case type $($caseRow.SueKind) has no process model" }
  $m = [int]$mid[0].ModelID
  [pscustomobject]@{ ModelID = $m; Nodes = @((Q "SELECT NodeID,NodeCaption,NodeKey FROM tblNodes WHERE ModelID=$m").Rows | Where-Object { $_.NodeKey -isnot [DBNull] -and "$($_.NodeKey)" -notin '','0' } | ForEach-Object { [pscustomobject]@{ NodeID = [int]$_.NodeID; Caption = "$($_.NodeCaption)" } }) }
}
function Do-ListStages {
  if (-not $Case) { throw '-Case required' }
  $r = Get-CaseRow $Case; $ms = Get-ModelStages $r
  $cur = (Q "SELECT NodeID FROM tblCaseNodeFlow WHERE FlowID=$([int](Nz $r.CurrentFlowID 0))").Rows
  $curNode = $(if ($cur.Count) { [int]$cur[0].NodeID } else { 0 })
  Say "Process model $($ms.ModelID) stages (current marked *):"
  foreach ($n in $ms.Nodes) { Say ("  {0} {1} | {2}" -f $(if ($n.NodeID -eq $curNode) { '*' } else { ' ' }),$n.NodeID,$n.Caption) }
  Say "NOTE: Legal's own list may offer only the stages connected to the current one in tblNodeChilds; not verified"
}
function Do-SetStage {
  if (-not $Case) { throw '-Case required' }; $t = "$Text".Trim(); if (-not $t) { throw '-Text required (stage name or NodeID)' }
  $r = Get-StatusCase; $ms = Get-ModelStages $r
  $node = @($ms.Nodes | Where-Object { "$($_.NodeID)" -eq $t -or (Norm $_.Caption) -eq (Norm $t) })
  if ($node.Count -ne 1) { throw "Stage '$t' not found (or ambiguous) in process model $($ms.ModelID). Use ListStages." }
  $n = $node[0]; $now = Get-Date
  $flow = RandId
  Do-Insert 'tblCaseNodeFlow' ([ordered]@{ FlowID = $flow; CaseID = $Case; NodeID = $n.NodeID; ChangeDate = $now }) | Out-Null
  Do-Update 'tblCase' ([ordered]@{ CurrentFlowID = $flow; NodeCaption = $n.Caption }) 'CaseID' $Case
  $script:Out = @{ caseId = $Case; stage = $n.Caption; nodeId = $n.NodeID; flowId = $flow }
  Say '[NOTE] if this case is open in a Legal card, close and reopen the card before saving there (stale row -> "Row cannot be located for updating")'
}
function Do-RemoveStatus {
  $t = "$Text".Trim(); if (-not $t) { throw '-Text required' }
  if (-not $AllowRealData) { throw 'RemoveStatus changes a shared catalog: needs -AllowRealData after the user approved' }
  $rows = @((Q 'SELECT BankID,BankName FROM tblBankStatusText').Rows | Where-Object { (Norm $_.BankName) -eq (Norm $t) })
  if ($rows.Count -ne 1) { throw "Status '$t' not found in the catalog (statuses that only exist as text in cases cannot be removed here)" }
  $id = [int]$rows[0].BankID; if ($id -eq 9999) { throw 'The "סגור" status (9999) is a system status and cannot be removed' }
  $n = [int](Q ("SELECT COUNT(*) AS n FROM tblCase WHERE CaseStatus='" + $t.Replace("'","''") + "'")).Rows[0].n
  if ($n -gt 0) { throw "Status '$t' is used by $n case(s); change those cases first" }
  Do-Delete 'tblBankStatusText' 'BankID' $id
  $script:Out = @{ removedStatus = $t; bankId = $id }
}function Do-DeleteFlow {
  if (-not $Case -or -not $Flow) { throw '-Case and -Flow (FlowID) required' }
  $r = Get-StatusCase
  $f = (Q "SELECT FlowID,CaseID,NodeID,ChangeDate FROM tblCaseNodeFlow WHERE FlowID=$Flow").Rows
  if ($f.Count -ne 1) { throw "Flow row $Flow not found" }
  if ([int]$f[0].CaseID -ne $Case) { throw "Flow row $Flow belongs to case $($f[0].CaseID), not $Case" }
  if ([int](Nz $r.CurrentFlowID 0) -eq $Flow) { throw 'This is the case''s current stage row and cannot be deleted' }
  $used = [int](Q "SELECT COUNT(*) AS n FROM tblCaseAct WHERE FlowID=$Flow").Rows[0].n
  if ($used -gt 0) { throw "Flow row $Flow is referenced by $used act(s)" }
  Say "[NOTE] deleting stage-history row: node $($f[0].NodeID) at $($f[0].ChangeDate)"
  Do-Delete 'tblCaseNodeFlow' 'FlowID' $Flow
  $script:Out = @{ caseId = $Case; deletedFlow = $Flow }
}function Get-StatusCase {
  if (-not $Case) { throw '-Case required' }
  $r = Get-CaseRow $Case; Assert-Allowed $Case
  if ((Nz $r.SueKind 0) -eq 77) { throw 'Sub-folders have no status' }
  $r
}
function Do-SetStatus {
  $t = "$Text".Trim(); if (-not $t) { throw '-Text required (the new status)' }
  $r = Get-StatusCase
  if ($t -eq 'סגור') { throw 'To close a case use CloseCase (sets the status "סגור" AND CaseCloseDate together)' }
  if ($null -ne (Nz $r.CaseCloseDate $null)) { throw 'This case has a close date (closed). Use ReopenCase to change its status and clear the date' }
  Assert-StatusKnown $t
  Do-Update 'tblCase' ([ordered]@{ CaseStatus = $t }) 'CaseID' $Case
  $script:Out = @{ caseId = $Case; status = $t }
}
function Do-CloseCase {
  [void](Get-StatusCase); $d = ParseDate $Date
  Do-Update 'tblCase' ([ordered]@{ CaseStatus = 'סגור'; CaseCloseDate = $d }) 'CaseID' $Case
  $script:Out = @{ caseId = $Case; status = 'סגור'; closeDate = $d.ToString('yyyy-MM-dd') }
  Say '[NOTE] a closed case is hidden from the case tree/search for users with HideCloseCaseInTreeSearchResults_<user>=1 (tblBankReg)'
}
function Do-ReopenCase {
  [void](Get-StatusCase); $t = "$Text".Trim()
  if ($t -eq 'סגור') { throw 'Reopen with a status other than "סגור" (or leave -Text empty)' }
  if ($t) { Assert-StatusKnown $t }
  Do-Update 'tblCase' ([ordered]@{ CaseStatus = $t; CaseCloseDate = $null }) 'CaseID' $Case
  $script:Out = @{ caseId = $Case; status = $t; closeDate = '' }
}
function Do-DeleteAct {
  if (-not $Act) { throw '-Act required' }
  $a = Get-ActRow $Act; Assert-Allowed $a.CaseID
  $kn = Get-KindName $a.ActKindID; $now = Get-Date
  $recv = "$(Nz $a.LReciver '')"; if (-not $recv) { $recv = Get-Pname $a.CaseID }
  $due = Nz $a.ActDueDate (Nz $a.ActDate $now)
  $notes = "$($a.ActTeur), $(([datetime]$due).ToString('dd/MM/yyyy')), $(Nz $a.Lsender ''), $recv"
  Do-Insert 'tblBankDeletes' ([ordered]@{ DelDate = $now; DelType = $kn.Name; DelNotes = $notes; DelUser = $script:User }) | Out-Null
  Do-Delete 'tblCaseAct' 'ActID' $Act
  if (Is-Calendar $a.ActKindID) { Do-Insert 'tblBankOutlookBIN' ([ordered]@{ ActID = $Act }) | Out-Null; Say '[NOTE] tblBasket row is left in place, as the app does' }
  $cur = $(if ($a.DocPath -isnot [DBNull] -and $a.DocPath) { Resolve-DocPath $a.DocPath } else { '' })
  if ($cur -and (Test-Path -LiteralPath $cur)) {
    $to = Join-Path $script:DelDir (Split-Path $cur -Leaf)
    Do-FileMove $cur $to
  }
  $script:Out = @{ actId = $Act; deletedKind = $kn.Name }
}

# ---------------- main ----------------
$script:Out = @{}
try {
  if ($env:MASTMD_CONFIG) { Say "[CONFIG] settings file overridden by MASTMD_CONFIG: $($env:MASTMD_CONFIG)" }
  Say ("[MODE] " + $(if ($script:TestMode) { 'TEST MODE ON (TestMode=true): test shortcuts enabled' } else { 'PRODUCTION (TestMode=false): real data only; -Test and -DbOverride are disabled' }))
  if ($Action -in 'ShowPaths','SetRoot') { Do-Paths; exit 0 }
  Open-Db
  $readOnly = $Action -in 'ListKinds','Find','Info','ListStatuses','FindStatus','ListStages'
  if ($readOnly) {
    switch ($Action) { 'ListStages' { Do-ListStages } 'ListKinds' { Do-ListKinds } 'Find' { Do-Find } 'Info' { Do-Info } 'ListStatuses' { Do-ListStatuses } 'FindStatus' { Do-FindStatus } }
    $script:Conn.Close(); exit 0
  }
  if ($script:Apply) { [void](Backup-Db); $script:Tx = $script:Conn.BeginTransaction() } else { Say '[DRY-RUN] nothing will be written. Add -Apply to execute.' }
  switch ($Action) {
    'AddEvent'    { Do-AddEvent }
    'AddDocument' { Do-AddDocument }
    'Rename'      { Do-Rename }
    'Move'        { Do-MoveDoc }
    'Delete'      { Do-DeleteAct }
    'NewCase'     { Do-NewCase }
    'NewSubfolder' { Do-NewSubfolder }
    'RenameFolder' { Do-RenameFolder }
    'SetStatus'   { Do-SetStatus }
    'CloseCase'   { Do-CloseCase }
    'ReopenCase'  { Do-ReopenCase }
    'AddStatus'   { Do-AddStatus }
    'RemoveStatus' { Do-RemoveStatus }
    'SetStage'    { Do-SetStage }
    'DeleteFlow'  { Do-DeleteFlow }
  }
  if ($script:Apply) {
    $script:Tx.Commit(); $script:Tx = $null
    Log-Run @{ out = $script:Out; args = @{ Case = $Case; Act = $Act; ToCase = $ToCase; Kind = $Kind; Text = $Text; NewText = $NewText } }
    Say '[OK] committed.'
    # verification
    if ($script:Out.actId -and $Action -ne 'Delete') {
      $v = Get-ActRow $script:Out.actId
      $fileInfo = ''
      if ($v.DocPath -isnot [DBNull] -and $v.DocPath) {
        $ok = Test-Path -LiteralPath (Resolve-DocPath $v.DocPath)
        $leaf = [IO.Path]::GetFileNameWithoutExtension($v.DocPath)
        $fileInfo = " | file exists: $ok | name matches ActID+ActTeur: $($leaf -eq ("$($v.ActID)$($v.ActTeur)"))"
      }
      Say ("[VERIFY] act {0} case {1} kind {2} text '{3}'{4}" -f $v.ActID,$v.CaseID,$v.ActKindID,(("$($v.ActTeur)" -replace "\r?\n",' ')),$fileInfo)
    }
    if ($script:Out.caseId) {
      $v = Get-CaseRow $script:Out.caseId
      $cd = Nz $v.CaseCloseDate $null
      Say ("[VERIFY] case {0} | num {1} | name '{2}' | subject '{3}' | sueKind {4} | parent {5} | customer {6} | status '{7}' | close date {8} | stage '{9}'" -f $v.CaseID,(Nz $v.CaseNum ''),(Nz $v.CaseCustName ''),(Nz $v.CaseSubject ''),$v.SueKind,(Nz $v.CaseParentID ''),(Nz $v.CustomerID ''),(Nz $v.CaseStatus ''),$(if ($cd) { ([datetime]$cd).ToString('yyyy-MM-dd') } else { '-' }),(Nz $v.NodeCaption ''))
    }
    if ($Action -eq 'Delete') { $left = (Q "SELECT COUNT(*) AS n FROM tblCaseAct WHERE ActID=$Act").Rows[0].n; Say "[VERIFY] act $Act remaining rows: $left" }
  }
  $script:Conn.Close()
} catch {
  if ($script:Tx) { try { $script:Tx.Rollback() } catch {} }
  if ($script:Apply) { Undo-Files; foreach ($dd in $script:UndoDirs) { Remove-Item -LiteralPath $dd -Force -ErrorAction SilentlyContinue } }
  Write-Output "[ERROR] $($_.Exception.Message)"
  if ($script:Conn) { try { $script:Conn.Close() } catch {} }
  exit 1
}

















