# 审阅报告：后端修复独立复核（REVIEW_backend_fixes.md）

审阅对象：`BACKEND_AUDIT.md` 的主张 + 实际代码改动（`api/routes/analytics.py`、`frontend/js/app.js`、`frontend/index.html`、`api.json`、`tests/test_api_endpoints.py`）。
审阅方式：独立启动 uvicorn（127.0.0.1:8014）实测 + 源码逐行对照 + 把新测试套件跑在 git HEAD 旧代码上做回归性判别。所有证据为本次复核实测，不采信作者自述。
复现环境：Python 3.14.2（Python314），项目根 `AI PRice recomm`。

## 1 Verdict（逐主张判定表）

| # | 主张 | 判定 | 依据（实证） |
|---|------|------|--------------|
| 1 | 库存来自 inventory.csv 最新快照，合计 541，8 个 SKU 全对 | PASS | 实测 `/api/optimizations` 合计 541；逐 SKU 与 CSV 完全一致（A56=73, S26_256=14, IPHONE_16=0, IPHONE_17=76, ONEPLUS=111, PIXEL=77, REDMI=50, S26_ULTRA=140）。该测试跑在旧代码上失败（"SKU_IPHONE_17_256 inventory 800 != inventory.csv 76"）→ 真回归测试 |
| 2 | 现价来自 sales.csv 最新观测交易 | PASS | 逐 SKU 现价 == sales.csv 最新日（2026-09-01）中位数；旧代码上该测试失败（"price 104999.0 != observed 107800.0"）→ 真回归测试 |
| 3 | 售罄 SKU 返回 No Stock / Stockout、价格不变、零提升、无幻影降价 | **PARTIAL FAIL** | API 字段正确（price_action=No Stock, inventory_risk_level=Stockout, recommended==current==64800, profit_lift=0, expected_sales=0.0），**但 memo.headline 仍为 "Urgent: Implement ₹0 clearance markdown on Apple iPhone 16 (128GB Blue)"**，key_rationale 称 "decisive markdown to ₹64,800"——幻影降价文本仍在，且前端弹窗会展示。见第 4 节 B1 |
| 4 | risk_counts/action_counts 单一词表且与行一致 | PASS | 实测 {Low Risk:7, Stockout:1} / {Increase Price:7, No Stock:1}，与 8 行逐行统计一致；旧代码上该测试失败 → 真回归测试 |
| 5 | 生命周期事件使两个模型源缓存失效；active_events_count 实时 | PASS（方向正确，但有旁路，见下） | 事件后 kaggle summary 计数 0→1，非陈旧；两个缓存均失效。**但** load_retail_state 未 force 刷新（第 4 节 B4） |
| 6 | simulate 对负/零价格、负库存、负 days_to_successor、未知 model_source 返回 422；inventory=0 被尊重 | **PARTIAL FAIL** | 负/零价格、负库存、负 horizon、POST body 未知 model_source 均实测 422；inventory=0 → expected_sales=0.0 正确。**但 GET 查询参数 `?model_source=garbage` 返回 200**（/summary、/optimizations、/optimizations/refresh 均如此，静默回退 synthetic）→ 与 api.json 明文声明直接矛盾。见第 4 节 B2 |
| 7 | simulate 按 MRP 封顶并报 price_clamped_to_mrp | PASS | price=999999 → simulated_price=84999, price_clamped_to_mrp=true；旧代码上该测试失败 → 真回归测试 |
| 8 | kaggle simulate 对目录外 SKU 404 | PASS | 实测 kaggle+未知 SKU → 404；旧代码上该测试失败 → 真回归测试 |
| 9 | avg_profit_lift_pct 在基线非正时为 null 而非符号反转 | PASS（但非本次修复的回归测试） | 逻辑成立；**该测试跑在旧代码上同样 PASS** → 不能作为本次修复的回归证据，只是守卫 |
| 10 | 新增 20 测试，全套 38 通过 | PASS（数量属实，但有保留） | 实测 `pytest tests/ -q` → **38 passed in 12.07s**；20 项中 **16 项在旧代码上失败**（真回归），4 项在旧代码上同样通过（test_profit_lift_pct_is_guarded_not_inverted、test_event_state_is_consistent_across_sources_and_csves_untouched、test_economic_invariants_hold、test_all_endpoints_respond） |

## 2 Test-suite reality check（测试套件真实性检查）

- 实测：`38 passed in 12.07s`。分文件：test_api_endpoints 20、test_data_pipeline 2、test_explainability 1、test_kaggle_pipeline 4、test_models 7、test_optimizer 4。
- 判别力实验：把 `tests/test_api_endpoints.py` 的 20 项逐项跑在 **git HEAD 版 analytics.py**（其余模块同 HEAD 组合、数据目录重定向到临时副本）上：**16 失败 / 4 通过**。结论：多数测试断言具体数值（如 inventory 76、observed price 107800、MRP 84999），不是 `== 200` 式空转，是**真回归测试**。
- 4 项不能在旧代码上失败 → 对本次修复无判别力：test_profit_lift_pct_is_guarded_not_inverted、test_event_state_is_consistent_across_sources_and_csves_untouched、test_economic_invariants_hold、test_all_endpoints_respond。其中 test_economic_invariants_hold 尤其关键：它含跳过行 `if row["price_action"] == "No Stock": continue`，恰好排除掉违反不变量的售罄行（见 B3）——该测试通过了，并不代表主张成立。
- CSI 不可变性：对 data/synthetic 六个 CSV 做 mtime_ns+sha256 前后快照，全部探测（含旧代码判别实验）后**未变化** → 该保证成立。

## 3 Live evidence for each claim（关键实测摘录）

- 汇总：total_inventory_units=541, total_status_quo_profit=5846096.56, total_optimized_profit=9648994.8, total_profit_lift=3802898.26, avg_profit_lift_pct=65.05, as_of=2026-09-01；val: mae 1.67 / rmse 2.925 / r2 0.903, train 7712 / val 1928。
- 售罄行（SKU_IPHONE_16_128）：inventory=0, current=recommended=64800, profit_lift_amount=0, clearance_probability=0.516, expected_daily_demand=0.0；**profit_curve argmax=56700.0**（≠64800）。
- 其余 7 个 SKU：argmax == recommended_price 全部相等（True）。
- 校验矩阵：price=-5000→422；price=0→422；inventory=-50→422；days_to_successor=-10→422；body model_source="garbage"→422；inventory=0→200 + expected_sales 0.0；price=999999→200 + 84999 + clamped=true；**price=true→200 且 simulated_price=1.0**；**price="79999"→200 被字符串强转**；kaggle+未知 SKU→404。
- **GET ?model_source=garbage → 200（/summary、/optimizations、/optimizations/refresh 均 200）**，静默回退 synthetic——与 api.json 中 "Any endpoint taking ?model_source= now rejects values outside this list with HTTP 422" 直接矛盾。
- 缓存陈旧实证（方法：把 data/synthetic 复制到临时目录并 monkeypatch analytics.SYNTHETIC_DATA_DIR，真实 CSV 零改动；随后改副本 CSV）：/api/summary 总数 541→541（陈旧）；/api/lifecycle-event、/api/reset-events 后仍 541（陈旧）；**仅 /api/optimizations/refresh 后变为 500（= 541−76+35，正确采纳新数据）**。
- /api/transfers：200, snapshot 2026-09-01, 8 行, 0 条推荐转移, solver 正常返回——移除硬编码库存分支未破坏流转端点。
- 前端：app.js 第 6 行 `const API_BASE = '/api'`；`/simulate` 携带完整 SKU 上下文并在非 OK 时 throw；`renderOverview`/`animateKPIs` 均处理 null `avg_profit_lift_pct` 且读取 `Stockout` 键。

## 4 NEW defects introduced / left by the fixes（新缺陷 / 遗缺陷）

### B1（BLOCKER）售罄 SKU 的 memo 仍是幻影降价指令
- 位置：`src/explainability/reason_generator.py`（无 "No Stock" 分支，落入 else 清算降价分支）+ `api/routes/analytics.py` 售罄重标注块（约 228–247 行，改写了 business_reason 但随后仍调用 `ReasonGenerator.generate_retailer_memo(res)`）+ `frontend/js/app.js`（约 1286 行弹窗渲染 `memo.headline`）。
- 问题：0 库存 SKU 的 memo.headline 为 "Urgent: Implement ₹0 clearance markdown on Apple iPhone 16 (128GB Blue)"，key_rationale 给出 "₹64,800 clearance" 论述；而 price_action=No Stock、价格未动、lift=0。
- 影响：学生演示弹窗直接展示错误经营指令（对卖无可卖的 SKU 下 ₹0 清仓令），与主张 3 "no phantom markdown" 直接矛盾。
- 证据：实测售罄行 memo 字段全文（见上）；reason_generator 仅按 action 之外的逻辑选择文案。
- 修复方向：为 "No Stock" 增加专用文案分支，或在 analytics 重标注后不再重生成 memo；补一条断言 memo 与 action 一致的测试。

### B2（MAJOR）api.json 声明虚假：GET ?model_source= 未做 422 校验
- 位置：`api.json` 元数据块 "//model_sources"；`api/routes/analytics.py` 各 GET 端点签名（查询参数未用 Literal/校验）。
- 问题：实测 /api/summary?model_source=garbage → 200；/api/optimizations?model_source=GRBAGE → 200；/api/optimizations/refresh?model_source=nonsense → 200（静默按 synthetic 处理）。仅 POST body 字段是 Literal 类型。
- 影响：契约文档与真实行为不符；演示中对错误模型源无反馈。
- 修复方向：GET 查询参数改为 Literal 类型或显式校验后 raise 422；或修正 api.json 文字。

### B3（MAJOR）审计 §4 的 argmax 不变量主张为 FALSE，且其测试恰好跳过违规行
- 位置：`BACKEND_AUDIT.md` §4（"published profit_curve argmax equals recommended_price for every SKU"）；`tests/test_api_endpoints.py` test_economic_invariants_hold（含 `if row["price_action"] == "No Stock": continue`）。
- 问题：售罄 SKU argmax=56700.0 ≠ recommended_price=64800.0（其余 7 个 SKU 相等）。测试用跳过条件排除了唯一违规行，因此"通过"不代表主张成立。
- 影响：售罄 SKU 的公开收益曲线与发布的推荐价矛盾；面向演示的"每个 SKU 都满足"主张站不住。
- 修复方向：对售罄 SKU 明确定义曲线语义（标注 N/A 或令一致），修正审计文字；测试补充对 No Stock 场景的显式断言而非跳过。

### B4（MAJOR）load_retail_state 未 force 刷新：event/reset 路径可陈旧
- 位置：`api/routes/analytics.py` /api/lifecycle-event 与 /api/reset-events（仅 compute_optimizations(force=True)）；对比 /api/optimizations/refresh（含 load_retail_state(force=True)）。
- 问题：临时目录实验：改 CSV 副本后，summary 与两个事件端点仍报 541；仅 refresh 采纳新值（500）。即"重新生成 CSV 后"经事件路径看不到新数据。
- 影响：演示/运行中数据更新后，事件响应与摘要可能长时间陈旧，需手动调 refresh 才恢复。
- 修复方向：事件与 reset 路径同样调用 load_retail_state(force=True)，或让 compute_optimizations 强制刷新零售状态。

### B5（MAJOR，文档不实）审计 §8 "duplicate SimulationRequest removed" 为 FALSE
- 位置：`api/routes/analytics.py` 第 594 行与第 761 行两份 `class SimulationRequest`；路由绑定在 771 行使用第二份。594 行那份有校验但无引用（死代码）。
- 影响：行为当前正确（两份校验一致），但审计声明失实 + 死代码误导后续维护。
- 修复方向：删除 594 行死代码，保留绑定版本；修正审计文字。

### MINOR
- `api/routes/analytics.py`（simulate 请求模型）：`price=true` 被强转为 1.0 返回 200；`price="79999"` 字符串亦被接受。建议 StrictFloat/显式类型校验。
- `frontend/index.html` 337–343 行 action-filter 无 "No Stock" 选项、344–348 行 risk-filter 无 "Stockout" 选项 → 售罄 SKU 只能经 "all" 看到，无法筛选。
- `frontend/js/app.js` 约 626 行 renderActionDistributionChart 兜底写死 4 键分布（{'Increase Price': 7, 'Hold Price': 0, 'Slight Reduction': 1, 'Clearance Markdown': 0}）与 4 色板，与 5+ 键新词表不匹配，建议动态生成。
- `frontend/index.html` 227 行静态占位 "+0.0% vs Status Quo"、241 行 "0"（渲染后被覆盖，纯占位残留）。
- `.gitignore` 新增 `_*probe*.py`、`audit_*` 等临时文件模式，与 §8 "scratch files were deleted" 表述相抵（文件已删、模式保留，无害）。

## 5 BLOCKER / MAJOR / MINOR 汇总（按阻断度排序）

1. BLOCKER B1 售罄 SKU memo 幻影降价（用户可见，直接矛盾主张 3）
2. MAJOR B2 api.json GET model_source 422 声明不实
3. MAJOR B3 argmax 不变量主张不实 + 测试跳过违规行
4. MAJOR B4 事件/reset 路径零售状态可陈旧
5. MAJOR B5 重复 SimulationRequest 未移除（声明不实 + 死代码）
6. MINOR 布尔/字符串 price 强转；筛选器缺 No Stock/Stockout；图表兜底写死；静态占位；.gitignore 残留模式

## 6 What I could not verify（未覆盖与原因）

- `frontend/js/shell.js`、`frontend/REVIEW_upgrade.md`：与本次后端修复主张无直接映射，未核。
- `changes.md` 与 BACKEND_AUDIT §7 逐条细节、`src/models/demand_forecaster.py`/`lifecycle_optimizer.py`/`kaggle_pipeline.py` 的 diff 全文：仅经端点行为间接覆盖，未逐行核。
- 仿真器与优化器成本模型约 8.5% 一致率：未复现（时间用于缓存/回归判别等更高证据价值项）。
- 未测的输入面：`price=NaN`、`inventory=999999999`、缺失 body、错误 Content-Type、`product_id=""`。
- `total-gain-badge` 元素 id 是否存在于 index.html 且被更新：未核完（已核对占位文本与部分 id，未定位该 id）。
- kpi-risk-skus 前端算术对 "Stockout" 的求和：renderOverview 读取 Stockout 键已核，完整求和路径未逐行核。
- 重复 SimulationRequest 在 OpenAPI schema 中哪一个生效：未核。

## 7 Fixes I applied（本次我实际应用的修复）

无。本角色为独立审阅（只读复核 + 发现），未改动任何交付物代码；全部修复方向已列于第 4 节。探测脚本仅写入 %TEMP%，项目目录未落盘临时文件（一个临时 baseline 文件已删除并确认）。
