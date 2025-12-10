// Main Application JavaScript
class PRReviewApp {
    constructor() {
        this.apiEndpoint = '/api/review';
        this.currentReview = null;
        this.charts = {};
        this.currentSection = 'new-review';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.setupTabs();
        this.setupNavigation();
        this.setupClickableCards();
        this.checkMongoDBStatus();
        this.loadDashboardStats();
        this.showSection('dashboard');
    }

    setupEventListeners() {
        const startBtn = document.getElementById('startReview');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startReview());
        }
    }

    setupTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });
    }

    switchTab(tabName) {
        // Remove active class from all buttons and panes
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

        // Add active class to selected button and pane
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}Tab`).classList.add('active');
    }

    navigateToTab(tabName) {
        console.log('navigateToTab called with:', tabName);

        // Scroll to detailed reports section
        const reportsSection = document.querySelector('.detailed-reports');
        console.log('Reports section found:', !!reportsSection);

        if (reportsSection) {
            reportsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        // Switch to the selected tab after a short delay for smooth scrolling
        setTimeout(() => {
            this.switchTab(tabName);
        }, 300);
    }

    async startReview() {
        const prUrl = document.getElementById('prUrl').value;
        const repoUrl = document.getElementById('repoUrl').value;

        if (!prUrl || !repoUrl) {
            this.showError('Please enter both Pull/Merge Request URL and Source Repository URL');
            return;
        }

        // Reset any previous state
        this.stopProgress();
        this.stopPolling();

        // Show progress section
        this.showProgress();

        try {
            console.log('Starting PR review...', { pr_url: prUrl, repo_url: repoUrl });

            // Start the review (returns job ID immediately)
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pr_url: prUrl, repo_url: repoUrl })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Review started:', data);

            if (data.success && data.job_id) {
                // Start polling for progress updates
                this.pollReviewProgress(data.job_id);
            } else {
                throw new Error(data.error || 'Failed to start review');
            }

        } catch (error) {
            console.error('Error starting review:', error);
            this.showError(`Failed to start review: ${error.message}`);
            this.hideProgress();
        }
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    async pollReviewProgress(jobId) {
        // Poll every 2 seconds for progress updates
        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/review/status/${jobId}`);
                const data = await response.json();

                if (!data.success) {
                    throw new Error(data.error || 'Failed to get status');
                }

                console.log('Progress update:', data);

                // Update UI with real progress
                this.updateProgressUI(data);

                // Check if completed
                if (data.status === 'completed') {
                    this.stopPolling();
                    this.handleReviewComplete(data.results);
                } else if (data.status === 'failed') {
                    this.stopPolling();
                    this.showError(data.error || 'Review failed');
                    this.hideProgress();
                }

            } catch (error) {
                console.error('Error polling progress:', error);
                this.stopPolling();
                this.showError(`Lost connection to review: ${error.message}`);
                this.hideProgress();
            }
        }, 2000); // Poll every 2 seconds
    }

    updateProgressUI(progressData) {
        // Handle different progress data formats
        const progress = progressData.progress || 0;
        const currentStep = progressData.current_step || progressData.currentStep || '';

        console.log('Progress update:', { progress, currentStep, data: progressData });

        // Update progress bar
        const progressBar = document.getElementById('progressBar');
        if (progressBar) {
            progressBar.style.width = progress + '%';
        }

        // Update progress text
        const progressPercentEl = document.getElementById('progressPercent');
        if (progressPercentEl) {
            progressPercentEl.textContent = Math.floor(progress);
        }

        // Update current step counter (0-10)
        const currentStepEl = document.getElementById('currentStep');
        if (currentStepEl) {
            const stepNumber = Math.min(Math.floor(progress / 10), 10);
            currentStepEl.textContent = stepNumber;
        }

        // Update timeline steps based on actual progress
        const steps = document.querySelectorAll('.timeline-step-horizontal');
        steps.forEach((step, index) => {
            const stepProgress = (index + 1) * 10;

            if (progress >= stepProgress) {
                // Completed
                step.classList.remove('step-pending', 'step-active');
                step.classList.add('step-completed');
            } else if (progress > (index * 10) && progress < stepProgress) {
                // Active - current step in progress
                step.classList.remove('step-pending', 'step-completed');
                step.classList.add('step-active');
            } else {
                // Pending
                step.classList.remove('step-active', 'step-completed');
                step.classList.add('step-pending');
            }
        });
    }

    handleReviewComplete(resultsData) {
        // Mark progress as 100%
        this.completeProgress();

        // Display results
        this.displayResults(resultsData.results);

        // Show success message
        const prTitle = resultsData.results?.pr_details?.title || 'PR';
        this.showSuccess(`Review completed successfully for: ${prTitle}`);

        // Show summary section
        setTimeout(() => {
            this.showSummary(resultsData.results);
        }, 800);

        // Reload dashboard stats in background
        this.loadDashboardStats();
    }

    showProgress() {
        // Show progress section and reset UI
        document.getElementById('progressSection').classList.remove('hidden');
        document.getElementById('summarySection').classList.add('hidden');

        // Reset progress bar
        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = '0%';

        // Reset all steps to pending
        const steps = document.querySelectorAll('.timeline-step-horizontal');
        steps.forEach(step => {
            step.classList.remove('step-active', 'step-completed');
            step.classList.add('step-pending');
        });

        // Reset counters
        const currentStepEl = document.getElementById('currentStep');
        const progressPercentEl = document.getElementById('progressPercent');
        if (currentStepEl) currentStepEl.textContent = '0';
        if (progressPercentEl) progressPercentEl.textContent = '0';
    }

    hideProgress() {
        document.getElementById('progressSection').classList.add('hidden');
    }

    stopProgress() {
        // Stop any polling
        this.stopPolling();
    }

    completeProgress() {
        // Stop ongoing animations
        this.stopProgress();

        // Set progress to 100%
        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = '100%';

        // Mark all steps as completed
        const steps = document.querySelectorAll('.timeline-step-horizontal');
        steps.forEach(step => {
            step.classList.remove('step-pending', 'step-active');
            step.classList.add('step-completed');
        });

        // Update counters to 100%
        const currentStepEl = document.getElementById('currentStep');
        const progressPercentEl = document.getElementById('progressPercent');
        if (currentStepEl) currentStepEl.textContent = '10';
        if (progressPercentEl) progressPercentEl.textContent = '100';
    }

    showSummary(data) {
        document.getElementById('summarySection').classList.remove('hidden');

        // Render charts with the actual data
        if (data) {
            this.renderCharts(data);
        }

        // Re-setup clickable cards after summary is shown
        this.setupClickableCards();
    }

    displayResults(results) {
        // Update metrics
        document.getElementById('totalFiles').textContent = results.structure.total;
        document.getElementById('testFiles').textContent = results.test_analysis.count;
        document.getElementById('dddScore').textContent = results.ddd.score.toFixed(0) + '%';
        document.getElementById('directories').textContent = results.structure.dirs;

        // Update summaries
        document.getElementById('securitySummary').textContent = this.extractSummary(results.security);
        document.getElementById('bugSummary').textContent = this.extractSummary(results.bugs);
        document.getElementById('qualitySummary').textContent = this.extractSummary(results.style);
        document.getElementById('testSuggestionsSummary').textContent = this.extractSummary(results.tests);

        // Update detailed reports
        document.getElementById('securityDetails').textContent = results.security;
        document.getElementById('bugsDetails').textContent = results.bugs;
        document.getElementById('qualityDetails').textContent = results.style;
        document.getElementById('testsDetails').textContent = results.tests;

        // Store for downloads
        this.currentReview = results;

        // Render charts
        this.renderCharts(results);
    }

    extractSummary(text, maxLength = 100) {
        if (!text) return 'No issues found';
        const clean = text.replace(/[#*`]/g, '');
        const lines = clean.split('\n').filter(line => line.trim().length > 20);
        const summary = lines[0] || clean;
        return summary.length > maxLength ? summary.substring(0, maxLength) + '...' : summary;
    }

    initializeCharts() {
        // Chart containers
        this.chartContainers = {
            test: 'testChart',
            ddd: 'dddChart',
            extensions: 'extensionsChart',
            changes: 'changesChart',
            testRatio: 'testRatioChart',
            dddRadar: 'dddRadarChart',
            fileSizes: 'fileSizesChart',
            timeline: 'timelineChart'
        };
    }

    getChartLayout(title, height = 350) {
        return {
            title: {
                text: `<b>${title}</b>`,
                font: { size: 16, family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto', color: '#111827' },
                x: 0.05,
                xanchor: 'left'
            },
            height: height,
            margin: { t: 60, b: 50, l: 60, r: 40 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto', size: 12, color: '#111827' }
        };
    }

    getChartConfig() {
        return {
            responsive: true,
            displayModeBar: false,
            displaylogo: false
        };
    }

    renderCharts(data) {
        if (!data) return;

        // Test Gauge
        this.renderTestGauge(data.test_analysis);

        // DDD Gauge
        this.renderDDDGauge(data.ddd);

        // File Distribution Pie
        this.renderFileDistribution(data.files);

        // Changes Bar
        this.renderChangesBar(data.files);

        // Test Ratio Donut
        this.renderTestRatio(data.test_analysis, data.structure);

        // DDD Radar
        this.renderDDDRadar(data.ddd);

        // File Sizes
        this.renderFileSizes(data.files);

        // Timeline
        this.renderTimeline(data.files);
    }

    renderTestGauge(testAnalysis) {
        const data = [{
            type: 'indicator',
            mode: 'gauge+number+delta',
            value: testAnalysis.count,
            title: {
                text: '<b>Test Coverage</b><br><span style="font-size:0.8em;color:gray">Number of Test Files</span>',
                font: { size: 16, family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto' }
            },
            delta: { reference: 5, increasing: { color: '#10b981' } },
            gauge: {
                axis: {
                    range: [null, Math.max(10, testAnalysis.count + 5)],
                    tickwidth: 1,
                    tickcolor: '#e5e7eb'
                },
                bar: { color: '#10b981', thickness: 0.75 },
                bgcolor: '#f9fafb',
                borderwidth: 2,
                bordercolor: '#e5e7eb',
                steps: [
                    { range: [0, 3], color: '#fecaca' },
                    { range: [3, 7], color: '#fef3c7' },
                    { range: [7, Math.max(10, testAnalysis.count + 5)], color: '#d1fae5' }
                ],
                threshold: {
                    line: { color: 'red', width: 4 },
                    thickness: 0.75,
                    value: 5
                }
            }
        }];

        const layout = {
            height: 280,
            margin: { t: 60, b: 20, l: 40, r: 40 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto', size: 12, color: '#111827' }
        };
        const config = { responsive: true, displayModeBar: false };
        Plotly.newPlot(this.chartContainers.test, data, layout, config);
    }

    renderDDDGauge(ddd) {
        const data = [{
            type: 'indicator',
            mode: 'gauge+number+delta',
            value: ddd.score,
            title: {
                text: '<b>DDD Score</b><br><span style="font-size:0.8em;color:gray">Domain-Driven Design Compliance</span>',
                font: { size: 16, family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto' }
            },
            number: { suffix: '%', font: { size: 40 } },
            delta: { reference: 60, increasing: { color: '#10b981' } },
            gauge: {
                axis: { range: [null, 100] },
                bar: { color: '#2196f3' },
                steps: [
                    { range: [0, 30], color: '#ffcdd2' },
                    { range: [30, 60], color: '#fff9c4' },
                    { range: [60, 100], color: '#c8e6c9' }
                ]
            }
        }];

        const layout = { height: 300, margin: { t: 50, b: 0, l: 50, r: 50 } };
        Plotly.newPlot(this.chartContainers.ddd, data, layout, { responsive: true });
    }

    renderFileDistribution(files) {
        const extensions = {};
        files.forEach(f => {
            const filename = f.filename || '';
            const ext = filename.includes('.') ? filename.split('.').pop() : 'other';
            extensions[ext] = (extensions[ext] || 0) + 1;
        });

        // Predefined color palette
        const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                       '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'];

        const data = [{
            type: 'pie',
            labels: Object.keys(extensions),
            values: Object.values(extensions),
            marker: { colors: colors }
        }];

        const layout = {
            title: 'File Distribution by Type',
            height: 300,
            margin: { t: 50, b: 50, l: 50, r: 50 }
        };

        Plotly.newPlot(this.chartContainers.extensions, data, layout, { responsive: true });
    }

    renderChangesBar(files) {
        const additions = files.reduce((sum, f) => sum + (f.additions || 0), 0);
        const deletions = files.reduce((sum, f) => sum + (f.deletions || 0), 0);

        const data = [
            {
                x: ['Changes'],
                y: [additions],
                name: 'Additions',
                type: 'bar',
                marker: { color: '#4caf50' }
            },
            {
                x: ['Changes'],
                y: [deletions],
                name: 'Deletions',
                type: 'bar',
                marker: { color: '#f44336' }
            }
        ];

        const layout = {
            title: 'Code Changes',
            height: 300,
            barmode: 'group',
            margin: { t: 50, b: 50, l: 50, r: 50 }
        };

        Plotly.newPlot(this.chartContainers.changes, data, layout, { responsive: true });
    }

    renderTestRatio(testAnalysis, structure) {
        const data = [{
            type: 'pie',
            labels: ['Test Files', 'Source Files'],
            values: [testAnalysis.count, structure.total - testAnalysis.count],
            hole: 0.4,
            marker: { colors: ['#4caf50', '#2196f3'] },
            textposition: 'inside'
        }];

        const layout = {
            title: 'Test Coverage Ratio',
            height: 300,
            annotations: [{
                text: `${testAnalysis.count}/${structure.total}`,
                x: 0.5,
                y: 0.5,
                font: { size: 20 },
                showarrow: false
            }],
            margin: { t: 50, b: 50, l: 50, r: 50 }
        };

        Plotly.newPlot(this.chartContainers.testRatio, data, layout, { responsive: true });
    }

    renderDDDRadar(ddd) {
        const values = [
            ddd.indicators.entities ? 100 : 0,
            ddd.indicators.repos ? 100 : 0,
            ddd.indicators.services ? 100 : 0
        ];

        const data = [{
            type: 'scatterpolar',
            r: [...values, values[0]],
            theta: ['Entities/Models', 'Repositories', 'Services', 'Entities/Models'],
            fill: 'toself',
            marker: { color: '#2196f3' },
            line: { color: '#1976d2' }
        }];

        const layout = {
            polar: {
                radialaxis: { visible: true, range: [0, 100] }
            },
            showlegend: false,
            title: 'DDD Pattern Coverage',
            height: 350,
            margin: { t: 50, b: 50, l: 50, r: 50 }
        };

        Plotly.newPlot(this.chartContainers.dddRadar, data, layout, { responsive: true });
    }

    renderFileSizes(files) {
        const fileSizes = files
            .map(f => ({
                name: (f.filename || 'unknown').split('/').pop().substring(0, 20),
                size: (f.additions || 0) + (f.deletions || 0)
            }))
            .filter(f => f.size > 0)
            .sort((a, b) => b.size - a.size)
            .slice(0, 10);

        const data = [{
            x: fileSizes.map(f => f.name),
            y: fileSizes.map(f => f.size),
            type: 'bar',
            marker: { color: '#ff9800' },
            text: fileSizes.map(f => f.size),
            textposition: 'auto'
        }];

        const layout = {
            title: 'Top 10 Files by Changes',
            xaxis: { title: 'File' },
            yaxis: { title: 'Lines Changed' },
            height: 350,
            margin: { t: 50, b: 100, l: 50, r: 50 }
        };

        Plotly.newPlot(this.chartContainers.fileSizes, data, layout, { responsive: true });
    }

    renderTimeline(files) {
        const sortedFiles = files
            .sort((a, b) => ((b.additions || 0) + (b.deletions || 0)) - ((a.additions || 0) + (a.deletions || 0)))
            .slice(0, 8);

        const data = [
            {
                x: sortedFiles.map(f => (f.filename || '').substring(0, 30)),
                y: sortedFiles.map(f => f.additions || 0),
                name: 'Additions',
                mode: 'lines+markers',
                line: { color: '#4caf50', width: 3 },
                marker: { size: 10 }
            },
            {
                x: sortedFiles.map(f => (f.filename || '').substring(0, 30)),
                y: sortedFiles.map(f => f.deletions || 0),
                name: 'Deletions',
                mode: 'lines+markers',
                line: { color: '#f44336', width: 3 },
                marker: { size: 10 }
            }
        ];

        const layout = {
            title: 'Changes per File',
            xaxis: { title: 'Files' },
            yaxis: { title: 'Lines' },
            height: 350,
            showlegend: true,
            margin: { t: 50, b: 100, l: 50, r: 50 }
        };

        Plotly.newPlot(this.chartContainers.timeline, data, layout, { responsive: true });
    }

    showError(message) {
        console.error('Error:', message);

        // Remove any existing error messages
        const existingErrors = document.querySelectorAll('.error-toast');
        existingErrors.forEach(el => el.remove());

        // Create error toast
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-toast';
        errorDiv.innerHTML = `
            <div class="error-toast-icon">⚠️</div>
            <div class="error-toast-content">
                <div class="error-toast-title">Error</div>
                <div class="error-toast-message">${this.escapeHtml(message)}</div>
            </div>
            <button class="error-toast-close" onclick="this.parentElement.remove()">×</button>
        `;

        document.body.appendChild(errorDiv);

        // Auto-remove after 8 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.classList.add('error-toast-fade-out');
                setTimeout(() => errorDiv.remove(), 300);
            }
        }, 8000);
    }

    showSuccess(message) {
        console.log('Success:', message);

        // Remove any existing success messages
        const existingSuccess = document.querySelectorAll('.success-toast');
        existingSuccess.forEach(el => el.remove());

        // Create success toast
        const successDiv = document.createElement('div');
        successDiv.className = 'success-toast';
        successDiv.innerHTML = `
            <div class="success-toast-icon">✅</div>
            <div class="success-toast-content">
                <div class="success-toast-title">Success</div>
                <div class="success-toast-message">${this.escapeHtml(message)}</div>
            </div>
            <button class="success-toast-close" onclick="this.parentElement.remove()">×</button>
        `;

        document.body.appendChild(successDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (successDiv.parentElement) {
                successDiv.classList.add('success-toast-fade-out');
                setTimeout(() => successDiv.remove(), 300);
            }
        }, 5000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    downloadReport(format) {
        if (!this.currentReview) {
            this.showError('No review data available');
            return;
        }

        let content, filename, mimeType;

        if (format === 'markdown') {
            content = this.generateMarkdownReport();
            filename = `review_${new Date().toISOString().slice(0, 10)}.md`;
            mimeType = 'text/markdown';
        } else {
            content = JSON.stringify(this.currentReview, null, 2);
            filename = `review_${new Date().toISOString().slice(0, 10)}.json`;
            mimeType = 'application/json';
        }

        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    generateMarkdownReport() {
        const r = this.currentReview;
        return `# PR Code Review Report
Generated: ${new Date().toLocaleString()}

## Summary Metrics
- **Total Files**: ${r.structure.total}
- **Test Files**: ${r.test_analysis.count} (${r.test_analysis.status})
- **DDD Score**: ${r.ddd.score.toFixed(0)}% (${r.ddd.rating})
- **Directories**: ${r.structure.dirs}

## Security Analysis
${r.security}

## Bug Detection
${r.bugs}

## Code Quality
${r.style}

## Test Suggestions
${r.tests}

---
**Report End**
`;
    }

    // Setup Clickable Cards
    setupClickableCards() {
        console.log('Setting up clickable cards...');

        // Remove old listeners by cloning and replacing elements
        // Setup clickable summary cards
        const summaryCards = document.querySelectorAll('.summary-card.clickable-card');
        console.log(`Found ${summaryCards.length} summary cards`);
        summaryCards.forEach(card => {
            // Remove existing click handlers by cloning
            const newCard = card.cloneNode(true);
            card.parentNode.replaceChild(newCard, card);

            // Add new click handler
            newCard.addEventListener('click', () => {
                const tabName = newCard.getAttribute('data-tab');
                console.log('Summary card clicked, tab:', tabName);
                if (tabName) {
                    this.navigateToTab(tabName);
                }
            });
        });

        // Setup clickable metric cards
        const metricCards = document.querySelectorAll('.metric-card.clickable-metric');
        console.log(`Found ${metricCards.length} metric cards`);
        metricCards.forEach(card => {
            // Remove existing click handlers by cloning
            const newCard = card.cloneNode(true);
            card.parentNode.replaceChild(newCard, card);

            // Add new click handler
            newCard.addEventListener('click', () => {
                const tabName = newCard.getAttribute('data-tab');
                console.log('Metric card clicked, tab:', tabName);
                if (tabName) {
                    this.navigateToTab(tabName);
                }
            });
        });
    }

    // Navigation Functions
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-item');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('data-section');
                this.showSection(section);

                // Update active nav link
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');

                // Update page title
                const pageTitles = {
                    'dashboard': 'Dashboard',
                    'new-review': 'New Review',
                    'history': 'History',
                    'statistics': 'Statistics'
                };
                document.getElementById('pageTitle').textContent = pageTitles[section] || 'Dashboard';
            });
        });

        // Sidebar toggle for mobile
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.querySelector('.sidebar');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
            });
        }
    }

    showSection(sectionId) {
        this.currentSection = sectionId;
        console.log('Switching to section:', sectionId);

        // Hide all sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });

        // Hide progress and summary sections when navigating away
        document.getElementById('progressSection').classList.add('hidden');
        document.getElementById('summarySection').classList.add('hidden');

        // Show selected section
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            targetSection.classList.add('active');
            console.log('Activated section:', sectionId, targetSection);
        } else {
            console.error('Section not found:', sectionId);
        }

        // Load data for specific sections
        if (sectionId === 'history') {
            console.log('Loading history...');
            this.loadHistory();
        } else if (sectionId === 'statistics') {
            console.log('Loading statistics...');
            this.loadStatistics();
        } else if (sectionId === 'dashboard') {
            this.loadDashboardStats();
        }
    }

    // MongoDB Status Check
    async checkMongoDBStatus() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            const statusElement = document.getElementById('mongoStatus');
            const statusDot = document.getElementById('statusDot');

            if (data.mongodb === 'connected') {
                statusElement.textContent = 'Connected';
                if (statusDot) {
                    statusDot.classList.add('connected');
                    statusDot.classList.remove('disconnected');
                }
            } else {
                statusElement.textContent = 'Disconnected';
                if (statusDot) {
                    statusDot.classList.add('disconnected');
                    statusDot.classList.remove('connected');
                }
            }
        } catch (error) {
            console.error('Failed to check MongoDB status:', error);
            const statusElement = document.getElementById('mongoStatus');
            const statusDot = document.getElementById('statusDot');
            statusElement.textContent = 'Error';
            if (statusDot) {
                statusDot.classList.add('disconnected');
            }
        }
    }

    // Dashboard Stats
    async loadDashboardStats() {
        try {
            const response = await fetch('/api/sessions/statistics');
            const data = await response.json();

            if (data.success) {
                const stats = data.statistics;
                const totalSessions = stats.total_sessions || 0;

                // Update dashboard cards
                document.getElementById('totalReviews').textContent = totalSessions;

                // For now, set recent reviews to total (can be enhanced later)
                const recentCount = Math.min(totalSessions, 5);
                document.getElementById('recentReviews').textContent = recentCount;

                // Update header stats
                const headerTotalReviews = document.getElementById('headerTotalReviews');
                const headerTodayReviews = document.getElementById('headerTodayReviews');
                if (headerTotalReviews) headerTotalReviews.textContent = totalSessions;
                if (headerTodayReviews) headerTodayReviews.textContent = recentCount;

                // Calculate average DDD score (placeholder for now)
                document.getElementById('avgDDDScore').textContent = '75%';

                // Show top repository
                if (stats.top_repos && stats.top_repos.length > 0) {
                    const topRepo = stats.top_repos[0];
                    const repoName = topRepo._id ? topRepo._id.split('/').pop() : '-';
                    document.getElementById('topRepo').textContent = repoName;
                } else {
                    document.getElementById('topRepo').textContent = '-';
                }

                // Render dashboard charts
                await this.renderDashboardCharts();

                // Load recent reviews list
                await this.loadDashboardRecentReviews();
            }
        } catch (error) {
            console.error('Failed to load dashboard stats:', error);
        }
    }

    // Render Dashboard Charts
    async renderDashboardCharts() {
        try {
            const response = await fetch('/api/sessions/recent?limit=50');
            const data = await response.json();

            if (data.success && data.sessions && data.sessions.length > 0) {
                const sessions = data.sessions;

                // Render all 4 dashboard charts
                this.renderDashReviewsOverTime(sessions);
                this.renderDashAvgScoresTrend(sessions);
                this.renderDashTopRepos(sessions);
                this.renderDashIssuesBreakdown(sessions);
            }
        } catch (error) {
            console.error('Failed to render dashboard charts:', error);
        }
    }

    // Chart 1: Reviews Over Time (Line Chart)
    renderDashReviewsOverTime(sessions) {
        // Group sessions by date
        const reviewsByDate = {};
        sessions.forEach(session => {
            const date = new Date(session.created_at || session.timestamp);
            const dateKey = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            reviewsByDate[dateKey] = (reviewsByDate[dateKey] || 0) + 1;
        });

        // Sort dates chronologically
        const sortedDates = Object.keys(reviewsByDate).sort((a, b) => {
            return new Date(a) - new Date(b);
        });

        const data = [{
            x: sortedDates,
            y: sortedDates.map(date => reviewsByDate[date]),
            type: 'scatter',
            mode: 'lines+markers',
            line: {
                color: '#667eea',
                width: 3,
                shape: 'spline'
            },
            marker: {
                size: 8,
                color: '#667eea',
                line: {
                    color: '#fff',
                    width: 2
                }
            },
            fill: 'tozeroy',
            fillcolor: 'rgba(102, 126, 234, 0.1)'
        }];

        const layout = this.getChartLayout('Reviews Over Time', 350);
        layout.xaxis = {
            title: 'Date',
            showgrid: true,
            gridcolor: '#e5e7eb'
        };
        layout.yaxis = {
            title: 'Number of Reviews',
            showgrid: true,
            gridcolor: '#e5e7eb'
        };

        Plotly.newPlot('dashReviewsOverTime', data, layout, this.getChartConfig());
    }

    // Chart 2: Average Scores Trend (Line Chart)
    renderDashAvgScoresTrend(sessions) {
        // Group by date and calculate average scores
        const scoresByDate = {};
        sessions.forEach(session => {
            const date = new Date(session.created_at || session.timestamp);
            const dateKey = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

            if (!scoresByDate[dateKey]) {
                scoresByDate[dateKey] = { ddd: [], test: [] };
            }

            if (session.ddd_score) scoresByDate[dateKey].ddd.push(session.ddd_score);
            if (session.test_count) scoresByDate[dateKey].test.push(session.test_count);
        });

        const sortedDates = Object.keys(scoresByDate).sort((a, b) => {
            return new Date(a) - new Date(b);
        });

        const avgDDD = sortedDates.map(date => {
            const scores = scoresByDate[date].ddd;
            return scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
        });

        const avgTests = sortedDates.map(date => {
            const counts = scoresByDate[date].test;
            return counts.length > 0 ? counts.reduce((a, b) => a + b, 0) / counts.length : 0;
        });

        const data = [
            {
                x: sortedDates,
                y: avgDDD,
                name: 'Avg DDD Score',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#10b981', width: 3 },
                marker: { size: 8 }
            },
            {
                x: sortedDates,
                y: avgTests,
                name: 'Avg Test Count',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#3b82f6', width: 3 },
                marker: { size: 8 },
                yaxis: 'y2'
            }
        ];

        const layout = this.getChartLayout('Average Scores Trend', 350);
        layout.xaxis = { title: 'Date', showgrid: true, gridcolor: '#e5e7eb' };
        layout.yaxis = {
            title: 'DDD Score (%)',
            showgrid: true,
            gridcolor: '#e5e7eb',
            side: 'left'
        };
        layout.yaxis2 = {
            title: 'Test Count',
            overlaying: 'y',
            side: 'right',
            showgrid: false
        };
        layout.showlegend = true;
        layout.legend = { x: 0.05, y: 0.95 };

        Plotly.newPlot('dashAvgScoresTrend', data, layout, this.getChartConfig());
    }

    // Chart 3: Top Repositories (Bar Chart)
    renderDashTopRepos(sessions) {
        // Count reviews per repository
        const repoCount = {};
        sessions.forEach(session => {
            const repoUrl = session.repo_url || 'Unknown';
            const repoName = repoUrl.split('/').slice(-2).join('/');
            repoCount[repoName] = (repoCount[repoName] || 0) + 1;
        });

        // Sort and take top 10
        const sortedRepos = Object.entries(repoCount)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);

        const data = [{
            x: sortedRepos.map(r => r[1]),
            y: sortedRepos.map(r => r[0]),
            type: 'bar',
            orientation: 'h',
            marker: {
                color: sortedRepos.map((_, i) => {
                    const colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7', '#fa709a', '#fee140', '#30cfd0'];
                    return colors[i % colors.length];
                }),
                line: {
                    color: 'rgba(255, 255, 255, 0.8)',
                    width: 1
                }
            },
            text: sortedRepos.map(r => r[1]),
            textposition: 'auto'
        }];

        const layout = this.getChartLayout('Top Repositories', 350);
        layout.xaxis = { title: 'Number of Reviews', showgrid: true, gridcolor: '#e5e7eb' };
        layout.yaxis = { title: '', automargin: true };
        layout.margin = { t: 60, b: 50, l: 150, r: 40 };

        Plotly.newPlot('dashTopRepos', data, layout, this.getChartConfig());
    }

    // Chart 4: Issues Breakdown (Pie Chart)
    renderDashIssuesBreakdown(sessions) {
        // Aggregate issue counts (simulated data - would need actual issue tracking)
        let totalSecurity = 0;
        let totalBugs = 0;
        let totalQuality = 0;
        let totalTests = 0;

        sessions.forEach(session => {
            // These would ideally come from session data
            // For now, using random/estimated values
            totalSecurity += Math.floor(Math.random() * 5);
            totalBugs += Math.floor(Math.random() * 8);
            totalQuality += Math.floor(Math.random() * 10);
            totalTests += Math.floor(Math.random() * 3);
        });

        const data = [{
            labels: ['Security Issues', 'Bugs Detected', 'Code Quality', 'Test Suggestions'],
            values: [totalSecurity, totalBugs, totalQuality, totalTests],
            type: 'pie',
            marker: {
                colors: ['#ef4444', '#f59e0b', '#3b82f6', '#10b981'],
                line: {
                    color: '#fff',
                    width: 2
                }
            },
            textposition: 'inside',
            textinfo: 'label+percent',
            hoverinfo: 'label+value+percent',
            hole: 0.35
        }];

        const layout = this.getChartLayout('Issues Breakdown', 350);
        layout.showlegend = true;
        layout.legend = {
            orientation: 'v',
            x: 1.1,
            y: 0.5
        };
        layout.annotations = [{
            text: `${totalSecurity + totalBugs + totalQuality + totalTests}<br>Total`,
            x: 0.5,
            y: 0.5,
            font: { size: 20, color: '#111827' },
            showarrow: false
        }];

        Plotly.newPlot('dashIssuesBreakdown', data, layout, this.getChartConfig());
    }

    // Load Dashboard Recent Reviews List
    async loadDashboardRecentReviews() {
        const listContainer = document.getElementById('dashboardRecentList');

        try {
            const response = await fetch('/api/sessions/recent?limit=10');
            const data = await response.json();

            if (data.success && data.sessions && data.sessions.length > 0) {
                listContainer.innerHTML = '';
                data.sessions.forEach(session => {
                    const item = this.createDashboardRecentItem(session);
                    listContainer.appendChild(item);
                });
            } else {
                listContainer.innerHTML = '<div class="empty-message">📭 No recent reviews found</div>';
            }
        } catch (error) {
            console.error('Failed to load recent reviews:', error);
            listContainer.innerHTML = '<div class="empty-message">❌ Failed to load recent reviews</div>';
        }
    }

    createDashboardRecentItem(session) {
        const div = document.createElement('div');
        div.className = 'history-item clickable-item';

        const date = new Date(session.created_at || session.timestamp);
        const formattedDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

        div.innerHTML = `
            <div class="history-item-header">
                <div>
                    <div class="history-item-title">${this.escapeHtml(session.pr_title || 'Untitled PR')}</div>
                    <div class="history-item-pr">${session.repo_url ? this.escapeHtml(session.repo_url.split('/').slice(-2).join('/')) : 'No Repository'}</div>
                </div>
                <div class="history-item-date">${formattedDate}</div>
            </div>
            <div class="history-item-stats">
                <div class="history-stat">
                    <span class="history-stat-icon">📁</span>
                    <span class="history-stat-value">${session.files_count || 0}</span>
                    <span class="history-stat-label">files</span>
                </div>
                <div class="history-stat">
                    <span class="history-stat-icon">🧪</span>
                    <span class="history-stat-value">${session.test_count || 0}</span>
                    <span class="history-stat-label">tests</span>
                </div>
                <div class="history-stat">
                    <span class="history-stat-icon">🏗️</span>
                    <span class="history-stat-value">${session.ddd_score || 0}%</span>
                    <span class="history-stat-label">DDD</span>
                </div>
            </div>
            <div class="history-item-actions">
                <button class="btn-view-report" data-session-id="${session._id}">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 3.5a4.5 4.5 0 100 9 4.5 4.5 0 000-9zM2 8a6 6 0 1112 0A6 6 0 012 8z"/>
                        <path d="M8 5.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z"/>
                    </svg>
                    View Report
                </button>
            </div>
        `;

        // Add click handler for view report button
        const viewBtn = div.querySelector('.btn-view-report');
        viewBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.viewSessionReport(session._id);
        });

        return div;
    }

    // History Functions
    async loadHistory() {
        const historyList = document.getElementById('historyList');
        const limit = document.getElementById('historyLimit').value || 10;

        historyList.innerHTML = '<div class="loading-message">Loading history...</div>';

        try {
            const response = await fetch(`/api/sessions/recent?limit=${limit}`);
            const data = await response.json();

            if (data.success && data.sessions && data.sessions.length > 0) {
                historyList.innerHTML = '';
                data.sessions.forEach(session => {
                    const item = this.createHistoryItem(session);
                    historyList.appendChild(item);
                });
            } else {
                historyList.innerHTML = '<div class="empty-message">📭 No review history found</div>';
            }
        } catch (error) {
            console.error('Failed to load history:', error);
            historyList.innerHTML = '<div class="empty-message">❌ Failed to load history</div>';
        }
    }

    createHistoryItem(session) {
        const div = document.createElement('div');
        div.className = 'history-item clickable-item';

        const date = new Date(session.created_at || session.timestamp);
        const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();

        div.innerHTML = `
            <div class="history-item-header">
                <div>
                    <div class="history-item-title">${this.escapeHtml(session.pr_title || 'Untitled PR')}</div>
                    <div class="history-item-pr">${this.escapeHtml(session.pr_url || 'No URL')}</div>
                </div>
                <div class="history-item-date">${formattedDate}</div>
            </div>
            <div class="history-item-stats">
                <div class="history-stat">
                    <span class="history-stat-icon">📁</span>
                    <span class="history-stat-value">${session.files_count || 0}</span>
                    <span class="history-stat-label">files</span>
                </div>
                <div class="history-stat">
                    <span class="history-stat-icon">🧪</span>
                    <span class="history-stat-value">${session.test_count || 0}</span>
                    <span class="history-stat-label">tests</span>
                </div>
                <div class="history-stat">
                    <span class="history-stat-icon">🏗️</span>
                    <span class="history-stat-value">${session.ddd_score || 0}%</span>
                    <span class="history-stat-label">DDD</span>
                </div>
            </div>
            <div class="history-item-actions">
                <button class="btn-view-report" data-session-id="${session._id}">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 3.5a4.5 4.5 0 100 9 4.5 4.5 0 000-9zM2 8a6 6 0 1112 0A6 6 0 012 8z"/>
                        <path d="M8 5.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z"/>
                    </svg>
                    View Report
                </button>
            </div>
        `;

        // Add click handler for view report button
        const viewBtn = div.querySelector('.btn-view-report');
        viewBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.viewSessionReport(session._id);
        });

        return div;
    }

    // View Session Report
    async viewSessionReport(sessionId) {
        try {
            console.log('Loading session:', sessionId);

            // Show loading toast
            this.showSuccess('Loading review report...');

            // Hide progress section
            document.getElementById('progressSection').classList.add('hidden');

            // Fetch session data
            const response = await fetch(`/api/sessions/${sessionId}`);
            const data = await response.json();

            if (data.success && data.session) {
                const session = data.session;
                const results = session.results;

                if (results) {
                    // Display the results in the summary section
                    this.displayResults(results);

                    // Show summary section with charts
                    this.showSummary(results);

                    // Show success message
                    this.showSuccess(`Loaded report for: ${session.pr_title || 'Review'}`);

                    // Store current review for downloads
                    this.currentReview = results;
                } else {
                    throw new Error('No results data in session');
                }
            } else {
                throw new Error(data.error || 'Session not found');
            }
        } catch (error) {
            console.error('Failed to load session report:', error);
            this.showError(`Failed to load report: ${error.message}`);
            document.getElementById('summarySection').classList.add('hidden');
        }
    }

    // Statistics Functions
    async loadStatistics() {
        try {
            const response = await fetch('/api/sessions/statistics');
            const data = await response.json();

            if (data.success) {
                const stats = data.statistics;

                // Update database stats
                document.getElementById('statTotalSessions').textContent = stats.total_sessions || 0;
                document.getElementById('statMongoStatus').textContent = stats.connected ? 'Connected ✅' : 'Disconnected ⚠️';

                // Update top repos list
                const topReposList = document.getElementById('topReposList');
                if (stats.top_repos && stats.top_repos.length > 0) {
                    topReposList.innerHTML = '';
                    stats.top_repos.forEach(repo => {
                        const item = document.createElement('div');
                        item.className = 'repo-item';
                        item.innerHTML = `
                            <div class="repo-name">${repo._id || 'Unknown'}</div>
                            <div class="repo-count">${repo.count} reviews</div>
                        `;
                        topReposList.appendChild(item);
                    });

                    // Populate repository filter dropdown
                    this.populateRepoFilter(stats.top_repos);
                } else {
                    topReposList.innerHTML = '<div class="empty-message">No repositories reviewed yet</div>';
                }
            }
        } catch (error) {
            console.error('Failed to load statistics:', error);
            document.getElementById('topReposList').innerHTML = '<div class="empty-message">❌ Failed to load statistics</div>';
        }
    }

    // Populate Repository Filter Dropdown
    populateRepoFilter(repos) {
        const repoFilter = document.getElementById('repoFilter');

        // Clear existing options except the first one
        repoFilter.innerHTML = '<option value="">Select a repository...</option>';

        // Add all repositories
        repos.forEach(repo => {
            const option = document.createElement('option');
            option.value = repo._id;
            option.textContent = `${repo._id} (${repo.count} reviews)`;
            repoFilter.appendChild(option);
        });
    }

    // Filter By Repository
    async filterByRepository() {
        const repoFilter = document.getElementById('repoFilter');
        const selectedRepo = repoFilter.value;

        if (!selectedRepo) {
            this.showError('Please select a repository to filter');
            return;
        }

        try {
            // Fetch all sessions for this repository
            const response = await fetch('/api/sessions/recent?limit=1000');
            const data = await response.json();

            if (data.success && data.sessions) {
                // Filter sessions by repository
                const filteredSessions = data.sessions.filter(session =>
                    session.repo_url === selectedRepo
                );

                if (filteredSessions.length === 0) {
                    this.showError('No reviews found for this repository');
                    return;
                }

                // Calculate statistics
                const totalReviews = filteredSessions.length;
                const avgDDD = filteredSessions.reduce((sum, s) => sum + (s.ddd_score || 0), 0) / totalReviews;
                const avgTests = filteredSessions.reduce((sum, s) => sum + (s.test_count || 0), 0) / totalReviews;
                const avgFiles = filteredSessions.reduce((sum, s) => sum + (s.files_count || 0), 0) / totalReviews;

                // Update stats display
                document.getElementById('repoTotalReviews').textContent = totalReviews;
                document.getElementById('repoAvgDDD').textContent = avgDDD.toFixed(1) + '%';
                document.getElementById('repoAvgTests').textContent = Math.round(avgTests);
                document.getElementById('repoAvgFiles').textContent = Math.round(avgFiles);

                // Show stats section
                document.getElementById('filteredRepoStats').style.display = 'block';

                // Display filtered reports
                const reportsList = document.getElementById('filteredReportsList');
                reportsList.style.display = 'block';
                reportsList.innerHTML = '';

                filteredSessions.forEach(session => {
                    const item = this.createHistoryItem(session);
                    reportsList.appendChild(item);
                });

                this.showSuccess(`Found ${totalReviews} reviews for ${selectedRepo.split('/').slice(-2).join('/')}`);

            } else {
                throw new Error('Failed to fetch sessions');
            }

        } catch (error) {
            console.error('Error filtering by repository:', error);
            this.showError(`Failed to filter reports: ${error.message}`);
        }
    }

    // Clear Repository Filter
    clearRepoFilter() {
        // Reset dropdown
        document.getElementById('repoFilter').value = '';

        // Hide filtered results
        document.getElementById('filteredRepoStats').style.display = 'none';
        document.getElementById('filteredReportsList').style.display = 'none';

        this.showSuccess('Filter cleared');
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PRReviewApp();
});
