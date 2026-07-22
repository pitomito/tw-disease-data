<#
.SYNOPSIS
  本機資料刷新:擷取最新疾管署資料 → 若快照有變更則 commit + push。
  推上去後 GitHub Actions 會自動重建倉儲並重新部署 Pages。

  在「有台灣網路」的機器上執行(疾管署主機封鎖雲端 IP,GitHub Actions 抓不到)。
  可掛到 Windows 工作排程器每週跑一次(見 DEPLOY.md)。

.EXAMPLE
  pwsh -File scripts/refresh_local.ps1
#>
$ErrorActionPreference = "Stop"

# 切到 repo 根目錄(此腳本位於 <root>/scripts/)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== 擷取最新資料 =="
python src/extract_raw.py
if ($LASTEXITCODE -ne 0) { throw "extract_raw.py 失敗(exit $LASTEXITCODE)" }

# 只看 data/snapshot 是否有變(raw 時間戳歷史是本機、不進版控)
$changed = git status --porcelain -- data/snapshot
if ([string]::IsNullOrWhiteSpace($changed)) {
    Write-Host "快照無變更,略過 commit。"
    exit 0
}

Write-Host "== 快照有更新,commit + push =="
$stamp = Get-Date -Format "yyyy-MM-dd"
git add data/snapshot
git commit -m "data: 更新資料快照 $stamp"
git push
Write-Host "完成 —— GitHub Actions 將自動重建並部署。"
