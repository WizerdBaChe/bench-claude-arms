# bench-claude-arms — 檔案索引

在一台真實的 Windows 開發機上，量測 LLM 編碼代理的**執行成本**：執行通道、
委派架構、推理強度，以及一個兩點的任務規模劑量反應。
22 筆任務執行 ＋ 2 筆儀器探針，\$254.22，全部通過預先登記的排除稽核。

**這份檔案只做一件事：告訴你哪個檔案是什麼、可不可以拿它的數字。**
研究本身怎麼讀、下一步該做什麼，去 `HANDOFF_2026-08-21.md`。

> **這是去識別化後的分享副本 (de-identified share copy)。**
> 原始樹是一台個人 Windows 機器上的私有工作目錄。發布前移除了作者的帳號名、
> 絕對路徑、130 筆帶有私有代理設定的 transcript 紀錄，以及 31 張內嵌截圖中的 5 張。
> **沒有任何量測數值被改動**，證明在 `DATA_NOTICE.md` §4；用
> `python tools\deidentify.py --check` 可以自行驗證。
> 授權：程式 MIT（`LICENSE`）、數據與文件 CC BY 4.0（`DATA-LICENSE.txt`）。
> **GitHub 側欄只會顯示 MIT** —— 那是它對 `LICENSE` 的偵測結果，只涵蓋程式，
> 不涵蓋數據與論文。完整範圍見第 8 節。

---

## 1. 三種讀者，三條路

| 你是 | 讀這個 | 不要讀 |
|---|---|---|
| **新 session 要接手** | `HANDOFF_2026-08-21.md` → `CLAUDE.md` | 不要從論文開始，會漏掉限定詞 |
| **要知道結論與花費** | `COST_BRIEF_2026-08-21.html`（絕對金額）或 `SUMMARY_2026-08-21.html`（過程與比值） | — |
| **要重新推導一個數字** | `results/*/record.json` ＋ `results/*/cli_result.json` ＋ `holdout/*.json`，再對 `RECONCILIATION_2026-08-21.md` | **不要**從 `RESULTS_*.md` 抄值 |

---

## 2. 權威順序（本專案的核心紀律）

任何數字出現分歧時，**上層永遠贏**：

| 層 | 檔案 | 說明 |
|---|---|---|
| **T1 權威** | `results/*/record.json`、`results/*/cli_result.json`、`holdout/*.json` | 逐筆原始紀錄。**帶 UTF-8 BOM，`json.load` 要用 `encoding='utf-8-sig'`** |
| **T2 衍生登記簿** | `RUN_MANIFEST.md`、`AUDIT_2026-08-20.md` | 由 T1 生成。至今每次比對都是它們對 |
| **T3 主文** | `PAPER_2026-08-20.md` | 論文。已對帳，但它是**被檢查的一方** |
| **T4 分輪紀錄** | `RESULTS_*.md`、`FINAL_REPORT_2026-08-20.md` | **不是權威。** 逐輪快照，其中數份帶可見更正區塊 |

已知的漂移全部記在 `RECONCILIATION_2026-08-21.md`：13 筆更正、3 個追不到檔案的
數字（標為 UNVERIFIED）、以及**掃過沒事**與**根本沒掃**的分界。

---

## 3. 根目錄檔案

每一份文件的第一行都有一條 `**文件層級**` 標示，說明它能不能被引用為數字來源。
`python tools/check_docs.py` 會檢查這張表與那些標示都還在。

### 入口與規則

| 檔案 | 是什麼 |
|---|---|
| `README.md` | 本檔。檔案索引與權威順序 |
| `HANDOFF_2026-08-21.md` | **入口**。定位表、帶限定詞的結論、開放工作線（一條線一個 session）|
| `CLAUDE.md` | 本專案硬規則：五條誠實約束、量測規則、環境事實、版本控制約束 |
| `DATA_NOTICE.md` | 本副本相對於原始工作樹改了什麼、為什麼，以及「沒動到任何數字」的三項實測證明 |

### 主文與登記簿

| 檔案 | 層級 | 是什麼 |
|---|---|---|
| `PAPER_2026-08-20.md` | T3 | 論文，9 章 ＋ 4 附錄。附錄 C／C-2 是更正紀錄 |
| `RUN_MANIFEST.md` | T2 | 22 筆執行 ＋ 2 筆探針的自動生成清單，含逐筆 crosscheck |
| `AUDIT_2026-08-20.md` | T2 | 3 項計算錯誤 ＋ 4 項登記缺漏的完整揭露 |
| `RECONCILIATION_2026-08-21.md` | T2 | **全論文數字對帳**。13 筆更正、3 個 UNVERIFIED、覆蓋範圍聲明 |

### 設計

| 檔案 | 層級 | 是什麼 |
|---|---|---|
| `PROTOCOL_2026-08-20.md` | 設計 | 實驗設計；§9A 是 11 條實測驅動的修正（A-1…A-11）|
| `PROPOSAL_ROUND2_2026-08-20.md` | 設計 | 第二輪提案，承接 `FINAL_REPORT` |

### 分輪紀錄（**不是權威**）

| 檔案 | 層級 | 是什麼 | 帶更正區塊 |
|---|---|---|---|
| `RESULTS_PILOT_2026-08-20.md` | T4 | 階段 0 先導執行，n=1 | |
| `RESULTS_EXPERIMENT1_2026-08-20.md` | T4 | 實驗一：CLI vs Desktop，n=4 | |
| `RESULTS_EXPERIMENT2_2026-08-20.md` | T4 | 實驗二：獨力 vs 委派，n=4 | ⚠️ 適用範圍 ＋ 19% 標為 UNVERIFIED |
| `RESULTS_T0-1_FUZZ_2026-08-20.md` | T4 | 差分模糊測試（**9 份實作時期**的快照）| ⚠️ 乘積已由 13 份實作取代 |
| `RESULTS_T0-2-3-4_2026-08-20.md` | T4 | 突變測試、語料快取經濟學、`schemaVersion` 漏洞的稽核 | ⚠️ 成本數字已被稽核修正 |
| `RESULTS_T1-2_EFFORT_2026-08-20.md` | T4 | effort 消融：high vs medium，n=4 | |
| `RESULTS_G4_GUI_SCREENING_2026-08-21.md` | T4 | G4 人工篩檢兩階段結果 | |
| `FINAL_REPORT_2026-08-20.md` | T4 | **第一輪報告，多處已被後續稽核推翻** | ⚠️ 開頭橫幅 ＋ 3.7–4.9× 標為 UNVERIFIED |

### 過程層（回顧與複核）

| 檔案 | 是什麼 |
|---|---|
| `RETRO_INDEX_2026-08-21.md` | 過程問題索引（約 30 項），每項附已驗證的 digest 行號 |
| `REVIEW_RETRO_ADVERSARIAL_2026-08-21.md` | 對抗性複核：13 CONFIRMED／3 PLAUSIBLE。§9.7 有它自己的方法限制聲明 |
| `REVIEW_RULINGS_CLOSED_2026-08-21.md` | 複核九條裁決的處置紀錄（規則層四項的結案）|

### 已發表頁面

| 檔案 | 是什麼 |
|---|---|
| `COST_BRIEF_2026-08-21.html` | 成本帳：絕對金額、每組消耗、可以動哪顆旋鈕 |
| `SUMMARY_2026-08-21.html` | 過程頁：研究做了什麼、儀器怎麼被證明可信、不宣稱什麼（僅比值）|

> 兩份是**刻意分開的兩份 artifact**，職責不同，不要合併也不要互相覆蓋。
> 更新方式：以各自的檔案路徑重新發布，並帶上該 artifact 自己的 `url`；
> 不帶 `url` 會生出第三份。

---

## 4. 目錄

| 目錄 | 內容 | 換一個研究標的時 |
|---|---|---|
| `results/` | **24 個執行紀錄目錄**（22 筆任務執行 ＋ 2 筆儀器探針）。每個含 `record.json`、`meta.json`、`score.json`、`transcript.jsonl`，CLI 執行另有 `cli_result.json` | 重新產生 |
| `holdout/` | 驗收層：oracle、評分器、模糊測試、突變測試、校準結果、G4 計分表與版面探針 | **必須重寫**（編碼了這一份契約的語意）|
| `tools/` | 13 支主腳本（11 支量測 ＋ `check_docs.py` 索引檢查 ＋ `deidentify.py` 去識別化檢查）＋ `adhoc/` 15 支即席分析腳本 | **完全不需改**（與任務無關）|
| `fixtures/` | 5 份 prompt（4 個契約 ＋ 1 個基準線探針），逐筆以 SHA-256 記錄 | 重新撰寫 |
| `archive/` | `C3-02-ABORTED-*`：一筆作廢執行的完整保留 ＋ 說明檔。**不刪檔，只封存** | — |

### 三件關於 `results/` 與 `holdout/` 的事，別踩

1. **`record.json` 帶 UTF-8 BOM。** 用 `encoding='utf-8-sig'`。
2. **`results/*/transcript.jsonl` 對七筆委派執行只保留主線**（C3-01…04、XL-B-01…03），
   Sonnet 記錄一筆不存。要分模型的量請改讀 `cli_result.json` 的 `modelUsage`。
3. **`holdout/fuzz-trees/B_unicode_long/` 內有一個 269 字元的路徑。**
   這是長檔名測試案例，不得改名；沒有 `core.longpaths=true` 就 `git add` 不進去。

---

## 5. 常用指令

驗證論文引用的數字與磁碟一致（會印出逐筆全距、比值與精確 $p$、成本項佔比，
並直接讀論文重乘每個 `A × B = C`）：

```powershell
python tools\paper_data.py --quiet
```

重建執行清單：

```powershell
python tools\build_manifest.py
```

檢查本索引與各文件的層級標示都還在：

```powershell
python tools\check_docs.py
```

檢查去識別化的各項屬性都還成立（改動了 `results/` 或 transcript 之後必跑）：

```powershell
python tools\deidentify.py --check
```

---

## 6. 版本控制與取用

分支 `main`。本副本是**全新歷史**，不接續原始工作樹的本機歷史——原始 commit 的
內容含有 `DATA_NOTICE.md` 所列的全部四類資料，搬歷史等於把剛移除的東西從
`git log` 裡再放出來一次。

**clone 之前必須先設定長路徑支援**，否則 `holdout/fuzz-trees/B_unicode_long/`
的 269 字元測試案例會讓 checkout 失敗（Windows 260 字元上限）：

```powershell
git config --global core.longpaths true
```

`.gitattributes` 釘 `* -text` 是刻意的（prompt 逐筆 SHA-256、結果 JSON 逐位元
解析，行尾改寫會靜默改動證據）——不要「修正」成 `text=auto`。
`CLAUDE.md`「Version control」節有完整理由。

---

## 8. 授權

| 範圍 | 授權 | 檔案 |
|---|---|---|
| 程式（`tools/`、`holdout/**.py`、參考實作、探針）| MIT | `LICENSE` |
| 數據與文件（`results/`、`holdout/*.json`、`fixtures/`、`archive/`、論文與各 `.md`／`.html`）| CC BY 4.0 | `DATA-LICENSE.txt` |

不在上表 MIT 那一列的檔案，一律適用 CC BY 4.0。

> ⚠️ **GitHub 一個 repo 只認一個授權**，且是從 `LICENSE` 偵測而來，
> 所以側欄會標成 **MIT**。那個標籤對程式正確、**對數據與論文錯誤**。
> `LICENSE` 因此保持標準 MIT 全文不加註（否則 GitHub 連 MIT 都認不出來），
> 兩邊的完整範圍改放在 `DATA-LICENSE.txt` 裡。

引用資訊（機器可讀）在 `CITATION.cff`。
`results/**/transcript.jsonl` 內含執行當下 Claude 模型的逐字輸出，作為研究證據發布；
再利用前請先讀 `DATA_NOTICE.md`。

---

## 7. 五條不得被摘要壓縮掉的限定

完整版在 `CLAUDE.md` 規則 1–5，這裡只列標題：

1. 「等品質」只在**契約層**成立——XL-B-01 拿 55/55 卻交出載不進資料夾的 GUI。
2. G4 的 2/3 對 0/3 是 **Fisher p=0.4，描述性**，不得與 n=4、p=0.0286 的成本結論並排。
3. GUI 發現量到的是**組內離散度**，不是「委派讓 GUI 變差」——委派組同時產出全研究最不可用與最好看的兩個 build。
4. effort 的 thinking −33% **不是節省**（總成本僅降 5%，p=0.8857）。
5. 每個數字都要追得到檔案。`tools/paper_data.py` 現在會掃描形狀，
   但它仍然**不能證明論文引用了它印出來的值**——那一步是人做的。

---

*review-when：根目錄新增或移除文件時、或 `results/` 目錄數改變時，本表需同步；
`tools/check_docs.py` 會擋下前者。*
