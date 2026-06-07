// Billing Dashboard JavaScript

class BillingDashboard {
    constructor() {
        this.institutionId = localStorage.getItem('institution_id');
        this.currentPlan = null;
        this.studentCount = 0;
        this.init();
    }

    async init() {
        await this.loadCurrentPlan();
        await this.loadStudentCount();
        await this.loadAutoRenewalStatus();
        this.renderPlanCards();
        this.renderUsageMeter();
        this.renderAutoRenewalToggle();
        this.checkExpiry();
        await this.loadInvoices();
    }

    async loadCurrentPlan() {
        try {
            const response = await fetch(`/admin/institutions/${this.institutionId}`);
            const data = await response.json();
            this.currentPlan = {
                name: data.plan || 'free',
                subscriptionEnd: data.subscription_end,
                graceStart: data.grace_period_start,
                graceEnd: data.grace_period_end
            };
        } catch (error) {
            console.error('Failed to load plan:', error);
        }
    }

    async loadStudentCount() {
        try {
            const response = await fetch(`/admin/students?institution_id=${this.institutionId}`);
            const data = await response.json();
            this.studentCount = data.length || 0;
        } catch (error) {
            console.error('Failed to load students:', error);
        }
    }

    async loadAutoRenewalStatus() {
        try {
            const response = await fetch(`/admin/auto-renewal/status/${this.institutionId}`);
            this.autoRenewalStatus = await response.json();
        } catch (error) {
            console.error('Failed to load auto-renewal status:', error);
            this.autoRenewalStatus = { enabled: false, configured: false };
        }
    }

    renderAutoRenewalToggle() {
        const html = `
            <div style="background: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 4px; padding: 16px; margin: 24px 0;">
                <h3 style="margin: 0 0 12px 0;">Auto-Renewal</h3>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <p style="margin: 0; color: #666;">
                            Automatically renew your subscription each month
                            ${this.autoRenewalStatus.enabled ? `<br><small>Next renewal: ${new Date(this.autoRenewalStatus.next_renewal_date).toLocaleDateString()}</small>` : ''}
                        </p>
                    </div>
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" 
                            ${this.autoRenewalStatus.enabled ? 'checked' : ''} 
                            onchange="billing.toggleAutoRenewal(this.checked)"
                            style="width: 20px; height: 20px; cursor: pointer;">
                        <span style="margin-left: 8px; font-weight: 500;">
                            ${this.autoRenewalStatus.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                    </label>
                </div>
            </div>
        `;
        
        const container = document.getElementById('auto-renewal-container');
        if (container) container.innerHTML = html;
    }

    async toggleAutoRenewal(enabled) {
        try {
            const response = await fetch('/admin/auto-renewal/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    institution_id: this.institutionId,
                    enabled: enabled,
                    payment_method: 'pesapal'
                })
            });

            const result = await response.json();
            if (result.success) {
                this.autoRenewalStatus = { ...result, configured: true };
                this.renderAutoRenewalToggle();
                alert(`Auto-renewal ${enabled ? 'enabled' : 'disabled'} successfully`);
            }
        } catch (error) {
            alert('Failed to update auto-renewal: ' + error.message);
        }
    }

    renderPlanCards() {
        const plans = [
            {
                name: 'free',
                displayName: 'Free',
                price: 0,
                students: 50,
                features: ['Up to 50 students', 'Basic attendance tracking', 'Email support']
            },
            {
                name: 'premium',
                displayName: 'Premium',
                price: 5000,
                students: 500,
                features: ['Up to 500 students', 'Advanced analytics', 'Priority support', 'API access']
            },
            {
                name: 'enterprise',
                displayName: 'Enterprise',
                price: 15000,
                students: Infinity,
                features: ['Unlimited students', 'Custom integrations', 'Dedicated support', 'SLA guarantee']
            }
        ];

        const container = document.getElementById('plans-container');
        container.innerHTML = plans.map(plan => this.renderPlanCard(plan)).join('');
    }

    renderPlanCard(plan) {
        const isCurrent = this.currentPlan?.name === plan.name;
        const canDowngrade = this.studentCount <= plan.students;
        
        return `
            <div class="plan-card ${isCurrent ? 'current' : ''}">
                <div class="plan-header">
                    <div class="plan-name">${plan.displayName}</div>
                    <div class="plan-price">
                        <span class="currency">KES</span> ${plan.price.toLocaleString()}
                        <span style="font-size: 14px; color: #666;">/month</span>
                    </div>
                </div>
                <ul class="plan-features">
                    ${plan.features.map(f => `<li>${f}</li>`).join('')}
                </ul>
                ${isCurrent ? 
                    '<div style="color: #4CAF50; font-weight: bold;">Current Plan</div>' :
                    `<button class="btn-upgrade ${plan.name < this.currentPlan?.name ? 'btn-downgrade' : ''}"
                        onclick="billing.showUpgradeModal('${plan.name}')"
                        ${!canDowngrade ? 'disabled title="Too many students for this plan"' : ''}>
                        ${plan.name > this.currentPlan?.name ? 'Upgrade' : 'Downgrade'}
                    </button>`
                }
            </div>
        `;
    }

    renderUsageMeter() {
        const limits = { free: 50, premium: 500, enterprise: Infinity };
        const limit = limits[this.currentPlan?.name] || 50;
        const percentage = limit === Infinity ? 0 : (this.studentCount / limit) * 100;
        
        let fillClass = '';
        if (percentage > 90) fillClass = 'danger';
        else if (percentage > 75) fillClass = 'warning';

        const html = `
            <div class="usage-meter">
                <h3>Student Usage</h3>
                <div style="font-size: 24px; margin: 8px 0;">
                    ${this.studentCount} / ${limit === Infinity ? '∞' : limit} students
                </div>
                ${limit !== Infinity ? `
                    <div class="usage-bar">
                        <div class="usage-fill ${fillClass}" style="width: ${Math.min(percentage, 100)}%"></div>
                    </div>
                ` : ''}
                <div style="color: #666; font-size: 14px;">
                    ${limit === Infinity ? 'Unlimited students' : `${limit - this.studentCount} students remaining`}
                </div>
            </div>
        `;

        document.getElementById('usage-container').innerHTML = html;
    }

    checkExpiry() {
        if (!this.currentPlan?.subscriptionEnd) return;

        const now = new Date();
        const expiry = new Date(this.currentPlan.subscriptionEnd);
        const daysUntilExpiry = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));

        let html = '';
        if (daysUntilExpiry < 0) {
            // Expired - check grace period
            if (this.currentPlan.graceEnd && new Date(this.currentPlan.graceEnd) > now) {
                const graceDays = Math.ceil((new Date(this.currentPlan.graceEnd) - now) / (1000 * 60 * 60 * 24));
                html = `
                    <div class="expiry-banner grace">
                        ⚠️ Your subscription expired. You have ${graceDays} days of grace period remaining.
                        <a href="#" onclick="billing.showRenewModal()">Renew Now</a>
                    </div>
                `;
            } else {
                html = `
                    <div class="expiry-banner danger">
                        🚫 Your subscription has expired. Please renew to continue using the service.
                        <a href="#" onclick="billing.showRenewModal()">Renew Now</a>
                    </div>
                `;
            }
        } else if (daysUntilExpiry <= 7) {
            html = `
                <div class="expiry-banner ${daysUntilExpiry <= 1 ? 'danger' : 'warning'}">
                    ⏰ Your subscription expires in ${daysUntilExpiry} day${daysUntilExpiry !== 1 ? 's' : ''}.
                    <a href="#" onclick="billing.showRenewModal()">Renew Now</a>
                </div>
            `;
        }

        document.getElementById('expiry-container').innerHTML = html;
    }

    async showUpgradeModal(newPlan) {
        // Get proration preview
        const proration = await this.getProration(newPlan);
        
        const modal = `
            <div class="modal-overlay" onclick="this.remove()">
                <div class="modal-content" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        ${newPlan > this.currentPlan.name ? 'Upgrade' : 'Downgrade'} to ${newPlan}
                    </div>
                    ${proration ? `
                        <div class="proration-preview">
                            <h4>Billing Preview</h4>
                            <div class="proration-line">
                                <span>Current plan (${this.currentPlan.name})</span>
                                <span>-KES ${proration.refund_amount}</span>
                            </div>
                            <div class="proration-line">
                                <span>New plan (${newPlan})</span>
                                <span>+KES ${proration.charge_amount}</span>
                            </div>
                            <div class="proration-line total">
                                <span>${proration.net_amount >= 0 ? 'Amount Due' : 'Credit'}</span>
                                <span>KES ${Math.abs(proration.net_amount)}</span>
                            </div>
                            <p style="font-size: 12px; color: #666; margin-top: 12px;">
                                Based on ${proration.days_remaining} days remaining in current cycle
                            </p>
                        </div>
                    ` : ''}
                    <div class="modal-actions">
                        <button class="btn-upgrade btn-cancel" onclick="this.closest('.modal-overlay').remove()">
                            Cancel
                        </button>
                        <button class="btn-upgrade" onclick="billing.confirmUpgrade('${newPlan}')">
                            Confirm ${newPlan > this.currentPlan.name ? 'Upgrade' : 'Downgrade'}
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modal);
    }

    async getProration(newPlan) {
        try {
            const response = await fetch(`/admin/billing/proration/${this.institutionId}?new_plan=${newPlan}`);
            return await response.json();
        } catch (error) {
            console.error('Failed to get proration:', error);
            return null;
        }
    }

    async confirmUpgrade(newPlan) {
        try {
            const response = await fetch('/admin/billing/upgrade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    institution_id: this.institutionId,
                    new_plan: newPlan
                })
            });

            const result = await response.json();
            
            if (result.payment_required && result.payment_link) {
                window.location.href = result.payment_link;
            } else {
                alert(`Successfully changed to ${newPlan} plan!`);
                location.reload();
            }
        } catch (error) {
            alert('Failed to change plan: ' + error.message);
        }
    }

    async loadInvoices() {
        try {
            const response = await fetch(`/admin/billing/invoices/${this.institutionId}`);
            const invoices = await response.json();
            this.renderInvoices(invoices);
        } catch (error) {
            console.error('Failed to load invoices:', error);
        }
    }

    renderInvoices(invoices) {
        const html = `
            <h3>Invoice History</h3>
            <table class="invoice-table">
                <thead>
                    <tr>
                        <th>Invoice ID</th>
                        <th>Plan</th>
                        <th>Amount</th>
                        <th>Issue Date</th>
                        <th>Due Date</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${invoices.length ? invoices.map(inv => `
                        <tr>
                            <td>${inv.invoice_id}</td>
                            <td>${inv.plan}</td>
                            <td>KES ${inv.amount.toLocaleString()}</td>
                            <td>${new Date(inv.issue_date).toLocaleDateString()}</td>
                            <td>${new Date(inv.due_date).toLocaleDateString()}</td>
                            <td><span class="invoice-status ${inv.status}">${inv.status}</span></td>
                            <td><a href="/admin/billing/invoices/${this.institutionId}/${inv.invoice_id}/pdf" target="_blank" class="download-btn">📄 PDF</a></td>
                        </tr>
                    `).join('') : '<tr><td colspan="7" style="text-align: center;">No invoices yet</td></tr>'}
                </tbody>
            </table>
        `;

        document.getElementById('invoices-container').innerHTML = html;
    }

    showRenewModal() {
        this.showUpgradeModal(this.currentPlan.name);
    }
}

// Initialize
let billing;
document.addEventListener('DOMContentLoaded', () => {
    billing = new BillingDashboard();
});
