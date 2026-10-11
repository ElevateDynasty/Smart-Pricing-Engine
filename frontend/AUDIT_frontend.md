# AUDIT — ApexPricing static front-end

Scope: `frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js` only.
Method: full read of all three files (no skimming), plus regex extraction of ids/selectors/tokens and cross-check of every JS-referenced id against the HTML.
Line numbers are 1-based and refer to the current files. No file was modified except this report.

File facts (verified: `[System.IO.File]::ReadAllText` + `Get-Content` agree; all files LF-only, UTF-8, 0 CRLF):

| File | Total lines | Non-blank | Bytes |
|---|---|---|---|
| `index.html` | 645 | 607 | 36,381 |
| `css/style.css` | 1778 | 1543 | 40,060 |
| `js/app.js` | 1180 | 1039 | 48,736 |

---

## 1. View inventory

`index.html` contains **6 `<section>` elements**, **63 unique `id` attributes**, 3 `<canvas>`, 5 `<table>`, 4 `<select>`, 2 `<input>`, 24 `<button>`, 25 `onclick`, 2 `oninput`, 4 `onchange`, 5 `<tbody id>`.

### 1.0 Chrome / shell (outside the view container)

| Element (line) | id / class | Content |
|---|---|---|
| (25) | `#scroll-progress` `.scroll-progress` | 2px fixed top bar; `aria-hidden="true"`; scaled by JS |
| (28) | `.bg-fx` (`aria-hidden="true"`) | `.fx-orb-a`, `.fx-orb-b`, `.fx-grid` ambient background |
| (35) | `header.mobile-header` | `.brand-monogram` (`.mono-symbol` "AP", `.brand-wordmark` "ApexPricing"), `#mobile-menu-toggle` (40) |
| (43) | `.app-shell` | flex shell wrapping sidebar + main |
| (47) | `#sidebar-backdrop` | mobile scrim |
| (50) | `aside#sidebar` | `.brand-lockup` (`.brand-icon-box`, `.brand-title` "APEXPRICING", `.brand-status-badge` "ONLINE • METRO-IN" + `.pulse-beacon`), `.system-telemetry-box` (67–81: "CORE ENGINE" `LGBM-2.4-M`, "CONSTRAINTS" `MRP STRICT`, "LATENCY" `< 2.1ms`, "DATA SOURCE" `#telemetry-dataset` = "SYNTHETIC"), `nav.nav-system` (84) with `.nav-header-label` "CONTROL PLANES" and `ul.nav-list` (86, see §2), `.sidebar-bottom` (110): `#btn-reoptimize` (112) + `.legal-compliance-meta` (116) |
| (125) | `header.utility-bar` | `.scope-tag` "REGION: INDIA ELECTRONICS", `.scope-divider` "/", `#current-view-title` (129, initial text "Portfolio Summary"), `#live-clock` (132, initial "--:--:--"), `.source-toggle` (133, `role="tablist"` with `#src-synthetic` (134, `class="source-btn active"`) and `#src-kaggle` (135)), "Simulate Launch Signal" and "Sync Data" buttons |
| (147) | `section#tech-launch-banner.market-signal-wire.hidden` | `aria-live="polite"`; `.wire-tag` "MARKET SIGNAL // SUCCESSOR ANNOUNCED" + `.pulse-beacon.beacon-alert`; `#banner-title` h4 (static "Apple Keynote: iPhone 18 Series Announced"); `#banner-desc` p; actions → `app.inspectActiveEvent()`, `app.resetLifecycleEvents()` |
| (168) | `#loading-overlay.skeletal-overlay.hidden` | `.skeletal-shimmer-card` with 2 `.shimmer-line` + 3 `.shimmer-box` |
| (563) | `#memo-modal.modal-backdrop.hidden` | XAI memo dialog; `#modal-content` is the injection point; buttons → `app.closeModal()`, `app.simulateFromModal()` |
| (586) | `#launch-modal.modal-backdrop.hidden` | Tech-launch ingestion dialog; 3 `.signal-event-card` → `app.triggerTechEvent('iphone18' | 'galaxy_s27' | 'pixel11')`; footer → `app.closeLaunchModal()`, `app.resetLifecycleEvents()` |
| (643) | `script src="./js/app.js" defer` | single JS entry |

### 1.1 `#views-container` (181)

**View 1 — `#view-overview.view.active` (183)** — heading `h1.display-headline` "Lifecycle Profit Maximization & Clearance Balancing" (189) + `.metadata-crumbs` "SYSTEM OVERVIEW • MULTI-STORE RETAIL HARNESS" + `.editorial-subtext`.
Shows: (a) `.metric-ribbon` — 4 `.metric-strip-item` carrying 8 KPI slots: `#kpi-profit-lift` (205) + `#kpi-profit-lift-pct` (206), `#kpi-inventory-units` (210) + `#kpi-inventory-value` (211), `#kpi-total-skus` (215) + `#kpi-actions-summary` (216, static "7 Price Increases • 1 Markdown"), `#kpi-risk-skus` (220) + `#kpi-risk-subtext` (221); (b) panel "Net Profit Distribution by SKU" + static `.mono-badge.badge-accent` "+129.6% Total Gain" (233) + `canvas#profitComparisonChart` (236); (c) panel "Pricing Policy Breakdown" + static `.mono-badge` "Solver: LGBM Demand + Constrained Grid Search" + `.doughnut-fit` + `canvas#actionDistributionChart` (249); (d) panel "Prioritized Strategic Opportunities" with a "View Complete Matrix" button → `app.switchView('sku-pricing')` and `tbody#top-opportunities-body` (278) under 7 `<th>` (PRODUCT & VARIANT, CURRENT PRICE, RECOMMENDED, EXPECTED LIFT, STRATEGY, CLEARANCE PROB, ACTION).

**View 2 — `#view-sku-pricing.view.hidden` (287)** — heading `h2.section-headline` "Catalog SKU Matrix" + subtext "Optimal price points bounded strictly by Legal Metrology Maximum Retail Price caps."
Shows: (a) `.filter-wire-toolbar` (297) with `input#sku-search-input` (304), `select#brand-filter` (307, options all/Apple/Samsung/Google/OnePlus/Xiaomi), `select#action-filter` (315, options all/"Increase Price"/"Hold Price"/"Slight Reduction"/"Clearance Markdown"), `select#risk-filter` (322, options all/"Low Risk"/"Medium Risk"/"High Risk"); (b) panel with `tbody#sku-table-body` (347) under 8 `<th>` (PRODUCT IDENTIFIER, CURRENT, AI OPTIMAL, NET LIFT, HORIZON RUN-RATE, INVENTORY STATE, LEGAL MRP, AUDIT); nav-resize "Re-Calculate All" button → `app.refreshOptimizations()`.

**View 3 — `#view-simulator.view.hidden` (356)** — heading "Empirical Elasticity & Demand Simulator" + subtext "Simulate real-time revenue and net margin responses across candidate pricing tiers."
Shows: (a) `.console-column` panel "Simulation Parameters": `label for="sim-product-select"` (372), `select#sim-product-select` (373, empty, populated by JS), `.slider-instrument` with `#sim-price-display` (381, static "₹78,500"), `input#sim-price-slider` (383, `type=range min=50000 max=90000 step=100`), `#sim-min-price` (385), `#sim-mrp-price` (386); `.stepper-cluster` 5 buttons (−₹2,000, −₹500, "AI Optimal", +₹500, +₹2,000); `.spec-matrix-box` rows `#sim-unit-cost`, `#sim-mrp-limit`, `#sim-comp-price`, `#sim-days-successor`, `#sim-inventory`; (b) `.visualizer-column`: 4 `.telemetry-tile` → `#sim-result-demand` (427), `#sim-result-margin` (431), `#sim-result-profit` (435), `#sim-result-clearance` (439); panel "Expected Profit & Demand Response Curve" with static `.legend-cluster` (449–451) and `canvas#simulatorCurveChart` (455).

**View 4 — `#view-competitors.view.hidden` (463)** — heading "Market Parity & Competitor Radar" + subtext "Cross-channel positioning against Amazon, Flipkart, Croma, and Vijay Sales."
Shows: one panel, `tbody#competitor-table-body` (485) under 7 `<th>` (PRODUCT, OUR CURRENT, AI RECOMMENDATION, MARKET AVERAGE, MARKET FLOOR, LEGAL MRP, POSITIONING STRATEGY).

**View 5 — `#view-transfers.view.hidden` (494)** — heading "Multi-Store Balancing Engine" + subtext naming scipy HiGHS + `.mono-badge.badge-accent` "Solver: LP Transportation".
Shows: (a) panel "Recommended Transfer Plan" with `#transfer-total-benefit` (509, static "Net Benefit: ₹0") and `tbody#transfers-body` (524) under 7 `<th>` (PRODUCT, FROM STORE, TO STORE, UNITS, LOGISTICS, NET BENEFIT, RATIONALE); (b) panel "Store-Level Supply Health" with `tbody#store-health-body` (551) under 7 `<th>` (PRODUCT, STORE, CITY, INVENTORY, VELOCITY, DAYS SUPPLY, STATUS).

---

## 2. Navigation mechanics

**Binding.** `bindEvents()` (`app.js:175`) does `document.querySelectorAll('.nav-list li')` (**app.js:177**) and attaches a `click` listener per item that reads `data-view` and calls `this.switchView(viewId)` (**app.js:182**). Nav markup is `ul.nav-list` (index.html:86) with five `li` (87, 91, 95, 99, 103) carrying `data-view="overview|sku-pricing|simulator|competitors|transfers"` and ids `#nav-overview`…`#nav-transfers`. `#nav-overview` has the static `class="active"` (87).

**Switching — `switchView(viewId)` (`app.js:205`)** performs, in order:
1. `this.state.activeView = viewId`.
2. Active-highlight loop over `document.querySelectorAll('.nav-links li')` (**app.js:209**).
3. `document.querySelectorAll('.view').forEach(v => v.classList.remove('active'))` (218) then `targetView.classList.add('active')` (221) on `#view-${viewId}`.
4. Breadcrumb: `titles` map (226–232) → `#current-view-title` (233–235): `overview`→"Executive Overview", `sku-pricing`→"Catalog Recommendations", `simulator`→"Real-Time Demand Simulator", `competitors`→"Competitor Intelligence", `transfers`→"Multi-Store Balancing"; fallback `'Dashboard'`.
5. Closes the mobile drawer: `sidebar.classList.remove('open')`, `backdrop.classList.remove('active')` (238–243).
6. `window.dispatchEvent(new Event('resize'))` (246) so Chart.js re-measures hidden canvases.
7. `requestAnimationFrame(() => this.prepareViewReveals(viewId))` (249).

**Defects verified:**

- **`.nav-links` does not exist.** `app.js:209` queries `.nav-links li`; the only nav list in the document is `.nav-list` (`index.html:86`). Zero matches → the declared `active` class is never moved. `#nav-overview` keeps `class="active"` (index.html:87) permanently, so the sidebar always highlights "Portfolio Summary" after any navigation. (Confirmed by exact-string grep: `nav-links` appears only at app.js:209; `nav-list` only at app.js:177 and index.html:86.)
- **No router.** Grep for `location.hash`, `history.`, `popstate`, `hashchange` in `app.js`: **0 hits**. No URL fragment is written or read, so there is no deep-linking, no back/forward support, no reload persistence of the current view (a reload always returns to `overview`, the only view with `active` in the HTML).
- **`.hidden` class on views is inert.** Views 2–5 are declared `class="view hidden"` (287, 356, 463, 494), but `style.css` defines `.hidden` only as `.market-signal-wire.hidden` (411), `.modal-backdrop.hidden` (1037) and `.skeletal-overlay.hidden` (1161) — there is **no** generic `.hidden` rule and no `.view.hidden` rule. Visibility is governed solely by `.view { display: none; animation: fadeInView … }` (759–762) / `.view.active { display: block }` (764–766). The `hidden` class is therefore a no-op today, but any future global `.hidden { display: none }` would break all view switching.
- **Not keyboard-accessible.** Nav items are `<li>` with `cursor: pointer` (CSS 286–306) — not focusable, no `role`, no `tabindex`, no `aria-current`, no keydown handler. Grep in `app.js` for `keydown|keyup|keypress|Escape|tabindex|aria-|focus(`: **0 hits**. A keyboard-only user cannot change views. Only the true `<button>` elements are reachable, and the 5 view-switch entry points available from buttons are: "View Complete Matrix" (index.html:270) and `simulateFromModal()` (app.js:1143) → `simulator`, plus event-triggered jumps (app.js:418).
- **Mobile drawer:** `#mobile-menu-toggle` toggles `sidebar.open` + `backdrop.active` (app.js:190–196); backdrop click closes (198–201). CSS: `.sidebar` becomes `position: fixed; transform: translateX(-100%)` at ≤900px (CSS 1240–1252), `.sidebar.open` → `translateX(0)` (1253); `.sidebar-backdrop` is `display:none` (141) and `.active` → `display:block` (146). No Escape-to-close, no focus trap, no scroll lock, `aria-expanded` absent.
- **Back-button / re-entry:** because `switchView` is also called from `simulateFromModal` (1149), `triggerTechEvent` (418) and the overview's button (index.html:270), a rewrite must keep `switchView(viewId)` as the single chokepoint or replicate all four call sites.
- **Breadcrumb mismatch:** the initial HTML text is "Portfolio Summary" (index.html:129) but the first `switchView` paints "Executive Overview" (app.js:224). Two different labels for the same view depending on whether the user has navigated.

---

## 3. JS ↔ DOM contract table

`app.js` contains **66 `getElementById(...)` calls** covering **51 unique literal ids** plus 1 dynamic template id, **4 `querySelectorAll` calls**, **0 `querySelector`**, **18 `innerHTML` writes**. Cross-check result: **all 51 literal ids + the dynamic `view-${viewId}` family (view-overview, view-sku-pricing, view-simulator, view-competitors, view-transfers) exist in `index.html` — 0 missing.** Every write is guarded by an existence check (23 guard clauses).

| id | RW | Purpose | In index.html |
|---|---|---|---|
| `scroll-progress` | W | `style.transform = scaleX(ratio)` on scroll/resize (app.js:50–61) | ✔ 25 |
| `mobile-menu-toggle` | R+listen | click → toggle drawer (190) | ✔ 40 |
| `sidebar` | W | add/remove `open` (191, 200, 242) | ✔ 50 |
| `sidebar-backdrop` | W+listen | add/remove `active` (195, 200, 242) | ✔ 47 |
| `telemetry-dataset` | W | textContent = `SYNTHETIC` / `REAL KAGGLE` (265) | ✔ 79 |
| `current-view-title` | W | breadcrumb text (236) | ✔ 129 |
| `live-clock` | W | `toLocaleTimeString('en-IN',{hour12:false})`, 1 Hz (36–48) | ✔ 132 |
| `src-synthetic` | W | toggle `active` (260) | ✔ 134 |
| `src-kaggle` | W | toggle `active` (261) | ✔ 135 |
| `tech-launch-banner` | W | toggle `hidden` (344–358) | ✔ 147 |
| `banner-title` | W | `ev.headline` (352) | ✔ 153 |
| `banner-desc` | W (innerHTML) | successor/days sentence (353) | ✔ 154 |
| `loading-overlay` | W | toggle `hidden` (1156–1161) | ✔ 168 |
| `kpi-profit-lift` | W | `+₹…` (466) + count-up (107–117) | ✔ 205 |
| `kpi-profit-lift-pct` | W | `+X% vs Status Quo baseline` (467) + count-up | ✔ 206 |
| `kpi-inventory-units` | W | `N units` (468) + count-up | ✔ 210 |
| `kpi-inventory-value` | W | `Catalog Value: ₹…` (469) | ✔ 211 |
| `kpi-total-skus` | W | `N SKUs` (470) + count-up | ✔ 215 |
| `kpi-actions-summary` | W | `N Increases \| N Markdowns` (473) | ✔ 216 |
| `kpi-risk-skus` | W | `N SKUs` (479) + count-up | ✔ 220 |
| `kpi-risk-subtext` | W | `N Medium \| N High Urgency` (480) | ✔ 221 |
| `profitComparisonChart` | R (canvas) | bar chart ctor/destroy (488–558) | ✔ 236 |
| `actionDistributionChart` | R (canvas) | doughnut ctor/destroy (560–607) | ✔ 249 |
| `top-opportunities-body` | W (innerHTML) | top-3 rows (609–640) | ✔ 278 |
| `sku-search-input` | R | filter text (715) | ✔ 304 |
| `brand-filter` | R | filter brand (716) | ✔ 307 |
| `action-filter` | R | filter action (717) | ✔ 315 |
| `risk-filter` | R | filter risk (718) | ✔ 322 |
| `sku-table-body` | W (innerHTML) | SKU rows (642–712) + error state + empty state | ✔ 347 |
| `sim-product-select` | R+W | options + value (839–855, 1149) | ✔ 373 |
| `sim-price-display` | W | `₹…` (940) | ✔ 381 |
| `sim-price-slider` | R+W | min/max/step/value + inline `style.background` (152–160, 879–887, 901–931) | ✔ 383 |
| `sim-min-price` | W | `Cost: ₹…` (889) | ✔ 385 |
| `sim-mrp-price` | W | `MRP: ₹…` (890) | ✔ 386 |
| `sim-result-demand` | W (innerHTML) | `N.N <small>units/day</small>` (964) | ✔ 427 |
| `sim-result-margin` | W | `₹…` (965) | ✔ 431 |
| `sim-result-profit` | W | `₹…` (966) | ✔ 435 |
| `sim-result-clearance` | W (innerHTML) | `N <small>days</small>` (967) | ✔ 439 |
| `simulatorCurveChart` | R (canvas) | dual-axis line ctor/destroy (970–1058) | ✔ 455 |
| `competitor-table-body` | W (innerHTML) | parity rows (740–775) | ✔ 485 |
| `transfer-total-benefit` | W | `Net Benefit: +₹… · N transfers` (831) | ✔ 509 |
| `transfers-body` | W (innerHTML) | transfer rows (777–828) | ✔ 524 |
| `store-health-body` | W (innerHTML) | store supply rows (790–813) | ✔ 551 |
| `memo-modal` | W | toggle `hidden` (1061–1135) | ✔ 563 |
| `modal-content` | W (innerHTML) | memo + XAI bars (1090–1130) | ✔ 578 |
| `launch-modal` | W | toggle `hidden` (360–368) | ✔ 586 |
| `sim-unit-cost` | W | `₹…` (891) | ✔ 401 |
| `sim-mrp-limit` | W | `₹…` (892) | ✔ 405 |
| `sim-comp-price` | W | `₹…` (893) | ✔ 409 |
| `sim-days-successor` | W | `N days` (894) | ✔ 413 |
| `sim-inventory` | W | `N units` (895) | ✔ 417 |
| `view-${viewId}` (dynamic) | R+W | add/remove `active` (218–222); reveal prep (79) | ✔ ×5 |

**Selectors read by JS:** `.nav-list li` (177, exists), `.nav-links li` (209, **does not exist**), `.view` (218, exists), `.reveal`-eligible selector list (87–96: `.terminal-banner`, `.metric-ribbon .metric-strip-item`, `.split-analytics-grid > .architectural-panel`, `.architectural-panel.mt-6`, `.architectural-panel.mt-4`, `.view-header-strip`, `.filter-wire-toolbar`, `.simulator-cockpit-grid > *`, `.telemetry-tiles-grid .telemetry-tile` — all present in markup).

**Classes JS adds/removes:** `active` (views, nav li, source buttons, backdrop), `open` (sidebar), `hidden` (banner, overlay, both modals), `reveal` / `revealed` (reveal system), `animating` (KPI count-up), `pop` (sim tiles), `row-enter`, `row-urgent-event` (table rows), `price-up` / `price-down` / `price-hold`, `risk-low` / `risk-medium` / `risk-high`, `badge badge-primary|badge-danger|badge-success|badge-warning`, `xai-bar-pos` / `xai-bar-neg`, `text-success`, `text-warning`, `text-accent`, `font-semibold`, `mono-num`.
**Inline styles JS writes:** `tr.style --rd` stagger, `el.style --d` stagger, `slider.style.background` gradient, `el.style.transition`.

**Declared but never touched by JS:** `#btn-reoptimize` (112), `#views-container` (181), `#nav-*` ids (87–103), `.legal-compliance-meta`.

---

## 4. Data layer

**Backend-dependent; there is no embedded/fallback dataset in `app.js`.** `const API_BASE = '/api';` is the only base (`app.js:6`) — relative, so calls resolve against the page origin.

Exact fetch calls:

| # | Method + URL (as written) | Line | Envelope handling |
|---|---|---|---|
| 1 | `` fetch(`${API_BASE}/summary?model_source=${src}`) `` → `/api/summary?model_source=synthetic\|kaggle` | 277 | `state.summary = await summaryRes.json()` |
| 2 | `` fetch(`${API_BASE}/optimizations?model_source=${src}`) `` → `/api/optimizations?model_source=…` | 278 | `optData.data` → `state.optimizations`; `optData.active_events` → `state.activeEvents` |
| 3 | `` fetch(`${API_BASE}/transfers`).catch(() => null) `` → `/api/transfers` | 279 | `transfersData.data` → `state.transfers`; failure tolerated |
| 4 | `` fetch(`${API_BASE}/optimizations/refresh?model_source=${src}`, { method: 'POST' }) `` | 317 | `res.json()` reused as `optData` |
| 5 | `` fetch(`${API_BASE}/lifecycle-event`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) }) `` | 408–412 | payload keys: `product_id`, `successor_name`, `announcement_headline`, `days_to_successor`, `competitor_price_drop_pct` |
| 6 | `` fetch(`${API_BASE}/reset-events`, { method: 'POST' }) `` | 428 | result ignored |

1–3 run under `Promise.all` inside `loadData()` (272–311); 2 and 3 are read once; if `!summaryRes.ok || !optRes.ok` it throws (283–285). After success it renders in this order: `renderOverview()`, `renderTable()`, `renderCompetitors()`, `renderTransfers()`, `renderTechBanner()`, `initSimulator()`, `animateKPIs()`, then `prepareViewReveals('overview')` (297–304).

**`state` shape (`app.js:9–20`):** `optimizations: []`, `summary: {}`, `filtered: []`, `activeEvents: []`, `transfers: []`, `activeView: 'overview'`, `currentSimSku: null`, `activeModalSku: null`, `simPrice: 0`, `modelSource: 'synthetic'`.
**`charts` shape (22–26):** `profitComparison: null`, `actionDistribution: null`, `simulatorCurve: null`.

**Required API field names (hard contract, read from `optData.data[]` items):** `product_id`, `product_name`, `current_price`, `recommended_price`, `price_change`, `profit_lift_amount`, `profit_lift_pct`, `price_action`, `clearance_probability`, `expected_sales_horizon`, `expected_daily_demand`, `days_to_successor`, `current_inventory`, `inventory_risk_level`, `mrp`, `unit_cost`, `competitor_avg_price`, `competitor_min_price`, `status_quo_profit`, `expected_lifecycle_profit`, `elasticity` (optional, default 2.0), `feasible_prices[]`, `profit_curve[]`, `demand_curve[]`, `active_event` (optional object with `successor_name`), `business_reason`, `brand` (optional), `memo.{headline,key_rationale,offline_advantage}`, `xai.{method,base_value,top_factors[]{feature,direction:'positive'|'negative',contribution,abs_contribution}}`. From `/transfers`: per-SKU `{product_name, stores_summary[]{store_name,city,current_inventory,daily_sales_velocity,days_of_supply,status}, recommended_transfers[]{from_store_name,to_store_name,transfer_units,transfer_cost,net_benefit,reason}}`. `summary` needs at minimum `total_profit_lift`, `avg_profit_lift_pct`, `total_inventory_units`, `total_inventory_value`, `total_skus`, `action_counts`, `risk_counts`.

**Offline / API-down behaviour (all paths verified in code):**
- `loadData` catches → `console.error("Failed to load AI pricing data:", error)` (306) → `renderErrorState()` (307).
- `renderErrorState()` (1163–1178) writes **only** into `#sku-table-body`: an exclamation icon, heading "Could not connect to AI Engine API", text "Please ensure the FastAPI backend is running on `http://localhost:8000`" and a "Retry Connection" button → `app.loadData()`. Note the hardcoded `localhost:8000` in the message versus the relative `/api` base — the two only agree if FastAPI serves the static files itself (inference, not stated anywhere in the file).
- Everything else silently keeps its static placeholder: KPIs stay `₹0` / `0` / `0 SKUs`, charts never instantiate (blank canvases), `#top-opportunities-body`, `#competitor-table-body`, `#transfers-body`, `#store-health-body` stay empty, simulator select stays empty, banner stays hidden. The clock still ticks (local).
- `showLoading(false)` is in `finally` (309) → no stuck overlay.
- **On the other three endpoints the failure is completely invisible to the user:** `refreshOptimizations` catch only `console.error("Refresh error:", error)` (338); `triggerTechEvent` → `console.error("Failed to trigger tech event:", err)` (415); `resetLifecycleEvents` → `console.error("Failed to reset events:", err)` (431). No error state, no toast.
- If Chart.js (CDN, `index.html:18`) is blocked, `new Chart(...)` throws inside `renderOverview` → caught by `loadData` → the user sees the *connection* error even though the API is healthy (misleading message).

**Only literal "fallbacks" in JS** (not data sources): doughnut labels `this.state.summary.action_counts || { 'Increase Price': 7, 'Hold Price': 0, 'Slight Reduction': 1, 'Clearance Markdown': 0 }` (562–567); `sku.elasticity || 2.0` (947); memo text defaults `memo.headline || \`Pricing Guidance: ${sku.product_name}\``, `memo.key_rationale || sku.business_reason`, `memo.offline_advantage || 'In-store touch-and-feel inspection and instant setup justify this price point.'` (1094–1104); `xai.method || 'TreeSHAP'`, `(xai.base_value ?? 0)` (1082).

---

## 5. Charts (Chart.js 4.4.1, loaded `index.html:18`)

Chart.js global defaults are mutated once, in `renderProfitComparisonChart` (503–504): `Chart.defaults.color = '#94a3b8'`, `Chart.defaults.font.family = "'Inter', sans-serif"`. Every chart destroys its previous instance before recreating (`if (this.charts.X) this.charts.X.destroy()`).

**C1 — `#profitComparisonChart` (236), `renderProfitComparisonChart` (488).** Type `bar`.
- Labels: `o.product_name.split(' (')[0]` with `'Apple '`, `'Samsung '`, `'Google '` stripped (492–494).
- Dataset 1 `'Status Quo Baseline (₹)'` ← `o.status_quo_profit`; `backgroundColor: 'rgba(148, 163, 184, 0.3)'`, `borderColor: '#64748b'`, `borderWidth: 1`, `borderRadius: 6`.
- Dataset 2 `'AI Optimized Net Profit (₹)'` ← `o.expected_lifecycle_profit`; `backgroundColor: 'rgba(99, 102, 241, 0.85)'`, `borderColor: '#6366f1'`, `borderWidth: 1`, `borderRadius: 6`.
- Options: `responsive: true`, `maintainAspectRatio: false`, `animation {duration:850, easing:'easeOutQuart'}`, legend top (`boxWidth:12, padding:14, font.size:12`), tooltip label callback → `` `${context.dataset.label}: ${this.formatCurrency(context.raw)}` ``, scales: `y` `beginAtZero:true`, grid `rgba(255,255,255,0.05)`, ticks callback → `` `₹${(val/100000).toFixed(1)}L` ``, `x` `grid.display:false`.

**C2 — `#actionDistributionChart` (249), `renderActionDistributionChart` (560).** Type `doughnut`.
- Labels/values: `Object.keys/values` of `summary.action_counts` (or the literal fallback above).
- `backgroundColor: ['#10b981','#f59e0b','#06b6d4','#ef4444']` **positional, not keyed** — if the API returns a different key order/count the colours silently mismatch. `borderWidth: 2`, `borderColor: '#11192e'`.
- Options: `responsive:true`, `maintainAspectRatio:false`, `cutout:'68%'`, `animation {animateRotate:true, duration:950, easing:'easeOutQuart'}`, legend bottom (`boxWidth:10, padding:12, font.size:11`). No tooltip callback.

**C3 — `#simulatorCurveChart` (455), `renderSimulatorCurves` (970).** Type `line`, dual y-axis. Bail-out guard: `if (!ctx || !sku || !sku.feasible_prices) return;` (972).
- Labels: `sku.feasible_prices.map(p => \`₹${p.toLocaleString('en-IN')}\`)` (pre-formatted strings).
- Dataset 1 `'Projected Net Profit (₹)'` ← `sku.profit_curve`; `borderColor:'#6366f1'`, `backgroundColor:'rgba(99,102,241,0.1)'`, `fill:true`, `tension:0.35`, `yAxisID:'yProfit'`, `pointRadius:2`, `pointHoverRadius:6`.
- Dataset 2 `'Daily Demand (Units)'` ← `sku.demand_curve`; `borderColor:'#06b6d4'`, `backgroundColor:'transparent'`, `borderDash:[4,4]`, `tension:0.3`, `yAxisID:'yDemand'`.
- Options: `animation {duration:750, easing:'easeOutQuart'}`, `interaction {mode:'index', intersect:false}`, `legend.display:false`, tooltip callback branches on `context.dataset.yAxisID` (`Net Profit: ₹…` vs `Daily Demand: N.N units/day`); scales `x` grid `rgba(255,255,255,0.05)` + `maxTicksLimit:7`; `yProfit` linear/left, grid, `₹L` ticks; `yDemand` linear/right, `grid.drawOnChartArea:false`, ticks `` `${val.toFixed(0)} u/d` ``.
- The panel's visible legend (`.legend-cluster`, index.html:449–451) is **static HTML and does not match**: `.bg-cyan` = `--accent-signal` #00e5ff (CSS 1008) and `.bg-white` = #cbd5e1 (1009), whereas the series are #6366f1 and #06b6d4. Chart.js's own legend is disabled for this chart.

**Chart canvases are never given `role`/`aria-label`/fallback text.**

---

## 6. Interactions

All handlers are inline HTML attributes calling the global `app` object (25 `onclick`, 2 `oninput`, 4 `onchange`). `app.init()` runs on `DOMContentLoaded` (app.js:1180); `app.js` is loaded with `defer` (index.html:643).

| # | Interaction | Trigger | Handler (line) | Effect |
|---|---|---|---|---|
| 1 | Sidebar view switch | click `.nav-list li` | `switchView` (205) | §2 |
| 2 | Mobile drawer | `#mobile-menu-toggle`, `#sidebar-backdrop` | `bindEvents` (190–201) | toggle `open`/`active` |
| 3 | Clock | `setInterval` 1 s | `startClock` (36) | `#live-clock` HH:MM:SS en-IN |
| 4 | Scroll progress bar | scroll + resize, passive | `initScrollProgress` (50) | `scaleX(top/(scrollHeight-clientHeight))` |
| 5 | Scroll reveals | `IntersectionObserver` (threshold 0.12, rootMargin `0px 0px -6% 0px`) | `initRevealObserver` (64) / `prepareViewReveals` (76) | adds `.reveal` + `--d` stagger (i×70 ms, cap 490) then `.revealed`, unobserves |
| 6 | KPI count-up | on load/refresh | `animateKPIs` (105), `animateValue` (128) | easeOutCubic over 950+i·120 ms; honours `prefers-reduced-motion`; toggles `.animating` |
| 7 | Data-source segmented control | `#src-synthetic` / `#src-kaggle` | `switchDataSource` (252) | no-op if unchanged; resets `currentSimSku`; toggles `active`; rewrites `#telemetry-dataset`; destroys curve chart; `await loadData()` |
| 8 | Sync / Re-Calculate / Recalculate Engine | 3 buttons (index.html 112, 140, 293) | `refreshOptimizations` (313) | POST refresh + re-GET summary, full re-render |
| 9 | SKU filters | `#sku-search-input` (oninput), 3 selects (onchange) | `filterTable` (714) | filters `optimizations` → `filtered` → `renderTable`; query vs `product_name`/`product_id`; brand exact-lowercase match on `item.brand` **or** substring of `product_name`; action exact `===` on `price_action`; risk substring on `inventory_risk_level`; **no sort, no export, no pagination, no debounce** |
| 10 | Simulator SKU pick | `#sim-product-select` onchange | `loadSimulatorProduct` (857) | sets slider `min = round(unit_cost*0.95)`, `max = round(mrp)`, `step 100`, `value = recommended_price`; fills 5 spec rows; recalc + redraw curve |
| 11 | Price slider | `#sim-price-slider` oninput | `onSliderChange` (901) | updates `state.simPrice`, inline gradient fill, local recalc |
| 12 | Stepper ±₹500/±2,000 and "AI Optimal" | 5 buttons (387–393) | `setSimPriceRel` (910), `resetSimToRecommended` (922) | clamps to slider min/max, `.pop` tile animation |
| 13 | Simulator local math | `updateSimulatorCalculations` (934) | — | `horizon=min(days_to_successor,60)`; `priceRatio=p/competitor_avg_price`; `estimatedDemand=max(0.1, expected_daily_demand * pow(max(0.5, priceRatio), -elasticity))`; `expectedSales=min(current_inventory, demand*horizon)`; `leftover`; `holdingCost=0.5*(current_inventory+leftover)*unit_cost*0.0005*horizon`; `deprecLoss=leftover*unit_cost*0.25`; `netProfit=expectedSales*unitMargin-holdingCost-deprecLoss`; `clearanceDays=current_inventory/(demand+1e-5)` |
| 14 | XAI memo modal | row buttons → `app.openModal(product_id)` | `openModal` (1061) | builds `#modal-content` innerHTML: headline, "Econometric Rationale", optional TreeSHAP bars (width = `abs_contribution/maxAbs`, max 3–100%), "Offline Store Advantage", 3 stat tiles |
| 15 | Modal dismissal | backdrop click, ✕, "Dismiss" | `closeModal` (1132), `closeModalOnBackdrop` (1137) | closes only when `e.target.id === 'memo-modal'` (so inner clicks don't close) |
| 16 | "Test In Simulator" | `app.simulateFromModal()` (1143) | closes modal, `switchView('simulator')`, sets select value, `loadSimulatorProduct()` |
| 17 | Launch modal | `app.openLaunchModal()` / `closeLaunchModal()` (360/365) | shows `#launch-modal` |
| 18 | Tech event ingestion | 3 `.signal-event-card` | `triggerTechEvent(eventKey)` (376) | hardcoded configs: `iphone18`→`SKU_IPHONE_17_256`/Apple iPhone 18/14 days/0.04; `galaxy_s27`→`SKU_GALAXY_S26_256`/Samsung Galaxy S27/21 days/0.05; `pixel11`→`SKU_PIXEL_10_PRO`/Google Pixel 11 Pro/18 days/0.03. POST then `refreshOptimizations()` then `switchView('sku-pricing')` |
| 19 | Revert events | banner button + launch-modal footer | `resetLifecycleEvents` (424) | POST `/reset-events`, refresh |
| 20 | Inspect pricing action | banner button | `inspectActiveEvent` (437) | opens memo for `activeEvents[0].product_id` |
| 21 | Banner | `renderTechBanner` (344) | shows first active event, or hides banner |

**Not present anywhere:** sorting UI, CSV/Excel/print export (grep `download|csv|export|Blob|xlsx|print(` → 0 hits), pagination, tabs other than the source toggle, drag/drop, search debounce, keyboard shortcuts, `Escape`-to-close, form validation, localStorage/sessionStorage persistence. The only `sort(` is the internal top-3 by `profit_lift_amount` (615).

---

## 7. Quality metrics & design tokens

**CSS:** 296 `{` blocks, 1024 declarations, **13 `@keyframes` declarations / 12 unique names** (`beaconPulse`, `fadeInWire`, `fadeInView` ×2, `modalBackdropFade`, `modalSlide`, `shimmerSlide`, `fxDrift`, `rowEnter`, `navIndicatorIn`, `brandGlow`, `numPop`, `xaiGrow`), **5 `!important`**: line 619 (`.row-urgent-event` background), line 1268 (`.metric-strip-item` inside the ≤600px block), and lines 1773 / 1775 / 1776 inside the `prefers-reduced-motion` block.
**Media queries (5):** `max-width:1100px` (1221), `max-width:900px` (1240), `max-width:600px` (1263), `max-width:700px` (1753), `prefers-reduced-motion:reduce` (1760, block runs to 1777). Behaviour: ≤1100 → split grid and cockpit collapse to 1 column, ribbon 2×2; ≤900 → mobile header appears and sidebar becomes off-canvas; ≤600 → ribbon 1 column, telemetry tiles 2 columns, signal wire stacks; ≤700 → XAI bar grid narrows. Note the 700px block is the last in the file (after 600px) — harmless today (different selectors) but an ordering smell.

**CSS custom properties: 29 defined, all in `:root` (12–57) plus `--ease-out-quart` re-declared in a second `:root` (1285–1287).** Usage counts in-file: `--glass-border` 33, `--font-mono` 29, `--text-secondary` 19, `--accent-signal` 17, `--bg-subtle` 16, `--bg-surface` 16, `--ease-spring` 16, `--text-muted` 16, `--duration-fast` 13, `--glass-specular` 12, `--accent-signal-border` 9, `--bg-base` 8, `--font-display` 8, `--status-negative` 8, `--status-positive` 8, `--status-warning` 7, `--accent-signal-dim` 4, `--font-body` 4, `--text-primary` 4, `--ease-out-quart` 3, `--glass-border-hover` 3, `--status-negative-dim` 3, `--status-positive-dim` 3, `--status-warning-dim` 3, `--bg-void` 2, `--bg-surface-hover` 1, `--duration-smooth` 1, `--glass-shadow` 1, **`--text-subtle` 0 (dead token, defined at 24)**.

Full token list: `--bg-void --bg-base --bg-subtle --bg-surface --bg-surface-hover --text-primary --text-secondary --text-muted --text-subtle --accent-signal --accent-signal-dim --accent-signal-border --status-positive --status-positive-dim --status-warning --status-warning-dim --status-negative --status-negative-dim --glass-border --glass-border-hover --glass-specular --glass-shadow --font-display --font-body --font-mono --ease-spring --ease-out-quart --duration-fast --duration-smooth`.

**JS:** 44 methods on the `app` object literal (+ `API_BASE`, `app`, and the `DOMContentLoaded` listener at module level), 23 defensive guard clauses, 18 `innerHTML` writes (all with template literals — note values are interpolated unescaped into HTML, i.e. no output encoding).

**Dead code / duplicates (all verified by grep):**
- `.price-indicator-up|down|hold` (CSS 647–649): **0 references** in HTML or JS.
- `.risk-pill`, `.risk-pill-low`, `.risk-pill-med`, `.risk-pill-high` (CSS 651–662): **0 references**; the live system is `.risk-tag` (CSS 1573) + `.risk-low` (1583) / `.risk-medium` (1584) / `.risk-high` (1585).
- `--text-subtle`: 0 references.
- Duplicate rule blocks (later one wins): `@keyframes fadeInView` at 768 **and** 1388; `.view.active` at 764 **and** 1393; `.brand-icon-box` at 172 **and** 1454; `.terminal-slider` at 902 **and** 1487; `.architectural-panel` 541 + 1398; `.telemetry-tile` 964 + 1399; `.metric-strip-item` 499 + 1231–1237 + 1267–1269 + 1400.
- `.nav-links li` selector (app.js:209) with no matching element (`/dev/null` path).
- Unused ids: `#btn-reoptimize`, `#views-container`, `#nav-*`.
- Static text that JS never updates and that contradicts live data: "+129.6% Total Gain" (index.html:233), "7 Price Increases • 1 Markdown" (216 — overwritten only on success), `₹78,500` (381), `LGBM-2.4-M` (67), `< 2.1ms` (75), "Solver: …" badges, the whole `.legend-cluster`.

**Accessibility gaps (evidence-based):**
- Nav `li` items are mouse-only (§2); no keyboard path to four of five views.
- Only 5 aria attributes exist in the whole document (index.html:25, 28, 40, 133, 147) plus 2 `aria-label="Close dialog"` (569, 592). No `role="dialog"`, `aria-modal`, `aria-labelledby`, `aria-expanded`, `aria-selected`, `aria-current`, `aria-sort` anywhere.
- `.source-toggle` declares `role="tablist"` (133) but its buttons have no `role="tab"`/`aria-selected` and no arrow-key handling → invalid ARIA pattern.
- `outline: none` on `#sku-search-input` (835), `.terminal-select` (857) and `.terminal-slider` (907); the only focus styling is a border-colour change on input/select (`.search-terminal-input input:focus` 839, `.terminal-select:focus` 861). **The slider has no visible focus affordance at all**; no `:focus-visible` rules exist.
- Charts: `<canvas>` elements are unlabelled and have no text alternative; all chart-encoded data is invisible to AT.
- Dynamic content (`#sku-table-body`, KPIs, tiles, tables) is not in a live region — only the banner has `aria-live="polite"` (147).
- Modals: no focus management, no Escape, no scroll lock, no `aria-modal`.
- Decorative FontAwesome `<i>` glyphs are not `aria-hidden`.
- **Contrast (computed from the hex values in `:root`, WCAG 2.1 relative-luminance formula):** `--text-muted` #57606a on `--bg-base` #090d14 ≈ **3.05:1** — fails AA (4.5:1) for normal text, and it is the colour of nearly all labels, table headers (0.68rem), telemetry keys and `.memo-stat-label` (0.62rem). `--text-secondary` #8b949e on #090d14 ≈ **6.33:1** — passes. `--accent-signal` #00e5ff on #090d14 ≈ **12.7:1** — passes.

---

## 8. Risks for a rewrite

Ordered by likelihood of silently losing behaviour.

1. **The active-nav bug is load-bearing for appearance.** `switchView` writes the highlight to `.nav-links li` (app.js:209), which does not exist; `.nav-list li` (177) is the real list. Today the sidebar always shows `#nav-overview` as active. Decide explicitly: keep the (broken) frozen highlight, or fix it by targeting `.nav-list li`. Also note view visibility depends on the `active` class while views 2–5 carry an inert `hidden` class (287, 356, 463, 494) with no CSS rule — do not introduce a generic `.hidden { display:none }` without removing those classes, or all four views will vanish.
2. **No routing means no URL contract to preserve — but four call sites feed `switchView`.** Keep one chokepoint: nav clicks (177–183), `simulateFromModal` (1149), `triggerTechEvent` (418), and the overview's "View Complete Matrix" button (index.html:270). A hash router is a safe addition, but back-button support will change what "reload" means (today: always `#view-overview`).
3. **The app is 100% API-dependent with no fallback data.** `/api` is relative (app.js:6) yet the offline message hardcodes `http://localhost:8000` (1170) — the app must be served from the FastAPI origin for either to be true. Preserve: the `data` / `active_events` envelope unwrapping (288–289), the tolerated `/transfers` failure (279), the query param `model_source`, and the fact that only `#sku-table-body` shows an error.
4. **The API field-name contract is implicit and total.** ~30 field names are read straight off response objects (§4). Any rewrite that renames or reshapes data will fail silently (rows render `undefined`, `formatCurrency(undefined)` → `₹0`). Treat §4's field list as the frozen interface.
5. **Inline handlers everywhere.** 25 `onclick` + 2 `oninput` + 4 `onchange` call the global `app` object. Any move to modules/classes breaks every one of them simultaneously; either keep a global `app` namespace or convert all 31 attributes in the same change.
6. **Client-side simulation math must be reproduced exactly** (app.js:934–967): the elasticity formula, the `max(0.5, priceRatio)` clamp, the 0.0005 holding-cost coefficient, the 0.25 depreciation rate, `horizon=min(days_to_successor,60)`, and the `e-5` clearance denominator. This is the only "engine" that runs purely in the browser, and it also drives the slider's dynamic `min`/`max` (`unit_cost*0.95` … `mrp`, step 100) and the inline gradient `slider.style.background` (152–160).
7. **The reveal system can make content permanently invisible.** `.reveal` sets `opacity: 0` (CSS 1358–1368) and only the IntersectionObserver adds `.revealed`; `prepareViewReveals` is invoked per view switch (249) and after load (304/336). If a rewrite keeps `.reveal` but drops the observer call, panels stay blank. Note the observer early-returns when `IntersectionObserver` is unsupported (65) — that path is safe only because the class is added by JS, not by markup.
8. **Chart.js is a CDN single point of failure whose absence masquerades as a backend outage.** If `chart.umd.min.js` (index.html:18) fails, `new Chart` throws inside `renderOverview` and the user sees "Could not connect to AI Engine API". Also preserve: `Chart.defaults` mutation (503–504, leaks globally), dual axes on C3, `maxTicksLimit:7`, the `₹L` tick formatter, positional doughnut colours (which silently mismatch if `action_counts` key order changes), and the fact that C3 is only drawn when `sku.feasible_prices` exists (972).
9. **Two visual legends disagree with the data.** The simulator panel's static `.legend-cluster` (index.html:449–451, CSS 1008–1009) claims #00e5ff profit / #cbd5e1 demand while the series are #6366f1 / #06b6d4; the doughnut's colours are index-based. Either drive these from one source or delete the hand-written legend.
10. **Stale hardcoded values contradict live data**: "+129.6% Total Gain" (233), "7 Price Increases • 1 Markdown" (216), `₹78,500` (381), `LGBM-2.4-M` / `< 2.1ms` (67, 75), and the breadcrumb's initial "Portfolio Summary" (129) vs "Executive Overview" (224).
11. **Logic quirk in the KPI summary:** `acts['Slight Reduction'] || acts['Clearance Markdown'] || 0` (app.js:474) is a falsy-coalesce, not a sum — a zero Slight Reduction silently reports the Clearance count. Related: `criticalCount` (478) adds `'High Risk' + 'Critical' + 'Medium Risk'` into `#kpi-risk-skus`, so "risk" there means medium-or-worse. Decide keep-vs-fix consciously.
12. **Accessibility debt is structural, not cosmetic:** mouse-only `<li>` navigation, no focus ring on the slider, modals with no dialog semantics or Escape handling, unlabelled canvases, `--text-muted` at ≈3.05:1 used for nearly all small text. A "visual rewrite" that does not address these will keep failing the same checks.

**Unknowns / not verifiable from these three files:** the actual response payloads (no fixtures or API tests were read — `api/`, `src/`, `data/` are out of scope); whether FastAPI serves `frontend/` as static files (which would reconcile `/api` with the `localhost:8000` message); whether `/api/transfers` accepts or ignores a `model_source` parameter (the client does not send one); and whether the API returns `action_counts` in the fixed key order the doughnut's colour array assumes.
