# Run with 32-bit PowerShell. Read-only. Needs schema-out\{columns,indexes,rowcounts}.json (see Invoke-MasTmd.ps1).
# Checks every numeric column that shares its name with another table's single-column primary key,
# and counts rows whose value has no match in the parent table. Output: schema-out\relation-check.json
# Generic names (BankID, Id, Oid, ViewID, OtherID, SortID, TypeID) give accidental matches - ignore them.
param([string]$DbPath = (Join-Path (Split-Path $PSScriptRoot -Parent) 'MasTmd.mdb'))
$cj = $(if ($env:MASTMD_CONFIG) { $env:MASTMD_CONFIG } else { Join-Path $env:APPDATA 'MasTmd\config.json' }); $cc = Get-Content $cj -Raw -Encoding UTF8 | ConvertFrom-Json
$DbPass = $(if ($cc.PasswordProtected) { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR((ConvertTo-SecureString "$($cc.PasswordProtected)"))) } else { "$($cc.Password)" })
$ErrorActionPreference = 'Stop'
$d = Join-Path $PSScriptRoot 'schema-out'
$cols = Get-Content "$d\columns.json" -Raw | ConvertFrom-Json
$ix   = Get-Content "$d\indexes.json" -Raw | ConvertFrom-Json
$rc   = Get-Content "$d\rowcounts.json" -Raw | ConvertFrom-Json
$cnt = @{}; $rc | ForEach-Object { $cnt[$_.T] = $_.N }
$skip = '_ts$|_Bak|_BAK|_ORG|_FUT|^aaa$|^AAA'

$pk = @{}
$ix | Where-Object { $_.PRIMARY_KEY -eq $true } | Group-Object TABLE_NAME | ForEach-Object {
  if ($_.Count -eq 1 -and $_.Name -notmatch $skip -and $cnt[$_.Name] -gt 0) { $pk[$_.Group[0].COLUMN_NAME] += @($_.Name) }
}
$numeric = 2,3,4,5,6,14,17,18,19,20,21,131

$c = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.Jet.OLEDB.4.0;Data Source=$DbPath;Jet OLEDB:Database Password=$DbPass;Mode=Read")
$c.Open()
function Scalar($sql) { $cmd = $c.CreateCommand(); $cmd.CommandText = $sql; $cmd.CommandTimeout = 120; $cmd.ExecuteScalar() }

$res = foreach ($col in $cols) {
  $t = $col.TABLE_NAME
  if ($t -match $skip -or $cnt[$t] -eq 0 -or -not $pk.ContainsKey($col.COLUMN_NAME)) { continue }
  if ($numeric -notcontains [int]$col.DATA_TYPE) { continue }
  foreach ($p in $pk[$col.COLUMN_NAME]) {
    if ($p -eq $t) { continue }
    $k = $col.COLUMN_NAME
    try {
      $filled = [int](Scalar "SELECT COUNT(*) FROM [$t] WHERE [$k] IS NOT NULL AND [$k]<>0")
      if ($filled -eq 0) { $orph = 0; $dist = 0 } else {
        $orph = [int](Scalar "SELECT COUNT(*) FROM [$t] WHERE [$k] IS NOT NULL AND [$k]<>0 AND [$k] NOT IN (SELECT [$k] FROM [$p])")
        $dist = [int](Scalar "SELECT COUNT(*) FROM (SELECT DISTINCT [$k] FROM [$t] WHERE [$k] IS NOT NULL AND [$k]<>0)")
      }
      [pscustomobject]@{ Child=$t; Column=$k; Parent=$p; Rows=$cnt[$t]; Filled=$filled; DistinctVals=$dist; Orphans=$orph }
    } catch { [pscustomobject]@{ Child=$t; Column=$k; Parent=$p; Rows=$cnt[$t]; Filled=-1; DistinctVals=-1; Orphans=-1 } }
  }
}
$c.Close()
$res | ConvertTo-Json | Set-Content "$d\relation-check.json" -Encoding UTF8
"checked: $(@($res).Count)"
