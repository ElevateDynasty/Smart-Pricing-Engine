/**
 * ApexPricing — Navigation Shell
 * ---------------------------------------------------------------------------
 * A thin, additive layer on top of the existing `app` engine (js/app.js).
 * It never re-implements business logic: every command delegates to a method
 * that already exists on `app`. It is loaded AFTER app.js.
 *
 * Adds:
 *   1. Deep-linkable hash routes      (#overview, #sku-pricing, ...)
 *   2. Browser Back / Forward support (via hashchange)
 *   3. Keyboard shortcuts             (1-5, Ctrl/Cmd+K, "/", Esc)
 *   4. Command palette                (fuzzy jump-to, arrow keys, Enter)
 *   5. Modal & drawer keyboard/Escape handling + focus restore
 *   6. ARIA state sync                (aria-current, aria-expanded)
 */
(function () {
    'use strict';

    var VIEWS = [
        { id: 'overview',    label: 'Executive Overview',    icon: 'fa-chart-line',        hint: 'KPIs, profit distribution, priority ledger' },
        { id: 'sku-pricing', label: 'Catalog SKU Matrix',    icon: 'fa-table-cells-large', hint: 'Full SKU ledger with AI optimal prices' },
        { id: 'simulator',   label: 'Elasticity Simulator',  icon: 'fa-bezier-curve',      hint: 'What-if pricing sandbox' },
        { id: 'competitors', label: 'Market Intelligence',   icon: 'fa-radar',             hint: 'Competitor positioning vs Amazon, Flipkart' },
        { id: 'transfers',   label: 'Store Balancing',       icon: 'fa-right-left',        hint: 'Inter-store transfer plan and supply health' }
    ];

    var VIEW_IDS = VIEWS.map(function (v) { return v.id; });

    var shell = {
        paletteOpen: false,
        paletteIndex: 0,
        paletteResults: [],
        lastFocus: null,
        suppressHistory: false,

        /* ---------------- boot ---------------- */
        init: function () {
            this.bindHashRouting();
            this.bindKeyboard();
            this.bindDrawer();
            this.bindPalette();
            this.bindNavSemantics();
            this.syncFromHash(true);
        },

        /* ---------------- 1 & 2. hash routing ---------------- */
        isValidView: function (id) {
            return VIEW_IDS.indexOf(id) !== -1;
        },

        // Read the hash and route. `initial` avoids fighting the engine on boot.
        /* Route to the view named by the current hash.
           IMPORTANT: the router never writes history. A hashchange means the URL
           already changed (the browser recorded that entry), so writing again
           would duplicate it. Terminal navigation is pushed by switchView; the
           router only mirrors URL -> view. Idempotent by design. */
        syncFromHash: function (initial) {
            var id = (window.location.hash || '').replace(/^#\/?/, '');
            if (!this.isValidView(id)) return false;
            if (window.app && typeof window.app.switchView === 'function') {
                // Already there? Nothing to do (also absorbs the hashchange that a
                // programmatic switchView triggers).
                if (window.app.state && window.app.state.activeView === id) {
                    this.syncAria();
                    return true;
                }
                var previous = this.suppressHistory;
                this.suppressHistory = true;
                try {
                    window.app.switchView(id);
                } finally {
                    this.suppressHistory = previous;
                }
            }
            this.syncAria();
            return true;
        },

        bindHashRouting: function () {
            window.addEventListener('hashchange', function () {
                if (!shell.syncFromHash(false)) {
                    // Unknown fragment: snap the URL back to the current engine view.
                    var current = (window.app && window.app.state && window.app.state.activeView) || 'overview';
                    if (window.history && window.history.replaceState) {
                        window.history.replaceState({ view: current }, '', '#' + current);
                    }
                }
            });
        },

        /* ---------------- 3. keyboard ---------------- */
        isTyping: function (el) {
            if (!el) return false;
            var tag = (el.tagName || '').toLowerCase();
            return tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable === true;
        },

        bindKeyboard: function () {
            document.addEventListener('keydown', function (e) {
                var key = e.key;

                // Ctrl/Cmd + K  or  "/"  -> command palette
                if ((key === 'k' || key === 'K') && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    shell.togglePalette();
                    return;
                }
                if (key === '/' && !shell.isTyping(e.target) && !shell.paletteOpen) {
                    e.preventDefault();
                    shell.openPalette();
                    return;
                }

                // Escape closes the topmost layer
                if (key === 'Escape') {
                    if (shell.paletteOpen) { e.preventDefault(); shell.closePalette(); return; }
                    var drawer = document.getElementById('sidebar');
                    if (drawer && drawer.classList.contains('open')) {
                        e.preventDefault();
                        shell.closeDrawer();
                        return;
                    }
                    var memo = document.getElementById('memo-modal');
                    var launch = document.getElementById('launch-modal');
                    if (memo && !memo.classList.contains('hidden')) {
                        e.preventDefault();
                        if (window.app && window.app.closeModal) window.app.closeModal();
                        return;
                    }
                    if (launch && !launch.classList.contains('hidden')) {
                        e.preventDefault();
                        if (window.app && window.app.closeLaunchModal) window.app.closeLaunchModal();
                        return;
                    }
                    return;
                }

                if (shell.paletteOpen) return;          // palette owns its own keys
                if (shell.isTyping(e.target)) return;   // never hijack form fields
                if (e.ctrlKey || e.metaKey || e.altKey) return;

                // Quick view keys 1-5
                if (key >= '1' && key <= '5') {
                    var target = VIEWS[parseInt(key, 10) - 1];
                    if (target) {
                        e.preventDefault();
                        shell.go(target.id);
                    }
                }
            });
        },

        /* Activate a view through the engine. The engine pushes the history entry
           for navigations the USER initiated (clicks, shortcuts, palette). */
        go: function (viewId) {
            if (!this.isValidView(viewId)) return;
            if (window.app && typeof window.app.switchView === 'function') {
                window.app.switchView(viewId);       // engine also pushes the hash
            }
            if ((window.location.hash || '').replace(/^#\/?/, '') !== viewId &&
                window.history && window.history.replaceState) {
                window.history.replaceState({ view: viewId }, '', '#' + viewId);
            }
            this.syncAria();
            var raf = window.requestAnimationFrame || function (f) { return setTimeout(f, 16); };
            raf(function () { shell.syncAria(); });
        },

        /* ---------------- 4. command palette ---------------- */
        commands: function () {
            var list = VIEWS.map(function (v) {
                return {
                    label: v.label,
                    icon: v.icon,
                    hint: v.hint,
                    group: 'View',
                    run: function () { shell.go(v.id); }
                };
            });

            var actions = [
                { label: 'Sync Data & Recalculate', icon: 'fa-arrows-rotate', group: 'Action',
                  hint: 'Re-run the pricing engine against the active dataset',
                  run: function () { if (window.app && app.refreshOptimizations) app.refreshOptimizations(); } },
                { label: 'Simulate Launch Signal', icon: 'fa-satellite-dish', group: 'Action',
                  hint: 'Ingest a flagship successor announcement',
                  run: function () { if (window.app && app.openLaunchModal) app.openLaunchModal(); } },
                { label: 'Switch dataset: Synthetic', icon: 'fa-database', group: 'Dataset',
                  run: function () { if (window.app && app.switchDataSource) app.switchDataSource('synthetic'); } },
                { label: 'Switch dataset: Real Kaggle', icon: 'fa-database', group: 'Dataset',
                  run: function () { if (window.app && app.switchDataSource) app.switchDataSource('kaggle'); } },
                { label: 'Focus catalogue search', icon: 'fa-magnifying-glass', group: 'Action',
                  hint: 'Jump to the SKU Matrix and focus the search field',
                  run: function () {
                      shell.go('sku-pricing');
                      var input = document.getElementById('sku-search-input');
                      if (input) setTimeout(function () { input.focus(); }, 120);
                  } },
                { label: 'Revert lifecycle events to baseline', icon: 'fa-arrow-rotate-left', group: 'Action',
                  run: function () { if (window.app && app.resetLifecycleEvents) app.resetLifecycleEvents(); } }
            ];

            return list.concat(actions);
        },

        score: function (item, q) {
            var hay = (item.label + ' ' + (item.hint || '') + ' ' + item.group).toLowerCase();
            var needle = q.toLowerCase();
            var idx = hay.indexOf(needle);
            if (idx === -1) {
                // subsequence fallback so "skm" matches "SKU Matrix"
                var i = 0;
                for (var c = 0; c < hay.length && i < needle.length; c++) {
                    if (hay[c] === needle[i]) i++;
                }
                return i === needle.length ? 900 : -1;
            }
            return idx;
        },

        bindPalette: function () {
            var openBtn = document.getElementById('cmdk-open');
            var backdrop = document.getElementById('cmdk-backdrop');
            var input = document.getElementById('cmdk-input');
            if (!backdrop || !input) return;

            if (openBtn) openBtn.addEventListener('click', function () { shell.openPalette(); });
            backdrop.addEventListener('click', function (e) {
                if (e.target === backdrop) shell.closePalette();
            });

            input.addEventListener('input', function () { shell.renderPalette(input.value); });
        },

        openPalette: function () {
            var backdrop = document.getElementById('cmdk-backdrop');
            var input = document.getElementById('cmdk-input');
            if (!backdrop || !input) return;
            this.lastFocus = document.activeElement;
            this.paletteOpen = true;
            backdrop.classList.add('open');
            input.value = '';
            this.paletteIndex = 0;
            this.renderPalette('');
            input.focus();
        },

        closePalette: function () {
            var backdrop = document.getElementById('cmdk-backdrop');
            var input = document.getElementById('cmdk-input');
            if (!backdrop) return;
            this.paletteOpen = false;
            backdrop.classList.remove('open');
            if (input) input.value = '';
            if (this.lastFocus && typeof this.lastFocus.focus === 'function') {
                this.lastFocus.focus();
            }
        },

        togglePalette: function () {
            if (this.paletteOpen) this.closePalette(); else this.openPalette();
        },

        renderPalette: function (query) {
            var listEl = document.getElementById('cmdk-list');
            if (!listEl) return;

            var all = this.commands();
            var q = (query || '').trim();
            var scored = [];

            all.forEach(function (item) {
                if (!q) { scored.push({ item: item, s: 0 }); return; }
                var s = shell.score(item, q);
                if (s >= 0) scored.push({ item: item, s: s });
            });
            scored.sort(function (a, b) { return a.s - b.s; });
            var items = scored.map(function (r) { return r.item; });

            this.paletteResults = items;
            if (this.paletteIndex >= items.length) this.paletteIndex = 0;

            if (!items.length) {
                listEl.innerHTML = '<div class="cmdk-item" aria-disabled="true">' +
                    '<i class="fa-solid fa-magnifying-glass"></i><span>No matching command</span></div>';
                return;
            }

            var html = '';
            var lastGroup = null;
            items.forEach(function (item, i) {
                if (item.group !== lastGroup) {
                    lastGroup = item.group;
                    html += '<div class="cmdk-foot" style="border:0;background:transparent;padding:0.5rem 0.7rem 0.25rem;">' +
                        item.group.toUpperCase() + '</div>';
                }
                html += '<div class="cmdk-item" role="option" data-index="' + i + '"' +
                    ' aria-selected="' + (i === shell.paletteIndex ? 'true' : 'false') + '">' +
                    '<i class="fa-solid ' + item.icon + '"></i>' +
                    '<span>' + item.label + '</span>' +
                    (item.hint ? '<span class="mono-label" style="margin-left:auto;text-transform:none;letter-spacing:0;">' + item.hint + '</span>' : '') +
                    '</div>';
            });
            listEl.innerHTML = html;

            Array.prototype.forEach.call(listEl.querySelectorAll('.cmdk-item[data-index]'), function (el) {
                el.addEventListener('click', function () {
                    shell.runPaletteItem(parseInt(el.getAttribute('data-index'), 10));
                });
                el.addEventListener('mouseenter', function () {
                    shell.setPaletteIndex(parseInt(el.getAttribute('data-index'), 10), false);
                });
            });
        },

        setPaletteIndex: function (idx, scroll) {
            var listEl = document.getElementById('cmdk-list');
            if (!listEl || !this.paletteResults.length) return;
            var n = this.paletteResults.length;
            this.paletteIndex = ((idx % n) + n) % n;
            var nodes = listEl.querySelectorAll('.cmdk-item[data-index]');
            Array.prototype.forEach.call(nodes, function (el) {
                el.setAttribute('aria-selected',
                    parseInt(el.getAttribute('data-index'), 10) === shell.paletteIndex ? 'true' : 'false');
            });
            if (scroll !== false) {
                var active = listEl.querySelector('.cmdk-item[aria-selected="true"]');
                if (active && active.scrollIntoView) active.scrollIntoView({ block: 'nearest' });
            }
        },

        runPaletteItem: function (idx) {
            var item = this.paletteResults[idx];
            if (!item) return;
            this.closePalette();
            try {
                item.run();
            } catch (err) {
                if (window.console && console.warn) console.warn('[shell] command failed:', err);
            }
        },

        /* Palette key ownership is registered on capture so it wins over globals. */
        paletteKeys: function (e) {
            if (!this.paletteOpen) return;
            if (e.key === 'ArrowDown') { e.preventDefault(); this.setPaletteIndex(this.paletteIndex + 1); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); this.setPaletteIndex(this.paletteIndex - 1); }
            else if (e.key === 'Home') { e.preventDefault(); this.setPaletteIndex(0); }
            else if (e.key === 'End') { e.preventDefault(); this.setPaletteIndex(this.paletteResults.length - 1); }
            else if (e.key === 'Enter') {
                e.preventDefault();
                this.runPaletteItem(this.paletteIndex);
            }
        },

        /* ---------------- 5. mobile drawer ---------------- */
        bindDrawer: function () {
            var btn = document.getElementById('mobile-menu-toggle');
            var sidebar = document.getElementById('sidebar');
            var backdrop = document.getElementById('sidebar-backdrop');
            if (!btn || !sidebar || !backdrop) return;

            var syncAria = function () {
                btn.setAttribute('aria-expanded', sidebar.classList.contains('open') ? 'true' : 'false');
            };

            btn.addEventListener('click', function () { setTimeout(syncAria, 0); });
            backdrop.addEventListener('click', syncAria);
            syncAria();

            // Tapping a nav link on mobile should close the drawer (engine only does
            // this when the *list* is clicked; anchors need an explicit nudge).
            Array.prototype.forEach.call(sidebar.querySelectorAll('.nav-list li a'), function (a) {
                a.addEventListener('click', function () {
                    if (window.matchMedia && window.matchMedia('(max-width: 900px)').matches) {
                        setTimeout(function () { shell.closeDrawer(); }, 0);
                    }
                });
            });
        },

        closeDrawer: function () {
            var sidebar = document.getElementById('sidebar');
            var backdrop = document.getElementById('sidebar-backdrop');
            var btn = document.getElementById('mobile-menu-toggle');
            if (sidebar) sidebar.classList.remove('open');
            if (backdrop) backdrop.classList.remove('active');
            if (btn) btn.setAttribute('aria-expanded', 'false');
        },

        /* ---------------- 6. ARIA sync ---------------- */
        bindNavSemantics: function () {
            var sidebar = document.getElementById('sidebar');
            if (!sidebar || !window.MutationObserver) return;
            // Catches switches the engine performs on its own (e.g. the overview's
            // "View Complete Matrix" button), which never pass through shell.go().
            var mo = new MutationObserver(function () { shell.syncAria(); });
            Array.prototype.forEach.call(sidebar.querySelectorAll('.nav-list li'), function (li) {
                mo.observe(li, { attributes: true, attributeFilter: ['class'] });
            });
            this.syncAria();
        },

        /* Mirror the active view onto the nav for assistive tech. Prefers the
           engine's own state and falls back to the rendered .active class. */
        syncAria: function () {
            var sidebar = document.getElementById('sidebar');
            if (!sidebar) return;
            var li = sidebar.querySelector('.nav-list li.active');
            var current = (li && li.getAttribute('data-view')) ||
                (window.app && window.app.state && window.app.state.activeView) || 'overview';
            Array.prototype.forEach.call(sidebar.querySelectorAll('.nav-list li'), function (item) {
                if (item.getAttribute('data-view') === current) {
                    item.setAttribute('aria-current', 'page');
                } else {
                    item.removeAttribute('aria-current');
                }
            });
        }
    };

    // Capture-phase palette keys (registered before other document listeners)
    document.addEventListener('keydown', function (e) { shell.paletteKeys(e); }, true);

    window.shell = shell;

    document.addEventListener('DOMContentLoaded', function () {
        shell.init();
    });
})();
