# Frontend Visual + Navigation Upgrade — Independent Review

Reviewer: independent adversarial review pass (separate agent, read-only on deliverables).
Artifacts under review: `frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js`,
`frontend/js/shell.js`, `frontend/AUDIT_frontend.md`.
Baseline for diffing: `.review_baseline/` (`index.html`, `css_style.css`, `js_app.js` — copies of
the pre-upgrade files recovered from git HEAD).

Method: full read of every in-scope file; `git diff --no-index` hunk-level comparison of `app.js`
against baseline; `node --check` on both JS files; independent id/handler/class coverage scripts;
a real DOM rehearsal via jsdom (Node v24.20.0, harness installed in a system temp directory — nothing
written into the project); CSS cascade/specificity analysis; targeted probes with instrumented
`history.pushState`/`replaceState` to count history writes per navigation kind.

---

## 1. Verdict

**The upgrade is correct after two blocking defects were found and fixed.** The `app.js` claim
("changes confined to 5 areas, no statements lost") was **upheld** by hunk-level diff. Two
independent blockers were found — both in the *new* code, not in the preserved engine — and both
are now verified fixed:

- **B1** — the engine was never reachable as `window.app`, so every new feature gated on it was dead.
- **B2** — the new table base rule out-specified the pre-existing semantic colour classes.

The invariant "100% of `app.js` behaviour preserved" holds: 51/51 ids, 17/17 inline handlers,
182/182 class tokens, and the reveal/row animation system all intact.

---

## 2. `app.js` change set (hunk-level diff vs baseline)

Baseline `js_app.js` = 1180 lines / 48,735 bytes. Delivered = 1,186 lines / larger by the added
global publication. Changes are confined to the following, exactly as claimed:

| # | Location | Change | Rationale |
|---|---|---|---|
| 1 | `bindEvents()` / `switchView()` | `.nav-links li` → `.nav-list li` | **Fixes a latent bug**: `.nav-links` appeared 0 times in the baseline HTML, so the original selector matched 0 elements and the nav highlight never moved. |
| 2 | end of `switchView()` | added `history.pushState`/`replaceState` hash sync | Makes views deep-linkable and Back/Forward work. Honors `shell.suppressHistory` so router-driven syncs never duplicate an entry. |
| 3 | `updateSliderFill()` | slider gradient `#0284c7/#00e5ff` → `#0e9e96/var(--accent-signal)` | Palette consistency with the new design tokens. |
| 4 | Chart.js configs | palette hex values (`#94a3b8`→`#78848c`, `#6366f1`→`#14d6c4`, doughnut + simulator series) | Palette consistency; removes the banned indigo/cyan "AI neon" cast. |
| 5 | `renderErrorState()` | `var(--warning)` → `var(--status-warning)` | The original token was never defined in either stylesheet. |

Plus one addition outside those five, required by B1:

| 6 | end of file | `window.app = app;` | See B1. `const` at the top level of a classic script creates a global *lexical* binding (inline `onclick="app.x()"` resolves) but **not** a `window` property. |

No other statements were modified, dropped, or reordered.

---

## 3. Coverage results (recomputed independently)

| Check | Result |
|---|---|
| JS syntax (`node --check`) | `app.js` OK, `shell.js` OK |
| ids read/written by `app.js` present in HTML | **51 / 51** (0 missing) |
| HTML ids / duplicates | 73 / **0 duplicates** |
| Inline handlers resolving to an `app.js` method | **17 / 17** (0 broken) |
| Class tokens styled in CSS | **182 / 182** (0 unstyled outside `fa-*`) |
| CSS brace balance | 338 / 338 balanced |
| `aria-labelledby` + `<label for>` targets | all resolve |
| `app.js` CSS-variable references | all defined |

The only unstyled "tokens" a naive parser reports — `===`, `'positive'`, `'text-success'` — are
substring artifacts of parsing JS ternaries inside template literals, not real classes.

---

## 4. Findings

### BLOCKER (both found, both fixed and re-verified)

**B1. `shell.js` engine calls were gated on `window.app`, which was never defined. — FIXED**
- Was: `app.js` line 8 declares `const app = {`; no `window.app =` / `globalThis.app =` existed.
  `shell.js` guarded ~14 call sites with `if (window.app && ...)`, so all fell through.
- Impact when broken (reproduced by execution): deep link `#transfers` did not land; `hashchange`
  did not route; pressing `1`–`5` moved the URL while the view stayed put (**URL and UI disagreeing —
  worse than doing nothing**); Escape did not close modals; all four palette actions were no-ops;
  `aria-current` reported the wrong view.
- Fix: `window.app = app;` at the end of `app.js` (single root cause, one line).
- **Re-verified:** `window.app` is an object; deep link activates `view-transfers`; `hashchange`
  routes to competitors; `3` activates the simulator *and* keeps `#simulator` in sync; Escape closes
  the launch modal; `aria-current="page"` lands on the correct nav item.

**B2. Table base rule out-specified the semantic colour classes. — FIXED**
- Was: `.terminal-table tbody td { color: var(--text-secondary) }` — specificity (0,2,1), which beats
  `.price-up`, `.text-success`, `.text-warning`, `.text-accent`. Five class combinations emitted by
  `renderTable()` / `renderTransfers()` all rendered grey.
- Fix: base colour moved to a zero-specificity `:where()` rule, and `mono-num` brightening likewise
  wrapped so it cannot swamp semantic classes. `color` is deliberately absent from `tbody td`.
- **Re-verified:** the only rules setting colour on table cells are now `:where(...)` (0,0,0) and the
  `:where(...) :where(...)` chain (0,0,0), so semantic classes always win.

### MAJOR

**M1. "Back/Forward works" was initially overstated, then made true.**
The first implementation used `replaceState` for every navigation, so `history.length` never grew and
Back did nothing. Resolved by splitting the two cases: **terminal** navigation (nav click, shortcut,
palette) goes through `switchView`, which now *pushes* one entry; **router** sync (`hashchange`, i.e.
Back/Forward or a direct hash edit) writes nothing, because the browser already recorded that entry.
Instrumented probe confirms: nav click → `push=1, replace=0`; `hashchange` → `push=0, replace=0`.
This also makes the router **idempotent** — the `hashchange` that a programmatic `switchView` itself
triggers is absorbed by an equal-state check instead of looping.

### MINOR

**m1. Nav anchors point at view ids, not element ids.** `<a href="#overview">` — no element has
`id="overview"` (the section is `id="view-overview"`). Nothing scrolls; the anchors exist for
keyboard focus, native link semantics and router handoff, and JS does not `preventDefault`.
Acceptable, and preferable to plain `<li>`s which were unfocusable. Recorded as intentional.

**m2. `AUDIT_frontend.md` describes the pre-upgrade state.** It scopes itself to the three original
files (which is exactly why the B1 class of bug was invisible to it), and its line/byte/id counts
predate this change. Historical document; not a defect.

### Verified-clean (previously identified hazards)

- **Global `.hidden` trap** — PASS. No global `.hidden` rule exists; visibility is governed solely by
  `.view { display:none }` / `.view.active { display:block }`. The inert `hidden` class on views 2–5
  computes to `display:block` once activated, i.e. harmless as before.
- **Reveal trap** — PASS. `.reveal` / `.reveal.revealed` / `.row-enter` / `--d` / `--rd` /
  `.tile-number.pop` / `.metric-ribbon-val.animating` and all keyframes are defined.
  Executed with a firing observer: every `.reveal` element reached `.revealed` — **0 stuck at
  `opacity:0`**. Selector coverage per view is correct by construction (each selector matches only
  the view that contains it; the empty matches in a given view are expected).
- **`!important` audit** — 7 uses, all benign: canvas sizing, `prefers-reduced-motion` overrides, and
  a print-only hide list. None touch text colour inside table cells.
- **Typing guard** — PASS. `1`–`5` and `/` are not hijacked while focus is in `#sku-search-input`,
  `#sim-price-slider`, `#sim-product-select` or the filter selects.
- **Palette key handling** — PASS. Capture-phase Arrow/Home/End/Enter/Escape all `preventDefault`;
  `runPaletteItem` is `try/catch`-guarded so a missing `app` method cannot throw.

---

## 5. Not verified (and why)

- **Real-browser rendering.** jsdom performs no layout or paint, and Chart.js was stubbed. Visual
  regression is therefore unverified by execution; a manual pass over the five views is still worth
  doing. CSS was validated structurally (balanced braces, token resolution, specificity analysis).
- **Data-driven render paths.** `fetch` rejects in the harness, so the live-data branch of `loadData()`
  did not execute end-to-end. The error state rendered as designed, which is itself a useful result:
  with the backend down the app degrades to an explicit retry panel rather than a blank page.
- **Chart.js visual output.** `Chart` was stubbed; only the config values were inspected.

---

## 6. Recommended fixes, ordered

All BLOCKER and MAJOR items are already applied and re-verified. Remaining, optional:

1. *(optional)* Align nav `href`s to real ids, or add `preventDefault` in `shell.go` — the current
   state is functional but the anchors are semantically loose.
2. *(optional)* Replace the static `+129.6% Total Gain` and `Solver: …` badges on the overview with
   values derived from `app.state.summary`, so they cannot drift from the data.
3. *(recommended)* Do one manual pass in a real browser with the FastAPI backend running
   (`python main.py --all` then `streamlit`/API serve) to confirm chart rendering and the table
   semantic colours visually.
