<#
  Persistent, READ-ONLY connection helper for MasTmd.mdb (Jet 4.0 => needs 32-bit PowerShell).
  Usage:
    & "C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File Invoke-MasTmd.ps1 -Action Test
    ... -Action Tables
    ... -Action Columns -Table "SomeTable"
    ... -Action Query -Sql "SELECT TOP 10 * FROM SomeTable"
    ... -Action Schema        # dumps tables/columns/indexes/FKs/queries to JSON in .\schema-out
    ... -Action RowCounts     # row count of every table -> schema-out\rowcounts.json
#>
param(
  [ValidateSet('Test','Tables','Columns','Query','Schema','RowCounts')][string]$Action = 'Test',
  [string]$Table,
  [string]$Sql,
  [string]$DbPath = $($cj = $(if ($env:MASTMD_CONFIG) { $env:MASTMD_CONFIG } else { Join-Path $env:APPDATA 'MasTmd\config.json' }); $lr = $null; if (Test-Path $cj) { $cc = Get-Content $cj -Raw -Encoding UTF8 | ConvertFrom-Json; $lr = $cc.LegalRoot }; if ($lr) { Join-Path $lr 'MasTmd.mdb' } else { Join-Path 'C:\Timin' 'MasTmd.mdb' }),
  [string]$Out = (Join-Path $PSScriptRoot 'schema-out')
)
$ErrorActionPreference = 'Stop'
$cj = $(if ($env:MASTMD_CONFIG) { $env:MASTMD_CONFIG } else { Join-Path $env:APPDATA 'MasTmd\config.json' }); $cc = $null
if (Test-Path $cj) { $cc = Get-Content $cj -Raw -Encoding UTF8 | ConvertFrom-Json }
if ($cc -and $cc.PasswordProtected) { $DbPass = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR((ConvertTo-SecureString "$($cc.PasswordProtected)"))) }
elseif ($cc -and $cc.Password) { $DbPass = "$($cc.Password)" }
elseif ($cc) { $DbPass = 'laroche' }   # built-in: the Legal database password is the same for every installation
else { throw 'Settings not found: run the Legal setup (/legal-db:legal-setup) first.' }
$ConnStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=$DbPath;Jet OLEDB:Database Password=$DbPass;Mode=Read"

function Open-Db { $c = New-Object System.Data.OleDb.OleDbConnection($ConnStr); $c.Open(); $c }
function Get-Schema($c, $guid, $restr = $null) { $c.GetOleDbSchemaTable($guid, $restr) }
$G = [System.Data.OleDb.OleDbSchemaGuid]

$c = Open-Db
try {
  switch ($Action) {
    'Test' {
      "Connected OK (state=$($c.State)); 32-bit process: $(-not [Environment]::Is64BitProcess)"
      Get-Schema $c $G::Tables | Group-Object TABLE_TYPE | ForEach-Object { "$($_.Name): $($_.Count)" }
    }
    'Tables' {
      Get-Schema $c $G::Tables | Where-Object TABLE_TYPE -in 'TABLE','VIEW','ACCESS TABLE' |
        Select-Object TABLE_NAME, TABLE_TYPE | Sort-Object TABLE_NAME | Format-Table -AutoSize | Out-String -Width 300
    }
    'Columns' {
      Get-Schema $c $G::Columns @($null,$null,$Table,$null) | Sort-Object ORDINAL_POSITION |
        Select-Object COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE | Format-Table -AutoSize | Out-String -Width 300
    }
    'Query' {
      $da = New-Object System.Data.OleDb.OleDbDataAdapter($Sql, $c)
      $dt = New-Object System.Data.DataTable; [void]$da.Fill($dt)
      $dt | Format-Table -AutoSize | Out-String -Width 400
    }
    'Schema' {
      New-Item -ItemType Directory -Force $Out | Out-Null
      $sel = 'TABLE_NAME','COLUMN_NAME','ORDINAL_POSITION','DATA_TYPE','CHARACTER_MAXIMUM_LENGTH','IS_NULLABLE','COLUMN_HASDEFAULT'
      Get-Schema $c $G::Tables | Select-Object TABLE_NAME,TABLE_TYPE | ConvertTo-Json | Set-Content "$Out\tables.json" -Encoding UTF8
      Get-Schema $c $G::Columns | Select-Object $sel | ConvertTo-Json | Set-Content "$Out\columns.json" -Encoding UTF8
      Get-Schema $c $G::Indexes | Select-Object TABLE_NAME,INDEX_NAME,PRIMARY_KEY,UNIQUE,COLUMN_NAME,ORDINAL_POSITION | ConvertTo-Json | Set-Content "$Out\indexes.json" -Encoding UTF8
      Get-Schema $c $G::Foreign_Keys | Select-Object PK_TABLE_NAME,PK_COLUMN_NAME,FK_TABLE_NAME,FK_COLUMN_NAME,FK_NAME | ConvertTo-Json | Set-Content "$Out\foreign_keys.json" -Encoding UTF8
      Get-Schema $c $G::Views | Select-Object TABLE_NAME,VIEW_DEFINITION | ConvertTo-Json | Set-Content "$Out\views.json" -Encoding UTF8
      Get-Schema $c $G::Procedures | Select-Object PROCEDURE_NAME,PROCEDURE_DEFINITION | ConvertTo-Json | Set-Content "$Out\procedures.json" -Encoding UTF8
      "Schema written to $Out"
    }
    'RowCounts' {
      New-Item -ItemType Directory -Force $Out | Out-Null
      $t = Get-Schema $c $G::Tables | Where-Object TABLE_TYPE -eq 'TABLE'
      $r = foreach ($x in $t) {
        $n = $x.TABLE_NAME
        try { $cmd = $c.CreateCommand(); $cmd.CommandText = "SELECT COUNT(*) FROM [$n]"; [pscustomobject]@{ T = $n; N = [int]$cmd.ExecuteScalar() } }
        catch { [pscustomobject]@{ T = $n; N = -1 } }
      }
      $r | ConvertTo-Json | Set-Content "$Out\rowcounts.json" -Encoding UTF8
      "Row counts written: $(@($r).Count) tables"
    }
  }
} finally { $c.Close() }
