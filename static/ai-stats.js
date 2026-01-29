/**
 * AI Token Statistics Page
 */

class AIStatsApp {
    constructor() {
        this.charts = {};
        this.init();
    }

    init() {
        console.log('AI Stats App initializing...');
        this.setupEventListeners();
        // Don't auto-load stats - only load when section is activated
        console.log('AI Stats App initialized (stats will load when section is viewed)');
    }

    loadStats() {
        // Reload all statistics and charts
        this.loadSummaryStats();
        this.loadTokenStatistics();
        this.loadCharts();
    }

    setupEventListeners() {
        // Toggle token table button
        const toggleTokenTableBtn = document.getElementById('toggleTokenTable');
        if (toggleTokenTableBtn) {
            toggleTokenTableBtn.addEventListener('click', () => this.toggleTokenTable());
        }
    }

    getChartColors() {
        const isDark = document.body.classList.contains('dark-mode');
        return {
            textColor: isDark ? '#f1f5f9' : '#111827',
            gridColor: isDark ? '#334155' : '#e5e7eb'
        };
    }

    toggleTokenTable() {
        const container = document.getElementById('tokenTableContainer');
        const button = document.getElementById('toggleTokenTable');

        if (container.style.display === 'none' || container.style.display === '') {
            container.style.display = 'block';
            button.classList.add('expanded');
        } else {
            container.style.display = 'none';
            button.classList.remove('expanded');
        }
    }

    async loadSummaryStats() {
        try {
            console.log('Loading summary stats...');
            const response = await fetch('/api/sessions/token-stats?limit=1000');
            const data = await response.json();
            console.log('Summary stats response:', data);

            if (data.success && data.sessions) {
                const sessions = data.sessions;
                const totalReviews = sessions.length;
                const totalTokens = sessions.reduce((sum, s) => sum + (s.total_tokens || 0), 0);
                const avgTokens = totalReviews > 0 ? Math.round(totalTokens / totalReviews) : 0;

                console.log(`Stats: ${totalReviews} reviews, ${totalTokens} tokens, ${avgTokens} avg`);

                // Update summary cards (using unique IDs to avoid conflicts with dashboard)
                const totalReviewsEl = document.getElementById('aiStatsReviewCount');
                const totalTokensEl = document.getElementById('aiStatsTokenTotal');
                const avgTokensEl = document.getElementById('aiStatsTokenAvg');

                console.log('Elements found:', {
                    aiStatsReviewCount: !!totalReviewsEl,
                    aiStatsTokenTotal: !!totalTokensEl,
                    aiStatsTokenAvg: !!avgTokensEl
                });

                if (totalReviewsEl) totalReviewsEl.textContent = totalReviews.toLocaleString();
                if (totalTokensEl) totalTokensEl.textContent = totalTokens.toLocaleString();
                if (avgTokensEl) avgTokensEl.textContent = avgTokens.toLocaleString();

                // Update header stats
                const headerTotalReviews = document.getElementById('headerTotalReviews');
                const headerTotalTokens = document.getElementById('headerTotalTokens');
                if (headerTotalReviews) headerTotalReviews.textContent = totalReviews.toLocaleString();
                if (headerTotalTokens) headerTotalTokens.textContent = totalTokens.toLocaleString();
            } else {
                console.warn('No sessions data or request failed');
            }
        } catch (error) {
            console.error('Error loading summary stats:', error);
            const totalReviewsEl = document.getElementById('aiStatsReviewCount');
            const totalTokensEl = document.getElementById('aiStatsTokenTotal');
            const avgTokensEl = document.getElementById('aiStatsTokenAvg');

            if (totalReviewsEl) totalReviewsEl.textContent = '0';
            if (totalTokensEl) totalTokensEl.textContent = '0';
            if (avgTokensEl) avgTokensEl.textContent = '0';
        }
    }

    async loadCharts() {
        try {
            const response = await fetch('/api/sessions/token-stats?limit=100');
            const data = await response.json();

            if (data.success && data.sessions) {
                this.renderStageDistributionChart(data.sessions);
                this.renderTokenTrendChart(data.sessions);
            }
        } catch (error) {
            console.error('Error loading charts:', error);
        }
    }

    renderStageDistributionChart(sessions) {
        const ctx = document.getElementById('stageDistributionChart');

        // Calculate total tokens per stage
        const totals = {
            architecture: 0,
            security: 0,
            bugs: 0,
            style: 0,
            performance: 0,
            tests: 0
        };

        sessions.forEach(session => {
            totals.architecture += session.token_usage?.architecture?.total_tokens || 0;
            totals.security += session.token_usage?.security?.total_tokens || 0;
            totals.bugs += session.token_usage?.bugs?.total_tokens || 0;
            totals.style += session.token_usage?.style?.total_tokens || 0;
            totals.performance += session.token_usage?.performance?.total_tokens || 0;
            totals.tests += session.token_usage?.tests?.total_tokens || 0;
        });

        if (this.charts.stageDistribution) {
            this.charts.stageDistribution.destroy();
        }

        const colors = this.getChartColors();

        this.charts.stageDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Architecture', 'Security Review', 'Bug Detection', 'Style & Quality', 'Performance Optimization', 'Test Suggestions'],
                datasets: [{
                    data: [totals.architecture, totals.security, totals.bugs, totals.style, totals.performance, totals.tests],
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(139, 92, 246, 0.8)',
                        'rgba(75, 192, 192, 0.8)'
                    ],
                    borderColor: [
                        'rgba(102, 126, 234, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(139, 92, 246, 1)',
                        'rgba(75, 192, 192, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            font: {
                                size: 12
                            },
                            color: colors.textColor
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value.toLocaleString()} tokens (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderTokenTrendChart(sessions) {
        const ctx = document.getElementById('tokenTrendChart');

        // Sort sessions by date and group by day
        const sessionsByDate = {};
        sessions.forEach(session => {
            const date = new Date(session.timestamp || session.created_at);
            const dateKey = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

            if (!sessionsByDate[dateKey]) {
                sessionsByDate[dateKey] = {
                    total: 0,
                    count: 0
                };
            }

            sessionsByDate[dateKey].total += session.total_tokens || 0;
            sessionsByDate[dateKey].count += 1;
        });

        // Get last 30 entries
        const dates = Object.keys(sessionsByDate).slice(-30);
        const tokenCounts = dates.map(date => sessionsByDate[date].total);

        if (this.charts.tokenTrend) {
            this.charts.tokenTrend.destroy();
        }

        const colors = this.getChartColors();

        this.charts.tokenTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Total Tokens Used',
                    data: tokenCounts,
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed.y || 0;
                                return `Tokens: ${value.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: colors.textColor
                        },
                        grid: {
                            color: colors.gridColor
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: colors.textColor,
                            callback: function (value) {
                                return value.toLocaleString();
                            }
                        },
                        grid: {
                            color: colors.gridColor
                        }
                    }
                }
            }
        });
    }

    async loadTokenStatistics() {
        const tbody = document.getElementById('tokenStatsTableBody');
        console.log('Loading token statistics table...');

        try {
            tbody.innerHTML = '<tr><td colspan="9" class="loading-message">Loading token statistics...</td></tr>';

            const response = await fetch('/api/sessions/token-stats?limit=50');
            const data = await response.json();
            console.log('Token stats table response:', data);

            if (!data.success || !data.sessions || data.sessions.length === 0) {
                console.warn('No token statistics available');
                tbody.innerHTML = '<tr><td colspan="9" class="loading-message">No token statistics available</td></tr>';
                return;
            }

            console.log(`Loading ${data.sessions.length} sessions into table`);

            // Build table rows
            const rows = data.sessions.map(session => {
                const date = new Date(session.timestamp || session.created_at);
                const dateStr = date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric'
                });

                const prTitle = session.pr_title || 'Untitled PR';
                const outcome = this.determineOutcome(session.status);

                // Format branch information
                const sourceBranch = session.source_branch || null;
                const targetBranch = session.target_branch || null;
                const branchInfo = (sourceBranch && targetBranch)
                    ? `<span class="branch-label">${sourceBranch}</span> → <span class="branch-label">${targetBranch}</span>`
                    : '-';

                // Get token counts for each stage
                const architectureTokens = session.token_usage?.architecture?.total_tokens || 0;
                const securityTokens = session.token_usage?.security?.total_tokens || 0;
                const bugsTokens = session.token_usage?.bugs?.total_tokens || 0;
                const styleTokens = session.token_usage?.style?.total_tokens || 0;
                const performanceTokens = session.token_usage?.performance?.total_tokens || 0;
                const testsTokens = session.token_usage?.tests?.total_tokens || 0;
                const totalTokens = session.total_tokens || 0;

                return `
                    <tr>
                        <td class="date-cell">${dateStr}</td>
                        <td class="pr-title-cell" title="${prTitle}">${prTitle}</td>
                        <td class="branch-cell">${branchInfo}</td>
                        <td>${outcome}</td>
                        <td class="text-center"><span class="token-count">${this.formatTokenCount(architectureTokens)}</span></td>
                        <td class="text-center"><span class="token-count">${this.formatTokenCount(securityTokens)}</span></td>
                        <td class="text-center"><span class="token-count">${this.formatTokenCount(bugsTokens)}</span></td>
                        <td class="text-center"><span class="token-count">${this.formatTokenCount(styleTokens)}</span></td>
                        <td class="text-center"><span class="token-count">${this.formatTokenCount(performanceTokens)}</span></td>
                        <td class="text-center"><span class="token-count">${this.formatTokenCount(testsTokens)}</span></td>
                        <td class="text-center"><span class="token-count total">${this.formatTokenCount(totalTokens)}</span></td>
                    </tr>
                `;
            }).join('');

            tbody.innerHTML = rows;

        } catch (error) {
            console.error('Error loading token statistics:', error);
            tbody.innerHTML = '<tr><td colspan="9" class="loading-message">Error loading token statistics</td></tr>';
        }
    }

    determineOutcome(status) {
        if (!status) {
            return '<span class="outcome-badge warning">Unknown</span>';
        }

        if (status.includes('completed') || status.includes('success')) {
            return '<span class="outcome-badge success">Success</span>';
        } else if (status.includes('error') || status.includes('failed')) {
            return '<span class="outcome-badge error">Error</span>';
        } else {
            return '<span class="outcome-badge warning">Pending</span>';
        }
    }

    formatTokenCount(count) {
        if (count === 0) return '-';
        return count.toLocaleString();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.aiStatsApp = new AIStatsApp();
});
