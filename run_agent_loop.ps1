# AURIX AGENT LOOP
# Usage:  .\run_agent_loop.ps1 "add PDF reading support"
#
# What happens:
#   1. Aider reads your code + TASK.md
#   2. Writes a change, commits it to git
#   3. Runs pytest automatically
#   4. If tests FAIL, the failure text goes back to the model
#   5. It revises and retries until green (or tells you it is stuck)

param(
    [Parameter(Mandatory=$true)]
    [string]$Task
)

Write-Host "=== AURIX AGENT LOOP ===" -ForegroundColor Cyan
Write-Host "Task: $Task`n" -ForegroundColor Cyan

# Safety: never run without git. Git is your undo button.
if (-not (Test-Path ".git")) {
    Write-Host "ERROR: not a git repo. Run these first:" -ForegroundColor Red
    Write-Host "  git init"
    Write-Host "  git add ."
    Write-Host "  git commit -m 'baseline'"
    exit 1
}

# Safety: refuse to start with uncommitted work, so /undo always works.
$dirty = git status --porcelain
if ($dirty) {
    Write-Host "You have uncommitted changes. Commit them first:" -ForegroundColor Yellow
    Write-Host "  git add . ; git commit -m 'wip'"
    exit 1
}

# Baseline: tests must be green BEFORE the agent starts.
Write-Host "Checking baseline tests..." -ForegroundColor Yellow
python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests already failing. Fix these before running the agent." -ForegroundColor Red
    exit 1
}
Write-Host "Baseline green.`n" -ForegroundColor Green

aider `
    --model gemini/gemini-2.5-flash `
    --auto-test `
    --test-cmd "python -m pytest -q" `
    --auto-commit `
    --yes-always `
    --read TASK.md `
    --file aurix_core.py `
    --file test_aurix_core.py `
    --message "$Task. Follow the rules in TASK.md. Add tests for any new behavior."

Write-Host "`n=== LOOP FINISHED ===" -ForegroundColor Cyan
Write-Host "Review what changed:  git log --oneline -5" -ForegroundColor Cyan
Write-Host "Undo if bad:          git reset --hard HEAD~1" -ForegroundColor Cyan
