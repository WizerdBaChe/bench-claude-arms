# RUN MANIFEST — 本研究的完整執行登記

> **文件層級**：T2 衍生登記簿 — 由 T1 權威（`results/*/record.json`）自動生成，
> 可直接引用。至今每次比對都是它對。索引見 `README.md`。

> 自動生成，來源為 `results/*/meta.json` 與 `results/*/record.json`。
> 重建指令：`python tools/build_manifest.py`

**任務執行 22 筆 · 儀器探針 2 筆（不計入任何組別樣本）**

## 任務執行

| run | 組別 | prompt SHA | session | 排除 | Y1b | 峰值ctx | 時間s | Y4 | 成本 | 成本來源 | 子代理 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1-04 | C1    CLI x solo x high (small) | `616EC2F5EB54` | `a61b110a` | ✅ | 263,442 | 174,974 | 1,402 | 1.00 | $8.17 | cli_self_report | 0 |
| C2-01 | C2    Desktop x solo x high (small) | `616EC2F5EB54` | `5f0c5ed1` | ✅ | 378,185 | 260,570 | 2,215 | 1.00 | $18.20 | derived_from_validated_price_table | 0 |
| C2-02 | C2    Desktop x solo x high (small) | `616EC2F5EB54` | `477e62e3` | ✅ | 278,959 | 204,484 | 1,371 | 1.00 | $9.06 | derived_from_validated_price_table | 0 |
| C2-03 | C2    Desktop x solo x high (small) | `616EC2F5EB54` | `6bf1455a` | ✅ | 289,330 | 202,379 | 1,557 | 1.00 | $9.12 | derived_from_validated_price_table | 0 |
| C2-04 | C2    Desktop x solo x high (small) | `616EC2F5EB54` | `b4993d24` | ✅ | 304,199 | 219,892 | 1,537 | 1.00 | $11.68 | derived_from_validated_price_table | 0 |
| C3-01 | C3    CLI x delegated x high (small) | `F3DAB7457591` | `a8f00fe5` | ✅ | 1,203,354 | 192,794 | 2,927 | 1.00 | $18.34 | cli_self_report | 105 |
| C3-02 | C3    CLI x delegated x high (small) | `F3DAB7457591` | `83553581` | ✅ | 1,141,359 | 177,216 | 3,016 | 1.00 | $15.52 | cli_self_report | 165 |
| C3-03 | C3    CLI x delegated x high (small) | `F3DAB7457591` | `305c9d83` | ✅ | 1,654,454 | 180,889 | 3,383 | 1.00 | $18.26 | cli_self_report | 167 |
| C3-04 | C3    CLI x delegated x high (small) | `F3DAB7457591` | `14d40884` | ✅ | 934,104 | 187,365 | 2,334 | 1.00 | $13.98 | cli_self_report | 119 |
| M1-01 | M1    CLI x solo x MEDIUM (effort ablation) | `616EC2F5EB54` | `ab309e5d` | ✅ | 230,842 | 155,514 | 957 | 1.00 | $6.53 | cli_self_report | 0 |
| M1-02 | M1    CLI x solo x MEDIUM (effort ablation) | `616EC2F5EB54` | `fd327119` | ✅ | 209,264 | 150,013 | 1,175 | 1.00 | $7.01 | cli_self_report | 0 |
| M1-03 | M1    CLI x solo x MEDIUM (effort ablation) | `616EC2F5EB54` | `8aaa06f7` | ✅ | 229,117 | 172,104 | 1,196 | 1.00 | $7.48 | cli_self_report | 0 |
| M1-04 | M1    CLI x solo x MEDIUM (effort ablation) | `616EC2F5EB54` | `36fa1c35` | ✅ | 197,865 | 143,027 | 1,035 | 1.00 | $5.37 | cli_self_report | 0 |
| PILOT-C1-01 | C1    CLI x solo x high (small) | `616EC2F5EB54` | `2bdef0f6` | ✅ | 227,861 | 160,059 | 1,256 | 1.00 | $6.37 | cli_self_report | 0 |
| PILOT-C1-02 | C1    CLI x solo x high (small) | `616EC2F5EB54` | `569abbc8` | ✅ | 211,349 | 149,185 | 1,214 | 1.00 | $6.69 | cli_self_report | 0 |
| PILOT-C1-03 | C1    CLI x solo x high (small) | `616EC2F5EB54` | `9c3c3274` | ✅ | 233,755 | 161,352 | 1,216 | 1.00 | $6.69 | cli_self_report | 0 |
| XL-A-02 | XL-A  CLI x solo x high (XL contract) | `657ECCEB4C22` | `b33cec55` | ✅ | 290,581 | 194,936 | 1,568 | 1.00 | $10.60 | cli_self_report | 0 |
| XL-A-03 | XL-A  CLI x solo x high (XL contract) | `657ECCEB4C22` | `8ad71272` | ✅ | 352,416 | 228,153 | 1,954 | 1.00 | $13.54 | cli_self_report | 0 |
| XL-B-01 | XL-B  CLI x delegated x high (XL contract) | `E9FF0A701D0B` | `4b5b6b13` | ✅ | 901,160 | 200,454 | 2,413 | 1.00 | $15.83 | cli_self_report | 151 |
| XL-B-02 | XL-B  CLI x delegated x high (XL contract) | `E9FF0A701D0B` | `f0c2c7c1` | ✅ | 1,016,754 | 194,306 | 2,772 | 1.00 | $15.67 | cli_self_report | 127 |
| XL-B-03 | XL-B  CLI x delegated x high (XL contract) | `E9FF0A701D0B` | `026f1e1f` | ✅ | 839,934 | 217,557 | 2,359 | 1.00 | $16.39 | cli_self_report | 168 |
| XL-CAL-01 | XL-A  CLI x solo x high (XL contract) | `657ECCEB4C22` | `884d8235` | ✅ | 407,586 | 244,255 | 2,119 | 1.00 | $12.88 | cli_self_report | 0 |

## Crosscheck（分析器 vs CLI 自報）

| run | 結果 |
|---|---|
| C1-04 | cli_output=114876 analyzer_output=114876 delta=0 (0%) |
| C2-01 | n/a (no CLI self-report) |
| C2-02 | n/a (no CLI self-report) |
| C2-03 | n/a (no CLI self-report) |
| C2-04 | n/a (no CLI self-report) |
| C3-01 | cli_output=262584 analyzer_output=260870 delta=-1714 (0.65%) |
| C3-02 | cli_output=279335 analyzer_output=278333 delta=-1002 (0.36%) |
| C3-03 | cli_output=323414 analyzer_output=318955 delta=-4459 (1.38%) |
| C3-04 | cli_output=271646 analyzer_output=237068 delta=-34578 (12.73%) |
| M1-01 | cli_output=75208 analyzer_output=75208 delta=0 (0%) |
| M1-02 | cli_output=85649 analyzer_output=85649 delta=0 (0%) |
| M1-03 | cli_output=83415 analyzer_output=83415 delta=0 (0%) |
| M1-04 | cli_output=81290 analyzer_output=81290 delta=0 (0%) |
| PILOT-C1-01 | cli_output=94244 analyzer_output=94244 delta=0 (0%) |
| PILOT-C1-02 | cli_output=88580 analyzer_output=88580 delta=0 (0%) |
| PILOT-C1-03 | cli_output=98839 analyzer_output=98839 delta=0 (0%) |
| XL-A-02 | cli_output=122009 analyzer_output=122009 delta=0 (0%) |
| XL-A-03 | cli_output=150601 analyzer_output=150601 delta=0 (0%) |
| XL-B-01 | cli_output=263092 analyzer_output=259165 delta=-3927 (1.49%) |
| XL-B-02 | cli_output=310067 analyzer_output=300532 delta=-9535 (3.08%) |
| XL-B-03 | cli_output=261189 analyzer_output=252904 delta=-8285 (3.17%) |
| XL-CAL-01 | cli_output=163173 analyzer_output=163173 delta=0 (0%) |

## 分組彙總

| 組別 | n | runs |
|---|---|---|
| C1    CLI x solo x high (small) | 4 | C1-04, PILOT-C1-01, PILOT-C1-02, PILOT-C1-03 |
| C2    Desktop x solo x high (small) | 4 | C2-01, C2-02, C2-03, C2-04 |
| C3    CLI x delegated x high (small) | 4 | C3-01, C3-02, C3-03, C3-04 |
| M1    CLI x solo x MEDIUM (effort ablation) | 4 | M1-01, M1-02, M1-03, M1-04 |
| XL-A  CLI x solo x high (XL contract) | 3 | XL-A-02, XL-A-03, XL-CAL-01 |
| XL-B  CLI x delegated x high (XL contract) | 3 | XL-B-01, XL-B-02, XL-B-03 |

## 儀器探針（不是實驗資料）

以 `BASELINE_PROBE.md` 執行，用於量冷啟動基準線與驗證工具鏈。
**任何組別的樣本數都不包含這些。**

| run | 用途 | T0 基準線 | 成本 |
|---|---|---|---|
| P0-cli-opus-baseline | C1    CLI x solo x high (small) | 36,290 | $0.36 |
| P0-cli-opus-baseline-agents | C3    CLI x delegated x high (small) | 47,120 | $0.47 |
