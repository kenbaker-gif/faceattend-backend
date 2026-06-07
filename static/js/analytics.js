class AnalyticsDashboard {
    constructor() {
        this.period = 30;
        this.init();
    }

    async init() {
        await this.loadAllMetrics();
    }

    async loadAllMetrics() {
        await Promise.all([
            this.loadRevenue(),
            this.loadChurn(),
            this.loadUsage(),
            this.loadPayments()
        ]);
    }

    async loadRevenue() {
        const data = await this.fetchAPI('/admin/analytics/revenue');
        this.renderRevenue(data);
    }

    async loadChurn() {
        const data = await this.fetchAPI(`/admin/analytics/churn?days=${this.period}`);
        this.renderChurn(data);
    }

    async loadUsage() {
        const data = await this.fetchAPI('/admin/analytics/usage');
        this.renderUsage(data);
    }

    async loadPayments() {
        const data = await this.fetchAPI(`/admin/analytics/payments?days=${this.period}`);
        this.renderPayments(data);
    }

    async fetchAPI(url) {
        const response = await fetch(url);
        return await response.json();
    }

    renderRevenue(data) {
        document.getElementById('mrr-value').textContent = `KES ${data.mrr.toLocaleString()}`;
        document.getElementById('arr-value').textContent = `KES ${data.arr.toLocaleString()}`;
        document.getElementById('total-institutions').textContent = data.total_institutions;

        const breakdown = data.plan_breakdown;
        let html = '';
        for (const [plan, stats] of Object.entries(breakdown)) {
            html += `
                <div class="plan-stat">
                    <div class="plan-name">${plan}</div>
                    <div class="plan-count">${stats.count}</div>
                    <div class="plan-revenue">KES ${stats.mrr.toLocaleString()}/mo</div>
                </div>
            `;
        }
        document.getElementById('plan-breakdown').innerHTML = html;
    }

    renderChurn(data) {
        const churnEl = document.getElementById('churn-rate');
        churnEl.textContent = `${data.churn_rate}%`;
        churnEl.className = `metric-value ${data.churn_rate > 5 ? 'metric-negative' : 'metric-positive'}`;
        
        document.getElementById('churned-count').textContent = 
            `${data.churned_count} churned in ${data.period_days} days`;
    }

    renderUsage(data) {
        const html = `
            <table class="usage-table">
                <thead>
                    <tr>
                        <th>Institution</th>
                        <th>Plan</th>
                        <th>Students</th>
                        <th>Utilization</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(item => `
                        <tr>
                            <td>${item.institution}</td>
                            <td>${item.plan}</td>
                            <td>${item.students} / ${item.limit === 999999 ? '∞' : item.limit}</td>
                            <td>
                                <div class="utilization-bar">
                                    <div class="utilization-fill ${item.utilization > 90 ? 'critical' : item.utilization > 70 ? 'high' : ''}" 
                                         style="width: ${Math.min(item.utilization, 100)}%">
                                    </div>
                                    <span class="utilization-text">${item.utilization}%</span>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        document.getElementById('usage-trends').innerHTML = html;
    }

    renderPayments(data) {
        const successEl = document.getElementById('payment-success');
        successEl.textContent = `${data.success_rate}%`;
        successEl.className = `metric-value ${data.success_rate < 90 ? 'metric-negative' : 'metric-positive'}`;
        
        document.getElementById('payment-stats').textContent = 
            `${data.successful}/${data.total_payments} successful`;
    }

    setPeriod(days) {
        this.period = days;
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.period == days);
        });
        this.loadChurn();
        this.loadPayments();
    }
}

let analytics;
document.addEventListener('DOMContentLoaded', () => {
    analytics = new AnalyticsDashboard();
});
