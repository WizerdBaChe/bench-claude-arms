<#
  Batch Rename Studio — headless contract acceptance harness (owned by the lead).

  Runs every case under tests/acceptance/cases/*.json against the built executable
  and checks the fixed contract: exit code, single stdout line, UTF-8 without BOM,
  LF-only newlines, JSON key order, item order/values, summary, determinism, and
  that --plan renamed nothing.

  Usage (PowerShell):
    .\tests\acceptance\run-acceptance.ps1
    .\tests\acceptance\run-acceptance.ps1 -Exe "path\to\BatchRenameStudio.exe"
#>
[CmdletBinding()]
param(
  [string]$Exe = "",
  [string]$WorkRoot = ""
)

$ErrorActionPreference = 'Continue'
$script:Pass = 0
$script:Fail = 0
$script:Failures = @()

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if ($Exe -eq "") {
  $Exe = Join-Path $RepoRoot "src\BatchRenameStudio\bin\Release\net8.0-windows\BatchRenameStudio.exe"
}
if ($WorkRoot -eq "") {
  $WorkRoot = Join-Path $env:TEMP ("brs-acceptance-" + (Get-Random))
}
$CasesDir = Join-Path $PSScriptRoot "cases"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Check([string]$case, [string]$label, [bool]$ok, [string]$detail) {
  if ($ok) {
    $script:Pass++
    Write-Host ("  [PASS] {0}" -f $label)
  } else {
    $script:Fail++
    $script:Failures += ("{0} :: {1} :: {2}" -f $case, $label, $detail)
    Write-Host ("  [FAIL] {0} -- {1}" -f $label, $detail) -ForegroundColor Red
  }
}

function Read-TextUtf8([string]$path) {
  return [System.IO.File]::ReadAllText($path, $Utf8NoBom)
}

function Invoke-Plan([string]$dataDir, [string]$rulesPath, [string]$outPath, [string]$stdoutPath, [string]$stderrPath) {
  $argList = @("--plan", "--dir", $dataDir, "--rules", $rulesPath, "--out", $outPath)
  $p = Start-Process -FilePath $Exe -ArgumentList $argList -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
  return $p.ExitCode
}

if (-not (Test-Path $Exe)) {
  Write-Host "Executable not found: $Exe" -ForegroundColor Red
  Write-Host "Build first:  dotnet build -c Release" -ForegroundColor Yellow
  exit 9
}

Write-Host "Executable : $Exe"
Write-Host "Work root  : $WorkRoot"
Write-Host ""

$caseFiles = Get-ChildItem -Path $CasesDir -Filter "*.json" | Sort-Object Name
if ($caseFiles.Count -eq 0) { Write-Host "No cases found in $CasesDir" -ForegroundColor Red; exit 9 }

foreach ($cf in $caseFiles) {
  $caseId = [System.IO.Path]::GetFileNameWithoutExtension($cf.Name)
  $case = ConvertFrom-Json (Read-TextUtf8 $cf.FullName)
  Write-Host ("=== {0} : {1}" -f $caseId, $case.name) -ForegroundColor Cyan

  $caseRoot = Join-Path $WorkRoot $caseId
  $dataDir  = Join-Path $caseRoot "data"
  New-Item -ItemType Directory -Path $dataDir -Force | Out-Null

  # --- materialise the fixture files -------------------------------------
  foreach ($f in @($case.files)) {
    $fp = Join-Path $dataDir $f.name
    $content = ""
    if ($f.PSObject.Properties.Name -contains 'content' -and $null -ne $f.content) { $content = [string]$f.content }
    [System.IO.File]::WriteAllText($fp, $content, $Utf8NoBom)
  }
  # timestamps in a second pass so writing content cannot clobber them
  foreach ($f in @($case.files)) {
    $fp = Join-Path $dataDir $f.name
    if ($f.PSObject.Properties.Name -contains 'created' -and $f.created) {
      [System.IO.File]::SetCreationTimeUtc($fp, [DateTime]::Parse($f.created, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal))
    }
    if ($f.PSObject.Properties.Name -contains 'modified' -and $f.modified) {
      [System.IO.File]::SetLastWriteTimeUtc($fp, [DateTime]::Parse($f.modified, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal))
    }
  }

  $rulesPath  = Join-Path $caseRoot "rules.json"
  [System.IO.File]::WriteAllText($rulesPath, (ConvertTo-Json $case.rules -Depth 30), $Utf8NoBom)

  $planPath   = Join-Path $caseRoot "plan.json"
  $planPath2  = Join-Path $caseRoot "plan2.json"
  $stdoutPath = Join-Path $caseRoot "stdout.txt"
  $stderrPath = Join-Path $caseRoot "stderr.txt"

  $before = (Get-ChildItem -Path $dataDir -File | Select-Object -ExpandProperty Name | Sort-Object) -join "|"

  # --- run ---------------------------------------------------------------
  $exit = Invoke-Plan $dataDir $rulesPath $planPath $stdoutPath $stderrPath
  $stderrTxt = ""
  if (Test-Path $stderrPath) { $stderrTxt = (Read-TextUtf8 $stderrPath).Trim() }

  Check $caseId "exit code 0" ($exit -eq 0) ("exit=$exit stderr=$stderrTxt")
  if ($exit -ne 0) { continue }
  if (-not (Test-Path $planPath)) { Check $caseId "plan.json written" $false "missing"; continue }
  Check $caseId "plan.json written" $true ""

  # --- stdout: exactly one line, no BOM ----------------------------------
  $outBytes = [System.IO.File]::ReadAllBytes($stdoutPath)
  $outHasBom = ($outBytes.Length -ge 3 -and $outBytes[0] -eq 0xEF -and $outBytes[1] -eq 0xBB -and $outBytes[2] -eq 0xBF)
  Check $caseId "stdout has no BOM" (-not $outHasBom) "leading EF BB BF"
  $outTxt = Read-TextUtf8 $stdoutPath
  $outLines = @($outTxt -split "`r?`n" | Where-Object { $_ -ne "" })
  Check $caseId "stdout is exactly one line" ($outLines.Count -eq 1) ("lines=" + $outLines.Count + " raw='" + ($outTxt -replace "`r","\r" -replace "`n","\n") + "'")
  if ($outLines.Count -eq 1) { Write-Host ("         summary line: " + $outLines[0]) }
  Check $caseId "stderr empty on success" ($stderrTxt -eq "") $stderrTxt

  # --- plan.json bytes ---------------------------------------------------
  $planBytes = [System.IO.File]::ReadAllBytes($planPath)
  $planHasBom = ($planBytes.Length -ge 3 -and $planBytes[0] -eq 0xEF -and $planBytes[1] -eq 0xBB -and $planBytes[2] -eq 0xBF)
  Check $caseId "plan.json has no BOM" (-not $planHasBom) "leading EF BB BF"
  $crCount = 0
  foreach ($b in $planBytes) { if ($b -eq 0x0D) { $crCount++ } }
  Check $caseId "plan.json is LF-only" ($crCount -eq 0) "found $crCount CR bytes"

  $planTxt = Read-TextUtf8 $planPath
  $plan = $null
  try { $plan = ConvertFrom-Json $planTxt } catch { }
  Check $caseId "plan.json parses as JSON" ($null -ne $plan) "parse failed"
  if ($null -eq $plan) { continue }

  Check $caseId "schemaVersion == 1" ([int]$plan.schemaVersion -eq 1) ("got " + $plan.schemaVersion)

  # --- key order ---------------------------------------------------------
  $iSchema  = $planTxt.IndexOf('"schemaVersion"')
  $iItems   = $planTxt.IndexOf('"items"')
  $iSummary = $planTxt.IndexOf('"summary"')
  Check $caseId "root key order schemaVersion<items<summary" ($iSchema -ge 0 -and $iSchema -lt $iItems -and $iItems -lt $iSummary) "$iSchema/$iItems/$iSummary"
  # scope the key-order checks to the relevant slice of the document: searching the
  # whole text would match '"ok"' inside an item's "status" value and misjudge order.
  $summaryTxt = ""
  if ($iSummary -ge 0) { $summaryTxt = $planTxt.Substring($iSummary) }
  $itemsTxt = ""
  if ($iItems -ge 0 -and $iSummary -gt $iItems) { $itemsTxt = $planTxt.Substring($iItems, $iSummary - $iItems) }

  $iTotal = $summaryTxt.IndexOf('"total"'); $iOk = $summaryTxt.IndexOf('"ok"')
  $iColl = $summaryTxt.IndexOf('"collision"'); $iUnch = $summaryTxt.IndexOf('"unchanged"'); $iInv = $summaryTxt.IndexOf('"invalid"')
  Check $caseId "summary key order total<ok<collision<unchanged<invalid" `
    ($iTotal -ge 0 -and $iTotal -lt $iOk -and $iOk -lt $iColl -and $iColl -lt $iUnch -and $iUnch -lt $iInv) `
    "$iTotal/$iOk/$iColl/$iUnch/$iInv"
  if (@($case.expected.items).Count -gt 0) {
    $iOrig = $itemsTxt.IndexOf('"original"'); $iProp = $itemsTxt.IndexOf('"proposed"')
    $iStat = $itemsTxt.IndexOf('"status"');   $iReas = $itemsTxt.IndexOf('"reason"')
    Check $caseId "item key order original<proposed<status<reason" `
      ($iOrig -ge 0 -and $iOrig -lt $iProp -and $iProp -lt $iStat -and $iStat -lt $iReas) `
      "$iOrig/$iProp/$iStat/$iReas"
  }

  # --- items -------------------------------------------------------------
  $expItems = @($case.expected.items)
  $gotItems = @($plan.items)
  Check $caseId "item count" ($gotItems.Count -eq $expItems.Count) ("expected " + $expItems.Count + ", got " + $gotItems.Count)
  if ($gotItems.Count -eq $expItems.Count) {
    for ($i = 0; $i -lt $expItems.Count; $i++) {
      $e = @($expItems[$i])
      $g = $gotItems[$i]
      $okRow = ($g.original -ceq $e[0]) -and ($g.proposed -ceq $e[1]) -and ($g.status -ceq $e[2])
      Check $caseId ("item[$i]") $okRow `
        ("expected [{0} -> {1} : {2}] got [{3} -> {4} : {5}]" -f $e[0], $e[1], $e[2], $g.original, $g.proposed, $g.status)
      $hasReason = $g.PSObject.Properties.Name -contains 'reason'
      Check $caseId ("item[$i] has reason field") $hasReason "missing"
    }
  }

  # --- summary -----------------------------------------------------------
  $es = $case.expected.summary
  $gs = $plan.summary
  $sumOk = ([int]$gs.total -eq [int]$es.total) -and ([int]$gs.ok -eq [int]$es.ok) -and `
           ([int]$gs.collision -eq [int]$es.collision) -and ([int]$gs.unchanged -eq [int]$es.unchanged) -and `
           ([int]$gs.invalid -eq [int]$es.invalid)
  Check $caseId "summary counts" $sumOk `
    ("expected t={0} ok={1} c={2} u={3} i={4}; got t={5} ok={6} c={7} u={8} i={9}" -f `
      $es.total,$es.ok,$es.collision,$es.unchanged,$es.invalid,$gs.total,$gs.ok,$gs.collision,$gs.unchanged,$gs.invalid)

  # --- nothing renamed ---------------------------------------------------
  $after = (Get-ChildItem -Path $dataDir -File | Select-Object -ExpandProperty Name | Sort-Object) -join "|"
  Check $caseId "--plan renamed nothing" ($before -ceq $after) ("before=[$before] after=[$after]")

  # --- determinism -------------------------------------------------------
  $exit2 = Invoke-Plan $dataDir $rulesPath $planPath2 (Join-Path $caseRoot "stdout2.txt") (Join-Path $caseRoot "stderr2.txt")
  if ($exit2 -eq 0 -and (Test-Path $planPath2)) {
    $h1 = (Get-FileHash $planPath  -Algorithm SHA256).Hash
    $h2 = (Get-FileHash $planPath2 -Algorithm SHA256).Hash
    Check $caseId "byte-identical on re-run" ($h1 -eq $h2) "$h1 vs $h2"
  } else {
    Check $caseId "byte-identical on re-run" $false "second run exit=$exit2"
  }
  Write-Host ""
}

# ---------------------------------------------------------------------------
# CLI-level negative checks
# ---------------------------------------------------------------------------
Write-Host "=== CLI-NEG : argument and error handling" -ForegroundColor Cyan
$negRoot = Join-Path $WorkRoot "cli-neg"
$negData = Join-Path $negRoot "data"
New-Item -ItemType Directory -Path $negData -Force | Out-Null
[System.IO.File]::WriteAllText((Join-Path $negData "a.txt"), "x", $Utf8NoBom)
$goodRules = Join-Path $negRoot "rules.json"
[System.IO.File]::WriteAllText($goodRules, '{"applyTo":"name","sort":"name","steps":[]}', $Utf8NoBom)
$badRules = Join-Path $negRoot "bad.json"
[System.IO.File]::WriteAllText($badRules, '{"applyTo":"name","steps":[{"op":"nosuchop"}]}', $Utf8NoBom)
$so = Join-Path $negRoot "o.txt"; $se = Join-Path $negRoot "e.txt"

$e1 = Invoke-Plan (Join-Path $negRoot "does-not-exist") $goodRules (Join-Path $negRoot "p1.json") $so $se
Check "CLI-NEG" "missing --dir exits non-zero" ($e1 -ne 0) "exit=$e1"
Check "CLI-NEG" "missing --dir writes nothing to stdout" ((Read-TextUtf8 $so).Trim() -eq "") (Read-TextUtf8 $so)

$e2 = Invoke-Plan $negData $badRules (Join-Path $negRoot "p2.json") $so $se
Check "CLI-NEG" "unknown op exits non-zero" ($e2 -ne 0) "exit=$e2"

$e3 = Invoke-Plan $negData (Join-Path $negRoot "no-rules.json") (Join-Path $negRoot "p3.json") $so $se
Check "CLI-NEG" "missing rules file exits non-zero" ($e3 -ne 0) "exit=$e3"

$p4 = Join-Path $negRoot "nested\deep\p4.json"
$e4 = Invoke-Plan $negData $goodRules $p4 $so $se
Check "CLI-NEG" "creates missing output directory" (($e4 -eq 0) -and (Test-Path $p4)) "exit=$e4"

# same-shape invocation with '=' argument style
$p5 = Join-Path $negRoot "p5.json"
$pr = Start-Process -FilePath $Exe -ArgumentList @("--plan", "--dir=$negData", "--rules=$goodRules", "--out=$p5") `
      -NoNewWindow -Wait -PassThru -RedirectStandardOutput $so -RedirectStandardError $se
Check "CLI-NEG" "--key=value argument form works" (($pr.ExitCode -eq 0) -and (Test-Path $p5)) ("exit=" + $pr.ExitCode + " stderr=" + (Read-TextUtf8 $se).Trim())

Write-Host ""
Write-Host "==================== RESULT ===================="
Write-Host ("PASS: {0}   FAIL: {1}" -f $script:Pass, $script:Fail)
if ($script:Fail -gt 0) {
  Write-Host ""
  Write-Host "Failures:" -ForegroundColor Red
  foreach ($f in $script:Failures) { Write-Host ("  - " + $f) -ForegroundColor Red }
  exit 1
}
Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
exit 0
