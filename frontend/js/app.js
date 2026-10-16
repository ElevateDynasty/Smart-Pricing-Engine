/**
 * ApexPricing AI - Retail Pricing & Lifecycle Optimization Engine
 * Frontend Client Application
 */

const API_BASE = '/api';

const app = {
    state: {
        optimizations: [],
        summary: {},
        filtered: [],
        activeEvents: [],
        transfers: [],
        activeView: 'overview',
        currentSimSku: null,
        activeModalSku: null,
        simPrice: 0,
        modelSource: 'synthetic',
        retailerInventory: [],
        currentRetailerResult: null,
        inventoryBrandFilter: 'all',
        inventoryRiskFilter: 'all',
        inventorySort: 'inventory-desc',
        inventorySearch: '',
        inventoryActiveTab: 'cards',
        activeHardwareModalSku: null
    },
    
    charts: {
        profitComparison: null,
        actionDistribution: null,
        simulatorCurve: null,
        retailerCurve: null
    },

    init() {
        this.initTheme();
        this.bindEvents();
        this.startClock();
        this.initScrollProgress();
        this.initRevealObserver();
        this.initRetailerHub();
        this.loadData();
    },

    /* ============ Theme & Refresh Controls ============ */

    initTheme() {
        const saved = localStorage.getItem('apex_theme') || 'dark';
        this.applyTheme(saved);
    },

    toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || (document.body.classList.contains('light-mode') ? 'light' : 'dark');
        const next = current === 'dark' ? 'light' : 'dark';
        this.applyTheme(next);
    },

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        if (theme === 'light') {
            document.body.classList.add('light-mode');
            document.body.classList.remove('terminal-dark');
        } else {
            document.body.classList.remove('light-mode');
            document.body.classList.add('terminal-dark');
        }
        try {
            localStorage.setItem('apex_theme', theme);
        } catch (e) {}

        // Update top bar toggle
        const icon = document.getElementById('theme-toggle-icon');
        const text = document.getElementById('theme-toggle-text');
        if (icon) {
            icon.className = theme === 'light' ? 'fa-solid fa-moon text-accent' : 'fa-solid fa-sun text-accent';
        }
        if (text) {
            text.textContent = theme === 'light' ? 'Dark Mode' : 'Light Mode';
        }

        // Update mobile header toggle
        const mobileIcon = document.getElementById('mobile-theme-icon');
        if (mobileIcon) {
            mobileIcon.className = theme === 'light' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
        }

        // Update sidebar bottom toggle
        const sidebarText = document.getElementById('sidebar-theme-text');
        const sidebarIcon = document.getElementById('sidebar-theme-icon');
        if (sidebarText) {
            sidebarText.textContent = theme === 'light' ? 'Dark Mode' : 'Light Mode';
        }
        if (sidebarIcon) {
            sidebarIcon.className = theme === 'light' ? 'fa-solid fa-moon text-accent' : 'fa-solid fa-sun text-accent';
        }

        // Re-render active charts with updated theme colors
        this.updateChartsTheme();
    },

    updateChartsTheme() {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        const textColor = isLight ? '#334155' : '#b6c0c6';

        if (window.Chart) {
            Chart.defaults.color = textColor;
        }

        if (this.state.optimizations && this.state.optimizations.length) {
            this.renderProfitComparisonChart();
            this.renderActionDistributionChart();
        }
        if (this.state.currentSimSku) {
            this.renderSimulatorCurves();
        }
        if (this.state.currentRetailerResult) {
            this.renderRetailerCurveChart(this.state.currentRetailerResult);
        }
    },

    refreshPage() {
        const btn = document.getElementById('btn-refresh-page');
        if (btn) {
            const icon = btn.querySelector('i');
            if (icon) icon.classList.add('fa-spin');
        }
        const mobileBtn = document.getElementById('mobile-refresh-btn');
        if (mobileBtn) {
            const mIcon = mobileBtn.querySelector('i');
            if (mIcon) mIcon.classList.add('fa-spin');
        }

        setTimeout(() => {
            window.location.reload();
        }, 160);
    },

    startClock() {
        const updateClock = () => {
            const clockEl = document.getElementById('live-clock');
            if (clockEl) {
                const now = new Date();
                clockEl.textContent = now.toLocaleTimeString('en-IN', { hour12: false });
            }
        };
        updateClock();
        setInterval(updateClock, 1000);
    },

    /* ============ Motion & Micro-Interaction Engine ============ */

    initScrollProgress() {
        const bar = document.getElementById('scroll-progress');
        if (!bar) return;
        const onScroll = () => {
            const doc = document.documentElement;
            const max = doc.scrollHeight - doc.clientHeight;
            const ratio = max > 0 ? Math.min(1, doc.scrollTop / max) : 0;
            bar.style.transform = `scaleX(${ratio.toFixed(4)})`;
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onScroll, { passive: true });
        onScroll();
    },

    initRevealObserver() {
        if (!('IntersectionObserver' in window)) return;
        this._revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    this._revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    },

    prepareViewReveals(viewId) {
        if (!this._revealObserver) return;
        const view = document.getElementById(`view-${viewId}`);
        if (!view) return;

        const selector = [
            '.terminal-banner',
            '.metric-ribbon .metric-strip-item',
            '.split-analytics-grid > .architectural-panel',
            '.architectural-panel.mt-6',
            '.architectural-panel.mt-4',
            '.view-header-strip',
            '.filter-wire-toolbar',
            '.inv-toolbar-strip',
            '.simulator-cockpit-grid > *',
            '.telemetry-tiles-grid .telemetry-tile'
        ].join(', ');

        view.querySelectorAll(selector).forEach((el, i) => {
            // Reset without replaying the exit transition (avoids flicker on re-prep)
            el.style.transition = 'none';
            el.classList.remove('reveal', 'revealed');
            void el.offsetWidth;
            el.style.transition = '';
            el.style.setProperty('--d', `${Math.min(i * 70, 490)}ms`);
            el.classList.add('reveal');
            this._revealObserver.observe(el);
        });
    },

    animateKPIs() {
        const s = this.state.summary;
        if (!s) return;
        const risks = s.risk_counts || {};
        const jobs = [
            { id: 'kpi-profit-lift', target: s.total_profit_lift || 0,
              format: v => `${v >= 0 ? '+' : ''}${this.formatCurrency(Math.round(v))}` },
            // `avg_profit_lift_pct` can legitimately be null (non-positive status-quo
            // baseline). Counting up to 0 would render "+0.0%", claiming a break-even
            // result we never measured — so fall through to the explicit wording.
            { id: 'kpi-profit-lift-pct', target: s.avg_profit_lift_pct,
              format: v => `${v >= 0 ? '+' : ''}${v.toFixed(1)}% vs Status Quo baseline` },
            { id: 'kpi-inventory-units', target: s.total_inventory_units || 0,
              format: v => `${Math.round(v).toLocaleString('en-IN')} units` },
            { id: 'kpi-total-skus', target: s.total_skus || 0,
              format: v => `${Math.round(v)} ${Math.round(v) === 1 ? 'SKU' : 'SKUs'}` },
            { id: 'kpi-risk-skus', target: (risks['High Risk'] || 0) + (risks['Critical'] || 0) + (risks['Medium Risk'] || 0) + (risks['Stockout'] || 0),
              format: v => `${Math.round(v)} ${Math.round(v) === 1 ? 'SKU' : 'SKUs'}` }
        ];

        jobs.forEach((job, i) => {
            const el = document.getElementById(job.id);
            if (!el) return;
            this.animateValue(el, 0, job.target, 950 + i * 120, job.format);
        });

        // The two sub-labels are not animated; set them explicitly so the animation
        // pass never leaves the static placeholder text in place.
        const actionsEl = document.getElementById('kpi-actions-summary');
        const acts = s.action_counts || {};
        if (actionsEl) {
            const markdowns = (acts['Clearance Markdown'] || 0) + (acts['Slight Reduction'] || 0);
            const noStock = acts['No Stock'] || 0;
            actionsEl.textContent = `${acts['Increase Price'] || 0} Increases | ${markdowns} Markdowns` +
                (noStock ? ` | ${noStock} Out of Stock` : '');
        }
        const riskSubEl = document.getElementById('kpi-risk-subtext');
        if (riskSubEl) {
            riskSubEl.textContent = (risks['Stockout'] || 0)
                ? `${risks['Medium Risk'] || 0} Medium | ${risks['High Risk'] || 0} High | ${risks['Stockout']} Out of Stock`
                : `${risks['Medium Risk'] || 0} Medium | ${risks['High Risk'] || 0} High Urgency`;
        }
    },

    animateValue(el, from, to, duration, format) {
        if (typeof to !== 'number' || !isFinite(to)) {
            // Null / non-finite targets are stated in words rather than animated,
            // so an unavailable metric is never rendered as a confident 0.
            el.textContent = (to === null || to === undefined)
                ? 'baseline profit is non-positive'
                : (format ? format(to) : to);
            return;
        }
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            el.textContent = format(to);
            return;
        }
        el.classList.add('animating');
        const start = performance.now();
        const step = (now) => {
            const t = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
            el.textContent = format(from + (to - from) * eased);
            if (t < 1) {
                requestAnimationFrame(step);
            } else {
                el.classList.remove('animating');
            }
        };
        requestAnimationFrame(step);
    },

    updateSliderFill() {
        const slider = document.getElementById('sim-price-slider');
        if (!slider) return;
        const min = parseFloat(slider.min) || 0;
        const max = parseFloat(slider.max) || 1;
        const pct = ((parseFloat(slider.value) - min) / (max - min)) * 100;
        slider.style.background =
            `linear-gradient(90deg, #0e9e96 0%, var(--accent-signal) ${Math.max(0, pct - 8)}%, var(--bg-subtle) ${pct}%)`;
    },

    popTile(id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.remove('pop');
        void el.offsetWidth; // restart animation
        el.classList.add('pop');
    },

    popTiles() {
        ['sim-result-demand', 'sim-result-margin', 'sim-result-profit', 'sim-result-clearance']
            .forEach(id => this.popTile(id));
    },

    bindEvents() {
        // Desktop & Mobile Navigation Links
        const navLinks = document.querySelectorAll('.nav-list li');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const viewId = e.currentTarget.getAttribute('data-view');
                if (viewId) {
                    this.switchView(viewId);
                }
            });
        });

        // Mobile Hamburger Menu
        const menuBtn = document.getElementById('mobile-menu-toggle');
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebar-backdrop');

        if (menuBtn && sidebar && backdrop) {
            menuBtn.addEventListener('click', () => {
                sidebar.classList.toggle('open');
                backdrop.classList.toggle('active');
            });

            backdrop.addEventListener('click', () => {
                sidebar.classList.remove('open');
                backdrop.classList.remove('active');
            });
        }
    },

    switchView(viewId) {
        this.state.activeView = viewId;

        // Update nav links (selector corrected: markup uses .nav-list)
        document.querySelectorAll('.nav-list li').forEach(l => {
            if (l.getAttribute('data-view') === viewId) {
                l.classList.add('active');
            } else {
                l.classList.remove('active');
            }
        });

        // Switch views with smooth transition
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const targetView = document.getElementById(`view-${viewId}`);
        if (targetView) {
            targetView.classList.add('active');
            window.scrollTo({ top: 0, behavior: 'instant' });
        }

        // Update breadcrumb
        const titleEl = document.getElementById('current-view-title');
        const titles = {
            'overview': 'Executive Overview',
            'sku-pricing': 'Catalog Recommendations',
            'simulator': 'Real-Time Demand Simulator',
            'competitors': 'Competitor Intelligence',
            'transfers': 'Hardware Inventory & Store Cockpit',
            'retailer-portal': 'Offline Retailer Hub'
        };
        if (titleEl) {
            titleEl.textContent = titles[viewId] || 'Dashboard';
        }

        // Close mobile drawer if open
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebar-backdrop');
        if (sidebar && backdrop) {
            sidebar.classList.remove('open');
            backdrop.classList.remove('active');
        }

        // Resize charts if switching to a view with canvas
        window.dispatchEvent(new Event('resize'));

        if (viewId === 'retailer-portal') {
            if (this.state.currentRetailerResult) {
                setTimeout(() => this.renderRetailerCurveChart(this.state.currentRetailerResult), 60);
            } else if (!this._retailerAutoLoaded) {
                this._retailerAutoLoaded = true;
                this.loadRetailerPreset('iphone16');
            }
        }

        // Re-arm scroll reveals for the newly active view
        requestAnimationFrame(() => this.prepareViewReveals(viewId));

        // Keep the URL in sync so every view is deep-linkable and Back/Forward work.
        // Navigation driven by the router (hashchange / popstate) must not add a new
        // history entry, so shell.js raises suppressHistory for those calls.
        if (window.history && typeof window.history.pushState === 'function') {
            if ((window.location.hash || '') !== `#${viewId}`) {
                const quiet = !!(window.shell && window.shell.suppressHistory);
                window.history[quiet ? 'replaceState' : 'pushState']({ view: viewId }, '', `#${viewId}`);
            }
        }
    },

    async switchDataSource(source) {
        if (source === this.state.modelSource) return;
        this.state.modelSource = source;
        this.state.currentSimSku = null;

        // Toggle segmented control state
        const btnSyn = document.getElementById('src-synthetic');
        const btnKag = document.getElementById('src-kaggle');
        if (btnSyn) btnSyn.classList.toggle('active', source === 'synthetic');
        if (btnKag) btnKag.classList.toggle('active', source === 'kaggle');

        // Update sidebar provenance badge
        const badge = document.getElementById('telemetry-dataset');
        if (badge) badge.textContent = source === 'synthetic' ? 'SYNTHETIC' : 'REAL KAGGLE';

        // Reset simulator state and reload everything for the new source
        if (this.charts.simulatorCurve) { this.charts.simulatorCurve.destroy(); this.charts.simulatorCurve = null; }
        await this.loadData();
    },

    async loadData() {
        this.showLoading(true);
        try {
            const src = this.state.modelSource;
            const [summaryRes, optRes, transfersRes] = await Promise.all([
                fetch(`${API_BASE}/summary?model_source=${src}`),
                fetch(`${API_BASE}/optimizations?model_source=${src}`),
                fetch(`${API_BASE}/transfers`).catch(() => null)
            ]);
            
            if (!summaryRes.ok || !optRes.ok) {
                throw new Error("Server responded with error");
            }

            this.state.summary = await summaryRes.json();
            const optData = await optRes.json();
            this.state.optimizations = optData.data || [];
            this.state.activeEvents = optData.active_events || [];
            this.state.filtered = [...this.state.optimizations];

            if (transfersRes && transfersRes.ok) {
                const transfersData = await transfersRes.json();
                this.state.transfers = transfersData.data || [];
            }

            this.renderOverview();
            this.renderTable();
            this.renderCompetitors();
            this.renderTransfers();
            this.renderInventoryCockpit();
            this.renderTechBanner();
            this.initSimulator();
            this.animateKPIs();
            requestAnimationFrame(() => this.prepareViewReveals('overview'));
        } catch (error) {
            console.error("Failed to load AI pricing data:", error);
            this.renderErrorState();
        } finally {
            this.showLoading(false);
        }
    },

    async refreshOptimizations() {
        this.showLoading(true);
        try {
            const src = this.state.modelSource;
            const res = await fetch(`${API_BASE}/optimizations/refresh?model_source=${src}`, { method: 'POST' });
            if (!res.ok) throw new Error("Refresh failed");
            
            const [summaryRes, optData] = await Promise.all([
                fetch(`${API_BASE}/summary?model_source=${src}`).then(r => r.json()),
                res.json()
            ]);

            this.state.summary = summaryRes;
            this.state.optimizations = optData.data || [];
            this.state.activeEvents = optData.active_events || [];
            this.state.filtered = [...this.state.optimizations];

            this.renderOverview();
            this.renderTable();
            this.renderCompetitors();
            this.renderTransfers();
            this.renderInventoryCockpit();
            this.renderTechBanner();
            this.initSimulator();
            this.animateKPIs();
            requestAnimationFrame(() => this.prepareViewReveals(this.state.activeView));
        } catch (error) {
            console.error("Refresh error:", error);
        } finally {
            this.showLoading(false);
        }
    },

    renderTechBanner() {
        const banner = document.getElementById('tech-launch-banner');
        const title = document.getElementById('banner-title');
        const desc = document.getElementById('banner-desc');
        if (!banner) return;

        if (this.state.activeEvents && this.state.activeEvents.length > 0) {
            const ev = this.state.activeEvents[0];
            if (title) title.textContent = ev.headline || `${ev.successor_name} Announced!`;
            if (desc) desc.innerHTML = `Target: <strong>${ev.product_name}</strong> &bull; Urgent clearance window shifted from ${ev.old_days} to <strong>${ev.days_to_successor} days</strong>. Tactical markdown active to prevent post-launch depreciation write-down.`;
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
    },

    openLaunchModal() {
        const modal = document.getElementById('launch-modal');
        if (modal) modal.classList.remove('hidden');
    },

    closeLaunchModal() {
        const modal = document.getElementById('launch-modal');
        if (modal) modal.classList.add('hidden');
    },

    closeLaunchModalOnBackdrop(e) {
        if (e.target.id === 'launch-modal') {
            this.closeLaunchModal();
        }
    },

    async triggerTechEvent(eventKey) {
        this.closeLaunchModal();
        this.showLoading(true);

        const configs = {
            'iphone18': {
                product_id: 'SKU_IPHONE_17_256',
                successor_name: 'Apple iPhone 18',
                announcement_headline: 'Apple Unveils iPhone 18 Series with Next-Gen A20 Silicon',
                days_to_successor: 14,
                competitor_price_drop_pct: 0.04
            },
            'galaxy_s27': {
                product_id: 'SKU_GALAXY_S26_256',
                successor_name: 'Samsung Galaxy S27',
                announcement_headline: 'Samsung Galaxy Unpacked: Galaxy S27 Announced',
                days_to_successor: 21,
                competitor_price_drop_pct: 0.05
            },
            'pixel11': {
                product_id: 'SKU_PIXEL_10_PRO',
                successor_name: 'Google Pixel 11 Pro',
                announcement_headline: 'Google I/O: Pixel 11 Pro Announced',
                days_to_successor: 18,
                competitor_price_drop_pct: 0.03
            }
        };

        const payload = configs[eventKey];
        if (!payload) return;

        try {
            const res = await fetch(`${API_BASE}/lifecycle-event`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error("Event trigger failed");
            
            await this.refreshOptimizations();
            this.switchView('sku-pricing');
        } catch (err) {
            console.error("Failed to trigger tech event:", err);
        } finally {
            this.showLoading(false);
        }
    },

    async resetLifecycleEvents() {
        this.closeLaunchModal();
        this.showLoading(true);
        try {
            await fetch(`${API_BASE}/reset-events`, { method: 'POST' });
            await this.refreshOptimizations();
        } catch (err) {
            console.error("Failed to reset events:", err);
        } finally {
            this.showLoading(false);
        }
    },

    inspectActiveEvent() {
        if (this.state.activeEvents && this.state.activeEvents.length > 0) {
            const ev = this.state.activeEvents[0];
            this.openModal(ev.product_id);
        }
    },

    formatCurrency(val) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0
        }).format(val || 0);
    },

    renderOverview() {
        const s = this.state.summary;
        if (!s) return;

        // KPI metrics
        const profitLiftEl = document.getElementById('kpi-profit-lift');
        const profitLiftPctEl = document.getElementById('kpi-profit-lift-pct');
        const invUnitsEl = document.getElementById('kpi-inventory-units');
        const invValEl = document.getElementById('kpi-inventory-value');
        const totalSkusEl = document.getElementById('kpi-total-skus');
        const actionsSummaryEl = document.getElementById('kpi-actions-summary');
        const riskSkusEl = document.getElementById('kpi-risk-skus');
        const riskSubtextEl = document.getElementById('kpi-risk-subtext');

        if (profitLiftEl) profitLiftEl.textContent = `${s.total_profit_lift >= 0 ? '+' : ''}${this.formatCurrency(s.total_profit_lift)}`;
        if (profitLiftPctEl) {
            const pct = s.avg_profit_lift_pct;
            profitLiftPctEl.textContent = (pct === null || pct === undefined)
                ? 'baseline profit is non-positive' // the ratio is not meaningful here
                : `${pct >= 0 ? '+' : ''}${pct}% vs Status Quo baseline`;
        }
        if (invUnitsEl) invUnitsEl.textContent = `${(s.total_inventory_units || 0).toLocaleString('en-IN')} units`;
        if (invValEl) invValEl.textContent = `Catalog Value: ${this.formatCurrency(s.total_inventory_value)}`;
        const totalCount = s.total_skus || 0;
        if (totalSkusEl) totalSkusEl.textContent = `${totalCount} ${totalCount === 1 ? 'SKU' : 'SKUs'}`;

        // Keep the panel badge in step with the live KPI rather than showing a
        // hardcoded figure that would contradict the table below it.
        const totalGainBadge = document.getElementById('total-gain-badge');
        if (totalGainBadge) {
            const pct = s.avg_profit_lift_pct;
            totalGainBadge.textContent = (pct === null || pct === undefined)
                ? `${this.formatCurrency(s.total_profit_lift)} Total Gain`
                : `${pct >= 0 ? '+' : ''}${pct}% Total Gain`;
        }

        const acts = s.action_counts || {};
        if (actionsSummaryEl) {
            const markdowns = (acts['Clearance Markdown'] || 0) + (acts['Slight Reduction'] || 0);
            const noStock = acts['No Stock'] || 0;
            actionsSummaryEl.textContent =
                `${acts['Increase Price'] || 0} Increases | ${markdowns} Markdowns` +
                (noStock ? ` | ${noStock} Out of Stock` : '');
        }

        const risks = s.risk_counts || {};
        const criticalCount = (risks['High Risk'] || 0) + (risks['Critical'] || 0) + (risks['Medium Risk'] || 0) + (risks['Stockout'] || 0);
        if (riskSkusEl) riskSkusEl.textContent = `${criticalCount} ${criticalCount === 1 ? 'SKU' : 'SKUs'}`;
        if (riskSubtextEl) {
            riskSubtextEl.textContent = (risks['Stockout'] || 0)
                ? `${risks['Medium Risk'] || 0} Medium | ${risks['High Risk'] || 0} High | ${risks['Stockout']} Out of Stock`
                : `${risks['Medium Risk'] || 0} Medium | ${risks['High Risk'] || 0} High Urgency`;
        }

        // Render Charts
        this.renderProfitComparisonChart();
        this.renderActionDistributionChart();
        this.renderTopOpportunities();
    },

    renderProfitComparisonChart() {
        const ctx = document.getElementById('profitComparisonChart');
        if (!ctx) return;

        if (this.charts.profitComparison) {
            this.charts.profitComparison.destroy();
        }

        const labels = this.state.optimizations.map(o => {
            return o.product_name.split(' (')[0].replace('Apple ', '').replace('Samsung ', '').replace('Google ', '');
        });

        const statusQuoProfits = this.state.optimizations.map(o => o.status_quo_profit);
        const optimizedProfits = this.state.optimizations.map(o => o.expected_lifecycle_profit);

        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        const textColor = isLight ? '#475569' : '#78848c';
        const gridColor = isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.05)';
        const baselineBarColor = isLight ? 'rgba(100, 116, 139, 0.22)' : 'rgba(120, 132, 140, 0.28)';
        const baselineBorder = isLight ? '#64748b' : '#78848c';
        const optBarColor = isLight ? 'rgba(0, 137, 123, 0.85)' : 'rgba(20, 214, 196, 0.75)';
        const optBorder = isLight ? '#00897b' : '#14d6c4';

        Chart.defaults.color = textColor;
        Chart.defaults.font.family = "'Inter', sans-serif";

        this.charts.profitComparison = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Status Quo Baseline (₹)',
                        data: statusQuoProfits,
                        backgroundColor: baselineBarColor,
                        borderColor: baselineBorder,
                        borderWidth: 1,
                        borderRadius: 6
                    },
                    {
                        label: 'AI Optimized Net Profit (₹)',
                        data: optimizedProfits,
                        backgroundColor: optBarColor,
                        borderColor: optBorder,
                        borderWidth: 1,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 850, easing: 'easeOutQuart' },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, padding: 14, font: { size: 12 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => `${context.dataset.label}: ${this.formatCurrency(context.raw)}`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: {
                            callback: (val) => `₹${(val / 100000).toFixed(1)}L`
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    },

    renderActionDistributionChart() {
        const ctx = document.getElementById('actionDistributionChart');
        if (!ctx) return;

        if (this.charts.actionDistribution) {
            this.charts.actionDistribution.destroy();
        }

        // Derive the distribution from the live summary. The previous fallback was a
        // hardcoded four-key object, so any action the API introduced (e.g. "No Stock")
        // would render with no colour and no legend entry.
        const acts = (this.state.summary && this.state.summary.action_counts) || {};
        const entries = Object.entries(acts).filter(([, v]) => v > 0);

        if (!entries.length) {
            // Nothing to plot: destroy and show a note instead of an empty ring.
            ctx.parentNode.innerHTML =
                '<div class="mono-label" style="display:grid;place-items:center;height:100%;">No pricing actions returned.</div>';
            return;
        }

        const ACTION_COLORS = {
            'Increase Price': '#34d399',
            'Hold Price': '#f5a524',
            'Slight Reduction': '#14d6c4',
            'Clearance Markdown': '#f4586a',
            'No Stock': '#78848c'
        };

        const labels = entries.map(([k]) => k);
        const dataVals = entries.map(([, v]) => v);
        const colors = labels.map((l) => ACTION_COLORS[l] || '#55606a');

        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        this.charts.actionDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataVals,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: isLight ? '#ffffff' : '#101417'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                animation: { animateRotate: true, duration: 950, easing: 'easeOutQuart' },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 10,
                            padding: 12,
                            font: { size: 11, family: "'Inter', sans-serif" },
                            color: isLight ? '#1e293b' : '#e2e8f0'
                        }
                    }
                }
            }
        });
    },

    /* ============ Electronic Device Iconography & Hardware Badges ============ */

    getDeviceVisual(productName, brand, category, skuId, imageUrl) {
        const text = `${productName || ''} ${category || ''} ${brand || ''}`.toLowerCase();
        
        let devType = 'smartphone';
        let iconClass = 'fa-solid fa-mobile-screen';
        let categoryLabel = category || 'Smartphone';

        if (text.includes('laptop') || text.includes('macbook') || text.includes('notebook') || text.includes('thinkpad') || text.includes('xps') || text.includes('zenbook')) {
            devType = 'laptop';
            iconClass = 'fa-solid fa-laptop';
            categoryLabel = 'Laptop / PC';
        } else if (text.includes('tablet') || text.includes('ipad') || text.includes('tab s') || text.includes('xiaomi pad')) {
            devType = 'tablet';
            iconClass = 'fa-solid fa-tablet-screen-button';
            categoryLabel = 'Tablet';
        } else if (text.includes('watch') || text.includes('smartwatch') || text.includes('garmin')) {
            devType = 'smartwatch';
            iconClass = 'fa-solid fa-stopwatch';
            categoryLabel = 'Smartwatch';
        } else if (text.includes('headphone') || text.includes('audio') || text.includes('earbud') || text.includes('buds') || text.includes('airpod') || text.includes('wh-1000') || text.includes('xm5')) {
            devType = 'audio';
            iconClass = 'fa-solid fa-headphones';
            categoryLabel = 'Audio / TWS';
        } else if (text.includes('tv') || text.includes('television') || text.includes('bravia') || text.includes('oled tv')) {
            devType = 'tv';
            iconClass = 'fa-solid fa-tv';
            categoryLabel = 'Smart TV';
        } else if (text.includes('console') || text.includes('playstation') || text.includes('ps5') || text.includes('xbox') || text.includes('nintendo')) {
            devType = 'console';
            iconClass = 'fa-solid fa-gamepad';
            categoryLabel = 'Gaming Console';
        } else if (text.includes('camera') || text.includes('dslr') || text.includes('mirrorless')) {
            devType = 'camera';
            iconClass = 'fa-solid fa-camera';
            categoryLabel = 'Camera';
        } else if (text.includes('chip') || text.includes('charger') || text.includes('accessory')) {
            devType = 'accessories';
            iconClass = 'fa-solid fa-microchip';
            categoryLabel = 'Accessories';
        }

        // Clean Brand Badge
        const bText = `${brand || ''} ${productName || ''}`.toLowerCase();
        let brandBadgeHtml = '';
        if (bText.includes('apple')) {
            brandBadgeHtml = '<i class="fa-brands fa-apple" title="Apple"></i> Apple';
        } else if (bText.includes('google')) {
            brandBadgeHtml = '<i class="fa-brands fa-google" title="Google"></i> Google';
        } else if (bText.includes('samsung')) {
            brandBadgeHtml = '<span style="color:#5b8def; font-weight:700;">SAM</span> Samsung';
        } else if (bText.includes('oneplus')) {
            brandBadgeHtml = '<span style="color:#ea384c; font-weight:700;">1+</span> OnePlus';
        } else if (bText.includes('xiaomi') || bText.includes('redmi')) {
            brandBadgeHtml = '<span style="color:#ff6900; font-weight:700;">MI</span> Xiaomi';
        } else if (bText.includes('sony')) {
            brandBadgeHtml = '<span style="color:#e2e8f0; font-weight:700;">SONY</span>';
        } else if (brand) {
            brandBadgeHtml = `<span>${brand.toUpperCase()}</span>`;
        } else {
            brandBadgeHtml = `<span>HARDWARE</span>`;
        }

        // Micro-thumbnail if resolved or available
        let thumbHtml = '';
        const imgPath = imageUrl || this.resolveProductThumbnail(productName, brand, skuId);
        if (imgPath) {
            thumbHtml = `<img src="${imgPath}" class="device-thumb" alt="${productName}" onerror="this.style.display='none'">`;
        }

        const clickAttr = skuId ? `onclick="app.openHardwareInspector('${skuId}')" style="cursor:pointer;" title="Click to inspect electronic hardware &amp; stock allocation"` : '';

        return `
            <div class="device-cell" ${clickAttr}>
                <div class="device-visual-wrap">
                    ${thumbHtml}
                    <div class="device-icon-box device-${devType}" title="${categoryLabel}">
                        <i class="${iconClass}"></i>
                    </div>
                </div>
                <div class="device-info">
                    <div class="device-title-row">
                        <span class="device-title" title="${productName}">${productName}</span>
                        <span class="device-category-chip">${categoryLabel}</span>
                    </div>
                    <div class="device-meta-row">
                        <span class="device-brand-badge">${brandBadgeHtml}</span>
                        ${skuId ? `<span class="device-sku-id mono-num">&bull; ${skuId}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    },

    resolveProductThumbnail(productName, brand, productId) {
        const text = `${productName || ''} ${brand || ''} ${productId || ''}`.toLowerCase();
        // Do not attach phone images to non-phone categories
        if (text.includes('laptop') || text.includes('macbook') || text.includes('headphone') || text.includes('audio') || text.includes('watch') || text.includes('tv') || text.includes('tablet')) {
            return null;
        }
        if (text.includes('iphone 17') || text.includes('iphone_17') || (text.includes('17') && text.includes('apple'))) return 'img/iphone_17.jpg?v=2.3';
        if (text.includes('iphone 16') || text.includes('iphone_16') || (text.includes('16') && text.includes('apple'))) return 'img/iphone_16.jpg?v=2.3';
        if (text.includes('pixel') || text.includes('google')) return 'img/pixel_10_pro.jpg?v=2.3';
        if (text.includes('ultra') || text.includes('s26 ultra') || text.includes('s26_ultra') || text.includes('s25 ultra')) return 'img/galaxy_s26_ultra.jpg?v=2.3';
        if (text.includes('a56') || text.includes('galaxy_a56') || text.includes('galaxy a')) return 'img/galaxy_a56.jpg?v=2.3';
        if (text.includes('s26') || text.includes('galaxy_s26') || text.includes('s25') || text.includes('s24')) return 'img/galaxy_s26.jpg?v=2.3';
        if (text.includes('oneplus') || text.includes('nord')) return 'img/oneplus_13.jpg?v=2.3';
        if (text.includes('redmi') || text.includes('note 15') || text.includes('note_15')) return 'img/redmi_note_15.jpg?v=2.3';
        return null;
    },

    renderTopOpportunities() {
        const tbody = document.getElementById('top-opportunities-body');
        if (!tbody) return;

        tbody.innerHTML = '';
        const top3 = [...this.state.optimizations]
            .sort((a, b) => b.profit_lift_amount - a.profit_lift_amount)
            .slice(0, 3);

        top3.forEach((item, idx) => {
            const tr = document.createElement('tr');
            tr.classList.add('row-enter');
            tr.style.setProperty('--rd', `${idx * 90}ms`);
            const devVisual = this.getDeviceVisual(item.product_name, item.brand, item.category, item.product_id, item.image_url);
            tr.innerHTML = `
                <td>${devVisual}</td>
                <td>${this.formatCurrency(item.current_price)}</td>
                <td class="price-up"><strong>${this.formatCurrency(item.recommended_price)}</strong></td>
                <td class="text-success font-semibold">+${this.formatCurrency(item.profit_lift_amount)} (+${item.profit_lift_pct}%)</td>
                <td><span class="badge badge-primary">${item.price_action}</span></td>
                <td>${(item.clearance_probability * 100).toFixed(0)}%</td>
                <td>
                    <button class="btn btn-outline btn-xs" onclick="app.openModal('${item.product_id}')">
                        <i class="fa-solid fa-file-lines"></i> View Memo
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    renderTable() {
        const tbody = document.getElementById('sku-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';
        if (this.state.filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 2rem; color: var(--text-muted);">No SKUs match the selected filters.</td></tr>`;
            return;
        }

        this.state.filtered.forEach((item, idx) => {
            const tr = document.createElement('tr');
            tr.classList.add('row-enter');
            tr.style.setProperty('--rd', `${Math.min(idx * 45, 420)}ms`);
            const isUrgentEvent = Boolean(item.active_event);
            if (isUrgentEvent) {
                tr.classList.add('row-urgent-event');
            }
            
            let priceClass = 'price-hold';
            let icon = '<i class="fa-solid fa-minus"></i>';
            if (item.recommended_price > item.current_price) {
                priceClass = 'price-up';
                icon = '<i class="fa-solid fa-arrow-trend-up"></i>';
            } else if (item.recommended_price < item.current_price) {
                priceClass = 'price-down';
                icon = '<i class="fa-solid fa-arrow-trend-down"></i>';
            }

            let riskClass = 'risk-low';
            const riskLc = (item.inventory_risk_level || '').toLowerCase();
            if (riskLc.includes('high') || riskLc.includes('critical') || riskLc.includes('stockout') || isUrgentEvent) {
                riskClass = 'risk-high';
            } else if (riskLc.includes('medium')) {
                riskClass = 'risk-medium';
            }

            const alertBadge = isUrgentEvent ? `<div class="badge badge-danger" style="margin-top:0.3rem;"><i class="fa-solid fa-satellite-dish pulse-radar"></i> ${item.active_event.successor_name} Announced!</div>` : '';
            const devVisual = this.getDeviceVisual(item.product_name, item.brand, item.category, item.product_id, item.image_url);

            tr.innerHTML = `
                <td>
                    ${devVisual}
                    ${alertBadge}
                </td>
                <td>${this.formatCurrency(item.current_price)}</td>
                <td class="${priceClass}">
                    ${icon} ${this.formatCurrency(item.recommended_price)}
                    <div style="font-size:0.75rem;">${item.price_change >= 0 ? '+' : ''}${this.formatCurrency(item.price_change)}</div>
                    <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;" title="${item.elasticity_method || 'Price Elasticity'}">
                        ε = ${item.elasticity !== null && item.elasticity !== undefined ? Number(item.elasticity).toFixed(2) : '--'} <span style="opacity:0.8;">(${item.elasticity_regime || 'Dynamic'})</span>
                    </div>
                </td>
                <td class="text-success">
                    <strong>+${this.formatCurrency(item.profit_lift_amount)}</strong>
                    <div style="font-size:0.75rem; color:var(--text-muted);">+${item.profit_lift_pct}%</div>
                </td>
                <td>
                    <div><strong>${item.expected_sales_horizon} units</strong></div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${item.expected_daily_demand} / day (${item.days_to_successor}d left)</div>
                </td>
                <td>
                    <div>${item.current_inventory} units</div>
                    <span class="risk-tag ${riskClass}">${isUrgentEvent ? 'Urgent Clearance' : item.inventory_risk_level}</span>
                </td>
                <td style="color:var(--text-muted)">${this.formatCurrency(item.mrp)}</td>
                <td>
                    <button class="btn btn-outline btn-xs" onclick="app.openModal('${item.product_id}')">
                        <i class="fa-solid fa-brain"></i> Explain
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    filterTable() {
        const query = (document.getElementById('sku-search-input')?.value || '').toLowerCase();
        const brand = document.getElementById('brand-filter')?.value || 'all';
        const action = document.getElementById('action-filter')?.value || 'all';
        const risk = document.getElementById('risk-filter')?.value || 'all';

        this.state.filtered = this.state.optimizations.filter(item => {
            const matchesQuery = !query || 
                item.product_name.toLowerCase().includes(query) || 
                item.product_id.toLowerCase().includes(query);

            const matchesBrand = brand === 'all' || 
                (item.brand && item.brand.toLowerCase() === brand.toLowerCase()) ||
                item.product_name.toLowerCase().includes(brand.toLowerCase());

            const matchesAction = action === 'all' || item.price_action === action;

            const matchesRisk = risk === 'all' || 
                item.inventory_risk_level.toLowerCase().includes(risk.toLowerCase());

            return matchesQuery && matchesBrand && matchesAction && matchesRisk;
        });

        this.renderTable();
    },

    renderCompetitors() {
        const tbody = document.getElementById('competitor-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';
        this.state.optimizations.forEach((item, idx) => {
            const tr = document.createElement('tr');
            tr.classList.add('row-enter');
            tr.style.setProperty('--rd', `${Math.min(idx * 45, 420)}ms`);
            const diffComp = item.recommended_price - item.competitor_avg_price;
            const diffPct = ((diffComp / item.competitor_avg_price) * 100).toFixed(1);

            let compAdvantageBadge = '';
            if (diffComp < 0) {
                compAdvantageBadge = `<span class="badge badge-success"><i class="fa-solid fa-shield"></i> Underpricing Comp by ${Math.abs(diffPct)}%</span>`;
            } else if (diffComp > 0) {
                compAdvantageBadge = `<span class="badge badge-primary"><i class="fa-solid fa-gem"></i> Premium Markup +${diffPct}%</span>`;
            } else {
                compAdvantageBadge = `<span class="badge badge-warning">Market Parity</span>`;
            }

            const devVisual = this.getDeviceVisual(item.product_name, item.brand, item.category, item.product_id, item.image_url);

            tr.innerHTML = `
                <td>${devVisual}</td>
                <td>${this.formatCurrency(item.current_price)}</td>
                <td class="text-accent font-semibold">${this.formatCurrency(item.recommended_price)}</td>
                <td>${this.formatCurrency(item.competitor_avg_price)}</td>
                <td>${this.formatCurrency(item.competitor_min_price)}</td>
                <td style="color:var(--text-muted)">${this.formatCurrency(item.mrp)}</td>
                <td>${compAdvantageBadge}</td>
            `;
            tbody.appendChild(tr);
        });
    },

    renderTransfers() {
        const tbody = document.getElementById('transfers-body');
        const healthBody = document.getElementById('store-health-body');
        const totalBenefitEl = document.getElementById('transfer-total-benefit');
        if (!tbody || !healthBody) return;

        tbody.innerHTML = '';
        healthBody.innerHTML = '';

        let totalBenefit = 0;
        let totalTransfers = 0;

        (this.state.transfers || []).forEach(sku => {
            const devVisual = this.getDeviceVisual(sku.product_name, sku.brand, sku.category, sku.product_id);

            // Store health rows
            (sku.stores_summary || []).forEach((s, si) => {
                const tr = document.createElement('tr');
                tr.classList.add('row-enter');
                tr.style.setProperty('--rd', `${Math.min(si * 35, 350)}ms`);
                let statusClass = 'risk-low';
                if (s.status === 'Excess Overstock') statusClass = 'risk-medium';
                if (s.status === 'Stockout Imminent' || s.status === 'Stockout') statusClass = 'risk-high';
                tr.innerHTML = `
                    <td>${devVisual}</td>
                    <td><strong>${s.store_name}</strong></td>
                    <td style="color:var(--text-muted);">${s.city}</td>
                    <td class="mono-num">${s.current_inventory} units</td>
                    <td class="mono-num">${s.daily_sales_velocity} u/d</td>
                    <td class="mono-num">${s.days_of_supply}d</td>
                    <td><span class="risk-tag ${statusClass}">${s.status}</span></td>
                `;
                healthBody.appendChild(tr);
            });

            // Transfer plan rows
            (sku.recommended_transfers || []).forEach((t, ti) => {
                totalTransfers++;
                totalBenefit += (t.net_benefit || 0);
                const tr = document.createElement('tr');
                tr.classList.add('row-enter');
                tr.style.setProperty('--rd', `${Math.min(ti * 50, 400)}ms`);
                tr.innerHTML = `
                    <td>${devVisual}</td>
                    <td>${t.from_store_name}</td>
                    <td>${t.to_store_name}</td>
                    <td class="mono-num"><strong>${t.transfer_units}</strong> units</td>
                    <td class="mono-num">${this.formatCurrency(t.transfer_cost)}</td>
                    <td class="text-success mono-num"><strong>+${this.formatCurrency(t.net_benefit)}</strong></td>
                    <td style="font-size:0.78rem; color:var(--text-secondary);">${t.reason}</td>
                `;
                tbody.appendChild(tr);
            });
        });

        if (totalBenefitEl) {
            totalBenefitEl.textContent = `Net Benefit: +${this.formatCurrency(totalBenefit)} · ${totalTransfers} transfers`;
        }

        if (totalTransfers === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-muted);">No profitable transfers found for this snapshot — no SKU has both a surplus store and a deficit store, or the logistics cost exceeds the margin recovered. Check the Store-Level Supply Health table below for stockout stores that need replenishment instead.</td></tr>`;
        }
    },

    /* ============ Electronic Hardware Inventory Cockpit ============ */

    setInventoryTab(tabName) {
        this.state.inventoryActiveTab = tabName;
        const tabs = ['cards', 'stores', 'transfers'];
        tabs.forEach(t => {
            const btn = document.getElementById(`tab-btn-${t}`);
            const pane = document.getElementById(`inv-pane-${t}`);
            if (btn) {
                if (t === tabName) {
                    btn.classList.add('btn-primary', 'active');
                    btn.classList.remove('btn-outline');
                    btn.setAttribute('aria-selected', 'true');
                } else {
                    btn.classList.remove('btn-primary', 'active');
                    btn.classList.add('btn-outline');
                    btn.setAttribute('aria-selected', 'false');
                }
            }
            if (pane) {
                if (t === tabName) {
                    pane.classList.remove('hidden');
                    pane.classList.add('active');
                } else {
                    pane.classList.add('hidden');
                    pane.classList.remove('active');
                }
            }
        });
    },

    setInventoryBrandFilter(brand) {
        this.state.inventoryBrandFilter = brand;
        const pills = document.querySelectorAll('#inv-brand-pills .brand-pill');
        pills.forEach(p => {
            if ((brand === 'all' && p.textContent.trim().toLowerCase().includes('all')) ||
                p.textContent.trim().toLowerCase() === brand.toLowerCase()) {
                p.classList.add('active');
            } else {
                p.classList.remove('active');
            }
        });
        this.filterInventoryCards();
    },

    renderInventoryCockpit() {
        const items = this.state.optimizations || [];
        if (!items || items.length === 0) return;

        // Compute aggregate inventory metrics
        let totalUnits = 0;
        let totalValuation = 0;
        let riskCapital = 0;
        let totalDosWeighted = 0;

        items.forEach(item => {
            const units = item.current_inventory || 0;
            const cost = item.unit_cost || 0;
            totalUnits += units;
            totalValuation += (units * cost);

            const isPreSuccessorRisk = (item.days_to_successor || 999) <= 30;
            const isHighRisk = item.inventory_risk_level === 'High Risk' || item.inventory_risk_level === 'Critical';
            if (isPreSuccessorRisk || isHighRisk) {
                riskCapital += (units * cost);
            }

            const dailyDemand = Math.max(0.2, item.expected_daily_demand || 1);
            const dos = units / dailyDemand;
            totalDosWeighted += (dos * units);
        });

        const avgDos = totalUnits > 0 ? (totalDosWeighted / totalUnits) : 0;

        // Update KPI telemetry ribbon
        const unitsEl = document.getElementById('inv-kpi-total-units');
        const valEl = document.getElementById('inv-kpi-valuation');
        const riskEl = document.getElementById('inv-kpi-risk-capital');
        const dosEl = document.getElementById('inv-kpi-avg-dos');
        const navStockBadge = document.getElementById('nav-stock-badge');

        if (unitsEl) unitsEl.textContent = `${totalUnits.toLocaleString('en-IN')} units`;
        if (valEl) valEl.textContent = this.formatCurrency(totalValuation);
        if (riskEl) riskEl.textContent = this.formatCurrency(riskCapital);
        if (dosEl) dosEl.textContent = `${avgDos.toFixed(1)}d`;
        if (navStockBadge) navStockBadge.textContent = `${items.length} SKUs`;

        this.filterInventoryCards();
    },

    filterInventoryCards() {
        const searchInput = document.getElementById('inv-search-input');
        const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        const riskSelect = document.getElementById('inv-risk-filter');
        const riskVal = riskSelect ? riskSelect.value : 'all';
        const sortSelect = document.getElementById('inv-sort-select');
        const sortVal = sortSelect ? sortSelect.value : 'inventory-desc';
        const brandFilter = (this.state.inventoryBrandFilter || 'all').toLowerCase();

        let filtered = (this.state.optimizations || []).filter(item => {
            // Brand filter
            if (brandFilter !== 'all') {
                const b = (item.brand || '').toLowerCase();
                if (!b.includes(brandFilter)) return false;
            }

            // Search query
            if (query) {
                const text = `${item.product_name || ''} ${item.product_id || ''} ${item.brand || ''} ${item.model || ''} ${item.category || ''}`.toLowerCase();
                if (!text.includes(query)) return false;
            }

            // Health / Risk filter
            const dailyDemand = Math.max(0.2, item.expected_daily_demand || 1);
            const dos = (item.current_inventory || 0) / dailyDemand;
            const daysToSucc = item.days_to_successor || 999;

            if (riskVal === 'Healthy') {
                if (dos < 15 || dos > 40) return false;
            } else if (riskVal === 'Overstock') {
                if (dos <= 40) return false;
            } else if (riskVal === 'Urgent') {
                if (daysToSucc > 25) return false;
            } else if (riskVal === 'Stockout') {
                if (dos >= 12) return false;
            }

            return true;
        });

        // Sorting
        filtered.sort((a, b) => {
            const aUnits = a.current_inventory || 0;
            const bUnits = b.current_inventory || 0;
            const aCost = a.unit_cost || 0;
            const bCost = b.unit_cost || 0;
            const aDailyDemand = Math.max(0.2, a.expected_daily_demand || 1);
            const bDailyDemand = Math.max(0.2, b.expected_daily_demand || 1);
            const aDos = aUnits / aDailyDemand;
            const bDos = bUnits / bDailyDemand;

            if (sortVal === 'inventory-desc') return bUnits - aUnits;
            if (sortVal === 'value-desc') return (bUnits * bCost) - (aUnits * aCost);
            if (sortVal === 'successor-asc') return (a.days_to_successor || 999) - (b.days_to_successor || 999);
            if (sortVal === 'dos-desc') return bDos - aDos;
            if (sortVal === 'dos-asc') return aDos - bDos;
            return 0;
        });

        this.renderInventoryCards(filtered);
    },

    renderInventoryCards(items) {
        const grid = document.getElementById('inventory-cards-grid');
        if (!grid) return;

        grid.innerHTML = '';
        if (!items || items.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3.5rem 1.5rem; background: var(--bg-surface); border: 1px solid var(--line); border-radius: var(--radius-lg);">
                    <i class="fa-solid fa-box-open" style="font-size: 2.2rem; color: var(--text-muted); margin-bottom: 0.75rem;"></i>
                    <h3 style="font-size: 1.05rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.35rem;">No matching hardware inventory items</h3>
                    <p style="font-size: 0.8rem; color: var(--text-muted); max-width: 420px; margin: 0 auto;">Try clearing search keywords or switching the brand filter to view all available devices.</p>
                </div>
            `;
            return;
        }

        items.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'inv-device-card';
            card.style.setProperty('--card-delay', `${Math.min(idx * 45, 360)}ms`);

            const imgPath = this.resolveProductThumbnail(item.product_name, item.brand, item.product_id) || 'img/iphone_17.jpg';
            const units = item.current_inventory || 0;
            const cost = item.unit_cost || 0;
            const valuation = units * cost;
            const velocity = (item.expected_daily_demand || 0).toFixed(1);
            const dailyDemand = Math.max(0.2, item.expected_daily_demand || 1);
            const dos = (units / dailyDemand).toFixed(1);
            const dosNum = parseFloat(dos);
            const daysToSucc = item.days_to_successor || 60;

            // Health status tag & progress color
            let statusLabel = 'Healthy Runway';
            let statusClass = 'healthy';
            let barPct = Math.min(100, Math.max(10, (dosNum / 60) * 100));

            if (daysToSucc <= 20) {
                statusLabel = 'Urgent Clearance';
                statusClass = 'urgent';
            } else if (dosNum > 45) {
                statusLabel = 'Overstock Markdown Risk';
                statusClass = 'overstock';
            } else if (dosNum < 12) {
                statusLabel = 'Stockout Imminent';
                statusClass = 'stockout';
            }

            // Brand emblem with explicit brand colors & vector iconography
            const brandText = (item.brand || 'HARDWARE').toUpperCase();
            let brandColor = '#14d6c4';
            let brandLabelHtml = `<span>${item.brand || 'Hardware'}</span>`;
            if (brandText.includes('APPLE')) {
                brandColor = '#ffffff';
                brandLabelHtml = `<i class="fa-brands fa-apple" style="color:#ffffff;"></i> <span>Apple</span>`;
            } else if (brandText.includes('SAMSUNG')) {
                brandColor = '#60a5fa';
                brandLabelHtml = `<span style="color:#60a5fa; font-weight:800;">SAM</span> <span>Samsung</span>`;
            } else if (brandText.includes('GOOGLE')) {
                brandColor = '#34a853';
                brandLabelHtml = `<i class="fa-brands fa-google" style="color:#34a853;"></i> <span>Google</span>`;
            } else if (brandText.includes('ONEPLUS')) {
                brandColor = '#f87171';
                brandLabelHtml = `<span style="color:#f87171; font-weight:800;">1+</span> <span>OnePlus</span>`;
            } else if (brandText.includes('XIAOMI')) {
                brandColor = '#fb923c';
                brandLabelHtml = `<span style="color:#fb923c; font-weight:800;">MI</span> <span>Xiaomi</span>`;
            }

            const runwayText = daysToSucc <= 30 ? `${daysToSucc}d to successor` : `${daysToSucc}d runway`;

            // Store allocation mini-bars (from transfers store summary if present)
            const skuTransfers = (this.state.transfers || []).find(t => t.product_id === item.product_id);
            const storeSummary = skuTransfers ? (skuTransfers.stores_summary || []) : [];
            let storePillsHtml = '';
            if (storeSummary.length > 0) {
                const maxStoreInv = Math.max(...storeSummary.map(s => s.current_inventory || 1), 1);
                storePillsHtml = `
                    <div class="inv-store-mini-alloc" title="Stock presence across metro stores">
                        ${storeSummary.slice(0, 6).map(s => {
                            const fill = Math.min(100, Math.max(8, ((s.current_inventory || 0) / maxStoreInv) * 100));
                            const cityAbbr = (s.city || s.store_name || '').substring(0, 3).toUpperCase();
                            return `
                                <div class="inv-store-dot-item" title="${s.store_name}: ${s.current_inventory} units (${s.days_of_supply}d)">
                                    <div class="inv-store-dot-bar">
                                        <div class="inv-store-dot-fill" style="width:${fill}%;"></div>
                                    </div>
                                    <span class="inv-store-dot-name">${cityAbbr}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="inv-card-media" onclick="app.openHardwareInspector('${item.product_id}')" title="Click to inspect electronic hardware &amp; multi-store inventory">
                    <span class="inv-media-badge-left" style="border-left: 3px solid ${brandColor};">
                        ${brandLabelHtml}
                    </span>
                    <span class="inv-media-badge-right ${statusClass}">
                        <span class="pulse-indicator"></span>
                        <span>${runwayText}</span>
                    </span>
                    <img src="${imgPath}" class="inv-device-img" alt="${item.product_name}" loading="lazy" onerror="this.src='img/iphone_17.jpg'">
                    <button class="btn btn-outline btn-xs inv-inspect-overlay" onclick="event.stopPropagation(); app.openHardwareInspector('${item.product_id}')">
                        <i class="fa-solid fa-magnifying-glass-plus"></i> Inspect
                    </button>
                </div>
                <div class="inv-card-body">
                    <div class="inv-title-strip">
                        <div class="inv-card-title" title="${item.product_name}">${item.product_name}</div>
                        <div class="inv-card-sku-meta">
                            <span class="sku-chip">${item.product_id}</span>
                            <span>&bull;</span>
                            <span>${item.category || 'Consumer Tech'}</span>
                        </div>
                    </div>

                    <div class="inv-pricing-strip">
                        <div class="inv-price-col">
                            <span class="inv-price-label">Shelf Price</span>
                            <span class="inv-price-val">${this.formatCurrency(item.current_price)}</span>
                        </div>
                        <div class="inv-price-col">
                            <span class="inv-price-label">AI Clearance</span>
                            <span class="inv-price-val optimal">${this.formatCurrency(item.recommended_price)}</span>
                        </div>
                        <div class="inv-price-col">
                            <span class="inv-price-label">Legal MRP</span>
                            <span class="inv-price-val subtle">${this.formatCurrency(item.mrp)}</span>
                        </div>
                    </div>

                    <div class="inv-stock-runway-wrap">
                        <div class="inv-runway-header">
                            <div class="inv-units-headline">${units.toLocaleString('en-IN')}<small>units on hand</small></div>
                            <span class="inv-dos-val text-${statusClass}">${dos}d supply</span>
                        </div>
                        <div class="inv-progress-track">
                            <div class="inv-progress-bar ${statusClass}" style="width: ${barPct}%;"></div>
                        </div>
                        <div class="inv-runway-footer">
                            <span>Valuation: <strong class="mono-num">${this.formatCurrency(valuation)}</strong></span>
                            <span>Velocity: <strong class="mono-num">${velocity} u/d</strong></span>
                        </div>
                    </div>

                    ${storePillsHtml}

                    <div class="inv-card-actions">
                        <button class="btn btn-outline btn-xs" onclick="app.openHardwareInspector('${item.product_id}')">
                            <i class="fa-solid fa-microchip"></i> Hardware Specs
                        </button>
                        <button class="btn btn-primary btn-xs" onclick="app.loadSimulatorProduct('${item.product_id}'); app.switchView('simulator');">
                            <i class="fa-solid fa-sliders"></i> Optimize
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    },

    openHardwareInspector(productId) {
        const item = (this.state.optimizations || []).find(x => x.product_id === productId);
        if (!item) return;

        this.state.activeHardwareModalSku = item;
        const modal = document.getElementById('hardware-modal');
        const content = document.getElementById('hardware-modal-content');
        if (!modal || !content) return;

        const imgPath = this.resolveProductThumbnail(item.product_name, item.brand, item.product_id) || 'img/iphone_17.jpg';
        const units = item.current_inventory || 0;
        const cost = item.unit_cost || 0;
        const valuation = units * cost;
        const dailyDemand = Math.max(0.2, item.expected_daily_demand || 1);
        const dos = (units / dailyDemand).toFixed(1);

        // Find store distribution
        const skuTransfers = (this.state.transfers || []).find(t => t.product_id === item.product_id);
        const storeSummary = skuTransfers ? (skuTransfers.stores_summary || []) : [];

        let storeRowsHtml = '';
        if (storeSummary.length > 0) {
            storeRowsHtml = storeSummary.map(s => {
                let badgeClass = 'risk-low';
                if (s.status === 'Excess Overstock') badgeClass = 'risk-medium';
                if (s.status === 'Stockout Imminent' || s.status === 'Stockout') badgeClass = 'risk-high';
                return `
                    <tr>
                        <td><strong>${s.store_name}</strong></td>
                        <td style="color:var(--text-muted);">${s.city}</td>
                        <td class="mono-num"><strong>${s.current_inventory}</strong> u</td>
                        <td class="mono-num">${s.daily_sales_velocity} u/d</td>
                        <td class="mono-num">${s.days_of_supply}d</td>
                        <td><span class="risk-tag ${badgeClass}">${s.status}</span></td>
                    </tr>
                `;
            }).join('');
        } else {
            storeRowsHtml = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:1rem;">Multi-store telemetry syncing...</td></tr>`;
        }

        content.innerHTML = `
            <div class="hw-modal-grid">
                <!-- Left Column: Photo & Hardware Specs -->
                <div class="hw-showcase-column">
                    <div class="hw-photo-frame">
                        <img src="${imgPath}" class="hw-photo-img" alt="${item.product_name}">
                    </div>
                    <div class="hw-specs-grid">
                        <div class="hw-spec-tile">
                            <span class="hw-spec-key">BRAND</span>
                            <span class="hw-spec-val">${item.brand || 'Electronics'}</span>
                        </div>
                        <div class="hw-spec-tile">
                            <span class="hw-spec-key">CATEGORY</span>
                            <span class="hw-spec-val">${item.category || 'Smartphone'}</span>
                        </div>
                        <div class="hw-spec-tile">
                            <span class="hw-spec-key">HARDWARE ID</span>
                            <span class="hw-spec-val mono-num">${item.product_id}</span>
                        </div>
                        <div class="hw-spec-tile">
                            <span class="hw-spec-key">SUCCESSOR</span>
                            <span class="hw-spec-val">${item.successor_model || 'Next-Gen'} (${item.days_to_successor || 60}d)</span>
                        </div>
                    </div>
                </div>

                <!-- Right Column: Economics & Store Allocation -->
                <div class="hw-data-column">
                    <div>
                        <h3 style="font-size:1.25rem; font-weight:700; color:var(--text-primary); margin-bottom:0.25rem;">${item.product_name}</h3>
                        <p style="font-size:0.8rem; color:var(--text-muted);">Finite-horizon hardware lifecycle optimization &amp; multi-store allocation matrix</p>
                    </div>

                    <!-- Financial Strip -->
                    <div class="inv-pricing-strip">
                        <div class="inv-price-col">
                            <span class="inv-price-label">Acquisition Cost</span>
                            <span class="inv-price-val">${this.formatCurrency(cost)}</span>
                        </div>
                        <div class="inv-price-col">
                            <span class="inv-price-label">Current Shelf</span>
                            <span class="inv-price-val">${this.formatCurrency(item.current_price)}</span>
                        </div>
                        <div class="inv-price-col">
                            <span class="inv-price-label">AI Optimal</span>
                            <span class="inv-price-val optimal">${this.formatCurrency(item.recommended_price)}</span>
                        </div>
                        <div class="inv-price-col">
                            <span class="inv-price-label">Total Units</span>
                            <span class="inv-price-val mono-num">${units.toLocaleString('en-IN')}</span>
                        </div>
                        <div class="inv-price-col">
                            <span class="inv-price-label">Capital Value</span>
                            <span class="inv-price-val mono-num">${this.formatCurrency(valuation)}</span>
                        </div>
                        <div class="inv-price-col">
                            <span class="inv-price-label">Days Supply</span>
                            <span class="inv-price-val mono-num">${dos}d</span>
                        </div>
                    </div>

                    <!-- Store Distribution Table -->
                    <div>
                        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.4rem;">
                            <span style="font-family:var(--font-mono); font-size:0.65rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); font-weight:600;">Store-Level Allocation &amp; Velocities</span>
                            <span style="font-family:var(--font-mono); font-size:0.65rem; color:var(--accent-signal);">6 Metro Branches</span>
                        </div>
                        <div class="hw-store-table-box">
                            <table class="hw-store-table">
                                <thead>
                                    <tr>
                                        <th>STORE</th>
                                        <th>CITY</th>
                                        <th>STOCK</th>
                                        <th>VELOCITY</th>
                                        <th>RUNWAY</th>
                                        <th>HEALTH</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${storeRowsHtml}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- AI Recommendation Memo -->
                    <div style="background:var(--bg-inset); border:1px solid var(--line); border-radius:var(--radius-sm); padding:0.75rem 0.85rem; font-size:0.78rem; line-height:1.45; color:var(--text-secondary);">
                        <strong style="color:var(--text-primary);"><i class="fa-solid fa-wand-magic-sparkles text-accent"></i> Optimization Rationale:</strong>
                        ${item.business_reason || `Recommended price of ${this.formatCurrency(item.recommended_price)} maximizes net profit before the ${item.days_to_successor}-day successor deadline.`}
                    </div>
                </div>
            </div>
        `;

        modal.classList.remove('hidden');
    },

    closeHardwareModal() {
        const modal = document.getElementById('hardware-modal');
        if (modal) modal.classList.add('hidden');
    },

    closeHardwareModalOnBackdrop(event) {
        if (event.target && event.target.id === 'hardware-modal') {
            this.closeHardwareModal();
        }
    },

    simulateFromHardwareModal() {
        const sku = this.state.activeHardwareModalSku;
        this.closeHardwareModal();
        if (sku) {
            this.loadSimulatorProduct(sku.product_id);
            this.switchView('simulator');
        }
    },

    initSimulator() {
        const select = document.getElementById('sim-product-select');
        if (!select || this.state.optimizations.length === 0) return;

        select.innerHTML = '';
        this.state.optimizations.forEach(item => {
            const opt = document.createElement('option');
            opt.value = item.product_id;
            opt.textContent = `${item.product_name} (${this.formatCurrency(item.recommended_price)})`;
            select.appendChild(opt);
        });

        if (!this.state.currentSimSku) {
            this.state.currentSimSku = this.state.optimizations[0];
        }
        this.loadSimulatorProduct();
    },

    loadSimulatorProduct() {
        const select = document.getElementById('sim-product-select');
        if (!select) return;

        const pid = select.value;
        const sku = this.state.optimizations.find(o => o.product_id === pid) || this.state.optimizations[0];
        if (!sku) return;

        this.state.currentSimSku = sku;
        this.state.simPrice = sku.recommended_price;

        // Update bounds & meta
        const minPrice = Math.round(sku.unit_cost * 0.95);
        const maxPrice = Math.round(sku.mrp);

        const slider = document.getElementById('sim-price-slider');
        const minPriceEl = document.getElementById('sim-min-price');
        const mrpPriceEl = document.getElementById('sim-mrp-price');
        const unitCostEl = document.getElementById('sim-unit-cost');
        const mrpLimitEl = document.getElementById('sim-mrp-limit');
        const compPriceEl = document.getElementById('sim-comp-price');
        const daysSuccEl = document.getElementById('sim-days-successor');
        const invEl = document.getElementById('sim-inventory');

        if (slider) {
            slider.min = minPrice;
            slider.max = maxPrice;
            slider.step = 100;
            slider.value = sku.recommended_price;
        }
        this.updateSliderFill();

        if (minPriceEl) minPriceEl.textContent = `Cost: ${this.formatCurrency(minPrice)}`;
        if (mrpPriceEl) mrpPriceEl.textContent = `MRP: ${this.formatCurrency(maxPrice)}`;
        if (unitCostEl) unitCostEl.textContent = this.formatCurrency(sku.unit_cost);
        if (mrpLimitEl) mrpLimitEl.textContent = this.formatCurrency(sku.mrp);
        if (compPriceEl) compPriceEl.textContent = this.formatCurrency(sku.competitor_avg_price);
        if (daysSuccEl) daysSuccEl.textContent = `${sku.days_to_successor} days`;
        if (invEl) invEl.textContent = `${sku.current_inventory} units`;
        const elSpecEl = document.getElementById('sim-baseline-elasticity');
        if (elSpecEl) elSpecEl.textContent = `${sku.elasticity !== null && sku.elasticity !== undefined ? Number(sku.elasticity).toFixed(2) : '--'} (${sku.elasticity_regime || 'Dynamic'})`;

        this.updateSimulatorCalculations();
        this.renderSimulatorCurves();
    },

    onSliderChange() {
        const slider = document.getElementById('sim-price-slider');
        if (!slider) return;

        this.state.simPrice = parseFloat(slider.value);
        this.updateSliderFill();
        this.updateSimulatorCalculations();
    },

    setSimPriceRel(delta) {
        const slider = document.getElementById('sim-price-slider');
        if (!slider) return;

        const newP = Math.max(parseFloat(slider.min), Math.min(parseFloat(slider.max), this.state.simPrice + delta));
        slider.value = newP;
        this.state.simPrice = newP;
        this.updateSliderFill();
        this.updateSimulatorCalculations();
        this.popTiles();
    },

    resetSimToRecommended() {
        if (!this.state.currentSimSku) return;
        const slider = document.getElementById('sim-price-slider');
        if (slider) {
            slider.value = this.state.currentSimSku.recommended_price;
            this.state.simPrice = this.state.currentSimSku.recommended_price;
            this.updateSliderFill();
            this.updateSimulatorCalculations();
            this.popTiles();
        }
    },

    updateSimulatorCalculations() {
        const sku = this.state.currentSimSku;
        if (!sku) return;

        const p = this.state.simPrice;
        const displayEl = document.getElementById('sim-price-display');
        if (displayEl) displayEl.textContent = this.formatCurrency(p);

        let estimatedDemand = sku.expected_daily_demand;
        let netProfit = sku.expected_lifecycle_profit;
        let demandLo = estimatedDemand;
        let demandHi = estimatedDemand;

        // 60fps server curve interpolation for seamless consistency between tiles and chart
        if (sku.feasible_prices && sku.feasible_prices.length > 1) {
            const prices = sku.feasible_prices;
            const demands = sku.demand_curve;
            const profits = sku.profit_curve;
            const demandsLo = sku.demand_curve_lower || demands;
            const demandsHi = sku.demand_curve_upper || demands;

            if (p <= prices[0]) {
                estimatedDemand = demands[0];
                netProfit = profits[0];
                demandLo = demandsLo[0];
                demandHi = demandsHi[0];
            } else if (p >= prices[prices.length - 1]) {
                const last = prices.length - 1;
                estimatedDemand = demands[last];
                netProfit = profits[last];
                demandLo = demandsLo[last];
                demandHi = demandsHi[last];
            } else {
                for (let i = 0; i < prices.length - 1; i++) {
                    if (p >= prices[i] && p <= prices[i + 1]) {
                        const span = prices[i + 1] - prices[i];
                        const t = span > 0 ? (p - prices[i]) / span : 0;
                        estimatedDemand = (1 - t) * demands[i] + t * demands[i + 1];
                        netProfit = (1 - t) * profits[i] + t * profits[i + 1];
                        demandLo = (1 - t) * demandsLo[i] + t * demandsLo[i + 1];
                        demandHi = (1 - t) * demandsHi[i] + t * demandsHi[i + 1];
                        break;
                    }
                }
            }
        }

        const unitMargin = p - sku.unit_cost;
        const clearanceDays = sku.current_inventory / (estimatedDemand + 1e-5);

        // Dynamically compute point/arc elasticity from candidate price-demand curve
        let pointElasticity = null;
        let pointRegime = 'Dynamic';
        if (sku.feasible_prices && sku.feasible_prices.length > 1 && sku.demand_curve && sku.demand_curve.length > 1) {
            const fp = sku.feasible_prices;
            const dc = sku.demand_curve;
            for (let i = 0; i < fp.length - 1; i++) {
                if (p >= fp[i] && p <= fp[i + 1]) {
                    const pDiff = fp[i + 1] - fp[i];
                    const dDiff = dc[i] - dc[i + 1];
                    const pAvg = (fp[i] + fp[i + 1]) / 2;
                    const dAvg = (dc[i] + dc[i + 1]) / 2;
                    if (pDiff > 0 && dAvg > 0) {
                        pointElasticity = (dDiff / dAvg) / (pDiff / pAvg);
                    }
                    break;
                }
            }
        }
        if (pointElasticity !== null && pointElasticity > 0.01) {
            pointRegime = pointElasticity > 1.8 ? 'Highly Elastic' : (pointElasticity >= 1.1 ? 'Moderately Elastic' : 'Inelastic');
        } else if (sku.elasticity !== null && sku.elasticity !== undefined) {
            pointElasticity = sku.elasticity;
            pointRegime = sku.elasticity_regime || 'Dynamic';
        }

        // Update UI tiles
        const resDemand = document.getElementById('sim-result-demand');
        const resMargin = document.getElementById('sim-result-margin');
        const resElasticity = document.getElementById('sim-result-elasticity');
        const resProfit = document.getElementById('sim-result-profit');
        const resClearance = document.getElementById('sim-result-clearance');

        if (resDemand) {
            resDemand.innerHTML = `${estimatedDemand.toFixed(1)} <small>units/day</small>`;
            if (demandLo !== undefined && demandHi !== undefined && Math.abs(demandHi - demandLo) > 0.05) {
                resDemand.title = `80% Conformal Interval: [${demandLo.toFixed(1)}, ${demandHi.toFixed(1)}] units/day`;
            }
        }
        if (resMargin) resMargin.textContent = this.formatCurrency(unitMargin);
        if (resElasticity) {
            resElasticity.innerHTML = `${pointElasticity !== null ? Number(pointElasticity).toFixed(2) : '--'} <span class="tile-unit" id="sim-result-regime">${pointRegime}</span>`;
        }
        if (resProfit) resProfit.textContent = this.formatCurrency(netProfit);
        if (resClearance) resClearance.innerHTML = `${clearanceDays.toFixed(0)} <small>days</small>`;

        // Debounced backend simulation to sync exact state
        this.scheduleBackendSimulation(p, sku);
    },

    scheduleBackendSimulation(price, sku) {
        if (this._simDebounceTimer) clearTimeout(this._simDebounceTimer);
        this._simDebounceTimer = setTimeout(() => {
            this.fetchBackendSimulation(price, sku);
        }, 180);
    },

    async fetchBackendSimulation(price, sku) {
        try {
            const res = await fetch(`${API_BASE}/simulate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_id: sku.product_id,
                    price: price,
                    model_source: this.state.modelSource || 'synthetic',
                    // Send the SKU's real context. Without these the endpoint falls back
                    // to its own defaults, so the tiles would contradict the chart
                    // (which is computed by the optimizer from the true values).
                    inventory: sku.current_inventory,
                    days_to_successor: sku.days_to_successor,
                    competitor_avg_price: sku.competitor_avg_price,
                    competitor_min_price: sku.competitor_min_price
                })
            });
            // A non-OK response must not silently leave stale numbers on screen.
            if (!res.ok) throw new Error(`simulate HTTP ${res.status}`);
            const data = await res.json();
            if (data.status === 'success') {
                const resDemand = document.getElementById('sim-result-demand');
                const resMargin = document.getElementById('sim-result-margin');
                const resProfit = document.getElementById('sim-result-profit');
                const resClearance = document.getElementById('sim-result-clearance');

                if (resDemand && data.daily_demand !== undefined) {
                    resDemand.innerHTML = `${data.daily_demand.toFixed(1)} <small>units/day</small>`;
                    if (data.daily_demand_lower !== undefined && data.daily_demand_upper !== undefined) {
                        resDemand.title = `80% Conformal Interval: [${data.daily_demand_lower.toFixed(1)}, ${data.daily_demand_upper.toFixed(1)}] units/day`;
                    }
                }
                if (resMargin && data.margin_per_unit !== undefined) {
                    resMargin.textContent = this.formatCurrency(data.margin_per_unit);
                }
                const resElasticity = document.getElementById('sim-result-elasticity');
                if (resElasticity && data.elasticity !== undefined && data.elasticity !== null) {
                    resElasticity.innerHTML = `${Number(data.elasticity).toFixed(2)} <span class="tile-unit" id="sim-result-regime">${data.elasticity_regime || 'Dynamic'}</span>`;
                    if (data.elasticity_advice) {
                        resElasticity.title = data.elasticity_advice;
                    }
                }
                if (resProfit && data.expected_net_profit !== undefined) {
                    resProfit.textContent = this.formatCurrency(data.expected_net_profit);
                }
                if (resClearance && data.clearance_days !== undefined) {
                    resClearance.innerHTML = `${data.clearance_days.toFixed(0)} <small>days</small>`;
                }
            }
        } catch (e) {
            // Silently maintain smooth interpolated values
        }
    },

    renderSimulatorCurves() {
        const ctx = document.getElementById('simulatorCurveChart');
        const sku = this.state.currentSimSku;
        if (!ctx || !sku || !sku.feasible_prices) return;

        if (this.charts.simulatorCurve) {
            this.charts.simulatorCurve.destroy();
        }

        const prices = sku.feasible_prices;
        const profits = sku.profit_curve;
        const demands = sku.demand_curve;

        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        const gridColor = isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.05)';
        const profitColor = isLight ? '#00897b' : '#14d6c4';
        const profitFill = isLight ? 'rgba(0, 137, 123, 0.12)' : 'rgba(20, 214, 196, 0.1)';
        const demandColor = isLight ? '#475569' : '#78848c';

        const datasets = [
            {
                label: 'Projected Net Profit (₹)',
                data: profits,
                borderColor: profitColor,
                backgroundColor: profitFill,
                fill: true,
                tension: 0.35,
                yAxisID: 'yProfit',
                pointRadius: 2,
                pointHoverRadius: 6,
                order: 1
            },
            {
                label: 'Daily Demand (Units)',
                data: demands,
                borderColor: demandColor,
                backgroundColor: 'transparent',
                borderDash: [4, 4],
                tension: 0.3,
                yAxisID: 'yDemand',
                pointRadius: 2,
                pointHoverRadius: 6,
                order: 2
            }
        ];

        // Conformal Prediction Interval band (P10 - P90)
        if (sku.demand_curve_upper && sku.demand_curve_lower) {
            datasets.push({
                label: 'Demand Uncertainty (P90)',
                data: sku.demand_curve_upper,
                borderColor: isLight ? 'rgba(71, 85, 105, 0.35)' : 'rgba(120, 132, 140, 0.3)',
                borderWidth: 1,
                borderDash: [2, 2],
                backgroundColor: isLight ? 'rgba(71, 85, 105, 0.08)' : 'rgba(120, 132, 140, 0.08)',
                fill: '+1',
                tension: 0.3,
                yAxisID: 'yDemand',
                pointRadius: 0,
                pointHoverRadius: 0,
                order: 3
            });
            datasets.push({
                label: 'Demand Uncertainty (P10)',
                data: sku.demand_curve_lower,
                borderColor: isLight ? 'rgba(71, 85, 105, 0.35)' : 'rgba(120, 132, 140, 0.3)',
                borderWidth: 1,
                borderDash: [2, 2],
                backgroundColor: 'transparent',
                fill: false,
                tension: 0.3,
                yAxisID: 'yDemand',
                pointRadius: 0,
                pointHoverRadius: 0,
                order: 4
            });
        }

        this.charts.simulatorCurve = new Chart(ctx, {
            type: 'line',
            data: {
                labels: prices.map(p => `₹${p.toLocaleString('en-IN')}`),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 750, easing: 'easeOutQuart' },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                if (context.dataset.yAxisID === 'yProfit') {
                                    return `Net Profit: ${this.formatCurrency(context.raw)}`;
                                }
                                if (context.dataset.label.includes('Uncertainty')) {
                                    return `${context.dataset.label}: ${context.raw.toFixed(1)} u/d`;
                                }
                                return `Daily Demand: ${context.raw.toFixed(1)} units/day`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { maxTicksLimit: 7 }
                    },
                    yProfit: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: gridColor },
                        ticks: {
                            callback: (val) => `₹${(val / 100000).toFixed(1)}L`
                        }
                    },
                    yDemand: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: {
                            callback: (val) => `${val.toFixed(0)} u/d`
                        }
                    }
                }
            }
        });
    },

    openModal(productId) {
        const sku = this.state.optimizations.find(o => o.product_id === productId);
        if (!sku) return;

        this.state.activeModalSku = sku;
        const modal = document.getElementById('memo-modal');
        const body = document.getElementById('modal-content');
        if (!modal || !body) return;

        const memo = sku.memo || {};

        // XAI: render TreeSHAP feature contributions as horizontal bars
        let xaiHtml = '';
        const xai = sku.xai;
        if (xai && xai.top_factors && xai.top_factors.length) {
            const maxAbs = Math.max(...xai.top_factors.map(f => f.abs_contribution), 1e-6);
            const bars = xai.top_factors.map(f => {
                const pct = Math.max(3, Math.round((f.abs_contribution / maxAbs) * 100));
                const cls = f.direction === 'positive' ? 'xai-bar-pos' : 'xai-bar-neg';
                const sign = f.contribution >= 0 ? '+' : '';
                return `
                    <div class="xai-row">
                        <span class="xai-feature mono-num">${f.feature}</span>
                        <div class="xai-track">
                            <div class="xai-bar ${cls}" style="width:${pct}%"></div>
                        </div>
                        <span class="xai-val mono-num ${f.direction === 'positive' ? 'text-success' : 'text-warning'}">${sign}${f.contribution.toFixed(2)}</span>
                    </div>`;
            }).join('');
            xaiHtml = `
                <div class="memo-section">
                    <div class="memo-section-title">Model Explanation · ${xai.method || 'TreeSHAP'}</div>
                    <p class="memo-text">Additive feature contributions to the predicted daily demand (model base value: ${(xai.base_value ?? 0).toFixed(2)}). Cyan = boosts demand, amber = suppresses demand.</p>
                    <div class="xai-list">${bars}</div>
                </div>`;
        }

        body.innerHTML = `
            <h3 class="memo-headline">${memo.headline || `Pricing Guidance: ${sku.product_name}`}</h3>
            
            <div class="memo-section">
                <div class="memo-section-title">Econometric Rationale</div>
                <p class="memo-text">${memo.key_rationale || sku.business_reason}</p>
            </div>

            ${xaiHtml}

            <div class="memo-section">
                <div class="memo-section-title">Offline Store Advantage</div>
                <p class="memo-text">${memo.offline_advantage || 'In-store touch-and-feel inspection and instant setup justify this price point.'}</p>
            </div>

            <div class="memo-stats-grid">
                <div class="memo-stat-item">
                    <span class="memo-stat-label">Price Action</span>
                    <span class="memo-stat-val text-accent">${sku.price_action}</span>
                </div>
                <div class="memo-stat-item">
                    <span class="memo-stat-label">Price Elasticity</span>
                    <span class="memo-stat-val text-accent" title="${sku.elasticity_method || ''}">ε = ${sku.elasticity !== null && sku.elasticity !== undefined ? Number(sku.elasticity).toFixed(2) : '--'} <small style="font-size:0.75rem; color:var(--text-muted);">(${sku.elasticity_regime || 'Dynamic'})</small></span>
                </div>
                <div class="memo-stat-item">
                    <span class="memo-stat-label">Profit Lift</span>
                    <span class="memo-stat-val text-success">+${this.formatCurrency(sku.profit_lift_amount)}</span>
                </div>
                <div class="memo-stat-item">
                    <span class="memo-stat-label">Clearance Prob.</span>
                    <span class="memo-stat-val">${(sku.clearance_probability * 100).toFixed(0)}%</span>
                </div>
            </div>
        `;

        modal.classList.remove('hidden');
    },

    closeModal() {
        const modal = document.getElementById('memo-modal');
        if (modal) modal.classList.add('hidden');
    },

    closeModalOnBackdrop(e) {
        if (e.target.id === 'memo-modal') {
            this.closeModal();
        }
    },

    simulateFromModal() {
        const sku = this.state.activeModalSku;
        this.closeModal();
        if (sku) {
            this.switchView('simulator');
            const select = document.getElementById('sim-product-select');
            if (select) {
                select.value = sku.product_id;
                this.loadSimulatorProduct();
            }
        }
    },

    /* ============ Offline Retailer Hub & Device Management Engine ============ */

    initRetailerHub() {
        this.updateDeviceIconPreview();
        this.loadSavedRetailerInventory();
    },

    updateDeviceIconPreview() {
        const typeSelect = document.getElementById('ret-device-type');
        const previewBox = document.getElementById('ret-device-icon-preview');
        const previewCat = document.getElementById('ret-preview-category');
        const brandSelect = document.getElementById('ret-brand');
        if (!typeSelect || !previewBox) return;

        const val = typeSelect.value || 'smartphone';
        const brand = brandSelect ? brandSelect.value : 'Apple';

        const typeMap = {
            smartphone: { cls: 'device-smartphone', icon: 'fa-mobile-screen-button', label: 'Smartphone Device' },
            laptop: { cls: 'device-laptop', icon: 'fa-laptop', label: 'Laptop / Ultrabook' },
            tablet: { cls: 'device-tablet', icon: 'fa-tablet-screen-button', label: 'Tablet / Slate' },
            smartwatch: { cls: 'device-smartwatch', icon: 'fa-clock', label: 'Smartwatch / Wearable' },
            audio: { cls: 'device-audio', icon: 'fa-headphones', label: 'Audio / TWS / ANC' },
            tv: { cls: 'device-tv', icon: 'fa-tv', label: 'Smart TV / Display' },
            console: { cls: 'device-console', icon: 'fa-gamepad', label: 'Gaming Console' },
            camera: { cls: 'device-camera', icon: 'fa-camera', label: 'Camera / Imaging' },
            accessories: { cls: 'device-accessories', icon: 'fa-plug', label: 'Accessory / Peripheral' }
        };

        const match = typeMap[val] || typeMap.smartphone;
        previewBox.className = `device-icon-box ${match.cls}`;
        previewBox.innerHTML = `<i class="fa-solid ${match.icon}"></i>`;
        if (previewCat) {
            previewCat.textContent = `${brand} · ${match.label}`;
        }
    },

    loadRetailerPreset(presetKey) {
        const buttons = document.querySelectorAll('.preset-chip-btn');
        buttons.forEach(b => b.classList.remove('active'));
        if (window.event && window.event.currentTarget) {
            window.event.currentTarget.classList.add('active');
        }

        const presets = {
            iphone16: {
                product_name: 'Apple iPhone 16 (128GB Blue)',
                brand: 'Apple',
                device_type: 'smartphone',
                inventory: 65,
                days_to_successor: 18,
                unit_cost: 58000,
                mrp: 79900,
                current_price: 69999,
                comp_avg: 66490,
                comp_min: 64999,
                offline_premium: 1000,
                store_channel: 'Metro Flagship Store'
            },
            galaxy_s25: {
                product_name: 'Samsung Galaxy S25 Ultra (512GB Titanium)',
                brand: 'Samsung',
                device_type: 'smartphone',
                inventory: 85,
                days_to_successor: 32,
                unit_cost: 102000,
                mrp: 141999,
                current_price: 134999,
                comp_avg: 131999,
                comp_min: 129499,
                offline_premium: 1500,
                store_channel: 'Metro Flagship Store'
            },
            oneplus13: {
                product_name: 'OnePlus 13 5G (256GB Black)',
                brand: 'OnePlus',
                device_type: 'smartphone',
                inventory: 40,
                days_to_successor: 45,
                unit_cost: 48000,
                mrp: 69999,
                current_price: 64999,
                comp_avg: 64200,
                comp_min: 63499,
                offline_premium: 800,
                store_channel: 'Tier-2 Hub Store'
            },
            macbook_m3: {
                product_name: 'Apple MacBook Air 15-inch M3 (16GB/512GB)',
                brand: 'Apple',
                device_type: 'laptop',
                inventory: 24,
                days_to_successor: 60,
                unit_cost: 112000,
                mrp: 134900,
                current_price: 128900,
                comp_avg: 126500,
                comp_min: 123990,
                offline_premium: 2000,
                store_channel: 'Metro Flagship Store'
            },
            sony_xm5: {
                product_name: 'Sony WH-1000XM5 Wireless Noise Cancelling Headphones',
                brand: 'Sony',
                device_type: 'audio',
                inventory: 50,
                days_to_successor: 28,
                unit_cost: 21500,
                mrp: 34990,
                current_price: 29990,
                comp_avg: 27990,
                comp_min: 26490,
                offline_premium: 1000,
                store_channel: 'High-Street Electronics'
            }
        };

        const p = presets[presetKey];
        if (!p) return;

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        };

        setVal('ret-product-name', p.product_name);
        setVal('ret-brand', p.brand);
        setVal('ret-device-type', p.device_type);
        setVal('ret-inventory', p.inventory);
        setVal('ret-days-successor', p.days_to_successor);
        setVal('ret-unit-cost', p.unit_cost);
        setVal('ret-mrp', p.mrp);
        setVal('ret-current-price', p.current_price);
        setVal('ret-comp-avg', p.comp_avg);
        setVal('ret-comp-min', p.comp_min);
        setVal('ret-offline-premium', p.offline_premium);
        setVal('ret-store-channel', p.store_channel);

        this.updateDeviceIconPreview();
        this.submitRetailerOptimization();
    },

    resetRetailerForm() {
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        };
        setVal('ret-product-name', '');
        setVal('ret-brand', 'Apple');
        setVal('ret-device-type', 'smartphone');
        setVal('ret-inventory', '20');
        setVal('ret-days-successor', '30');
        setVal('ret-unit-cost', '40000');
        setVal('ret-mrp', '59900');
        setVal('ret-current-price', '54900');
        setVal('ret-comp-avg', '52900');
        setVal('ret-comp-min', '51900');
        setVal('ret-offline-premium', '1000');
        this.updateDeviceIconPreview();

        const buttons = document.querySelectorAll('.preset-chip-btn');
        buttons.forEach(b => b.classList.remove('active'));

        const empty = document.getElementById('ret-empty-state');
        const container = document.getElementById('ret-results-container');
        if (empty) empty.classList.remove('hidden');
        if (container) container.classList.add('hidden');
    },

    async submitRetailerOptimization() {
        const getNum = (id) => parseFloat(document.getElementById(id)?.value || 0);
        const getStr = (id) => (document.getElementById(id)?.value || '').trim();

        const productName = getStr('ret-product-name') || 'Electronic Device';
        const brand = getStr('ret-brand') || 'Electronics';
        const deviceType = getStr('ret-device-type') || 'smartphone';
        const stockUnits = Math.max(1, Math.round(getNum('ret-inventory')));
        const daysToSuccessor = Math.max(1, Math.round(getNum('ret-days-successor')));
        const unitCost = Math.max(10, getNum('ret-unit-cost'));
        const mrp = Math.max(unitCost, getNum('ret-mrp'));
        let currentShelfPrice = Math.max(10, getNum('ret-current-price'));
        const compAvgPrice = Math.max(10, getNum('ret-comp-avg'));
        const compMinPrice = Math.max(10, getNum('ret-comp-min'));
        const showroomingPremium = Math.max(0, getNum('ret-offline-premium'));
        const storeChannel = getStr('ret-store-channel') || 'Metro Flagship Store';

        // Statutory Rule 18(2) compliance
        if (currentShelfPrice > mrp) {
            currentShelfPrice = mrp;
            const cpEl = document.getElementById('ret-current-price');
            if (cpEl) cpEl.value = mrp;
        }

        const payload = {
            product_name: productName,
            brand: brand,
            device_type: deviceType,
            unit_cost: unitCost,
            mrp: mrp,
            current_price: currentShelfPrice,
            current_shelf_price: currentShelfPrice,
            current_inventory: stockUnits,
            stock_units: stockUnits,
            days_to_successor: daysToSuccessor,
            competitor_avg_price: compAvgPrice,
            competitor_min_price: compMinPrice,
            offline_premium: showroomingPremium,
            offline_showrooming_premium: showroomingPremium,
            store_channel: storeChannel,
            channel_tier: storeChannel
        };

        const emptyState = document.getElementById('ret-empty-state');
        const loadingState = document.getElementById('ret-loading-state');
        const resultsContainer = document.getElementById('ret-results-container');

        if (emptyState) emptyState.classList.add('hidden');
        if (loadingState) loadingState.classList.remove('hidden');
        if (resultsContainer) resultsContainer.classList.add('hidden');

        try {
            const res = await fetch(`${API_BASE}/retailer/optimize-inventory`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errText = await res.text();
                throw new Error(`Optimization failed: ${res.status} - ${errText}`);
            }

            const resData = await res.json();
            const data = resData.data || resData;
            this.state.currentRetailerResult = {
                ...data,
                request_payload: payload
            };

            if (loadingState) loadingState.classList.add('hidden');
            if (resultsContainer) resultsContainer.classList.remove('hidden');

            this.renderRetailerResults(this.state.currentRetailerResult);
        } catch (e) {
            if (loadingState) loadingState.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            alert(`Error calculating optimal retail price: ${e.message}`);
        }
    },

    renderRetailerResults(data) {
        if (!data) return;

        // Visual box in Hero
        const visualWrap = document.getElementById('ret-hero-device-visual');
        if (visualWrap) {
            const devClass = `device-${data.device_type || 'smartphone'}`;
            const devIcon = data.device_icon || 'fa-mobile-screen-button';
            visualWrap.innerHTML = `
                <div class="device-icon-box ${devClass}" style="width:48px; height:48px; font-size:1.35rem; border-radius:var(--radius-sm);">
                    <i class="fa-solid ${devIcon}"></i>
                </div>
            `;
        }

        const titleEl = document.getElementById('ret-hero-title');
        const catEl = document.getElementById('ret-hero-category');
        const paceEl = document.getElementById('ret-hero-pace');
        const curEl = document.getElementById('ret-hero-current-price');
        const mrpEl = document.getElementById('ret-hero-mrp');
        const stockEl = document.getElementById('ret-hero-stock');
        const recEl = document.getElementById('ret-hero-rec-price');
        const badgeEl = document.getElementById('ret-hero-action-badge');
        const liftEl = document.getElementById('ret-hero-profit-lift');

        if (titleEl) titleEl.textContent = data.product_name;
        if (catEl) catEl.textContent = `${(data.device_type || 'electronic').toUpperCase()} · ${data.brand_badge || data.brand}`;
        if (curEl) curEl.textContent = this.formatCurrency(data.current_price);
        if (mrpEl) mrpEl.textContent = this.formatCurrency(data.mrp);
        if (stockEl) stockEl.textContent = `${data.stock_units} units`;
        if (recEl) recEl.textContent = this.formatCurrency(data.recommended_price);

        if (paceEl) {
            const prob = data.clearance_probability;
            if (prob >= 0.85) {
                paceEl.textContent = 'High Clearance Certainty';
                paceEl.className = 'mono-badge badge-accent';
            } else if (prob >= 0.60) {
                paceEl.textContent = 'Moderate Clearance Velocity';
                paceEl.className = 'mono-badge badge-primary';
            } else {
                paceEl.textContent = 'Overstock Risk Pace';
                paceEl.className = 'mono-badge text-warning';
            }
        }

        if (badgeEl) {
            badgeEl.textContent = data.price_action || 'OPTIMIZED';
            if (data.price_action.includes('MARKDOWN') || data.price_action.includes('CLEARANCE')) {
                badgeEl.className = 'retailer-price-action-badge badge badge-warning';
            } else if (data.price_action.includes('PREMIUM') || data.price_action.includes('HIKE')) {
                badgeEl.className = 'retailer-price-action-badge badge badge-success';
            } else {
                badgeEl.className = 'retailer-price-action-badge badge badge-primary';
            }
        }

        if (liftEl) {
            const lift = data.profit_lift_amount || 0;
            const pct = data.profit_lift_pct || 0;
            const sign = lift >= 0 ? '+' : '';
            liftEl.textContent = `${sign}${this.formatCurrency(lift)} (${sign}${pct.toFixed(1)}% Net Lift)`;
            liftEl.className = lift >= 0 ? 'mono-num font-semibold text-success' : 'mono-num font-semibold text-warning';
        }

        // Telemetry Tiles
        const velEl = document.getElementById('ret-res-velocity');
        const velSubEl = document.getElementById('ret-res-velocity-sub');
        const clearEl = document.getElementById('ret-res-clearance');
        const clearSubEl = document.getElementById('ret-res-clearance-sub');
        const probEl = document.getElementById('ret-res-prob');
        const probSubEl = document.getElementById('ret-res-prob-sub');
        const holdingEl = document.getElementById('ret-res-holding');
        const holdingSubEl = document.getElementById('ret-res-holding-sub');

        const vel = (data.expected_daily_sales ?? data.expected_daily_demand ?? 0);
        const sqVel = (data.status_quo_daily_sales ?? data.status_quo_daily_demand ?? 0);
        const clearDays = (data.clearance_days_needed ?? data.clearance_days ?? 0);
        const holdingSaved = (data.holding_cost_saved ?? data.holding_and_finance_cost ?? 0);

        if (velEl) velEl.innerHTML = `${vel.toFixed(1)} <span class="tile-unit">units/day</span>`;
        if (velSubEl) velSubEl.textContent = `vs ${sqVel.toFixed(1)} status quo`;

        if (clearEl) clearEl.innerHTML = `${clearDays.toFixed(1)} <span class="tile-unit">days</span>`;
        if (clearSubEl) clearSubEl.textContent = `Target horizon: ${data.days_to_successor || 60} days`;

        if (probEl) probEl.textContent = `${((data.clearance_probability || 0.85) * 100).toFixed(1)}%`;
        if (probSubEl) probSubEl.textContent = (data.clearance_probability || 0.85) >= 0.85 ? 'Safe finite-horizon clearance' : 'Monitoring required';

        if (holdingEl) holdingEl.textContent = this.formatCurrency(holdingSaved);
        if (holdingSubEl) holdingSubEl.textContent = 'Holding & obsolescence risk saved';

        // Render response curve chart
        this.renderRetailerCurveChart(data);

        // Render Multi-Channel Competitor Benchmarks Matrix
        this.renderRetailerBenchmarks(data);

        // Render Actionable 3-Stage Retailer Execution Playbook
        this.renderRetailerRoadmap(data);

        // Render TreeSHAP memo
        const memoEl = document.getElementById('ret-memo-text');
        if (memoEl) {
            const memo = data.memo || {};
            memoEl.innerHTML = `
                <div style="font-weight:600; color:var(--text-primary); margin-bottom:0.4rem;">
                    <i class="fa-solid fa-brain text-accent"></i> ${memo.headline || 'Algorithmic Retail Recommendation'}
                </div>
                <div style="margin-bottom:0.5rem;">${memo.key_rationale || data.business_reason || ''}</div>
                <div style="padding:0.5rem 0.75rem; background:var(--bg-card); border-left:3px solid var(--accent); border-radius:0 var(--radius-xs) var(--radius-xs) 0; font-size:0.78rem;">
                    <strong>In-Store Showrooming Defense:</strong> ${memo.offline_advantage || 'Physical touch-and-feel display and immediate hand-off capture demand at or slightly above online aggregator prices.'}
                </div>
            `;
        }
    },

    renderRetailerBenchmarks(data) {
        const tbody = document.getElementById('ret-benchmarks-body');
        if (!tbody) return;

        const benchmarks = data.benchmarks || [];
        tbody.innerHTML = '';

        benchmarks.forEach((b, i) => {
            const tr = document.createElement('tr');
            tr.classList.add('row-enter');
            tr.style.setProperty('--rd', `${i * 40}ms`);

            const diff = data.recommended_price - b.price;
            const diffSign = diff > 0 ? '+' : '';
            const diffClass = diff === 0 ? 'text-subtle' : diff > 0 ? 'text-warning' : 'text-success';

            tr.innerHTML = `
                <td><strong>${b.channel}</strong></td>
                <td><span class="category-pill">${b.type}</span></td>
                <td class="mono-num">${this.formatCurrency(b.price)}</td>
                <td class="mono-num ${diffClass}"><strong>${diffSign}${this.formatCurrency(diff)}</strong></td>
                <td class="mono-num font-semibold text-accent">${b.margin_pct}%</td>
                <td><span class="risk-tag risk-low">${b.status}</span></td>
            `;
            tbody.appendChild(tr);
        });
    },

    renderRetailerRoadmap(data) {
        const container = document.getElementById('ret-strategy-steps');
        if (!container) return;

        const roadmap = data.strategic_roadmap || [];
        container.innerHTML = '';

        roadmap.forEach((step, idx) => {
            const card = document.createElement('div');
            card.className = 'strategy-step-card';
            card.innerHTML = `
                <div class="step-num">${step.stage || `0${idx + 1}`}</div>
                <div class="step-timeline">${step.phase || 'Immediate'}</div>
                <div class="step-action-title">${step.title || 'Execute Strategy'}</div>
                <div class="step-desc">${step.action || ''}</div>
                <div class="step-impact mono-num">Target: ${step.impact || 'Sales Acceleration'}</div>
            `;
            container.appendChild(card);
        });
    },

    renderRetailerCurveChart(data) {
        const ctx = document.getElementById('retailerCurveChart');
        if (!ctx || !data.candidate_prices) return;

        if (this.charts.retailerCurve) {
            this.charts.retailerCurve.destroy();
        }

        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        const gridColor = isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.05)';
        const profitColor = isLight ? '#00897b' : '#14d6c4';
        const profitFill = isLight ? 'rgba(0, 137, 123, 0.12)' : 'rgba(20, 214, 196, 0.1)';
        const demandColor = isLight ? '#475569' : '#ffffff';

        const prices = data.candidate_prices;
        const profits = data.profit_curve;
        const demands = data.demand_curve;

        this.charts.retailerCurve = new Chart(ctx, {
            type: 'line',
            data: {
                labels: prices.map(p => `₹${p.toLocaleString('en-IN')}`),
                datasets: [
                    {
                        label: 'Projected Net Profit (₹)',
                        data: profits,
                        borderColor: profitColor,
                        backgroundColor: profitFill,
                        fill: true,
                        tension: 0.35,
                        yAxisID: 'yProfit',
                        pointRadius: 2,
                        pointHoverRadius: 6,
                        order: 1
                    },
                    {
                        label: 'Expected Daily Sales (u/d)',
                        data: demands,
                        borderColor: demandColor,
                        backgroundColor: 'transparent',
                        borderDash: [4, 4],
                        tension: 0.3,
                        yAxisID: 'yDemand',
                        pointRadius: 2,
                        pointHoverRadius: 6,
                        order: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 650, easing: 'easeOutQuart' },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                if (context.dataset.yAxisID === 'yProfit') {
                                    return `Net Profit: ${this.formatCurrency(context.raw)}`;
                                }
                                return `Daily Sales: ${context.raw.toFixed(1)} units/day`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { maxTicksLimit: 7 }
                    },
                    yProfit: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: gridColor },
                        ticks: {
                            callback: (val) => `₹${(val / 100000).toFixed(1)}L`
                        }
                    },
                    yDemand: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: {
                            callback: (val) => `${val.toFixed(0)} u/d`
                        }
                    }
                }
            }
        });
    },

    async saveCurrentRetailerProduct() {
        const btn = document.getElementById('btn-save-retailer-product');
        const origHtml = btn ? btn.innerHTML : '';

        const getNum = (id) => parseFloat(document.getElementById(id)?.value || 0);
        const getStr = (id) => (document.getElementById(id)?.value || '').trim();

        const payload = {
            product_name: getStr('ret-product-name') || 'Electronic Device',
            brand: getStr('ret-brand') || 'Electronics',
            device_type: getStr('ret-device-type') || 'smartphone',
            unit_cost: Math.max(10, getNum('ret-unit-cost')),
            mrp: Math.max(10, getNum('ret-mrp')),
            current_price: Math.max(10, getNum('ret-current-price')),
            current_shelf_price: Math.max(10, getNum('ret-current-price')),
            current_inventory: Math.max(1, Math.round(getNum('ret-inventory'))),
            stock_units: Math.max(1, Math.round(getNum('ret-inventory'))),
            days_to_successor: Math.max(1, Math.round(getNum('ret-days-successor'))),
            competitor_avg_price: Math.max(10, getNum('ret-comp-avg')),
            competitor_min_price: Math.max(10, getNum('ret-comp-min')),
            offline_premium: Math.max(0, getNum('ret-offline-premium')),
            offline_showrooming_premium: Math.max(0, getNum('ret-offline-premium')),
            store_channel: getStr('ret-store-channel') || 'Metro Flagship Store',
            channel_tier: getStr('ret-store-channel') || 'Metro Flagship Store'
        };

        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
            btn.disabled = true;
        }

        try {
            const res = await fetch(`${API_BASE}/retailer/save-inventory-product`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.text();
                throw new Error(err);
            }

            const data = await res.json();

            if (btn) {
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Saved to Store Ledger!';
                btn.classList.remove('btn-success');
                btn.classList.add('btn-primary');
                setTimeout(() => {
                    btn.innerHTML = origHtml;
                    btn.classList.add('btn-success');
                    btn.classList.remove('btn-primary');
                    btn.disabled = false;
                }, 2200);
            }

            await this.loadSavedRetailerInventory();
            this.loadData();
        } catch (e) {
            if (btn) {
                btn.innerHTML = origHtml;
                btn.disabled = false;
            }
            alert(`Could not save product: ${e.message}`);
        }
    },

    async loadSavedRetailerInventory() {
        try {
            const res = await fetch(`${API_BASE}/retailer/inventory`);
            if (!res.ok) return;
            const resJson = await res.json();
            const data = resJson.data || resJson;

            this.state.retailerInventory = data.items || resJson.items || [];

            const kpiSkus = document.getElementById('ret-kpi-skus');
            const kpiUnits = document.getElementById('ret-kpi-units');
            const kpiVal = document.getElementById('ret-kpi-value');
            const kpiLift = document.getElementById('ret-kpi-lift');
            const kpiLiftSub = document.getElementById('ret-kpi-lift-sub');
            const ledgerCount = document.getElementById('ret-ledger-count');

            if (kpiSkus) kpiSkus.textContent = data.total_skus || this.state.retailerInventory.length;
            if (kpiUnits) kpiUnits.textContent = `${(data.total_units || 0).toLocaleString('en-IN')} units`;
            if (kpiVal) kpiVal.textContent = `Valuation: ${this.formatCurrency(data.total_inventory_valuation || 0)}`;

            const lift = data.total_profit_lift || 0;
            const sign = lift >= 0 ? '+' : '';
            if (kpiLift) kpiLift.textContent = `${sign}${this.formatCurrency(lift)}`;
            if (kpiLiftSub) kpiLiftSub.textContent = `Net Profit Expansion`;
            if (ledgerCount) ledgerCount.textContent = `${this.state.retailerInventory.length} Products Tracked`;

            this.renderRetailerInventoryTable(this.state.retailerInventory);
        } catch (e) {
            console.warn('Failed to load retailer inventory:', e);
        }
    },

    renderRetailerInventoryTable(items) {
        const tbody = document.getElementById('retailer-inventory-body');
        if (!tbody) return;

        tbody.innerHTML = '';
        if (!items || items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:2rem; color:var(--text-muted);">No products in store inventory yet. Use the form above to optimize and add your first electronic device!</td></tr>`;
            return;
        }

        items.forEach((item, i) => {
            const tr = document.createElement('tr');
            tr.classList.add('row-enter');
            tr.style.setProperty('--rd', `${i * 35}ms`);

            const devVisual = this.getDeviceVisual(item.product_name, item.brand, item.device_type, item.product_id);
            const lift = item.profit_lift_amount || 0;
            const sign = lift >= 0 ? '+' : '';
            const probPct = Math.round((item.clearance_probability || 0.85) * 100);

            tr.innerHTML = `
                <td>${devVisual}</td>
                <td class="mono-num"><strong>${item.stock_units}</strong> units</td>
                <td class="mono-num">${item.days_to_successor}d</td>
                <td class="mono-num">${this.formatCurrency(item.unit_cost)}</td>
                <td class="mono-num text-subtle">${this.formatCurrency(item.current_shelf_price)}</td>
                <td class="mono-num font-semibold text-accent">
                    ${this.formatCurrency(item.recommended_price)}
                    <span class="price-action-pill ${this.getActionClass(item.price_action)} ml-2">${item.price_action}</span>
                </td>
                <td class="mono-num font-semibold text-success">
                    ${sign}${this.formatCurrency(lift)}
                </td>
                <td class="mono-num">
                    <span class="risk-tag ${probPct >= 80 ? 'risk-low' : probPct >= 60 ? 'risk-medium' : 'risk-high'}">${probPct}%</span>
                </td>
                <td>
                    <div style="display:flex; align-items:center; gap:0.4rem;">
                        <button class="btn btn-outline btn-sm" onclick="app.viewRetailerProductReport('${item.product_id}')" title="Inspect Optimization Studio">
                            <i class="fa-solid fa-chart-line"></i> Inspect
                        </button>
                        <button class="btn-terminal-icon" onclick="app.deleteRetailerProduct('${item.product_id}')" title="Delete from store ledger" aria-label="Delete product">
                            <i class="fa-solid fa-trash-can text-warning"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    viewRetailerProductReport(productId) {
        const item = (this.state.retailerInventory || []).find(x => x.product_id === productId);
        if (!item) return;

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        };

        setVal('ret-product-name', item.product_name);
        setVal('ret-brand', item.brand);
        setVal('ret-device-type', item.device_type || 'smartphone');
        setVal('ret-inventory', item.stock_units);
        setVal('ret-days-successor', item.days_to_successor);
        setVal('ret-unit-cost', item.unit_cost);
        setVal('ret-mrp', item.mrp);
        setVal('ret-current-price', item.current_shelf_price);
        setVal('ret-comp-avg', item.competitor_avg_price);
        setVal('ret-comp-min', item.competitor_min_price);
        setVal('ret-offline-premium', item.offline_showrooming_premium || 1000);
        setVal('ret-store-channel', item.channel_tier || 'Metro Flagship Store');

        this.updateDeviceIconPreview();
        this.submitRetailerOptimization();

        const studio = document.querySelector('.retailer-studio-grid');
        if (studio) studio.scrollIntoView({ behavior: 'smooth' });
    },

    async deleteRetailerProduct(productId) {
        if (!confirm('Are you sure you want to remove this electronic device from the store inventory and pricing engine?')) {
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/retailer/inventory/${productId}`, {
                method: 'DELETE'
            });
            if (!res.ok) throw new Error(`Delete failed: ${res.status}`);

            await this.loadSavedRetailerInventory();
            this.loadData();
        } catch (e) {
            alert(`Could not delete item: ${e.message}`);
        }
    },

    testRetailerInSimulator() {
        const res = this.state.currentRetailerResult;
        if (!res) {
            alert('Please run pricing optimization first before simulating.');
            return;
        }

        const skuId = res.product_id || 'RET-CUSTOM-001';
        let sku = (this.state.optimizations || []).find(x => x.product_id === skuId);

        if (!sku) {
            sku = {
                product_id: skuId,
                product_name: res.product_name,
                category: res.device_type || 'Electronics',
                brand: res.brand || 'Electronics',
                unit_cost: res.unit_cost,
                mrp: res.mrp,
                current_price: res.current_price,
                recommended_price: res.recommended_price,
                price_action: res.price_action,
                profit_lift_amount: res.profit_lift_amount,
                expected_daily_demand: res.expected_daily_sales,
                expected_lifecycle_profit: res.projected_net_profit,
                current_inventory: res.stock_units,
                days_to_successor: res.days_to_successor,
                competitor_avg_price: res.competitor_avg_price,
                competitor_min_price: res.competitor_min_price,
                clearance_probability: res.clearance_probability,
                feasible_prices: res.candidate_prices,
                profit_curve: res.profit_curve,
                demand_curve: res.demand_curve
            };
            this.state.optimizations.unshift(sku);
            const select = document.getElementById('sim-product-select');
            if (select) {
                const opt = document.createElement('option');
                opt.value = sku.product_id;
                opt.textContent = `${sku.product_name} (${this.formatCurrency(sku.recommended_price)})`;
                select.insertBefore(opt, select.firstChild);
            }
        }

        this.state.currentSimSku = sku;
        this.switchView('simulator');
        const select = document.getElementById('sim-product-select');
        if (select) {
            select.value = sku.product_id;
        }
        this.loadSimulatorProduct();
    },

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (!overlay) return;
        if (show) overlay.classList.remove('hidden');
        else overlay.classList.add('hidden');
    },

    renderErrorState() {
        // Strip the API prefix so the message names the origin actually in use,
        // instead of hardcoding a port that may not be the one serving this page.
        const origin = (typeof window !== 'undefined' && window.location && window.location.origin)
            ? window.location.origin
            : 'the FastAPI server';

        // Static fallback copy in the markup would otherwise sit next to an error
        // claiming numbers that nothing has verified.
        ['kpi-profit-lift', 'kpi-profit-lift-pct', 'kpi-inventory-units',
         'kpi-inventory-value', 'kpi-total-skus', 'kpi-actions-summary',
         'kpi-risk-skus', 'kpi-risk-subtext'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.textContent = '—';
        });
        const badge = document.getElementById('total-gain-badge');
        if (badge) badge.textContent = 'Unavailable';

        const tbody = document.getElementById('sku-table-body');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 3rem;">
                        <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; color: var(--status-warning); margin-bottom: 1rem; display: block;"></i>
                        <h4 style="margin-bottom: 0.5rem;">Could not connect to AI Engine API</h4>
                        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">No response from <code>${origin}/api</code>. Start the backend with <code>python -m uvicorn api.main:app --host 127.0.0.1 --port 8000</code> and open this page from that server.</p>
                        <button class="btn btn-primary btn-sm" onclick="app.loadData()">Retry Connection</button>
                    </td>
                </tr>
            `;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => app.init());

// Expose the engine on the global object. `const` at the top level of a classic
// script creates a global *lexical* binding (so inline onclick="app.x()" resolves)
// but NOT a property of `window` — so any companion script probing `window.app`
// would silently find undefined.
window.app = app;
