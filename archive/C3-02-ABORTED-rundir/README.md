# Batch Rename Studio

Windows 桌面批次改檔名工具。核心想法只有一句：**改名規則是一條有順序的管線 (ordered pipeline)，
而使用者在按下執行之前，必須先看到每一個檔案會變成什麼、哪些會出事。**

同一套引擎有兩種用法：

- **GUI** — 疊規則、即時預覽、著色標示衝突、一鍵套用、一鍵復原
- **Headless 規劃模式 (`--plan`)** — 不改任何檔案，只把「打算怎麼改」寫成 `plan.json`，
  供腳本、CI 或人工審查使用

兩者共用同一個 `PlanBuilder`，所以 GUI 看到的預覽與 headless 產出的計畫**保證一致**。

---

## 1. 環境需求

| 項目 | 版本 |
|---|---|
| 作業系統 | Windows 10 / 11 |
| .NET SDK | 8.0 以上（目標框架 `net8.0-windows`；用 .NET 10 SDK 建置亦可） |
| 外部套件 | **無**。只用 base SDK，沒有任何 NuGet 相依 |

## 2. 建置

```powershell
cd D:\BenchRuns\C3-02
dotnet build -c Release
```

產出：

```
src\BatchRenameStudio\bin\Release\net8.0-windows\BatchRenameStudio.exe
```

> 注意：專案刻意使用 `<OutputType>Exe</OutputType>`（主控台子系統 (console subsystem)）而非
> `WinExe`。原因見 `docs/DECISIONS.md` D-20：`WinExe` 產出的是 PE subsystem 2，
> cmd.exe 與 PowerShell 對這種程序**不會等待、不會回傳 exit code、也收不到 stdout**，
> 那會讓 headless 契約在任何 shell 呼叫下失效。GUI 模式改用 `FreeConsole()` 收掉主控台視窗。

## 3. 執行 GUI

```powershell
.\src\BatchRenameStudio\bin\Release\net8.0-windows\BatchRenameStudio.exe
```

不帶任何參數就會開 GUI。操作流程：

1. 「瀏覽…」選一個資料夾（**不遞迴**，只處理該層的檔案）
2. 左側「規則步驟」按「新增 ▾」疊規則；順序可用 ▲▼ 調整，**順序會改變結果**
3. 右側「預覽」即時更新，用底色標示狀態
4. 確認無誤後按「套用重新命名」；只有狀態為「可執行」的項目會被改名
5. 改錯了按「復原上一批」

規則集可用「儲存規則…」存成 `.json`，格式與 headless 的 `rules.json` **完全相同**，
可以直接拿去做批次自動化。

### 預覽狀態的意思

| 狀態 | 底色 | 意思 |
|---|---|---|
| 可執行 (ok) | 無 | 會被改名 |
| 未變更 (unchanged) | 灰 | 新名字與原名完全相同，不動它 |
| 撞名 (collision) | 琥珀 | 目標名稱與其他項目或現有檔案重複（**不分大小寫**），會被跳過 |
| 不合法 (invalid) | 淡紅 | 名稱為空／超過 255 字元／含 `< > : " / \ | ? *` 或控制字元／是 Windows 保留裝置名，會被跳過 |

工具**不會**自作主張幫你加 `_1` 去避開撞名——衝突攤開來由你改規則，結果才可預測。

## 4. Headless 規劃模式

```powershell
BatchRenameStudio.exe --plan --dir <folder> --rules <rules.json> --out <plan.json>
```

- 成功時 **exit code 0**，stdout **只有一行**摘要，例如
  `total=12 ok=9 collision=1 unchanged=1 invalid=1`
- `plan.json` 以 **UTF-8 無 BOM**、LF 換行寫出
- **完全不會改動任何檔案**，只產生計畫
- 相同輸入必產出**位元組完全相同**的 `plan.json`

其他參數：`--help` / `-h` / `-?` 顯示用法後 exit 0。
`--dir` 與 `--rules` 支援 `--dir <path>` 與 `--dir=<path>` 兩種寫法。

### Exit code

| code | 意義 |
|---|---|
| 0 | 成功 |
| 2 | 參數錯誤，或 `--dir` 不存在／無法讀取 |
| 3 | `rules.json` 不存在、無法讀取，或內容不合法（含 regex 語法錯誤、未知的 `op`） |
| 4 | 寫出 `--out` 失敗 |
| 5 | 其他未預期的例外 |

非 0 的訊息一律寫到 **stderr**，stdout 保持空白。

### `rules.json` 格式

```json
{
  "applyTo": "name",
  "sort": "name",
  "steps": [
    {"op":"replace",  "find":"IMG",  "replaceWith":"photo", "regex":false, "ignoreCase":false},
    {"op":"insert",   "text":"2024-", "position":"prefix", "index":0},
    {"op":"remove",   "from":0, "count":3},
    {"op":"sequence", "pattern":"{n:000}_", "start":1, "step":1, "position":"prefix"},
    {"op":"case",     "mode":"title"},
    {"op":"extension","mode":"lower"}
  ]
}
```

- `applyTo`：`name`（只動主檔名）或 `nameAndExtension`（連副檔名一起動）
- `sort`：`name`（**ordinal 遞增，區分大小寫**）／`created`／`modified`
- `steps` 依陣列順序套用，每一步都吃上一步的結果
- `extension` 這一步**永遠**作用在副檔名上，與 `applyTo` 無關
- `sequence` 的 `{n:PAD}` 中 `PAD` 是補零寬度（`{n:000}` → 寬度 3）；
  計數器**每個檔案都前進一格**，不管那個檔案最後是什麼狀態

### `plan.json` 格式

```json
{
  "schemaVersion": 1,
  "items": [
    {"original":"a.txt","proposed":"001_a.txt","status":"ok","reason":""}
  ],
  "summary": {"total":1,"ok":1,"collision":0,"unchanged":0,"invalid":0}
}
```

`items` 的順序就是處理順序（由 `sort` 決定）。完整語意見 `docs/SPEC-ENGINE.md`。

### 使用範例

```powershell
$exe = ".\src\BatchRenameStudio\bin\Release\net8.0-windows\BatchRenameStudio.exe"
& $exe --plan --dir "D:\photos" --rules ".\rules.json" --out ".\plan.json"
if ($LASTEXITCODE -ne 0) { throw "planning failed with exit code $LASTEXITCODE" }
(Get-Content .\plan.json -Raw | ConvertFrom-Json).summary
```

## 5. 專案結構

```
BatchRenameStudio.sln
src/BatchRenameStudio/
  Program.cs              進入點：有 --plan 走 headless，無參數開 GUI
  Cli/                    命令列解析、主控台輸出橋接、headless 執行
  Core/                   引擎：規則模型、JSON 解析、名稱切分、計畫建構、驗證、輸出
  Rename/                 兩階段改名執行器與復原日誌 (journal)
  Gui/                    WinForms 介面
docs/
  SPEC-ENGINE.md          規範文件（實作者的唯一真相來源）
  DECISIONS.md            所有設計決策與理由
tests/acceptance/
  run-acceptance.ps1      黑箱驗收工具
  cases/*.json            16 組契約案例
```

`Core/PlanBuilder` 是**純函式**：不碰檔案系統，只吃一份已排序的檔案清單與規則集。
GUI 與 CLI 都走它，這是「預覽即所得」的唯一保證。

## 6. 自動驗收

```powershell
dotnet build -c Release
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\acceptance\run-acceptance.ps1
```

會對**建置後的執行檔**跑 16 組案例、共 341 項檢查，涵蓋：exit code、stdout 只有一行、
無 BOM、LF 換行、JSON key 順序、items 順序與內容、summary 計數、
`--plan` 沒有動到任何檔案、以及重跑的位元組一致性。全過會印 `ALL CHECKS PASSED` 並 exit 0。

案例包含幾個特別容易寫錯的邊界：
`C04` 未變更的檔案仍被判撞名 · `C05` 撞名不分大小寫 · `C08` 255／256 字元邊界 ·
`C13` `created` 與 `modified` 排序互不相干 · `C14` 序號會跳過不合法項繼續前進。

## 7. 手動驗收清單（GUI，需人工執行）

自動化只能證明引擎與契約，**畫面與互動必須由人確認**。請依序執行，每一步都寫著預期看到什麼。
建議先建一個測試資料夾（例如 `D:\brs-uat`），裡面放：
`a.txt`、`B.TXT`、`.gitignore`、`note.md`、`我的檔案.md`、`with space.txt`。

**基本路徑**

1. 直接雙擊 `BatchRenameStudio.exe`。
   → 視窗開啟，**不應該**有黑色主控台視窗殘留（閃一下即消失是正常的）。
2. 按「瀏覽…」選 `D:\brs-uat`。
   → 右側列出全部 6 個檔案，狀態全部是「未變更」（還沒有任何規則）。
3. 「新增 ▾」→ 序號 (sequence)，樣式維持 `{n:000}_`，確定。
   → 預覽立刻更新，`.gitignore` 排第一且變成 `001_.gitignore`（ordinal 排序：`.` 在字母之前）。
4. 再「新增 ▾」→ 大小寫 (case) → 全部小寫，確定。
   → `B.TXT` 那列的新名稱變成 `002_b.TXT`（副檔名沒被動，因為套用範圍是「僅檔名」）。
5. 把「套用範圍」切成「檔名＋副檔名」。
   → 同一列變成 `002_b.txt`。切回去應該還原。
6. 選中「大小寫」那一步，按「▲ 上移」。
   → 預覽跟著變（順序有意義）。再「▼ 下移」應回到原狀。
7. 按「儲存規則…」存成 `rules.json`，「清空」後再「載入規則…」載回來。
   → 步驟清單與預覽都回到儲存當下的樣子。
8. 按「套用重新命名」。
   → 出現確認對話框；按「是」之後，資料夾內檔名確實變了，底部訊息顯示改了幾個。
9. 按「復原上一批」。
   → 全部檔名回到原狀，該按鈕變成不可按。

**壓力與異常路徑（這幾項比上面更重要）**

10. 新增一條「取代 (replace)」，勾選「使用正規表示式」，在「尋找」裡打 `([a-z` （故意不合法）。
    → 錯誤訊息就地顯示，「確定」按鈕變灰，**不會**跳出未處理例外對話框。補上 `)` 後恢復可按。
11. 用 regex 規則輸入一個病態樣式（例如 `(a+)+$`）套在較長的檔名上。
    → 最壞情況是底部出現紅色錯誤訊息且保留上一次的預覽；**視窗不可以凍住或崩潰**。
12. 新增規則讓兩個檔案得到相同的新名稱（例如取代 `a`→`b`）。
    → 兩列都變成琥珀色「撞名」；按「套用」時的確認框要說明會跳過幾個。
13. 新增規則讓某個檔案的新名稱變成 `CON.txt` 或包含 `?`。
    → 該列淡紅「不合法」，且套用時被跳過、其他檔案照樣被改。
14. 在預覽有內容時，直接把資料夾改成一個空資料夾。
    → 顯示「這個資料夾沒有檔案」，不是空白或錯誤。
15. 在「刪除 (remove)」規則裡把「刪除字數」設成 9999。
    → 主檔名被清空；若套用範圍是「檔名＋副檔名」，該列應是「不合法（名稱為空）」。
16. 反覆快速點擊「▲ 上移」「▼ 下移」十幾次，中途切換排序方式。
    → 介面不卡死，預覽最終與規則清單一致。
17. 把視窗拉到最小尺寸再拉到最大，並在 150% 縮放的螢幕上開啟。
    → 版面不重疊、不截斷，分隔軸可拖動。
18. 套用改名的過程中，先用另一個程式（例如記事本）開著其中一個檔案鎖住它。
    → 出現明確的錯誤訊息指出是哪個檔案失敗，且**整批回滾**，資料夾不會停在做一半的狀態。

任何一項不符合預期，請把步驟編號與實際看到的畫面回報。

## 8. 已知限制

- **不遞迴**：只處理指定資料夾當層的檔案，子目錄完全排除（規格如此定義）。
- **復原只有一層**：只能還原最近一次成功的套用。歷史 journal 會保存在
  `%LOCALAPPDATA%\BatchRenameStudio\undo\`（最多 20 筆），最壞情況可據此人工復原。
- **撞名不自動避讓**：見第 3 節說明，這是刻意的設計。
- **`--plan` 不檢查磁碟權限**：計畫階段只做名稱運算，實際權限問題會在套用時才浮現。
