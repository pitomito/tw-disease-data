# 🚀 上線清單(Go-Live Checklist)

**架構前提**:疾管署主機封鎖雲端 IP,GitHub Actions 抓不到資料。故
**擷取**在有台灣網路的機器執行、提交 `data/snapshot/`;**建置與部署**由 GitHub Actions 從快照完成。

指令以 **Git Bash** 為主;PowerShell 差異處另註。

---

## 0. 前置(一次性)

```bash
gh --version && gh auth status    # 確認已安裝並登入(否則 gh auth login)
```

## 1. 本機先驗證(推之前先確認綠燈)

```bash
cd tw-disease-data
pip install -r requirements.txt
python src/extract_raw.py        # 擷取(需台灣網路)→ 產生 data/snapshot/*.parquet
python src/build_warehouse.py    # 從快照建倉,結尾應印 "ALL QA PASSED"
```

## 2. 初始化 git + 首次 commit

```bash
git init -b main
git add -A
git status               # 確認 data/raw、warehouse.duckdb、exports/ 沒被加入;data/snapshot 有被加入
git commit -m "台灣傳染病資料工程專案:擷取→倉儲→分析→視覺化→自動部署"
```

`data/snapshot/`(約 3.7MB)**要進版控** —— CI 由此建置。`data/raw/`(時間戳歷史)不進。

## 3.（可選)修正 README 徽章帳號

README 徽章預設已填 `pitomito`。若你的 GitHub 帳號不同,用**編碼安全**的方式取代
(⚠️ 別用 PowerShell 5.1 的 `Set-Content` 或非 UTF-8 的 sed —— 會弄壞中文):

```bash
python -c "import pathlib,sys; p=pathlib.Path('README.md'); p.write_text(p.read_text(encoding='utf-8').replace('pitomito/tw-disease-data', sys.argv[1]+'/tw-disease-data'), encoding='utf-8')" YOUR_GH_USER
git commit -am "docs: 更新徽章帳號"
```

## 4. 建立遠端 repo 並 push

```bash
gh repo create tw-disease-data --public --source=. --push --description "台灣疾管署傳染病資料工程管線"
```

push 到 main 會自動觸發 **`ci.yml`**(從快照建倉→QA→匯出)。

## 5. 啟用 GitHub Pages

repo → Settings → Pages → Build and deployment → Source 選 **GitHub Actions**。

## 6. 觸發首次部署

```bash
gh workflow run "refresh-and-deploy.yml"
gh run watch
```

## 7. 驗證上線

```bash
gh run list --limit 5             # ci 與 deploy 應皆 success
echo "Pages 網址:https://pitomito.github.io/tw-disease-data/"
```

---

## 🔁 資料自動更新(本機排程 —— 這是真正的「排程」)

擷取必須在台灣網路端跑,因此把排程掛在你的本機。腳本 [`scripts/refresh_local.ps1`](scripts/refresh_local.ps1)
會擷取 → 若快照有變更則 commit + push → GitHub Actions 自動重建並重新部署。

**手動跑一次:**
```powershell
pwsh -File scripts/refresh_local.ps1
```

**掛 Windows 工作排程器(每週一 08:00):**
```powershell
$repo = "C:\Users\cheng\claude_code\tw-disease-data"
$action  = New-ScheduledTaskAction -Execute "pwsh.exe" `
           -Argument "-File `"$repo\scripts\refresh_local.ps1`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:00am
Register-ScheduledTask -TaskName "tw-disease-data 資料刷新" -Action $action -Trigger $trigger
```

## 疑難排解

| 症狀 | 解法 |
|---|---|
| CI 從快照建倉失敗 | 本機 `python src/build_warehouse.py` 重現;多為 SQL/程式改動,非網路。 |
| Pages 部署失敗 | 確認第 5 步 Source 已選 GitHub Actions。 |
| 徽章顯示 `no status` | 該 workflow 尚未跑過;push 或手動觸發一次即可。 |
| README 中文變亂碼 | 取代徽章時用了非 UTF-8 工具;用第 3 步的 Python 寫法重做。 |
| push 被拒(檔案過大) | 確認 `data/raw`、`*.duckdb` 有被 `.gitignore` 排除(只有 `data/snapshot` 該進版控)。 |
