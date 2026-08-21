<#
.SYNOPSIS
  Assembles one run's complete record: metadata, CLI self-report, transcript
  analysis, held-out score, and the pre-registered exclusion audit.

.NOTES
  The exclusion audit runs BEFORE any number is presented. A run that trips a
  criterion is reported as EXCLUDED with the reason; its numbers are kept in the
  file (so nothing is silently dropped) but must not enter a comparison.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$ResultRoot = 'results',
    [string]$Python = 'python',
    [string]$Bench = (Split-Path -Parent $PSScriptRoot),
    # Live Claude Code session store. NOT part of this repository: collection only
    # runs on the machine that produced the runs.
    [string]$ProjectsDir = (Join-Path $env:USERPROFILE '.claude\projects')
)

$ErrorActionPreference = 'Stop'
$resDir = Join-Path $ResultRoot $RunId
if (-not (Test-Path $resDir)) { throw "no results for run: $RunId" }

$meta = Get-Content (Join-Path $resDir 'meta.json') -Raw | ConvertFrom-Json

# --- CLI self-report (the positive control for the transcript analyzer) ------
$cli = $null
$cliPath = Join-Path $resDir 'cli_result.json'
if (Test-Path $cliPath) {
    try { $cli = Get-Content $cliPath -Raw | ConvertFrom-Json } catch { $cli = $null }
}

# --- transcript analysis, located deterministically by session id ------------
$tr = Get-ChildItem $ProjectsDir -Recurse -Filter "$($meta.session_id).jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1
$analysis = $null
if ($tr) {
    $analysis = & $Python (Join-Path $Bench 'tools\analyze.py') $tr.FullName | ConvertFrom-Json
    Copy-Item $tr.FullName (Join-Path $resDir 'transcript.jsonl') -Force
}

# --- held-out score ----------------------------------------------------------
# Scorer is chosen from the prompt the run was actually given, not from a flag:
# scoring an XL run with the small-contract scorer would report a confident 0 for
# a perfectly good implementation, and the mistake would be invisible in the output.
$isXl = ($meta.prompt_file -match 'TASK_PROMPT_XL')
$scorer = if ($isXl) { 'holdout\score_xl.py' } else { 'holdout\score.py' }
$score = $null
if (Test-Path $meta.run_dir) {
    $score = & $Python (Join-Path $Bench $scorer) $meta.run_dir `
        --out (Join-Path $resDir 'score.json') | ConvertFrom-Json
}

# --- pre-registered exclusion audit (protocol S3.3 + A-2) --------------------
$excl = @()
if ($analysis) {
    $mainModels  = @($analysis.identity_main.models)
    $mainEfforts = @($analysis.identity_main.efforts)
    if ($mainModels.Count -ne 1 -or $mainModels[0] -ne 'claude-opus-5') {
        $excl += "#1 main model=$($mainModels -join ',')"
    }
    # Compare against the effort this run was CONFIGURED with, not a hardcoded 'high':
    # the effort-ablation arm is deliberately medium, and a rule that assumes high would
    # void it for doing exactly what it was told to do.
    $wantEffort = if ($meta.effort) { $meta.effort } else { 'high' }
    if ($mainEfforts.Count -ne 1 -or $mainEfforts[0] -ne $wantEffort) {
        $excl += "#1 main effort=$($mainEfforts -join ',') (expected $wantEffort)"
    }
    if ($analysis.Y2_context.Y2d_compact_markers -gt 0) { $excl += "#autocompact fired ($($analysis.Y2_context.Y2d_compact_markers) markers) - not fatal, flag only" }
    if ($meta.architecture -eq 'A_solo' -and $analysis.Y6_counts.sidechain_requests -gt 0) {
        $excl += "#7 architecture A but sidechain_requests=$($analysis.Y6_counts.sidechain_requests)"
    }
    if ($meta.architecture -eq 'B_delegated' -and $analysis.Y6_counts.sidechain_requests -eq 0) {
        $excl += "#7b architecture B but no subagent activity"
    }
}
$denials = 0
if ($cli) {
    if ($cli.api_error_status)          { $excl += "#2 api_error_status=$($cli.api_error_status)" }
    if ("$($cli.terminal_reason)" -ne 'completed') { $excl += "#4 terminal_reason=$($cli.terminal_reason)" }
    # Criterion #3 as PRE-REGISTERED reads "permission denials that SUBSTANTIVELY
    # INTERRUPT the task". The first implementation excluded on any denial > 0, which
    # is stricter than the registered text. PILOT-C1-03 tripped it with one denial on a
    # self-test command the arm itself wrote, while reaching terminal_reason=completed
    # over 82 turns. Corrected 2026-08-20 AFTER seeing that run, and applied to every
    # run from here on: denials are recorded as a covariate; only an actual failure to
    # complete excludes (that is criterion #4). Deliberately NOT keyed to Y4 -- an
    # exclusion rule that reads the outcome is a biased rule.
    $denials = $cli.permission_denials.Count
}
if ($meta.exit_code -ne 0) { $excl += "#exit_code=$($meta.exit_code)" }

# --- cross-check: analyzer vs CLI self-report -------------------------------
# Sum across EVERY model. A delegated run is mixed-model: this environment's
# model_cap_guard routes subagents to Sonnet, so C3-01 ran Opus main + 1 Opus
# subagent + 4 Sonnet subagents. Comparing an opus-only CLI figure against the
# analyzer's all-model total is not a crosscheck, it is two different quantities.
$crosscheck = 'n/a (no CLI self-report)'
$modelMix = @()
$cliTotal = $null; $cliFresh = $null; $mainFresh = $null; $completeness = $null
if ($cli) {
    $ti = 0; $tw = 0; $tr = 0; $to = 0
    foreach ($p in $cli.modelUsage.PSObject.Properties) {
        $ti += [int]$p.Value.inputTokens
        $tw += [int]$p.Value.cacheCreationInputTokens
        $tr += [int]$p.Value.cacheReadInputTokens
        $to += [int]$p.Value.outputTokens
    }
    $cliTotal = $ti + $tw + $tr + $to
    $cliFresh = $ti + $tw + $to
}
if ($analysis) {
    $mainFresh = $analysis.Y1_tokens.main.input + $analysis.Y1_tokens.main.cache_creation + $analysis.Y1_tokens.main.output
    $transcriptFresh = $analysis.Y1_tokens.total.Y1b_fresh_tokens
    if ($cliFresh -gt 0) {
        $completeness = [math]::Round($transcriptFresh / $cliFresh * 100, 1)
    } else {
        # Desktop arm: no --output-format json, so no self-report to cross-check against.
        # Fall back to the transcript. That is sound ONLY while sidechain_requests = 0,
        # because the main line was verified byte-exact against the CLI on every solo run
        # while subagent transcripts were not. A delegated Desktop run would need a
        # different instrument.
        $cliTotal = $analysis.Y1_tokens.total.Y1a_total_tokens
        $cliFresh = $transcriptFresh
        $completeness = $null
        if ($analysis.Y6_counts.sidechain_requests -gt 0) {
            $excl += "#instrument: desktop arm with subagents has no verifiable token total"
        }
    }
}
if ($cli -and $analysis) {
    $cliOut = 0
    foreach ($p in $cli.modelUsage.PSObject.Properties) {
        $cliOut += [int]$p.Value.outputTokens
        $modelMix += "$($p.Name)=$([int]$p.Value.outputTokens)"
    }
    $anaOut = [int]$analysis.Y1_tokens.total.output
    $delta = $anaOut - $cliOut
    $pct = if ($cliOut -gt 0) { [math]::Round([math]::Abs($delta) / $cliOut * 100, 2) } else { 0 }
    $crosscheck = "cli_output=$cliOut analyzer_output=$anaOut delta=$delta (${pct}%)"
}

$record = [ordered]@{
    run_id      = $RunId
    cell        = $meta.cell
    architecture= $meta.architecture
    enforcement = $meta.enforcement
    channel     = $meta.channel
    excluded    = ($excl.Count -gt 0)
    exclusions  = $excl
    permission_denials = $denials
    crosscheck  = $crosscheck
    # SOURCE OF TRUTH FOR TOKEN TOTALS IS THE CLI, NOT THE TRANSCRIPT.
    # Subagent transcripts are not always flushed completely: on C3-04 the five
    # subagent files summed to 146,326 Sonnet output tokens against the CLI's
    # 180,904 (-19%), while the MAIN line matched exactly (90,742 = 90,742).
    # So: totals come from modelUsage (complete), the main-line split comes from the
    # transcript (verified complete), and the sidechain share is the difference.
    # The transcript is still the only source for context curve, T0 and gaps.
    Y1a_total_tokens   = $cliTotal
    Y1b_fresh_tokens   = $cliFresh
    Y1c_main_fresh     = $mainFresh
    Y1c_side_fresh     = if ($null -ne $cliFresh -and $null -ne $mainFresh) { $cliFresh - $mainFresh } else { $null }
    transcript_completeness_pct = $completeness
    Y1d_thinking       = if ($analysis) { $analysis.Y1_tokens.total.thinking } else { $null }
    Y2a_T0             = if ($analysis) { $analysis.Y2_context.Y2a_T0_baseline } else { $null }
    Y2b_peak_context   = if ($analysis) { $analysis.Y2_context.Y2b_peak_context } else { $null }
    Y2d_compact        = if ($analysis) { $analysis.Y2_context.Y2d_compact_markers } else { $null }
    Y2e_warm_start_cache_read = if ($analysis) { $analysis.Y2_context.Y2e_first_request_cache_read } else { $null }
    Y3a_wall_seconds   = $meta.wall_seconds
    Y3b_api_ms         = if ($cli) { $cli.duration_api_ms } else { $null }
    contract           = if ($isXl) { 'XL' } else { 'small' }
    # XL scores use a 55-point denominator against the small contract's 25.
    # The two are NOT comparable; only compare arms within one contract.
    Y4_score           = if ($score) { if ($isXl) { $score.Y4_xl } else { $score.Y4_score } } else { $null }
    Y4_earned          = if ($score) { $score.Y4_earned } else { $null }
    Y4_total           = if ($score) { $score.Y4_total } else { $null }
    G2_ordered         = if ($score -and -not $isXl) { "$($score.G2.pass_count)/$($score.G2.max)" }
                         elseif ($score) { "$($score.G2_plan_cases.pass_count)/$($score.G2_plan_cases.max)" } else { $null }
    G2_unordered       = if ($score -and -not $isXl) { "$($score.G2.unordered_pass_count)/$($score.G2.unordered_max)" } else { $null }
    G4_trace           = if ($score -and $isXl) { "$($score.G4_trace_cases.pass_count)/$($score.G4_trace_cases.max)" } else { $null }
    Y6_requests        = if ($analysis) { $analysis.Y6_counts.total_requests } else { $null }
    Y6_sidechain_req   = if ($analysis) { $analysis.Y6_counts.sidechain_requests } else { $null }
    # CLI arms: the self-reported figure (authoritative). Desktop arm: derived from the
    # price table, which was validated to 0.00% against that same self-report on every
    # solo CLI run, so the derivation rests on a checked instrument rather than on trust.
    cost_usd           = if ($cli) { $cli.total_cost_usd }
                         elseif ($analysis) { $analysis.Y7_cache_and_pricing.cost_usd_actual }
                         else { $null }
    cost_source        = if ($cli) { 'cli_self_report' } else { 'derived_from_validated_price_table' }
    # PRIMARY METRIC: fresh tokens per unit of verified acceptance.
    # Raw token count alone rewards an arm that gives up early.
    primary_tokens_per_score = if ($analysis -and $score -and $score.Y4_score -gt 0) {
        [math]::Round($analysis.Y1_tokens.total.Y1b_fresh_tokens / $score.Y4_score, 0)
    } else { $null }
}

$record | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $resDir 'record.json') -Encoding utf8
$record | ConvertTo-Json -Depth 6
