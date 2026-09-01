[CmdletBinding()]
param(
    [string]$Python = "D:\Anaconda\envs\gui-agent\python.exe",
    [string]$Config = "configs\agent-v2.example.toml",
    [int]$StartDelay = 0,
    [switch]$SkipUnit,
    [switch]$CaptureScreen,
    [switch]$ExecuteDesktop,
    [switch]$ModelPreview,
    [switch]$BrowsePages,
    [ValidateRange(2, 3)][int]$PageCount = 3,
    [ValidateRange(5, 120)][int]$PageDelay = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONIOENCODING = "utf-8"
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new()

if (-not (Test-Path -LiteralPath $Python)) { throw "Python 不存在: $Python" }
if (-not (Test-Path -LiteralPath $Config)) { throw "配置不存在: $Config" }
if ($StartDelay -lt 0) { throw "等待时间不能为负数" }

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutputDir = Join-Path $Root "old\artifacts\demo-tests\$Stamp"
$TempDir = Join-Path $OutputDir "pytest-tmp"
$AcceptanceDir = Join-Path $OutputDir "acceptance"
$ModelRunName = "demo-preview-$Stamp"
$Results = [System.Collections.Generic.List[object]]::new()
New-Item -ItemType Directory -Force $OutputDir | Out-Null

function Invoke-PythonCommand {
    param([Parameter(Mandatory)][string[]]$CommandArgs)
    & $Python @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "命令失败: $Python $($CommandArgs -join ' ')"
    }
}

function Invoke-Phase {
    param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][scriptblock]$Action)
    $Started = Get-Date
    Write-Host ""
    Write-Host "[$Name] 开始" -ForegroundColor Cyan
    try {
        & $Action
        $Results.Add([pscustomobject]@{ name=$Name; status="passed"; started_at=$Started.ToString("o"); finished_at=(Get-Date).ToString("o") }) | Out-Null
        Write-Host "[$Name] 通过" -ForegroundColor Green
    }
    catch {
        $Results.Add([pscustomobject]@{ name=$Name; status="failed"; started_at=$Started.ToString("o"); finished_at=(Get-Date).ToString("o"); error=$_.Exception.Message }) | Out-Null
        throw
    }
}

$Failed = $false
try {
    if (-not $SkipUnit) {
        Invoke-Phase "自动化测试" {
            New-Item -ItemType Directory -Force $TempDir | Out-Null
            Invoke-PythonCommand @("-m", "pytest", "-q", "old\tests", "--basetemp=$TempDir", "-p", "no:cacheprovider")
        }
        Invoke-Phase "静态检查" {
            Invoke-PythonCommand @("-m", "ruff", "check", "--no-cache", "src", "old\tests")
        }
    }

    Invoke-Phase "动作预览" {
        Invoke-PythonCommand @("-m", "gui_agent.runtime.acceptance", "--task", "open-browser")
    }

    if ($CaptureScreen) {
        Invoke-Phase "真实感知" {
            Invoke-PythonCommand @("-m", "gui_agent.cli", "inspect", "--output", (Join-Path $OutputDir "perception.png"))
        }
    }

    if ($ExecuteDesktop) {
        $Query = (Read-Host "请输入要在 Google 搜索的内容").Trim()
        if ([string]::IsNullOrWhiteSpace($Query)) {
            throw "搜索内容不能为空"
        }
        Write-Host "Agent 将自动打开 Edge 并执行搜索" -ForegroundColor Yellow
        Invoke-Phase "真实搜索内容" {
            $searchArgs = @(
                "-m", "gui_agent.runtime.acceptance", "--task", "search-content",
                "--query", $Query, "--execute", "--yes", "--start-delay", "$StartDelay",
                "--artifact-dir", $AcceptanceDir
            )
            if ($BrowsePages) {
                $searchArgs += @(
                    "--browse-pages", "--page-count", "$PageCount", "--page-wait", "$PageDelay"
                )
            }
            Invoke-PythonCommand $searchArgs
        }

    }

    if ($ModelPreview) {
        Invoke-Phase "模型预览" {
            Invoke-PythonCommand @("-m", "gui_agent.runtime.cli", "--config", $Config, "--goal", "识别当前桌面中的主要界面元素，并给出一个安全的下一步操作", "--run-name", $ModelRunName)
        }
    }
}
catch {
    $Failed = $true
    [Console]::Error.WriteLine($_.Exception.Message)
}
finally {
    [pscustomobject]@{
        started_at = $Stamp
        output_dir = $OutputDir
        model_artifact_dir = (Join-Path $Root "old\artifacts\runtime-v2\$ModelRunName")
        results = $Results
    } | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $OutputDir "summary.json")
    if (Test-Path -LiteralPath $TempDir) { Remove-Item -LiteralPath $TempDir -Recurse -Force }
    Write-Host "结果目录: $OutputDir"
}
if ($Failed) { exit 1 }
