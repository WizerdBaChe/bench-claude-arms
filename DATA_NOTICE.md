**文件層級**：T2 衍生登記簿。本檔記錄**這份分享副本相對於原始工作樹被改動了什麼**。
它不含任何研究數值，但任何人要判斷「這份副本的證據還算不算數」，都必須先讀它。

# 資料與去識別化聲明 (Data & de-identification notice)

> **English summary.** This is a de-identified copy of a private working tree.
> The author's Windows account name was replaced with `USER`; the author's
> absolute source-tree path was made repo-relative; 130 transcript records that
> carried files from the author's private agent configuration were emptied; and
> 5 of 31 embedded screenshots were removed because they captured an unrelated
> window or real personal filenames. **No measured value was changed** — proof
> in §4. Everything else is byte-for-byte the original.

原始樹是一台個人 Windows 機器上的私有工作目錄，從未為外流設計。這份副本在
2026-08-21 建立，做了以下四類、且**只有以下四類**改動。

---

## 1. 為什麼需要這份聲明

本專案的第 5 條紀律是「每個數字都要追得到檔案」，第 8 條是「不得在分數發表後
回頭修改評分器」。**去識別化本身就是一次證據改寫**——它跟被禁止的那種改寫只差
在有沒有留下紀錄。所以改動範圍寫成可執行的檢查，而不是寫成一段承諾：

```powershell
python tools\deidentify.py --check
```

該指令檢查數項**資產屬性 (asset properties)**，不是檢查任何人的記憶：

| 屬性 | 內容 | 誰能跑 |
|---|---|---|
| **P1** | 沒有任何 `Users\<名稱>` 形式的路徑殘留，`<名稱>` 一律是佔位符 `USER` | 任何人 |
| **P1x** | 帳號名以裸 token 形式的精確掃描（`ls -l` 擁有者欄位等） | 需 `--account` |
| **P2** | 沒有任何檔案含有作者的絕對來源路徑 | 任何人 |
| **P3** | 沒有任何 `attachment` 紀錄仍帶著來自研究樹**之外**的檔案或清單內容 | 任何人 |
| **P4** | 封鎖清單上的截圖沒有任何一張仍帶著 base64 影像資料 | 任何人 |

**帳號名本身不隨這支腳本出貨**——把它寫進檢查器等於把 P1 剛移除的東西放回去。
腳本只帶著它的 SHA-256；`--account` 傳入的值必須雜湊相符才會被接受，傳錯直接拒跑。
所以第三方跑得動 P1/P2/P3/P4，只有作者跑得動 P1x，而也只有作者需要跑它。

該腳本兩側都校準過：對未處理的原始樹回報 **311 項違規**，對本副本回報 **0 項**。
一個對任何輸入都回報乾淨的檢查器沒有價值，所以已知為真的輸入也一併餵過。

唯一的豁免是**明示的**：`tools/deidentify.py` 自身免受 P2 檢查，因為它必須存著
那個要被移除的前綴；每次執行都會把這條豁免印出來，不會靜默生效。

---

## 2. 四類改動的逐項清單

### 2.1 帳號名（全樹）

作者的 Windows 帳號名一律替換為 `USER`，四種轉義層級（`\`、`\\`、`\\\\`、`/`）
與 `ls -l` 輸出的擁有者欄位皆涵蓋。**替換不套用於 base64 影像酬載**：帶影像的
行改走 JSON 物件走訪，跳過 `source.data`，因此不可能靜默損毀一張圖。

保留下來的仍然是 Windows 路徑（例：`C:\Users\USER\AppData\...`）。這是刻意的——
研究標的就是一台真實 Windows 機器，把路徑改成 POSIX 風格會使紀錄失真。

### 2.2 絕對來源路徑（文件與工具）

`PAPER_2026-08-20.md` 等文件中約 60 處指向作者機器上的絕對路徑，已改為 repo 相對路徑。
`results/*/meta.json` 的 `prompt_file` 同樣改為相對路徑（`fixtures\...`）。

**這一項讓證據變強而非變弱**：每筆 `meta.json` 都記錄了 `prompt_sha256`。改成相對
路徑之後，24/24 的雜湊值可以直接對本 repo 內的 `fixtures/` 驗證通過，第三方不再需要
作者的磁碟。

`results/*/meta.json` 的 `run_dir`（`D:\BenchRuns\<run-id>`）**未改動**——那是「這次
執行實際發生在哪裡」的紀錄，不是可攜性問題。

### 2.3 私有代理設定（transcript 內的 130 筆 attachment 紀錄）

原始 transcript 內嵌了作者 `~/.claude` 私有環境的內容。這些不是研究資料，是
Claude Code 執行時注入的環境上下文。已清空酬載的類型與筆數：

| `attachment.type` | 筆數 | 原本帶著什麼 |
|---|---|---|
| `skill_listing` | 24 | 作者已安裝 skill 的完整清單（每筆約 29 KB）|
| `deferred_tools_delta` | 42 | 延遲載入的工具名單，含已連接的 MCP 伺服器 |
| `hook_success` | 26 | 作者私有 hook 的輸出 |
| `agent_listing_delta` | 23 | 已設定的 subagent 清單 |
| `nested_memory` | 9 | 作者 `~/.claude/rules/*.md` 的**全文** |
| `mcp_instructions_delta` | 4 | MCP 伺服器的使用說明 |
| `hook_additional_context` | 2 | hook 附加上下文 |

**紀錄本身保留**（`type` 欄位不動，加上一個 `redacted` 說明欄），所以 transcript 的
結構與紀錄筆數不變，任何依賴筆數的分析都不受影響。

### 2.4 截圖（31 張中的 5 張）

原始 transcript 內嵌 31 張 base64 PNG，都是代理為了驗證自己做的 GUI 而截的圖。
逐張人工檢視後，5 張含有與研究無關的畫面內容，**已清空影像資料**（保留影像區塊
與一行說明），其餘 26 張原樣保留：

| 執行 | 行 | 移除原因 |
|---|---|---|
| `XL-CAL-01` | 267 | 全螢幕擷取，捕捉到一個不相關的應用程式視窗 |
| `XL-CAL-01` | 279 | 程式指向作者真實的文件資料夾；該畫面列出 104 個個人檔名，其中一個含第三人姓名 |
| `C2-01` | 391 | 畫面邊緣露出不相關應用程式視窗的片段 |
| `C2-01` | 403 | 同上 |
| `M1-03` | 196 | 程式視窗背後露出不相關的應用程式 |

`XL-CAL-01` 那兩張是**該次執行自己在結語裡承認的事故**：它第一版用了全螢幕擷取，
發現問題後改用 `PrintWindow` 只渲染自己的視窗。論文未曾引用任何一張截圖。

---

## 3. 沒有被改動的東西

- `results/*/record.json`、`cli_result.json`、`score.json`、`holdout/*.json` 的**任何數值**
- `.gitattributes` 的 `* -text`（行尾不轉換，本專案賴以成立的位元保真）
- UTF-8 BOM（`record.json` 等檔案帶 BOM，讀取請用 `encoding='utf-8-sig'`）
- `holdout/fuzz-trees/B_unicode_long/` 的 269 字元長檔名測試案例
- 評分器 `holdout/score.py` / `score_xl.py` 的任何一行

**一項邊界情況**：`holdout/refimpl_xl/Program.cs` 有兩個常數原本是作者機器上的
絕對路徑（Python 直譯器與 oracle 腳本）。已改為讀環境變數並提供可解析的預設值，
否則這支校準工具在別台機器上必然啟動失敗。**它下面的邏輯一行未改**，且
`results/` 內的分數是由改動前的二進位產生的。它是校準治具，不是評分器。

---

## 4. 「沒有動到任何數字」是怎麼證明的

不是宣稱，是三項實測：

| 檢查 | 結果 |
|---|---|
| `tools/analyze.py --json` 跑過全部 24 筆 transcript，逐欄比對處理前後 | **0 項數值差異** |
| `tools/paper_data.py` 完整輸出（363 行）比對處理前後，僅正規化根路徑 | **0 行差異** |
| 24 筆 `meta.json` 的 `prompt_sha256` 對 repo 內 `fixtures/` 驗證 | **24 ok / 0 bad** |

外加影像完整性：處理後 **26 張仍解碼為合法 PNG、5 張刻意清空、0 張損毀**。

原因很直接——`analyze.py` 讀的是每筆請求自報的 `message.usage`，而被清空的
是 attachment 酬載與影像位元組。兩者沒有交集。

---

## 5. 這份副本與原始樹的關係

| | 原始工作樹 | 本副本 |
|---|---|---|
| git 歷史 | 15 個 commit，本機獨有，無 remote | **全新歷史**，不接續原始樹 |
| commit 身分 | 作者真實姓名與信箱 | GitHub handle ＋ noreply 位址 |
| 內容 | 上述 4 類未處理 | 已處理 |

歷史刻意不搬移：原始 commit 的內容含有本檔列出的全部四類資料，搬歷史等於把
剛移除的東西從 `git log` 裡再放出去一次。原始樹仍在作者機器上，未受影響。

---

*review-when：任何一次對 `results/`、`holdout/` 或 transcript 的新增或重新產生，
都會使本檔的計數與 §4 的證明失效，必須重跑 `tools\deidentify.py --check` 並更新本檔。*
