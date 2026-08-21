# 對抗性複核裁決清單 — 規則層四項的結案報告

> **文件層級**：過程層（結案）— 記錄**裁決的處置**，不是量測資料。
> 數值層的對帳是另一條線，見 `RECONCILIATION_2026-08-21.md`。索引見 `README.md`。

- **日期**：2026-08-21
- **執行者**：獨立 session（Opus 5），`ops-relaxation` **L1（核心放寬）**，依 2026-08-11 常設裁定
- **標的**：`REVIEW_RETRO_ADVERSARIAL_2026-08-21.md` §8 九條裁決中的**規則層四項**
  （`HANDOFF_2026-08-21.md` 線 B）。數值層是線 A（`task_4b77c461`），本報告不碰論文數字。
- **本報告的完成判準**：九條裁決每一條都要有處置，**沒有一條靜默消失**——
  那正是 C-7 指認的失敗模式，所以本報告不能用它來收尾。

---

## 0. 一頁結論

| # | 裁決 | 處置 | 落點 |
|---|---|---|---|
| **6（C-7）** | 三項被靜默丟棄 | **做了** | `RETRO_INDEX_2026-08-21.md` 新增 §7A，三項各有裁決＋理由，並寫成一條**資產不變量** |
| **4（C-6）** | ops 層 sibling scan 未做；R2.2 要不要升層 | **做了** | 候選檔新增 12 列逐項掃描表＋升層裁決；**裁定不升層**，改為**原地拓寬 R2.2 的觸發**（已實作） |
| **7（P-1）** | F1 稽核找不到 | **做了——稽核找到了，但它的母體比那句話小** | 產物在 `RESULTS_T0-2-3-4_2026-08-20.md:54-57`；指標補進四份文件；**已補算全部 22 筆，結論不變** |
| **8（#8）** | L-027 的承載層 | **做了——hook 已上線** | `hooks/ps_pipeline_close_guard.py`，回測後**只掛 PowerShell**，49/49 雙向校準，sweep check 23 |
| **9** | L-024 之內兩個數（「all three」vs「2/2」） | **順手做了**（不在四項內，但它活在我正要提交的檔案裡） | 見 §5 |
| 1（C-5） | 論文兩筆數字缺陷 | **先前已修**，但被三筆新的取代 → **線 A** | 複核 §9.0 逐一驗證；C-11／C-12／C-13 未修 |
| 2（C-1/C-2） | 兩個循環的量化基石 | **先前已撤回** | `ops/lessons.md` L-025「THE BASE RATE — RETRACTED」 |
| 3（C-4） | hook-vs-prose A/B | **先前已撤回** | `ops/lessons.md` L-011 hit 3 的撤回聲明 |
| 5（C-3） | RC-1 的分類法 | **先前已更正** | L-025 Pitfall「CORRECTED / ORIGINAL, wrong and instructively so」 |

**一句話**：四項全部做完，其中兩項的結論與複核的預期不同——
P-1 的稽核**存在**（複核沒查 `RESULTS_*`），而 R2.2 **不該升層**（它的失效是範圍缺陷不是層級缺陷）。
兩處差異都附了逐字證據，見各節。

---

## 1. C-7｜三項「已審視、判定不立規則」

### 做了什麼

`RETRO_INDEX_2026-08-21.md` 新增 **§7A**，內含：

1. **一條寫成資產性質的不變量**（依全域規則「write it as a property of the ASSET, not an
   instruction about a path」）：
   > 這份索引裡的每一個編號項目，都必須能指到一個第 2 步的落點，或指到這一節的一列裁決。
   > 兩者皆無的項目，就是缺陷本身——不論它的內容多小。
2. **三項逐項裁決**（複核 §C-7 指名的那三項）。
3. **另外六項的落點表**，因為複核 §4.1 說「33 項裡 8 項沒有根因認領」，
   而「沒有根因認領」與「在第 2 步消失」是**兩個不同的問題**，混用會讓下一輪誤讀。

### 三項的裁決與理由

| 項目 | 裁決 | 理由（濃縮） |
|---|---|---|
| **E6**（Edit 因粗體標記位置比對失敗） | **不立規則** | 判準是**吵不吵**，不是**痛不痛**。Edit 比對失敗會當場報錯拒寫，代價一次重試，**不可能安靜地寫錯**。L-024／L-025 立規則的那一整類陷阱**全部是靜默的**。一個會自己 announce 的失敗不值得租金。**這個對比本身就是判準**，所以它被寫下來而不是消失 |
| **E3**（`dangerous_command_guard` 兩度擋下合法刪除） | **不立新規則，但帳目已補** | 索引原記成「規則正確運作」，成本只記在別格。該成本現在寫在 `ops/lessons.md` **L-011 hit 3 的 (b) 段**。**注意它是怎麼進帳的**：靠對抗性複核，不是靠第 2 步——這正是 C-7 要防的事 |
| **`AUDIT:135` §4 教訓 3**（通則要先掃過全組再寫） | **值得一條規則，而那條規則已經存在，在沒被掃的那一層** | `ops/30-judgment.md` R2 claim-calibration corollary 逐字要求 universal claims 要有 enumerable evidence，其 Scope 段更涵蓋「任何宣稱兩件事**相同**、或 X **推得** Y 的句子」。**正確處置不是立規則，是承認 ops 層沒被掃**——與 C-6 同根。複核說得對：這條規則會抓到 6/6 與 hook A/B |

### 我自己驗證了什麼

複核宣稱那三項在第 2 步產物裡命中數為 0。**我重跑了那三個 grep，確認為 0**
（唯一命中在 `retrospective-extdispatch-2026-08-16.md`，是另一個專案）。
沒有沿用複核的結論就直接寫。

---

## 2. C-6／裁決 #4｜ops 層 sibling scan 與 R2.2 的升層裁決

### 2.1 掃描本身

**做法**：逐檔讀 `ops/` 的 12 個 rules 檔全文（`OPS.md`、`05`／`10`／`20`／`30`／`40`／`50`／
`60`／`60-record-templates`／`70`、`environment.md`、`rules-usage-dict.md`）與 `ops/references/`，
**不是 grep 幾個關鍵詞**——C-6 的教訓就是關鍵詞掃描會漏掉措辭不同的同一條規則。
結果寫進 `~/.claude/outputs/retrospectives/global-rule-candidates-bench-claude-arms-2026-08-21.md`
的新節「補做：Step 2.4 的 ops 層 sibling scan」，12 列。

**三筆改變判定的發現：**

1. **G-1(b) 確實重複，而且是四處不是兩處**：`OPS.md:35` 硬規則 3、`30-judgment.md` R2.2、
   `10-command-loop.md` Step 6.3 sign-off、`40-maintenance.md` §4.2 Ghost mechanisms，
   外加 `30-judgment.md` R5 表格的 "Unattended automation" 列。複核的指控成立且低估了。
2. **G-2 的暫緩理由需要改寫**。候選檔原本把 G-2 寫成「**預算不是價值**」而暫緩。
   ops 掃描顯示 **`30-judgment.md` R5 最後一列**已經在租
   （"Numeric/factual claim to the requester → cite the source, or label 'unverified'"），
   加上 R2.1「Evidence about MUTABLE content names the version it attaches to」。
   **真正沒被涵蓋的只有「在你自己推理內部承重的常數」**，不是整條 G-2。
3. **C-6 的根**：`70-evolution.md` §1.4 "No duplicate mechanisms" 與 `40-maintenance.md` §2
   「a rule lives in **exactly one file**」——**要求做這個掃描的那條規則，就住在沒被掃的那一層**。

**掃描自己的限制（分母聲明）**：`ops/rule-registry.md`（75 KB）我只查了與本批次相關的 key，
沒有全讀。若某條規則的**理由**在裡面而條文不在，我會漏掉。

### 2.2 R2.2 要不要升層 — **裁定：不升層**

**先更正複核的一個前提**（我逐字讀了原文）。複核說 R2.2 是聚類 B 六個機制的「**逐字**覆蓋」。
R2.2 原文是：

> **Living proof** for mechanisms (**cron / hook / service / scheduled job**): an artifact
> from one successful REAL run has been seen.

括號是**封閉清單**，四項全是常駐／背景型。而聚類 B 的六個是 oracle、價表、探針登記、
完成監看器、版面探針、重疊檢查——**一個都不是**。
所以它沒啟動**不是因為住得太低，是因為照字面讀它不適用**。
原則通用，觸發是清單。**這是範圍缺陷 (scope defect)，不是層級缺陷 (layer defect)，兩者修法相反。**

**依 L-011 路由表逐條檢查「升層」：**

- **hook？** 不是。「相信一支腳本印出來的數字」不產生工具事件。按 L-011 第四形狀是 **OMISSION**；
  三條路徑（P1 攔替代動作／P2 讓缺席可 grep／P3 動作結束閘門）**都不比現況好**——
  尤其 P3 的「動作結束」就是交付，而 R2.2 已經在交付時啟動，**聚類 B 的損害發生在交付之前**。
- **升到全域 CLAUDE.md？它已經在那裡了。** 本批次 2026-08-21 採納的 G-1(b) 逐字就是那句話。
  **升層已經發生過一次，只是沒有人發現那是再推導**——C-6 罵的正是這個。再升一次會有三份副本，
  而 `40-maintenance.md` §2 明文禁止。
- **約束力不缺**：R2 已是 invariant 級（`05-authority.md` §1），任何 relaxation 都不放鬆。
  **缺的是命中率，不是層級。**
- **租金**：全域 CLAUDE.md 19,663 B／19,968 B，餘裕 305 B 且已被 claude-config 登記。

**實際做的三件事**（🟡／🟢 級，**沒有新的全域規則，Step 6.2 的閘門不觸發**）：

1. **拓寬 R2.2 的觸發**（`ops/30-judgment.md` R2 第 2 點，已實作）：從封閉清單改成性質——
   「**anything whose output will be BELIEVED rather than read line by line**」，
   機制清單降為例子，並點名一次性腳本的判定／總計／作廢決定，
   加上「a run nothing could have contradicted is not evidence either」。
   **0 B 全域租金，涵蓋面從 6 項擴到含 A3、A5、D1、`paper_data.py`**。
2. **L-025 fix (c) 降為指標**（已實作）：條文歸 R2.2，lessons 只留「它為什麼沒啟動」，
   並記下上面那個「逐字覆蓋」的更正。
3. **全域 CLAUDE.md 那半句不動**，但兩處互相指認，依 L-011 corollary「不得漂移」。

**什麼會推翻這個裁決**：拓寬後的 R2.2 若在**兩個專案內都沒有啟動過一次**，
就證明問題確實在層級，屆時 L-011 的 P3（`delivery_gate_shadow.py` 那個先例）是下一個候選。
**這把尺與候選檔給 G-1 的那把是同一把**，寫下來以免下一輪換尺。

---

## 3. P-1｜F1 的稽核 — **找到了**，但它的母體比那句話小

### 3.1 稽核在哪裡

`RESULTS_T0-2-3-4_2026-08-20.md:54-57`，標題就叫「對 `schemaVersion` 漏洞的處置」：

> 補查十份實作（9 受測 + 1 參考）：**全部輸出 `schemaVersion: 1`、summary 欄位齊全。**

複核查過 `AUDIT_2026-08-20.md` §3、`RUN_MANIFEST.md` 與 digest，**唯獨沒查 `RESULTS_*`**——
而那一格當初也沒留指標。**「找不到」是索引缺指標造成的，不是稽核不存在。**

### 3.2 但它有一個複核沒看到的缺陷：母體

該檔第 18 行自述「僅使用既有的 **9 份** transcript、9 份實作」，日期 2026-08-20。
當時 **M1 四筆、C2-02…04、全部 XL 執行都還不存在**。
所以「無組別利用」在 2026-08-20 為真，**涵蓋 22 筆中的 10 筆，其後從未重算**。

**這與複核 C-12 是同一個形狀**：`48–203` 是 M1／XL 加入前的全距，加完沒重算。
差別是 C-12 是區間、這一筆是**母體**——`tools/paper_data.py` 連前者都看不見，後者更完全在射程外。
（此點已透過 session 訊息交給線 A，作為它的形狀清單第四項：**「宣稱的母體後來變大了」**。）

### 3.3 補算：全部 22 筆，結論不變

唯讀 grep 全部 22 個執行樹的 `src/**/*.cs`：

- **22/22 都以編譯期常數輸出 `schemaVersion = 1`** —— `const int CurrentSchemaVersion = 1`、
  `public int SchemaVersion => 1`、`[JsonPropertyName("schemaVersion")] … = 1`、
  或 `writer.WriteNumber("schemaVersion", 1)` 的字面值。**沒有任何一組省略或改值。**
- **常數強於抽樣輸出**：抽樣只證明那一次輸入，常數證明全部輸入。
- 另外確認 **`holdout/score_xl.py` 也從未提及 `schemaVersion`（0 次）**——
  複核只查了 `score.py`。**漏洞橫跨小契約與 XL 兩把量尺，而兩把尺的受測組都沒利用它。**

### 3.4 指標補進了四個地方

| 檔案 | 改了什麼 |
|---|---|
| `RETRO_INDEX_2026-08-21.md` §6 | F1 那一格加上產物路徑，底下加一段母體與補算的註 |
| `PAPER_2026-08-20.md` §5.4 | **刪掉「獨立」二字**（該稽核由作者自己執行，不是獨立第三方——本研究自己的結論正是「同作者對照結構性失明」），加上產物路徑與「更正 2026-08-21c」區塊。**沒有動任何數字** |
| `~/.claude/references/bench-claude-arms-phase1-measurement.md` | 同上兩項；**另外修掉一筆過時值**，見 §6 |
| 專案 `CLAUDE.md` 規則 8 | 加上產物路徑與兩個限定詞 |

**「刻意不追溯修補評分器」的決定完全不變**（專案 `CLAUDE.md` 規則 8）。
改變的只有一件事：這一格的免罪理由現在**指得到檔案、也說得出母體**。

---

## 4. 裁決 #8｜L-027 的承載層 — **hook 已建、已回測、已上線**

### 4.1 為什麼建（依 L-011 第一條路由）

`| Select-Object -First N` 接在原生／直譯器指令後面，**在指令文字上機械可判定**，
正是 L-011 路由表第 1 列（named tool call with inspectable input → PreToolUse hook）。
它踩了 **2 次**、賠了 **2 輪**；而已經拿到 hook 的 `$ErrorActionPreference` 陷阱
**可判定性更低、踩 1 次、賠 1 輪**。承載層當初是「回顧的手剛好在那裡」決定的，不是規則決定的。

### 4.2 建了什麼

| 產物 | 內容 |
|---|---|
| `~/.claude/hooks/ps_pipeline_close_guard.py` | PreToolUse，**只 annotate 不 deny**，逃生口 `[pipeline-checked]`，fail-open |
| `~/.claude/tools/ps-pipeline-close-test/` | 雙向校準套件 **49/49**（19 必觸發／30 必靜默） |
| `~/.claude/tools/ps-pipeline-close-backtest/` | 語料回測，import hook 而非重寫（姊妹工具就是重寫後當天走樣的） |
| `~/.claude/ops/references/integrity-sweep.md` check 23 | 存活檢查，**與 hook 同一個 commit** |
| `~/.claude/ops/rule-registry.md` key `ps_pipeline_close_guard` | 條目＋四條 review-when |
| `~/.claude/ops/lessons.md` L-027 / L-011 | L-027 標記 CLOSED；L-011 記為 **hit 4** |

### 4.3 回測（**上線前跑的**，這是 L-011 第五形狀的要求）

語料：726 個 transcript 檔、56 天（2026-06-22…08-20）、26,046 次去重後的工具呼叫。

| tool | calls | PS payloads | tax/day | 命中 |
|---|---|---|---|---|
| **PowerShell** | 3,411 | 3,411 | 6.4 s | **160** |
| Write | 3,548 | 85 | 6.7 s | **0** |
| Edit | 7,668 | 142 | 14.4 s | **0** |
| Bash | 11,367 | 226 | 21.3 s | **0** |

**結果與姊妹 hook 完全相反，而這正是「每個陷阱各自量」的證據**：
`$ErrorActionPreference` 的 53 筆 payload 有 47 筆來自 Write（票寫錯了表面）；
這一個 **160 筆全部在 PowerShell 工具、`.ps1` 檔零命中**——它是**互動慣用語**，
是在提示字元前為了縮短輸出而打的，不是寫進腳本的。
所以 `settings.json` **只掛 `PowerShell`**；Write／Edit／Bash 三條分支留在程式碼裡、有測試、**不註冊**
（否則是 42.4 s/day 的稅換 56 天零命中）。

### 4.4 雙向校準，以及**校準器自己的正對照**

- 套件 49/49：19 必觸發 ／ 30 必靜默。
- **必靜默那一半是承重的**：其中包含 **L-027 自己開的藥方**
  （`$out = & python x.py; $out | Select-Object -First 30`）——
  **一個會對自己的解法報警的 hook 比沒有 hook 更糟**。
- **49/49 是剛寫好的檢查器對 n≥3 的一致判決，依全域閘門條這是儀器故障的訊號**，所以先跑了正對照：
  - `FIRE_TIERS = ()`（偵測器關掉）→ 觸發半邊 **0/19**，靜默半邊 30/30。
  - 觸發條件放寬到全部 → 觸發半邊 19/19，靜默半邊掉到 **16/30**。
  - **兩半都能失敗，所以 49/49 不是構造出來的。** 順帶量到：另外 14 個 negative 是因為
    **路由**（遮蔽、非 `.ps1`、無管線、逃生口）而靜默，不是因為分級——這一句是誠實的分母。

### 4.5 一個由資料做出的分級決定

160 筆分成兩層：**work 100 筆**（直譯器／建置工具／可變更狀態者）與 **report 60 筆**。
**report 那 60 筆全部是 `git diff|show|log` 與 `gh`**——作者要某個只會列印的東西的前 N 行。
對它們報警等於**每天 1.07 次對正確的程式碼說話**，那是 annotate-only hook 教會讀者跳過它的方法
（`40-maintenance.md` §4.3 ritualization）。

**裁定：`FIRE_TIERS = ("work",)`。report 層仍然偵測、仍然計數、但不出聲。**
回測每次執行都會**重印被抑制的那些列**——一個被抑制又不再計數的類別，是沒有人能重新打開的類別。

**最終速率（as registered）：100 / 3,412 inspected payloads = 2.93%，1.79 次/日，稅 6.4 s/日。**
讀過前 28 條相異的 work 層語句，**零偽陽性**，其中幾條是 L-027 的損害原尺寸：

- `dotnet publish -c Release … | Select-Object -First 40`
- `npx playwright test … | Select-Object -First 60`
- `.venv\Scripts\python.exe -m pytest … | Select-Object -First 16`

**一次 publish 與兩次測試執行，為了縮短畫面而被殺掉。**
其中兩次被診斷出來、各賠一輪；其餘想必被當成工具不穩定，從來沒被記到帳上。

### 4.6 存活檢查

`integrity-sweep.md` check 23 與 hook 同 commit，內容是**驅動它**（不是數列數）：
已知為真（直譯器＋early-close → 必須報警）與已知為假（純 cmdlet → 必須沉默）各一，
外加「production log 未被污染」的斷言。**實跑結果：`ALIVE`，production log 不存在。**

---

## 5. 順手處理的裁決 9（不在四項內）

複核在快照聲明裡留了一則「在途狀態，請作者自行收尾」：
`ops/lessons.md` L-024 之內，一處寫「reached for THREE times … intercepted all three」，
另一處仍寫「the hooked half **2/2** prevented」。**它沒有被收尾**，而我正要提交那個檔案。

**做了**：把那句改成記錄「3 與 1」的計數更正，**同時保留 C-4 的撤回**——
因為「3/3 vs 0/1」在同一天已被撤回為單邊取樣，**修數字而復活比率會是更糟的結果**。
留下的是機制（碰了三次都攔住、prose 那次沒攔住、其中一次 hook 命中發生在
正在論證 hook 的那份回顧的自檢裡），**不是比率**。

---

## 6. 屬於別條線、我沒有動的東西

| 發現 | 歸屬 | 我做了什麼 |
|---|---|---|
| **C-11／C-12／C-13** 三筆論文數字缺陷 | **線 A** | 沒碰 |
| **`PAPER_2026-08-20.md` 目前同時帶著我的與線 A 的未提交修改** | 線 A | **我只 commit 我自己的路徑，沒有 stage 論文**；已用 session 訊息告知線 A 我改了哪一段 |
| **「宣稱的母體後來變大了」是第四種形狀** | 線 A | 已用 session 訊息交出（§3.2）|
| `~/.claude/references/bench-claude-arms-phase1-measurement.md` 的突變盲區寫「3 項」 | 本輪修掉 | 論文 §5.4 的「更正 2026-08-21b」已改成 **4 項**（漏列 `ctrl_char@11104`），而這份下游交接檔沒跟上。**這就是 RC-4 的機制反向運轉**：更正住在上游、沒有傳到下游。已修，並在該處註明來由 |

---

## 7. 併發狀況：交接說明有一處與實測不符（**請看這條**）

任務說明寫「Work in this repo (`_bench-claude-arms`) is unaffected; it has no other live sessions.」

**實測不成立。** `list_sessions` 在本輪開始與中途兩次都顯示
`local_78f7477b`（"Full numeric reconciliation of the bench-claude-arms paper"，即線 A）
`isRunning: true`、`cwd = <repo root>`。**它在本輪期間確實寫入了本樹**：
`PAPER_2026-08-20.md` 在我編輯時回報「已被磁碟上的其他改動更新」，
`CLAUDE.md` 與 `COST_BRIEF`／`SUMMARY` 的 dirty 狀態也在本輪中途變過。

**因此我在本樹採用了與 `~/.claude` 相同的紀律**：
每次 git 動作前先 `git branch --show-current`，只 stage 我自己的路徑，**絕不 `git add -A`**，
並在 commit 前重新確認每個受影響檔案的 diff 只含我的改動。
`PAPER_2026-08-20.md` 因為同時含線 A 的未提交改動，**我沒有提交它**——它留在工作區給線 A。

`~/.claude` 那邊的併發紀律照 L-023 執行：本輪開始時
`local_5a7bd61b`（session board）`isRunning: true`，我在它執行期間**只寫檔、不做任何 git 動作**；
提交前重新確認，屆時它已把自己的工作提交完畢，我的 dirty 路徑全部是我自己的。

---

## 8. 前提與反證陳述

**前提（origin-tagged）**

- **P-env（已驗證）**：`ops/` 全部 rules 檔與 `ops/references/` 本機讀取；
  22 個執行樹存在於 `D:\BenchRuns\`（唯讀 grep）；回測語料 726 檔／56 天實跑；
  hook 套件與 sweep check 實跑；`settings.json` 解析通過且註冊數為 1。
- **P-intent（來自使用者，report-only 的部分）**：不碰論文數字、不加新的全域 CLAUDE.md 規則、
  不重啟已完成的撤回。**已遵守**——本輪沒有任何 `~/.claude/CLAUDE.md` 的改動。
- **P-validity（部分假設）**：
  1. **§3.3 的補算是靜態的**（讀原始碼常數），不是執行 22 個 exe 再讀輸出。
     常數在此比抽樣強，但**若某組在別處覆寫該欄位**，靜態掃描會漏。我搜的是全部 `src/**/*.cs`
     的 `schemaVersion`（不分大小寫），22 個樹全部命中且全部是常數 1。
  2. **回測語料是「本 hook 存在之前」的狀態**；重跑會多出本輪自己的呼叫，數字會微幅上飄。
  3. **ops 掃描沒有全讀 `rule-registry.md`**（75 KB，理由登記簿）。

**Holds when**：2026-08-21 的檔案狀態，Windows PowerShell 5.1，
且 `ops/`、`hooks/`、`settings.json` 沒有被其他 session 進一步改動。

**Overturned by**

1. **裁決 #8 的分級**：若被抑制的 report 層出現一個**能變更狀態**的 upstream
   （雲端 CLI、`reg`、`schtasks`、簽章或發佈工具），那就是分錯層，該名字要移進 `TIER_WORK`。
   回測每次都會印出被抑制的清單，所以這個條件是**可被機械發現的**，不靠人記得問。
2. **裁決 #4 的裁定**：拓寬後的 R2.2 若兩個專案內都沒啟動過一次，
   則問題確實在層級，L-011 的 P3 是下一個候選。
3. **§3 的補算**：若某個執行樹在 `src/` 以外（例如產生器、範本、後製腳本）覆寫 `schemaVersion`，
   §3.3 的結論下修為「原始碼層面未利用」。
4. **§4.3 的表面判定**：若 Write／Edit／Bash 的命中數開始累積（回測會顯示），
   matcher 決策重開。

**Evidence tier**

- §1、§2.1、§3、§4、§5、§6：**本機實測**（檔案內容、行號、實跑輸出）。
- §2.2 的裁決：**推論**，建立在實測的 R2.2 原文與實測的全域 CLAUDE.md 現況之上。
- §7：**本機實測**（`list_sessions` 兩次、`git status` 多次、工具回報的檔案衝突）。

**Not covered**

- 論文的全面數值對帳（線 A）；C-11／C-12／C-13；
  `rule-registry.md` 全文；raw transcript 全文；
  hook 在**真實互動**中的第一次命中（見下方驗收清單第 1 項）。

---

## 9. 人工驗收清單（可由非作者盲跑）

> 前四項是機械的，最後一項需要人眼。每一項都寫明「該看到什麼」。

1. **hook 的第一次真實命中**（唯一需要人的一項）
   在任一 PowerShell 呼叫裡打 `python --version | Select-Object -First 1`。
   **應該看到**：一段以 `ps-pipeline-close guard:` 開頭的註記，內容點名 `python` 與
   `Select-Object -First 1`，並給出 `$out = & python …; $out | …` 的替代寫法。
   **同時**：`~/.claude/telemetry/ps-pipeline-close.jsonl` 應新增 **1 列**（此前該檔不存在）。
   ❌ 若沒有註記 → hook 沒掛上或已死，跑第 2 項。

2. **存活檢查**（機械）
   ```powershell
   cd $HOME\.claude ; python tools\ps-pipeline-close-test\test_ps_pipeline_close_guard.py
   ```
   **應該看到**：`TOTAL : 49/49`，且最後一行寫「telemetry rows written to the redirected log: 19」。
   ❌ 任何一列 `FAIL` → 偵測器與它的校準漂移了。

3. **回測與註冊**（機械）
   ```powershell
   cd $HOME\.claude ; python tools\ps-pipeline-close-backtest\backtest.py --sample 4
   ```
   **應該看到**：`registration read from: settings.json -> PowerShell`；
   `AS REGISTERED` 區塊的比率在 **2.93% 附近**；
   `SUPPRESSED` 那一列的 upstream 只有 `git` 與 `gh`。
   ❌ `NOT REGISTERED YET` → `settings.json` 被其他 session 覆寫了，重新加回那個 `PowerShell` 區塊。
   ❌ `SUPPRESSED` 出現能變更狀態的指令 → 依 §8 Overturned by 第 1 條處理。

4. **壓力路徑：hook 不能對正確的程式碼說話**（機械，這一項比第 2 項重要）
   在 PowerShell 裡依序打這三行，**三行都不應該出現任何註記**：
   ```powershell
   Get-ChildItem | Select-Object -First 5
   git log --oneline | Select-Object -First 5
   $out = & python --version; $out | Select-Object -First 1
   ```
   ❌ 任何一行出現註記 → 分級或遮蔽壞了，`FIRE_TIERS` 與 `mask()` 是第一嫌疑。

5. **索引的不變量**（人眼，一分鐘）
   打開 `RETRO_INDEX_2026-08-21.md` §7A，隨機挑三個編號項目（例如 B3、D5、E7），
   **應該能在 30 秒內**指出它的第 2 步落點，或指出 §7A 裡對應的裁決列。
   ❌ 指不出來 → §7A 的表還缺列，這正是它存在的理由。

---

*本報告只報告本輪做了什麼與沒做什麼。線 A 的數值缺陷（C-11／C-12／C-13）在本輪結束時仍未修，
論文仍在發表那三個值——那不是我的線，但把它寫在這裡，比讓它從兩份報告的縫隙掉出去好。*
