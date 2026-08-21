<#
.SYNOPSIS
  Executes one experiment cell and records everything needed to score it.

.NOTES
  The prompt is piped via STDIN, never passed as an inline argument: PowerShell
  5.1's native-argument encoder does not escape " or [ , and the task prompt
  contains both. An inline pass would truncate it SILENTLY and the run would
  look successful while testing a different prompt.

  Run directories live outside the bench tree so that the held-out validation
  set is not reachable by ordinary exploration from the arm's cwd.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('C1', 'C2', 'C3', 'C4')][string]$Cell,
    [Parameter(Mandatory = $true)][string]$PromptFile,
    [Parameter(Mandatory = $true)][string]$RunId,
    [switch]$Solo,                       # architecture A (enforced by prompt + post-hoc audit)
    # Measured 2026-08-20: adding --disallowedTools Agent,Workflow shrinks the cached
    # prefix by 10,830 tokens (29.8% of T0) on an otherwise identical call. Using it to
    # enforce architecture A would bake that saving into arm A's token count and it would
    # be misread as a benefit of working solo. Default OFF: architecture A is enforced by
    # the prompt directive and verified afterwards via isSidechain (exclusion criterion).
    [switch]$BlockAgentTools,
    # Pinned explicitly on every call: ~/.claude/settings.json defaults to sonnet/medium,
    # so an unflagged run would silently not be the arm it claims to be.
    [ValidateSet('low', 'medium', 'high', 'xhigh', 'max')][string]$Effort = 'high',
    [double]$MaxBudgetUsd = 25.0,        # runaway guard only; not an expected spend
    [string]$RunRoot = 'D:\BenchRuns',
    [string]$ResultRoot = 'results'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $PromptFile)) { throw "prompt file not found: $PromptFile" }

$runDir = Join-Path $RunRoot $RunId
if (Test-Path $runDir) { throw "run dir already exists (runs must be fresh): $runDir" }
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$resDir = Join-Path $ResultRoot $RunId
New-Item -ItemType Directory -Path $resDir -Force | Out-Null

$sessionId = [guid]::NewGuid().ToString()
$promptHash = (Get-FileHash $PromptFile -Algorithm SHA256).Hash

$claudeArgs = @(
    '-p',
    '--model', 'opus',
    '--effort', $Effort,
    '--permission-mode', 'bypassPermissions',
    '--autocompact', 'auto',
    '--session-id', $sessionId,
    '--max-budget-usd', $MaxBudgetUsd,
    '--output-format', 'json'
)
if ($BlockAgentTools) { $claudeArgs += @('--disallowedTools', 'Agent,Workflow') }

$meta = [ordered]@{
    run_id       = $RunId
    cell         = $Cell
    architecture = if ($Solo) { 'A_solo' } else { 'B_delegated' }
    enforcement  = if ($BlockAgentTools) { 'mechanical_disallowedTools' } else { 'prompt_directive_then_audit' }
    channel      = if ($Cell -in @('C1', 'C3')) { 'cli_headless' } else { 'desktop' }
    session_id   = $sessionId
    prompt_file  = (Resolve-Path $PromptFile).Path
    prompt_sha256 = $promptHash
    run_dir      = $runDir
    claude_args  = $claudeArgs -join ' '
    effort       = $Effort
    bg_wait_ceiling_ms = '0 (wait indefinitely for background subagent tasks)'
    started_at   = (Get-Date).ToUniversalTime().ToString('o')
}
$meta | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $resDir 'meta.json') -Encoding utf8

Write-Host "[$RunId] cell=$Cell arch=$($meta.architecture) session=$sessionId"
Write-Host "[$RunId] run dir : $runDir"
Write-Host "[$RunId] prompt  : $promptHash"

# A delegated run parks work in background subagent tasks. Print mode waits only
# 600s for those by default and then TERMINATES the run -- which hit C3-02 while
# never touching any solo run, i.e. a failure mode that biases exactly one arm.
# 0 = wait indefinitely. Set for every arm so the two are configured alike.
$env:CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS = '0'

$sw = [System.Diagnostics.Stopwatch]::StartNew()
Push-Location $runDir
try {
    # No 2>&1 here. Under $ErrorActionPreference='Stop', redirecting a native exe's
    # stderr makes PowerShell 5.1 wrap each stderr line in a NativeCommandError and
    # abort the script even when the exe exits 0 -- that is what killed the batch
    # after C3-02, not the run itself. Let stderr flow to the console and judge the
    # call by $LASTEXITCODE, which is the only reliable signal for a native call.
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $stdout = (Get-Content $PromptFile -Raw) | & claude @claudeArgs | Out-String
    $exit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
}
finally {
    Pop-Location
    $sw.Stop()
}

$stdout | Set-Content (Join-Path $resDir 'cli_result.json') -Encoding utf8

$meta.finished_at = (Get-Date).ToUniversalTime().ToString('o')
$meta.wall_seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1)
$meta.exit_code = $exit
$meta | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $resDir 'meta.json') -Encoding utf8

Write-Host "[$RunId] exit=$exit wall=$($meta.wall_seconds)s"
Write-Host "[$RunId] results : $resDir"
