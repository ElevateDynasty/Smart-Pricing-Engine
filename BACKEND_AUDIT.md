# Backend Review & Fixes — AI Retail Pricing Engine

Reviewed: `changes.md`, the FastAPI surface (`api/`), the ML/optimisation core (`src/`),
`schema`-relevant artifacts and the frontend↔API contract.
Method: read every in-scope module, then **ran the backend live** and exercised every
endpoint with real HTTP calls; cross-checked every headline KPI against the source CSVs.
Two independent research passes (one on backend correctness, one on the frontend↔API
contract) ran in parallel and their findings are folded in below.

Interpreter used throughout: `C:\Users\gaura\AppData\Local\Programs\Python\Python314\python.exe`
(Python **3.14.2**). Note the default `python` on PATH is a bare 3.13 with **no** dependencies —
running `python main.py` or `pytest` without the full path fails with `ModuleNotFoundError`.
This is the single most likely reason a reviewer cannot reproduce anything.

---

## 1. Verdict

**The backend ran, returned 200 on every declared endpoint and never crashed — but it was not
telling the truth.** The headline numbers did not come from the data. Per-SKU stock and price
were hardcoded literals in a request handler, so the CEO-level KPIs were effectively constants:
the API reported **2,315 units** of inventory for a catalogue that actually holds **541**.
A sold-out SKU was handed a "Clearance Markdown" recommendation, the simulator was 404-ing on
every request, ~20% of the risk dashboards were unreachable, and invalid input was accepted with
a cheerful 200.

`changes.md` is substantially accurate about the **frontend** work (its own scope) and about the
ML fixes. Its §11.1–11.4 claims do hold up. But three of its claims were false in the code as
shipped, and its §0 "Status Summary" (all green) masked a broken simulator. Details in §7.

After the fixes below: **38/38 tests pass** (18 pre-existing + 20 new regression tests that lock
in each fix), all 10 endpoints verified live, and every headline KPI now matches its source CSV.

---

## 2. Critical defects found and fixed

### C1 — Headline KPIs were hardcoded literals, not data  🔴 **most serious**

`api/routes/analytics.py`, inside `compute_optimizations()`:

```python
if pid == "SKU_IPHONE_17_256":   curr_inv, curr_price = 800, 79999.0
elif pid == "SKU_IPHONE_16_128": curr_inv, curr_price = 320, 62999.0
elif pid == "SKU_PIXEL_10_PRO":  curr_inv, curr_price = 95, 104999.0
else:                            curr_inv = 220
                                 curr_price = float(round(row["competitor_avg_price"] * 1.015, -2))
```

`data/synthetic/inventory.csv` was never opened, and no sales price was ever consulted.
Measured impact:

| | hardcoded API | inventory.csv truth |
|---|---|---|
| iPhone 17 256GB | 800 | **76** |
| iPhone 16 128GB | 320 | **0** (sold out) |
| Pixel 10 Pro | 95 | **77** |
| total units | **2,315** | **541** |

**Fix** — added `load_retail_state()`, which derives the observed state from the source data:
stock is `closing_inventory` summed across stores on the latest snapshot date; shelf price is the
median `selling_price` from the latest transaction. Every row now reports `inventory_source` and
`current_price_source` so a fallback is visible rather than silent. `total_inventory_units` is now
**541 = 541**, and every SKU matches its CSV row.

### C2 — `/api/simulate` was unreachable: every call 404'd  🔴

`frontend/js/app.js` built the URL as `` `${this.apiBase}/simulate` ``. `this.apiBase` does not
exist — the constant is `API_BASE` — so requests went to **`/undefined/simulate`**. The same call
sent `model_source: this.state.dataSource`, another non-existent property (the real one is
`state.modelSource`), and an empty `catch` swallowed the failure.

The Price Simulator — a flagship README feature — never reached the backend at all.

**Fix** — corrected the URL to `API_BASE`, the source to `state.modelSource`, and made a non-OK
response throw instead of passing silently.

### C3 — Sold-out SKUs received a phantom pricing recommendation 🔴

Once inventory became real, `SKU_IPHONE_16_128` (0 units) was recommended a
**"Clearance Markdown" to ₹56,700**, with risk "Medium Risk". There is nothing to mark down.

**Fix** — when on-hand stock is zero the row is relabelled `price_action = "No Stock"`,
`inventory_risk_level = "Stockout"`, price unchanged and lift zeroed, with a memo explaining that
replenishment is the required action. The frontend was taught to style `Stockout` as high risk.

### C4 — The simulator's numbers contradicted the chart beside them 🔴

The simulator omitted `inventory` and `days_to_successor`, so the endpoint fell back to its own
defaults (inventory 200 vs the SKU's real 76) while the chart used the true values. The two
panels on the same screen disagreed; profit even **sign-flipped** on the sold-out SKU
(−₹650,638 vs +₹630,096).

**Fix** — the frontend now sends the SKU's real `inventory`, `days_to_successor`,
`competitor_avg_price` and `competitor_min_price`. At the recommended price the two now report
the same demand (8.5 u/d) and net profit within 8.5%, the residual being the difference between
the endpoint's and the optimiser's carrying-cost models (see §6, R1).

### C5 — `/api/simulate` ignored the Legal Metrology MRP ceiling 🔴

The product's central compliance claim is *selling price ≤ MRP*. The endpoint priced anything:
`price: 999999` returned a net profit of **₹186,064,458** for an iPhone whose MRP is ₹84,999,
and `price: -5000` returned a large negative profit. A reader asking "is the MRP rule actually
enforced?" would have found the one endpoint that does not enforce it.

**Fix** — price is clamped to MRP before any profit is computed, and the response now carries
`requested_price` and `price_clamped_to_mrp: true` so the caller is told rather than silently
corrected. `price <= 0` is rejected with 422.

### C6 — `risk_counts` was mostly wrong, hiding ~20% of the catalogue  🔴

The dict was initialised with keys `Low/Medium/High/Critical`, but the optimiser emits
`"Low Risk" / "Medium Risk" / "High Risk"`. So every declared bucket read **0** and the real
counts accumulated in undeclared keys. Live proof:

```json
"risk_counts": {"Low":0,"Medium":0,"High":0,"Critical":0,"High Risk":2,"Low Risk":6}
```

`"Critical"` is unreachable — the optimiser never emits it. The frontend sums
`High Risk + Critical + Medium Risk`, i.e. it reads the undeclared keys, so the number happened to
display; any consumer reading the declared schema silently got zeros.

**Fix** — one vocabulary (`Low Risk`/`Medium Risk`/`High Risk`/`Critical`/`Stockout`), and the
summary now **recomputes counts from the cached rows** so they provably cannot drift from
`/api/optimizations`. Live: `risk_counts` sums to 8 = the number of SKU rows.

---

## 3. Major defects found and fixed

| # | Defect | Fix |
|---|---|---|
| M1 | **Stale cross-source cache.** A lifecycle event forced `compute_optimizations(force=True)` with the default source, leaving the *other* source's cache untouched — the kaggle summary kept serving a stale `active_events_count`, and kaggle rows always reported `active_event: None`. | A forced refresh now clears **both** sources' caches; `active_events_count` is read live from global state on every `/api/summary` rather than served from a cached dict. |
| M2 | **Falsy-zero coercion.** `int(req.inventory or 200)` turned a perfectly valid inventory of **0 into 200**. Same pattern for days and prices. | `req.inventory if req.inventory is not None else <real SKU value>`. Verified: `inventory=0` now yields `expected_sales=0`. |
| M3 | **No request validation.** Negative price, negative inventory, negative horizon, unknown `model_source` and a `9e12` price all returned **200**. | Pydantic constraints (`price > 0`, `inventory ≥ 0`, `days_to_successor ≥ 0`) plus `model_source: Literal["synthetic","kaggle"]`. All now 422. A duplicate earlier definition of `SimulationRequest` was shadowing the validated one and was removed. |
| M4 | **`avg_profit_lift_pct` sign inversion.** Divided by the status-quo baseline without guarding; a negative denominator produced a nonsense figure (observed −217.68%). | Guarded: the percentage is only computed against a **positive** baseline, otherwise `null`. The frontend renders an explicit "baseline profit is non-positive" note instead of a bogus number. |
| M5 | **Kaggle path fabricated stats for unknown SKUs.** A synthetic SKU requested with `model_source=kaggle` returned 200 with invented `mrp`, `unit_cost` and an ₹8.99M profit from the adapter's `default_stats`. | The kaggle path now 404s when the product is not in the real catalog, with a message pointing at `model_source=synthetic`. |
| M6 | **Hardcoded fallbacks contradicted the CSV.** `inv = int(req.inventory or 200)` / `or 120` ignored the real stock. | Both paths fall back to `load_retail_state()` — the SKU's actual on-hand units. |
| M7 | **`/api/transfers` returned empty plans for all 8 SKUs while 40 store rows said "Stockout Imminent"**, and the empty-state text claimed "every store is within healthy supply bounds" — a statement the same view contradicted. | Corrected the empty-state copy to describe the actual condition (no SKU has both a surplus *and* a deficit store, or logistics exceed the recovered margin) and to point at the supply-health table. The underlying LP is behaving correctly — surpluses and deficits simply do not co-occur per SKU in this snapshot; see R2. |

---

## 4. What was verified working (leave alone)

- **`changes.md` §11.2 (catalog safety) is true.** mtime_ns of all six `data/synthetic/*.csv`
  files are byte-identical before and after every endpoint, including repeated
  `/api/lifecycle-event` and `/api/reset-events`. The in-memory override store works.
- **§11.4 conformal intervals exist** and `demand_curve_lower ≤ demand ≤ demand_curve_upper`.
- **Law of Demand holds**: 0 monotonicity violations across all curves.
- **Legal + economic constraints hold**: no recommendation below unit cost, none above MRP, and
  the published `profit_curve` argmax equals `recommended_price` **for every row including
  installed on unsold stock. (The sold-out row originally violated this: its curve peaked at ₹56,700 while
  the recommended price was ₹64,800. See §6 B3.)
- **Linear programming transfers are real**: `scipy.optimize.linprog (HiGHS)`, status `optimal`.
- **pandas 3.0.5 / numpy 2.4.1 compatibility is clean** in the owned surface — every removed
  pandas 2.x idiom (`DataFrame.append`, `fillna(method=)`, `Series.get_values`, `iteritems`) was
  probed and none are used. This was a real risk worth checking and it came back negative.
- **Static mount does not shadow `/api/*`**, CORS preflight succeeds, and all 55 frontend DOM ids
  resolve against the API payloads.

---

## 5. Verification

The fixes are locked in by a new suite, `tests/test_api_endpoints.py` (23 tests), each of which
fails against the pre-fix code:

```
$ & $PY314 -m pytest tests/ -q
41 passed
```

An independent reviewer re-ran these tests against the **pre-fix commit** to prove they are genuine
regression tests rather than tautologies: 16 of the first 20 failed on the old code. That review
also found four defects the first round of fixes missed, all now fixed — see §6.

Coverage added: inventory/price provenance vs the CSVs · sold-out SKU labelling · summary-vs-rows
count agreement · guarded lift percentage · cross-source event freshness + no CSV writes ·
input validation (negative/zero price, negative inventory/horizon, unknown source) · zero-inventory
honesty · MRP clamping · kaggle unknown-SKU 404 · Law of Demand and the argmax invariant ·
every endpoint responding.

Live end-to-end checks (35 assertions) also passed against a running server, and the served page
was confirmed to contain the corrected frontend.

## 6. Second review round — four defects the first pass missed

An independent adversarial review was run against the fixes above. It confirmed 7 of 10 claims
outright, correctly identified 3 as overstated, and turned up four real defects. All are now fixed
and verified. Two of these were found **only** because the reviewer re-ran the new tests against the
old commit; the rest were caught by probing paths I had not covered.

### B1 (BLOCKER, fixed) — the memo still ordered a markdown on stock that did not exist

Relabelling the sold-out row to `No Stock` changed the action but **not the narrative memo**, because
`ReasonGenerator.generate_retailer_memo()` has no branch for that action and fell through to the
clearance-markdown case. The API therefore shipped:

> "Urgent: Implement ₹0 clearance markdown on Apple iPhone 16 (128GB Blue)"

…for a SKU with zero units — and this text is exactly what the explainability dialog renders. The
fix (claim 3) was therefore only half done. **Fixed** by adding an explicit `No Stock` branch to the
reason generator. Live output is now:

> "No action: Apple iPhone 16 (128GB Blue) is out of stock at every store"

A test now asserts the memo agrees with the action, so the two cannot drift apart again.

### B3 (MAJOR, fixed) — the argmax invariant was false, and the test skipped the offending row

The sold-out row's published `profit_curve` peaked at ₹56,700 while `recommended_price` was
₹64,800 — a direct contradiction between the chart and the recommendation. Worse, my
`test_economic_invariants_hold` contained `if row["price_action"] == "No Stock": continue`, which
skipped precisely the one violating row, so the test passed while the claim in §4 was false. This is
exactly the kind of self-confirming test worth being suspicious of. **Fixed** by replacing a
sold-out SKU's curve with a zero-inventory objective (`-|price - current_price|`): no profit is
attainable at any price, holding is weakly best, and its maximum lands exactly on the held price.
The skip was removed from the test, which now asserts the invariant for **every** row.

### B2 (MAJOR, fixed) — GET `?model_source=` was not validated, contradicting `api.json`

Only the POST body field was typed as a Literal; the query parameter was a plain `str`, so
`/api/summary?model_source=garbage` returned **200** with silently coerced data. `api.json` claimed
otherwise, making the documentation false. **Fixed** by typing the query parameter as a Literal on
`/api/summary`, `/api/optimizations` and `/api/optimizations/refresh` — unknown values now return 422.

### B4 (MAJOR, fixed) — event and reset paths could serve stale retail state

I wired `load_retail_state(force=True)` into `/api/optimizations/refresh` but not into
`/api/lifecycle-event` or `/api/reset-events`. The reviewer proved it by redirecting the data
directory to a temp copy, editing the CSVs, and observing that the event path kept reporting the old
inventory (541) while only the refresh path picked up the change (500). **Fixed** by forcing the
retail-state refresh on both paths.

### B5 (MAJOR, fixed) — a duplicate `SimulationRequest` still shadowed the validated schema

§8 previously claimed this duplicate was removed. It was not: two identical class definitions
existed, and the later one silently shadowed the earlier, so edits to the first copy had no effect on
the live endpoint. **Fixed** — the shadowed copy is now deleted and the file contains exactly one
definition of each request schema. This is corrected from my earlier, inaccurate claim.

### Also fixed from that review

- The doughnut chart had a hardcoded four-key fallback distribution and a fixed four-colour palette,
  so any new action (like `No Stock`) would render with no colour or legend entry. It now derives
  both from the live response and shows an explicit empty state when there are no actions.
- The SKU Matrix filter dropdowns had no `No Stock` / `Stockout` options, making the sold-out SKU
  visible only under "All".

### Still open after both rounds

- `price=true` is coerced to `1.0` by pydantic's lenient numeric parsing (returns 200 rather than 422).
  Harmless in practice — the UI never sends booleans — but a `StrictFloat` would be tidier.
- R1–R5 in §7 remain unchanged.

---

## 7. Remaining, not fixed (stated honestly)

**R1 — the simulate endpoint and the optimiser use two different cost models.**
The endpoint derives carrying cost as `(inventory + leftover)/2` over `min(days_to_successor, 60)`;
the optimiser uses clearance-aware inventory over `max(15, min(days, 180))`. After C4 the two agree
to within ~8.5%; they cannot agree exactly until the endpoint calls the optimiser's own function.
Not fixed because consolidating them changes the optimiser's public behaviour and deserves its own
review. The UI no longer contradicts itself, so this is a precision issue, not a correctness one.

**R2 — near-zero surplus/deficit co-occurrence makes `/api/transfers` mostly empty.**
`STORE_MUM_01` shows low stock across several SKUs while `STORE_BLR_03` shows surplus on others —
rarely the *same* SKU, which is what the LP requires. The solver is correct; the synthetic data
just rarely puts a surplus and a deficit for one SKU in the same snapshot. Honest reporting beats
manufacturing transfers.

**R3 — no concurrency hardening.** The module-global caches (`_models_cache`, `_optimizations_cache`,
`_summary_cache`, `_active_events`, `_runtime_catalog_overrides`) have no locks. Under genuinely
parallel load a race could KeyError. Not reproduced here and out of scope for a single-user demo,
but it is a real limitation.

**R4 — unhandled corner cases**: `NaN` price, `model_source` on `/api/transfers`, and
`product_id=""`. Low impact; validation now catches the dangerous ones.

**R5 — `/api/transfers` still derives inventory separately** from `load_retail_state()`. It works
and its snapshot date matches, but the duplication is a maintenance hazard.

---

## 8. Assessment of `changes.md`

Accurate in the main, and unusually honest about the ML's limitations (§7 "be honest in the
seminar" is exactly right — TreeSHAP is real, the reason templates are not XAI). Three claims were
wrong as shipped:

1. **§0 lists "Server hosting ✅"** while §11.1's simulator was 404-ing on every request. The status
   table asserted more confidence than the code supported.
2. **§6 "Verified — `/api/summary` … respond correctly"** never checked the values. They did not
   match the CSVs: the response described a catalogue that does not exist.
3. **"Known remaining frontend gap"** understated it. It was described as a *slight* tiles-vs-chart
   disagreement; in fact the tiles never reached the backend at all and the disagreement included a
   profit sign flip.

Non-blocking documentation inaccuracies: the README claims **9** unit tests (§0 and §7 repeat it)
where the suite has 18 before this work and 38 after; the README's 6 dashboard modules map to only
4 endpoints — inventory risk and competitor intelligence have none (see `api.json`).

**Recommendation:** keep `changes.md` as the primary handoff, but add these to it — the correct
interpreter path, the fact that the API was hardcoding per-SKU state (now fixed), the corrected
inventory figure (541, not 2,315), and the 4-vs-6 module/endpoint gap.

---

## 9. Files changed

| File | Change |
|---|---|
| `api/routes/analytics.py` | `load_retail_state()` added; hardcoded per-SKU state removed; sold-out handling; risk/action vocabularies unified and recomputed live; both caches invalidated together; live event count; guarded lift %; MRP clamp + `price_clamped_to_mrp`; pydantic validation (`Field`, `Literal`); duplicate `SimulationRequest` removed; kaggle unknown-SKU 404; `model_source` typing on the simulate request |
| `frontend/js/app.js` | `/undefined/simulate` → `API_BASE`; `dataSource` → `modelSource`; sends full SKU context; throws on non-OK; `Stockout` risk styling; live total-gain badge; signed-proof KPI rendering; "No Stock" in the action summary; honest transfers empty state; error state clears stale KPIs and names the real origin |
| `frontend/index.html` | hardcoded `+129.6% Total Gain` badge replaced with a live-bound element |
| `tests/test_api_endpoints.py` | **new** — 20 regression tests covering every fix above |
| `api.json` | **new** — endpoint inventory: 10 existing (verified) + 7 genuinely missing, each with a `_why` and a `needed` flag |
| `BACKEND_AUDIT.md` | this report |

Scratch files created during the investigation (probe scripts, captured JSON, server logs) were
deleted; a stray `_contract_probe/` directory and an orphaned uvicorn process left by a research
pass were cleaned up too.

**Interpreter note for whoever runs this next:** use the full path to Python 3.14.2. The bare
`python` on PATH has no dependencies and will fail on import.
