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
        modelSource: 'synthetic'
    },
    
    charts: {
        profitComparison: null,
        actionDistribution: null,
        simulatorCurve: null
    },

    init() {
        this.bindEvents();
        this.startClock();
        this.initScrollProgress();
        this.initRevealObserver();
        this.loadData();
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
        const jobs = [
            { id: 'kpi-profit-lift', target: s.total_profit_lift || 0,
              format: v => `+${this.formatCurrency(Math.round(v))}`, prefix: '+' },
            { id: 'kpi-profit-lift-pct', target: s.avg_profit_lift_pct || 0,
              format: v => `+${v.toFixed(1)}% vs Status Quo baseline` },
            { id: 'kpi-inventory-units', target: s.total_inventory_units || 0,
              format: v => `${Math.round(v).toLocaleString('en-IN')} units` },
            { id: 'kpi-total-skus', target: s.total_skus || 0,
              format: v => `${Math.round(v)} SKUs` },
            { id: 'kpi-risk-skus', target: ((s.risk_counts || {})['High Risk'] || 0) + ((s.risk_counts || {})['Critical'] || 0) + ((s.risk_counts || {})['Medium Risk'] || 0),
              format: v => `${Math.round(v)} SKUs` }
        ];

        jobs.forEach((job, i) => {
            const el = document.getElementById(job.id);
            if (!el) return;
            this.animateValue(el, 0, job.target, 950 + i * 120, job.format);
        });
    },

    animateValue(el, from, to, duration, format) {
        if (typeof to !== 'number' || !isFinite(to)) {
            el.textContent = format ? format(to) : to;
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
            `linear-gradient(90deg, #0284c7 0%, #00e5ff ${Math.max(0, pct - 8)}%, var(--bg-surface) ${pct}%)`;
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

        // Update nav links
        document.querySelectorAll('.nav-links li').forEach(l => {
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
        }

        // Update breadcrumb
        const titleEl = document.getElementById('current-view-title');
        const titles = {
            'overview': 'Executive Overview',
            'sku-pricing': 'Catalog Recommendations',
            'simulator': 'Real-Time Demand Simulator',
            'competitors': 'Competitor Intelligence',
            'transfers': 'Multi-Store Balancing'
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

        // Re-arm scroll reveals for the newly active view
        requestAnimationFrame(() => this.prepareViewReveals(viewId));
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

        if (profitLiftEl) profitLiftEl.textContent = `+${this.formatCurrency(s.total_profit_lift)}`;
        if (profitLiftPctEl) profitLiftPctEl.textContent = `+${s.avg_profit_lift_pct}% vs Status Quo baseline`;
        if (invUnitsEl) invUnitsEl.textContent = `${(s.total_inventory_units || 0).toLocaleString('en-IN')} units`;
        if (invValEl) invValEl.textContent = `Catalog Value: ${this.formatCurrency(s.total_inventory_value)}`;
        if (totalSkusEl) totalSkusEl.textContent = `${s.total_skus || 0} SKUs`;

        const acts = s.action_counts || {};
        if (actionsSummaryEl) {
            actionsSummaryEl.textContent = `${acts['Increase Price'] || 0} Increases | ${acts['Slight Reduction'] || acts['Clearance Markdown'] || 0} Markdowns`;
        }

        const risks = s.risk_counts || {};
        const criticalCount = (risks['High Risk'] || 0) + (risks['Critical'] || 0) + (risks['Medium Risk'] || 0);
        if (riskSkusEl) riskSkusEl.textContent = `${criticalCount} SKUs`;
        if (riskSubtextEl) riskSubtextEl.textContent = `${risks['Medium Risk'] || 0} Medium | ${risks['High Risk'] || 0} High Urgency`;

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

        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = "'Inter', sans-serif";

        this.charts.profitComparison = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Status Quo Baseline (₹)',
                        data: statusQuoProfits,
                        backgroundColor: 'rgba(148, 163, 184, 0.3)',
                        borderColor: '#64748b',
                        borderWidth: 1,
                        borderRadius: 6
                    },
                    {
                        label: 'AI Optimized Net Profit (₹)',
                        data: optimizedProfits,
                        backgroundColor: 'rgba(99, 102, 241, 0.85)',
                        borderColor: '#6366f1',
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
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
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

        const acts = this.state.summary.action_counts || {
            'Increase Price': 7,
            'Hold Price': 0,
            'Slight Reduction': 1,
            'Clearance Markdown': 0
        };

        const labels = Object.keys(acts);
        const dataVals = Object.values(acts);

        this.charts.actionDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataVals,
                    backgroundColor: [
                        '#10b981', // Success for Increase
                        '#f59e0b', // Amber for Hold
                        '#06b6d4', // Cyan for Slight Reduction
                        '#ef4444'  // Red for Clearance Markdown
                    ],
                    borderWidth: 2,
                    borderColor: '#11192e'
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
                        labels: { boxWidth: 10, padding: 12, font: { size: 11 } }
                    }
                }
            }
        });
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
            tr.innerHTML = `
                <td>
                    <strong>${item.product_name}</strong>
                    <div style="font-size:0.75rem; color:var(--text-muted)">${item.product_id}</div>
                </td>
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
            if (item.inventory_risk_level.toLowerCase().includes('high') || item.inventory_risk_level.toLowerCase().includes('critical') || isUrgentEvent) {
                riskClass = 'risk-high';
            } else if (item.inventory_risk_level.toLowerCase().includes('medium')) {
                riskClass = 'risk-medium';
            }

            const alertBadge = isUrgentEvent ? `<div class="badge badge-danger" style="margin-top:0.3rem;"><i class="fa-solid fa-satellite-dish pulse-radar"></i> ${item.active_event.successor_name} Announced!</div>` : '';

            tr.innerHTML = `
                <td>
                    <strong>${item.product_name}</strong>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${item.product_id}</div>
                    ${alertBadge}
                </td>
                <td>${this.formatCurrency(item.current_price)}</td>
                <td class="${priceClass}">
                    ${icon} ${this.formatCurrency(item.recommended_price)}
                    <div style="font-size:0.75rem;">${item.price_change >= 0 ? '+' : ''}${this.formatCurrency(item.price_change)}</div>
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

            tr.innerHTML = `
                <td>
                    <strong>${item.product_name}</strong>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${item.product_id}</div>
                </td>
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
            // Store health rows
            (sku.stores_summary || []).forEach((s, si) => {
                const tr = document.createElement('tr');
                tr.classList.add('row-enter');
                tr.style.setProperty('--rd', `${Math.min(si * 35, 350)}ms`);
                let statusClass = 'risk-low';
                if (s.status === 'Excess Overstock') statusClass = 'risk-medium';
                if (s.status === 'Stockout Imminent') statusClass = 'risk-high';
                tr.innerHTML = `
                    <td style="font-size:0.8rem; color:var(--text-secondary);">${sku.product_name}</td>
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
                    <td style="font-size:0.8rem; color:var(--text-secondary);">${sku.product_name}</td>
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
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-muted);">No profitable transfers found — every store is within healthy supply bounds.</td></tr>`;
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

        // Instant local interpolation for fast 60fps response
        const horizon = Math.min(sku.days_to_successor, 60);
        const priceRatio = p / sku.competitor_avg_price;
        const baseDemand = sku.expected_daily_demand;
        const elasticity = sku.elasticity || 2.0;

        // Log-log demand elasticity formula: Q = Q0 * (P / P0)^(-elasticity)
        const estimatedDemand = Math.max(0.1, baseDemand * Math.pow(Math.max(0.5, priceRatio), -elasticity));
        const unitMargin = p - sku.unit_cost;
        const expectedSales = Math.min(sku.current_inventory, estimatedDemand * horizon);
        const leftover = Math.max(0, sku.current_inventory - expectedSales);
        const holdingCost = 0.5 * (sku.current_inventory + leftover) * sku.unit_cost * 0.0005 * horizon;
        const deprecLoss = leftover * sku.unit_cost * 0.25;
        const netProfit = (expectedSales * unitMargin) - holdingCost - deprecLoss;
        const clearanceDays = sku.current_inventory / (estimatedDemand + 1e-5);

        // Update UI tiles
        const resDemand = document.getElementById('sim-result-demand');
        const resMargin = document.getElementById('sim-result-margin');
        const resProfit = document.getElementById('sim-result-profit');
        const resClearance = document.getElementById('sim-result-clearance');

        if (resDemand) resDemand.innerHTML = `${estimatedDemand.toFixed(1)} <small>units/day</small>`;
        if (resMargin) resMargin.textContent = this.formatCurrency(unitMargin);
        if (resProfit) resProfit.textContent = this.formatCurrency(netProfit);
        if (resClearance) resClearance.innerHTML = `${clearanceDays.toFixed(0)} <small>days</small>`;
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

        this.charts.simulatorCurve = new Chart(ctx, {
            type: 'line',
            data: {
                labels: prices.map(p => `₹${p.toLocaleString('en-IN')}`),
                datasets: [
                    {
                        label: 'Projected Net Profit (₹)',
                        data: profits,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        tension: 0.35,
                        yAxisID: 'yProfit',
                        pointRadius: 2,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Daily Demand (Units)',
                        data: demands,
                        borderColor: '#06b6d4',
                        backgroundColor: 'transparent',
                        borderDash: [4, 4],
                        tension: 0.3,
                        yAxisID: 'yDemand',
                        pointRadius: 2,
                        pointHoverRadius: 6
                    }
                ]
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
                                return `Daily Demand: ${context.raw.toFixed(1)} units/day`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { maxTicksLimit: 7 }
                    },
                    yProfit: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
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

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (!overlay) return;
        if (show) overlay.classList.remove('hidden');
        else overlay.classList.add('hidden');
    },

    renderErrorState() {
        const tbody = document.getElementById('sku-table-body');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 3rem;">
                        <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; color: var(--warning); margin-bottom: 1rem; display: block;"></i>
                        <h4 style="margin-bottom: 0.5rem;">Could not connect to AI Engine API</h4>
                        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Please ensure the FastAPI backend is running on <code>http://localhost:8000</code></p>
                        <button class="btn btn-primary btn-sm" onclick="app.loadData()">Retry Connection</button>
                    </td>
                </tr>
            `;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => app.init());
