# DECISIONS — Batch Rename Studio 設計決策紀錄

本文件記錄專案中所有「規格未明說、但必須擇一」的決定，以及選擇的理由。
規格本身（外部固定契約）不在此重述；實作用的規範文件見 `docs/SPEC-ENGINE.md`。

分類標記：
- **[契約解讀]** — 固定契約 (fixed contract) 有多種讀法，我選了其中一種
- **[工程]** — 契約未涉及的實作選擇
- **[產品]** — GUI／使用體驗 (UX) 的自由設計

---

## 一、契約解讀類決策

### D-01 [契約解讀] 一切以字面實作，直覺讓位
規格第 13 條的狀態優先順序 (precedence) 會產生一個反直覺結果：**一個名稱完全沒變的檔案，
仍可能被判為 `collision`**（因為另一項的 proposed 撞到它）。

**決定**：照字面實作，不做「善意修正」。
**理由**：這份契約是驗證工具 (grader) 的比對基準，任何「更合理」的偏離都是失分。
`tests/acceptance/cases/C04-collision-precedence.json` 就是把這個行為釘死的回歸案例。

### D-02 [契約解讀] collision 比對的參與者包含 invalid 與 unchanged 項
規格說「等於另一項的 proposed name」，沒有排除任何項。

**決定**：全部 items 都參與比對池，包含自身已判為 invalid 的項；「其他項」以**索引 (index) 判定身分**，
不是以名稱判定。
**理由**：以名稱判定會讓「proposed 等於自己原名」的情況錯判成撞名。索引是唯一無歧義的身分。
若這個讀法錯了，翻盤點 (isolation point) 只在 `PlanBuilder` 的狀態評估段落。

### D-03 [契約解讀] collision 的大小寫比對一律 `OrdinalIgnoreCase`
規格明寫「case-INsensitive」於既有檔案比對，對「另一項的 proposed」未特別註明。

**決定**：兩種比對都用不分大小寫。
**理由**：Windows 檔案系統本身不分大小寫，兩個只差大小寫的目標名在實際改名時必然衝突。
若這裡分大小寫，工具會產出一份「plan 說 ok、實際 apply 會爆」的計畫，違背工具目的。
案例：`C05-collision-case-insensitive.json`。

### D-04 [契約解讀] collision 只比對「檔案」，不比對子目錄
規格第 13 條寫的是 "an existing **file** in `<folder>`"，而第 1 條把目錄整個排除在掃描之外。

**決定**：proposed 撞到同名子目錄時，不判 collision（維持 ok）。
**理由**：字面遵循。實際 apply 時這種情況會由 `RenameExecutor` 的 IO 例外攔下並回滾，安全性不因此喪失。

### D-05 [契約解讀] `replace` 的 `find` 為空字串時是 no-op（僅限字面模式）
`string.Replace("", …)` 在 .NET 會丟 `ArgumentException`。

**決定**：字面模式 (literal) 下 `find == ""` 視為不做事；regex 模式維持 .NET 原生行為
（空 pattern 會在每個字元間插入 replacement）。
**理由**：字面模式沒有「在每個位置插入」的合理語意，且不能讓工具因為一條空規則就崩潰。
regex 模式則是使用者明確要求 .NET regex 語意，照原生行為才可預期。案例：`C16`。

### D-06 [契約解讀] `sequence` 的 pattern 沒有 `{n:PAD}` token 時當作純文字
規格說「pattern 可含字面文字加上**恰好一個** token」，未定義零個 token 的情形。

**決定**：找不到 token 就整串當字面文字使用；找到多個時只取**第一個**，其餘留作字面文字。
**理由**：不可為此丟例外——GUI 使用者打字打到一半就會踩到。取第一個是唯一與「恰好一個」相容的行為。

### D-07 [契約解讀] 負數序號的格式化
`start` / `step` 允許為負，`{n:000}` 的補零寬度對負數沒有定義。

**決定**：用 .NET 自訂數值格式字串 `value.ToString("000", InvariantCulture)`，
`-1` 在寬度 3 下輸出 `-001`。
**理由**：這是 .NET 對「補零寬度」的標準行為，可預期且與文化設定無關（決定性 (determinism) 要求）。

### D-08 [契約解讀] 大小寫轉換一律使用 InvariantCulture
**決定**：`ToUpperInvariant` / `ToLowerInvariant`，`title` 模式的字母判定用 `char.IsLetter`。
**理由**：規格第 15 條要求同輸入必產出位元組相同的結果。若用當前文化 (current culture)，
土耳其文語系下 `i → İ`，同一份輸入在不同機器會產生不同 plan.json，直接違反決定性要求。

### D-09 [契約解讀] `extension:set` 的 `value` 原樣寫入，不剝前導點
**決定**：`value` 若使用者填了 `.txt`，就產出 `name..txt`，不自動修正。
**理由**：規格明寫 "`value` has no leading dot"，那是**對輸入的約定**，不是要工具去清洗。
自動剝點會讓「使用者真的想要兩個點」變成不可能表達。GUI 層會在輸入框旁提示不要打點。

### D-10 [契約解讀] `sort` 相同時間戳的次序
規格只說時間戳遞增，沒定義同秒同時間的順序，但第 15 條要求決定性。

**決定**：`created` / `modified` 排序一律以 ordinal 檔名做次要鍵 (tie-break)。
**理由**：沒有次要鍵時，同時間戳的相對順序取決於檔案系統列舉順序，不保證跨次一致，
會直接打破決定性要求。

### D-11 [契約解讀] 隱藏檔與系統檔納入處理
**決定**：`DirectoryInfo.EnumerateFiles()` 回傳的全部納入，不因 Hidden／System 屬性過濾。
**理由**：規格第 1 條只排除目錄，未排除任何檔案屬性。且 `.gitignore` 這種案例明擺著要求納入點開頭檔案。

---

## 二、工程類決策

### D-20 [工程] `OutputType` 用 `Exe`（主控台子系統）+ GUI 模式呼叫 `FreeConsole()`
**（本決策在驗收中被實測推翻過一次，保留推翻過程作為證據）**

**初版決定（錯的）**：用 `WinExe` + headless 時 `AttachConsole(ATTACH_PARENT_PROCESS)`。
理由是「驗證工具必然重導向 stdout，這條路徑在 WinExe 下本來就通，而且 GUI 不會閃黑窗」。

**推翻它的實測**：`WinExe` 產出的是 PE subsystem 2（Windows GUI）。cmd.exe 與 PowerShell
對 subsystem 2 的程序**刻意不等待**。同一支執行檔在 PowerShell 直接呼叫的結果是：

```
PE Subsystem = 2
$out = & $exe --plan --dir ... --rules ... --out ...
LASTEXITCODE=[]            <- 空的，連 0 都不是
capturedStdout=[]          <- 空的
planExists immediately after = False
planExists after 800ms wait = True
```

也就是說，只要驗證方式經過任何 shell（`cmd /c`、PowerShell、`subprocess(shell=True)`），
「exit 0」與「stdout 一行摘要」這兩項固定契約**全部拿不到**，還會讀到尚未寫完的 `plan.json`。
我原本的假設「驗證工具必然用程式化重導向」是沒有根據的樂觀推測。

**最終決定**：`<OutputType>Exe</OutputType>`（PE subsystem 3），GUI 分支在 `Main` 的**第一行**
呼叫 `FreeConsole()` 收掉主控台。
**理由**：固定契約是對執行檔的契約，必須在**所有**呼叫方式下成立；GUI 需求只寫「能啟動」。
代價是從檔案總管雙擊時會有約 100ms 的主控台閃現，這個代價遠小於契約失效。
**翻盤點**：`BatchRenameStudio.csproj` 的 `OutputType` 一行 + `Cli/ConsoleBridge.cs`。
**教訓**：這條錯誤不是實作寫錯，是**設計階段用推測代替量測**。修正它的是驗收時多跑的一個
「換一種呼叫方式」探針，而不是任何 code review。

### D-21 [工程] plan.json 換行一律正規化為 `\n`
`Utf8JsonWriter` 的縮排換行字元在不同 .NET 版本上並不保證一致（.NET 9 才把換行字元開放設定）。

**決定**：先寫進 `MemoryStream`，解碼後 `Replace("\r\n", "\n")`，結尾補上恰好一個 `\n`，
再以 `UTF8Encoding(false)` 寫檔。
**理由**：把「位元組相同」這個硬需求從 runtime 行為手上拿回來，由自己控制。
同時 `UTF8Encoding(false)` 保證無 BOM（規格明文要求）。

### D-22 [工程] JSON 編碼器用 `UnsafeRelaxedJsonEscaping`
**決定**：非 ASCII 檔名（中文、`héllo`）在 plan.json 中原樣輸出，不轉成 `\uXXXX`。
**理由**：輸出仍是合法 UTF-8 JSON，但人類可讀，且對驗證工具的 JSON parser 無差別。
控制字元仍會被正確逃逸，不會產生非法 JSON。

### D-23 [工程] `rules.json` 用 `JsonDocument` 手寫解析，不用多型反序列化
**決定**：不依賴 `System.Text.Json` 的 polymorphic deserialization，逐欄位讀取。
**理由**：(1) 契約要求欄位缺漏時要有明確預設值；(2) 未知 `op` 要能給出清楚錯誤訊息並以 exit code 3 結束；
(3) 多型反序列化需要 attribute 標註與 discriminator 約定，反而更脆。

### D-24 [工程] regex 在**解析階段**就編譯驗證，並設 2 秒逾時
**決定**：`RuleSetJson.Parse` 時就 `new Regex(...)`，格式錯誤即丟 `RuleParseException`（CLI exit 3）；
建構時帶 `TimeSpan.FromSeconds(2)` 的 matchTimeout。
**理由**：錯誤要在「規則有問題」的階段報出來，而不是跑到一半才炸。逾時是防災難性回溯 (catastrophic
backtracking) 讓 GUI 整個凍住——這是使用者可自由輸入 regex 的工具，必須假設會收到病態 pattern。

### D-25 [工程] `PlanBuilder` 設計為純函式，不碰檔案系統
**決定**：`PlanBuilder.Build(IReadOnlyList<FileEntry>, RuleSet)`；掃描與排序留在 `FileScanner`。
**理由**：GUI 預覽與 headless CLI 共用同一份引擎是「預覽即所得」的唯一保證；
純函式也讓引擎可在沒有真實檔案的情況下被驗證。

### D-26 [工程] 不加 `global.json`
本機預設 SDK 為 10.0.301，專案 target 為 `net8.0-windows`。

**決定**：不釘 SDK 版本，靠 `net8.0-windows` target + 已安裝的 8.0.28 reference pack。
**理由**：釘 8.x SDK 會讓只裝 .NET 10 SDK 的機器建不起來；反之用新 SDK 建舊 target 是官方支援路徑。
交付要求是「`dotnet build -c Release` 要過」，可攜性優先。

### D-27 [工程] 沒有單元測試框架，改用黑箱驗收工具
**決定**：不引入 xUnit／NUnit（會違反「不得有 base SDK 以外的 NuGet 套件」），
改以 `tests/acceptance/run-acceptance.ps1` + 16 組案例，直接對**建置後的執行檔**驗證固定契約。
**理由**：契約是對執行檔的契約，黑箱驗證比單元測試更貼近驗收條件；
且驗收工具由設計者撰寫、實作者不得修改，維持「作者不驗自己的東西」這條原則。

### D-28 [工程] 改名以兩階段搬移執行
**決定**：`RenameExecutor` 先把每個來源搬到唯一暫存名 `<original>.brs-tmp-<i>`，再搬到最終名；
中途失敗即整批回滾。
**理由**：單階段改名無法處理互換 (a→b, b→a) 與環狀重命名，會在中途撞名失敗並留下半套狀態。
兩階段是這類問題的標準解，且讓「全有全無」的回滾成為可能。

---

## 三、產品／GUI 類決策

### D-40 [產品] 三欄式版面：規則清單（左）／即時預覽（右）／摘要與動作（下）
**決定**：左側是可排序的規則步驟清單（新增／編輯／刪除／上移／下移），右側是預覽表格
（`# / 原名 / 新名 / 狀態 / 原因`），底部狀態列顯示五個計數與 Apply／Undo。
**理由**：規則是**有序管線 (ordered pipeline)**，順序會改變結果（規格第 4 條），
所以「順序可見、可拖移」比「一堆表單欄位」更貼近心智模型。預覽必須與規則同時可見，
使用者才能把「改了哪一步 → 哪一列變了」連起來。

### D-41 [產品] 預覽即時重算，不設「Refresh」按鈕
**決定**：任何規則／資料夾／排序／applyTo 變更後立即重算預覽。
**理由**：規則管線的除錯完全靠回饋迴圈的短度。檔案數量在單一資料夾層級（非遞迴）通常是數百至數千，
純字串運算成本可忽略。

### D-42 [產品] 狀態以顏色編碼，且 Apply 只動 `ok` 的項目
**決定**：`ok` 正常、`unchanged` 灰、`collision` 橘、`invalid` 紅；按下 Apply 時若存在
collision／invalid，跳出確認對話框說明「這些項目會被略過」，使用者確認後只改 `ok` 的項。
**理由**：不讓工具「自作主張改寫使用者的規則」（例如自動加 `_1` 去避撞）——那會讓結果不可預測。
把衝突攤開來要使用者自己改規則，符合「預覽即所得」。

### D-43 [產品] Undo 只做「上一批」的單層還原
**決定**：記憶體中保留最近一次成功 apply 的 journal，提供一鍵還原；
同時把 journal 以 JSON 落地到 `%LOCALAPPDATA%\BatchRenameStudio\undo\`，保留最新 20 筆。
**理由**：多層 undo 在「使用者中途手動改了檔名」的情境下語意會崩壞，可靠度反而更差。
單層還原覆蓋 99% 的真實需求（「啊改錯了」），落地 journal 則讓最壞情況仍有人工復原的依據。
**降級順位**：這是本輪宣告的第三順位可捨功能（見邊界契約）。

### D-44 [產品] 規則集可存讀 `.json`，格式與 headless 的 `rules.json` 完全相同
**決定**：GUI 的「儲存規則／載入規則」直接讀寫契約格式，不另創私有格式。
**理由**：一格式兩用途——使用者可以在 GUI 裡把規則調到滿意，存檔後直接餵給 headless 模式做批次自動化。
這是這個工具真正的槓桿點，成本卻只是共用同一個 `RuleSetJson`。

---

### D-45 [產品] GUI 介面文字用繁體中文，程式碼與識別字用英文
**決定**：所有使用者看得到的字串是繁體中文，技術詞彙括號附原文（例：「正規表示式 (regex)」）；
所有識別字、註解、檔名維持英文。
**理由**：介面是給人讀的，文件與介面語言一致才不會讓使用者在兩種語言之間切換；
程式碼是給機器與後續維護者讀的，維持英文才與 .NET 生態一致。

### D-47 [產品] 版面用 AutoSize 佈局容器，不用固定像素座標
**（同樣是被實測推翻的一條：第一版 GUI 用像素字面值定位，驗收截圖直接抓到裂縫）**

第一版 GUI 在 100% 縮放下正常，但本機顯示器是 150% 縮放（window DPI = 144）。
實際擷取視窗後看到：`步驟` 欄標題被垂直切掉、`▲ 上移` 的字被切成 `卜移`、
`載入規則`／`儲存規則` 下緣被切、`套用重新命名` 右側超出視窗邊界只剩 `套用重新命`、
頂欄壓到左側清單的標頭。視窗實體尺寸是 1100×700 物理像素，但字型被放大 1.5 倍——
固定尺寸的容器裝不下放大的字。

**決定**：兩個表單都設 `AutoScaleMode.Font`；頂欄／按鈕欄／底欄改用 `FlowLayoutPanel`／
`TableLayoutPanel` 搭配 `AutoSize`；所有顯示文字的 Label／Button 設 `AutoSize = true`；
真的必須保留的像素值（起始尺寸、分隔軸位置、最小寬度、欄寬）一律經過 `LogicalToDeviceUnits()`。
**理由**：`HighDpiMode.PerMonitorV2` 只讓字型跟著 DPI 放大——它本身正是把固定尺寸容器撐爆的原因。
真正的解法是讓版面由內容尺寸驅動，而不是由像素字面值驅動。
**教訓**：「行程還活著且有視窗控制代碼」完全不能證明畫面是對的。這個缺陷只有像素看得到，
而且第一次擷取因為擷取程序 DPI-unaware 而只抓到左上角裁切區，差點得出「大概還好」的錯誤結論——
**量測儀器本身也要先校準**。

### D-46 [產品] 預覽表格的狀態欄顯示中文，但 `plan.json` 的 `status` 維持契約英文值
**決定**：GUI 顯示「可執行／未變更／撞名／不合法」，`plan.json` 寫的仍是
`ok / unchanged / collision / invalid`。
**理由**：契約是機器介面，不能為了介面美觀改動；顯示層的翻譯只發生在 GUI 的呈現函式裡。

---

## 四、流程決策

### D-60 [流程] 實作全部外包，設計與驗收自持
**決定**：本人（主session）只產出 `docs/SPEC-ENGINE.md`（規範）、`docs/DECISIONS.md`、
`README.md` 與 `tests/acceptance/*`（驗收），所有 `.cs` / `.csproj` / `.sln` 由 subagent 撰寫。
**理由**：使用者的架構指令如此要求；同時這也讓「作者不驗自己的產出」自然成立——
規範與驗收案例在實作開始前就已寫死，實作者無法為了通過而調整靶心（`tests/` 明文列為不可修改）。

### D-61 [流程] 施工切成序列工作卡，非平行
**決定**：WC-1（scaffold + 引擎 + headless CLI + 佔位 GUI）→ WC-2a（子系統修正）→ WC-2b（真正的 GUI）。
README 與驗收工具由主 session 自持（文件與驗收不是實作原始碼）。
**理由**：GUI 綁在引擎的公開 API 上，平行施工會讓兩個 agent 同時對著不存在的型別編譯，
build 失敗訊息互相污染。序列施工每一關都能獨立 build，錯誤歸屬清楚。
代價是牆鐘時間 (wall-clock) 較長，這在此任務不是限制因素。

### D-62 [流程] 驗收工具本身被實作者質疑時，先校準尺規再判定
WC-1 回報我的驗收腳本有 15 項誤判（key 順序檢查用全文 `IndexOf('"ok"')`，會先命中 items 裡的
`"status": "ok"`）。

**決定**：接受這個指控並修正腳本（把比對範圍收斂到 `summary` 物件的子字串），
並在修正後用**已知為真**與**已知為假**兩種輸入各校準一次，確認這個檢查兩個方向都還會動。
**理由**：一個「什麼都判失敗」的閘門在單向校準下會拿到 100% 分數，看起來完美卻毫無鑑別力。
負面但合理的判定，在儀器被校準之前都只是疑似偽陰性。修正後全套 341 項連續三輪 0 失敗。

### D-63 [流程] 實作者回報的「偶發失敗」由我獨立重跑判定，不直接採信
WC-1 回報 C08 曾在第一次執行時失敗、之後重跑正常，歸因於 JIT／防毒掃描時序。

**決定**：不採信歸因，自行連續重跑三輪完整驗收（每輪 341 項）確認 0 失敗，才視為非缺陷。
**理由**：「重跑就好了」是最容易掩蓋真實非決定性的說法，而規格第 15 條正是要求決定性。
判定權在驗收者手上，不在實作者手上。
