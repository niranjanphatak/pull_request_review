// Main Application JavaScript
class PRReviewApp {
    constructor() {
        this.apiEndpoint = '/api/review';
        this.currentReview = null;
        this.charts = {};
        this.currentSection = 'new-review';
        this.currentSession = null; // For viewing historical sessions
        this.progressPromptVersions = null; // For prompt versions during active review
        this.progressOrientation = localStorage.getItem('progressOrientation') || 'horizontal'; // horizontal or vertical
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
        this.initTheme();
        this.initProgressOrientation();
        this.initReportRowClicks();
        this.initPromptManagement();

        // Handle initial hash or show dashboard
        this.handleHashChange();

        // Setup hash change listener for browser back/forward
        window.addEventListener('hashchange', () => this.handleHashChange());
    }

    initReportRowClicks() {
        // Add click listeners to all report rows to make them clickable
        document.addEventListener('click', (e) => {
            const reportRow = e.target.closest('.report-row');
            if (reportRow) {
                // Don't trigger if clicking on buttons or links
                if (e.target.closest('button') || e.target.closest('a')) {
                    return;
                }

                const stage = reportRow.getAttribute('data-stage');
                if (stage) {
                    this.toggleReportRow(stage);
                }
            }
        });
    }

    handleHashChange() {
        const hash = window.location.hash.slice(1);

        const validSections = [
            'dashboard', 'onboarding', 'new-review', 'history',
            'statistics', 'ai-stats', 'prompt-management'
        ];

        if (hash && validSections.includes(hash)) {
            console.log('Navigating to section:', hash);
            this.showSection(hash);

            // Update active nav link
            document.querySelectorAll('.nav-item').forEach(link => {
                if (link.getAttribute('data-section') === hash) {
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            });

            // Update page title
            const pageTitles = {
                'dashboard': 'Dashboard',
                'onboarding': 'Team Onboarding',
                'new-review': 'New Review',
                'history': 'History',
                'statistics': 'Statistics',
                'ai-stats': 'AI Token Statistics',
                'prompt-management': 'Prompt Management'
            };
            document.getElementById('pageTitle').textContent = pageTitles[hash] || 'Dashboard';

            // Hide analyzer specific header stats (just in case they exist but shouldn't be shown)
            const analyzerStat = document.getElementById('analyzerHeaderStat');
            if (analyzerStat) {
                analyzerStat.style.display = 'none';
            }
        } else {
            // Default to dashboard if no valid hash
            this.showSection('dashboard');
            window.location.hash = 'dashboard';
        }
    }

    setupEventListeners() {
        const startBtn = document.getElementById('startReview');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startReview());
        }

        // Theme toggle
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    initTheme() {
        // Check for saved theme preference or default to light mode
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
        }
    }

    toggleTheme() {
        const body = document.body;
        body.classList.toggle('dark-mode');

        // Save preference to localStorage
        const isDark = body.classList.contains('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');

        // Recreate charts with new theme colors if they exist
        if (this.charts && Object.keys(this.charts).length > 0) {
            this.initializeCharts();
        }
    }

    setupTabs() {
        // Setup old tab buttons (if any)
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });

        // Setup new professional tab buttons
        const tabButtonsPro = document.querySelectorAll('.tab-button-pro');
        tabButtonsPro.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.getAttribute('data-tab');
                this.switchTab(tabName, true); // Pass true for professional tabs
            });
        });
    }

    switchTab(tabName, isProfessional = false) {
        if (isProfessional) {
            // Professional tabs
            document.querySelectorAll('.tab-button-pro').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane-pro').forEach(pane => pane.classList.remove('active'));

            // Add active class to selected button and pane
            const button = document.querySelector(`.tab-button-pro[data-tab="${tabName}"]`);
            const pane = document.getElementById(`${tabName}Tab`);

            if (button) button.classList.add('active');
            if (pane) pane.classList.add('active');
        } else {
            // Old tabs (legacy support)
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

            const button = document.querySelector(`.tab-button[data-tab="${tabName}"]`);
            const pane = document.getElementById(`${tabName}Tab`);

            if (button) button.classList.add('active');
            if (pane) pane.classList.add('active');
        }
    }

    navigateToTab(tabName, isProfessional = false) {
        console.log('navigateToTab called with:', tabName, 'isProfessional:', isProfessional);

        // Scroll to detailed reports section (check both old and new selectors)
        let reportsSection = document.querySelector('.detailed-reports-pro');
        if (!reportsSection) {
            reportsSection = document.querySelector('.detailed-reports');
        }
        console.log('Reports section found:', !!reportsSection);

        if (reportsSection) {
            reportsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        // Switch to the selected tab after a short delay for smooth scrolling
        setTimeout(() => {
            this.switchTab(tabName, isProfessional);
        }, 300);
    }

    async startReview() {
        const prUrl = document.getElementById('prUrl').value;
        const repoUrl = document.getElementById('repoUrl').value;
        const analyzeTargetBranch = document.getElementById('analyzeTargetBranch').checked;

        // Get enabled stages
        const enabledStages = {
            security: document.getElementById('enableSecurity').checked,
            bugs: document.getElementById('enableBugs').checked,
            style: document.getElementById('enableStyle').checked,
            performance: document.getElementById('enablePerformance').checked,
            tests: document.getElementById('enableTests').checked
        };

        if (!prUrl || !repoUrl) {
            this.showError('Please enter both Merge Request/Pull Request URL and Source Repository URL');
            return;
        }

        // Check if at least one stage is enabled
        if (!Object.values(enabledStages).some(enabled => enabled)) {
            this.showError('Please enable at least one review stage');
            return;
        }

        // Reset any previous state
        this.stopProgress();
        this.stopPolling();

        // Show progress section with disabled stages greyed out
        this.showProgress(enabledStages);

        try {
            console.log('Starting code review...', {
                pr_url: prUrl,
                repo_url: repoUrl,
                analyze_target_branch: analyzeTargetBranch,
                enabled_stages: enabledStages
            });

            // Start the review (returns job ID immediately)
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pr_url: prUrl,
                    repo_url: repoUrl,
                    analyze_target_branch: analyzeTargetBranch,
                    enabled_stages: enabledStages
                })
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

        // Update current step counter (0-11)
        const currentStepEl = document.getElementById('currentStep');
        const stepNumber = Math.min(Math.floor(progress / 8.33), 12);
        if (currentStepEl) {
            currentStepEl.textContent = stepNumber;
        }

        // Define stage descriptions for each step
        const stageDescriptions = [
            { name: 'Initializing', description: 'Setting up review environment and preparing analysis tools' },
            { name: 'Fetching PR/MR', description: 'Retrieving pull request details and metadata from repository' },
            { name: 'Analyzing Diff', description: 'Processing code changes and preparing for analysis' },
            { name: 'Security Review', description: 'Scanning for vulnerabilities, SQL injection, XSS, and security risks' },
            { name: 'Bug Detection', description: 'Identifying logic errors, null references, and edge case issues' },
            { name: 'Code Quality', description: 'Reviewing style, best practices, and code optimization opportunities' },
            { name: 'Performance Analysis', description: 'Detecting bottlenecks, inefficiencies, and optimization opportunities' },
            { name: 'Test Analysis', description: 'Evaluating test coverage and suggesting test improvements' },
            { name: 'Target Branch Check', description: 'Analyzing target branch compatibility and potential conflicts' },
            { name: 'Chart Generation', description: 'Creating visual analytics and statistical summaries' },
            { name: 'Finalizing', description: 'Compiling comprehensive review report and recommendations' },
            { name: 'Complete', description: 'Review finished - presenting detailed analysis and insights' }
        ];

        // Update current stage description
        if (stepNumber > 0 && stepNumber <= stageDescriptions.length && progress < 100) {
            const currentStage = stageDescriptions[stepNumber - 1];
            this.updateCurrentStageDescription(currentStage.name, currentStage.description);
        } else if (progress >= 100) {
            this.hideCurrentStageDescription();
        }

        // Update horizontal timeline steps based on actual progress
        const stepsHorizontal = document.querySelectorAll('.timeline-step-horizontal');
        stepsHorizontal.forEach((step, index) => {
            const stepProgress = (index + 1) * 8.33;

            if (progress >= stepProgress) {
                // Completed
                step.classList.remove('step-pending', 'step-active');
                step.classList.add('step-completed');
            } else if (progress > (index * 8.33) && progress < stepProgress) {
                // Active - current step in progress
                step.classList.remove('step-pending', 'step-completed');
                step.classList.add('step-active');
            } else {
                // Pending
                step.classList.remove('step-active', 'step-completed');
                step.classList.add('step-pending');
            }
        });

        // Update vertical timeline steps based on actual progress
        const stepsVertical = document.querySelectorAll('.timeline-step-vertical');
        stepsVertical.forEach((step, index) => {
            const stepProgress = (index + 1) * 8.33;

            if (progress >= stepProgress) {
                // Completed
                step.classList.remove('step-pending', 'step-active');
                step.classList.add('step-completed');
            } else if (progress > (index * 8.33) && progress < stepProgress) {
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

        // Cleanup sticky progress behavior
        this.cleanupProgressStickyBehavior();

        // Display results
        this.displayResults(resultsData.results);

        // Update version badges (note: new reviews won't have prompt_versions yet
        // as this needs to be added to the response data structure)
        // For now, this will be populated when viewing existing reports

        // Show success message
        const prTitle = resultsData.results?.pr_details?.title || 'MR/PR';
        this.showSuccess(`Review completed successfully for: ${prTitle}`);

        // Show summary section
        setTimeout(() => {
            this.showSummary(resultsData.results);
        }, 800);

        // Reload dashboard stats in background
        this.loadDashboardStats();
    }

    showProgress(enabledStages = null) {
        // Hide the new review section
        const newReviewSection = document.getElementById('new-review');
        if (newReviewSection) newReviewSection.classList.add('hidden');

        // Show progress section and reset UI
        document.getElementById('progressSection').classList.remove('hidden');
        document.getElementById('summarySection').classList.add('hidden');

        // Reset progress bar
        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = '0%';

        // Reset all horizontal timeline steps to pending and apply disabled state if needed
        const stepsHorizontal = document.querySelectorAll('.timeline-step-horizontal');
        stepsHorizontal.forEach(step => {
            step.classList.remove('step-active', 'step-completed', 'step-disabled');
            step.classList.add('step-pending');

            // Check if this stage is disabled
            if (enabledStages) {
                const stepType = step.getAttribute('data-step');
                const stageMapping = {
                    'security': 'security',
                    'bugs': 'bugs',
                    'style': 'style',
                    'tests': 'tests'
                };

                if (stageMapping[stepType] && !enabledStages[stageMapping[stepType]]) {
                    step.classList.add('step-disabled');
                    step.classList.remove('step-pending');
                }
            }
        });

        // Reset all vertical timeline steps to pending and apply disabled state if needed
        const stepsVertical = document.querySelectorAll('.timeline-step-vertical');
        stepsVertical.forEach(step => {
            step.classList.remove('step-active', 'step-completed', 'step-disabled');
            step.classList.add('step-pending');

            // Check if this stage is disabled
            if (enabledStages) {
                const stepType = step.getAttribute('data-step');
                const stageMapping = {
                    'security': 'security',
                    'bugs': 'bugs',
                    'style': 'style',
                    'tests': 'tests'
                };

                if (stageMapping[stepType] && !enabledStages[stageMapping[stepType]]) {
                    step.classList.add('step-disabled');
                    step.classList.remove('step-pending');
                }
            }
        });

        // Reset counters
        const currentStepEl = document.getElementById('currentStep');
        const progressPercentEl = document.getElementById('progressPercent');
        if (currentStepEl) currentStepEl.textContent = '0';
        if (progressPercentEl) progressPercentEl.textContent = '0';

        // Store enabled stages for later use
        this.enabledStages = enabledStages;

        // Setup scroll listener for sticky progress bar
        this.setupProgressStickyBehavior();

        // Load and display prompt versions
        this.loadProgressPromptVersions();
    }

    async loadProgressPromptVersions() {
        try {
            // Fetch prompt versions from the API
            const response = await fetch('/api/prompt-versions');
            if (!response.ok) {
                console.warn('Could not load prompt versions');
                return;
            }

            const versions = await response.json();

            // Store prompt versions for use in modal during progress
            this.progressPromptVersions = {};

            // Update version badges and descriptions for each stage
            const stageMapping = {
                'security': { versionId: 'progressSecurityVersion', descId: 'progressSecurityDesc' },
                'bugs': { versionId: 'progressBugsVersion', descId: 'progressBugsDesc' },
                'style': { versionId: 'progressStyleVersion', descId: 'progressStyleDesc' },
                'tests': { versionId: 'progressTestsVersion', descId: 'progressTestsDesc' }
            };

            Object.keys(stageMapping).forEach(stage => {
                const stageVersions = versions[stage];
                if (stageVersions && stageVersions.length > 0) {
                    // Get the active version (most recent)
                    const activeVersion = stageVersions.find(v => v.active) || stageVersions[0];

                    // Store for modal use
                    this.progressPromptVersions[stage] = {
                        version: activeVersion.version,
                        description: activeVersion.description,
                        criteria: activeVersion.criteria
                    };

                    const { versionId, descId } = stageMapping[stage];
                    const versionBadge = document.getElementById(versionId);
                    const descriptionEl = document.getElementById(descId);

                    if (versionBadge) {
                        versionBadge.textContent = `v${activeVersion.version}`;
                    }
                    if (descriptionEl && activeVersion.description) {
                        descriptionEl.textContent = activeVersion.description;
                    }
                }
            });
        } catch (error) {
            console.error('Error loading prompt versions:', error);
        }
    }

    hideProgress() {
        document.getElementById('progressSection').classList.add('hidden');

        // Show the new review section again
        const newReviewSection = document.getElementById('new-review');
        if (newReviewSection) newReviewSection.classList.remove('hidden');
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

        // Mark all horizontal timeline steps as completed
        const stepsHorizontal = document.querySelectorAll('.timeline-step-horizontal');
        stepsHorizontal.forEach(step => {
            step.classList.remove('step-pending', 'step-active');
            step.classList.add('step-completed');
        });

        // Mark all vertical timeline steps as completed
        const stepsVertical = document.querySelectorAll('.timeline-step-vertical');
        stepsVertical.forEach(step => {
            step.classList.remove('step-pending', 'step-active');
            step.classList.add('step-completed');
        });

        // Update counters to 100%
        const currentStepEl = document.getElementById('currentStep');
        const progressPercentEl = document.getElementById('progressPercent');
        if (currentStepEl) currentStepEl.textContent = '12';
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
        this.currentReview = results;
        // Update professional header - Date and PR info
        const now = new Date();
        const dateEl = document.getElementById('reviewDateText');
        if (dateEl) {
            dateEl.textContent = now.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        const prEl = document.getElementById('reviewPRText');
        if (prEl && results.pr_info) {
            prEl.textContent = results.pr_info;
        }

        // Generate Executive Summary
        this.updateExecutiveSummary(results);

        // Update Overall Status Badge
        this.updateStatusBadge(results);

        // Update metrics
        document.getElementById('totalFiles').textContent = results.structure.total;
        document.getElementById('testFiles').textContent = results.test_analysis.count;
        document.getElementById('dddScore').textContent = results.ddd.score.toFixed(0) + '%';
        document.getElementById('directories').textContent = results.structure.dirs;

        // Update file detail
        const filesDetailEl = document.getElementById('filesDetail');
        if (filesDetailEl) {
            filesDetailEl.textContent = `${results.structure.files} files analyzed`;
        }

        // Update summaries
        document.getElementById('securitySummary').textContent = this.extractSummary(results.security);
        document.getElementById('bugSummary').textContent = this.extractSummary(results.bugs);
        document.getElementById('qualitySummary').textContent = this.extractSummary(results.style);
        const performanceSummaryEl = document.getElementById('performanceSummary');
        if (performanceSummaryEl) {
            performanceSummaryEl.textContent = this.extractSummary(results.performance);
        }
        document.getElementById('testSuggestionsSummary').textContent = this.extractSummary(results.tests);

        // Render Professional Recommendations Hub
        this.renderRecommendationsHub(results);

        // Update Analysis Browser
        this.updateAnalysisBrowser(results);

        // Update table view (legacy fallback or remove if not needed)
        // this.updateReportsTable(results);

        // Re-setup clickable finding cards
        setTimeout(() => {
            this.setupClickableCards();
        }, 100);

        // Handle target branch analysis if present
        if (results.target_branch_analysis) {
            const targetBranchCard = document.getElementById('targetBranchCard');
            const targetBranchTabBtn = document.getElementById('targetBranchTabBtn');
            const targetBranchSummary = document.getElementById('targetBranchSummary');
            const targetBranchDetails = document.getElementById('targetBranchDetails');

            if (targetBranchCard) targetBranchCard.style.display = 'block';
            if (targetBranchTabBtn) targetBranchTabBtn.style.display = 'inline-block';
            if (targetBranchSummary) {
                targetBranchSummary.textContent = this.extractSummary(results.target_branch_analysis);
            }
            if (targetBranchDetails) {
                this.updateDetailedReport('targetBranchDetails', results.target_branch_analysis);
            }
        } else {
            // Hide target branch elements if analysis wasn't performed
            const targetBranchCard = document.getElementById('targetBranchCard');
            const targetBranchTabBtn = document.getElementById('targetBranchTabBtn');
            if (targetBranchCard) targetBranchCard.style.display = 'none';
            if (targetBranchTabBtn) targetBranchTabBtn.style.display = 'none';
        }

        // Store for downloads
        this.currentReview = results;
    }

    extractSummary(data, maxLength = 120) {
        if (!data) return 'No findings reported.';

        let text = '';
        if (typeof data === 'string') {
            text = data;
        } else if (typeof data === 'object' && data.summary) {
            text = data.summary;
        } else if (typeof data === 'object' && data.findings && data.findings.length > 0) {
            text = data.findings[0].title || data.findings[0].description;
        } else {
            return 'Analysis complete.';
        }

        // Clean up markdown common elements for summary view
        let clean = text.replace(/[#*`]/g, '').trim();

        // Try to find the first substantial paragraph or line
        const lines = clean.split('\n')
            .map(l => l.trim())
            .filter(l => l.length > 20 && !l.toLowerCase().includes('report') && !l.toLowerCase().includes('analysis'));

        const summary = lines[0] || clean.split('\n')[0] || clean;

        return summary.length > maxLength ? summary.substring(0, maxLength).trim() + '...' : summary;
    }

    updateExecutiveSummary(results) {
        const summaryEl = document.getElementById('executiveSummary');
        if (!summaryEl) return;

        // Count total issues across all categories
        const securityIssues = this.countIssues(results.security);
        const bugIssues = this.countIssues(results.bugs);
        const qualityIssues = this.countIssues(results.style);

        const totalIssues = securityIssues + bugIssues + qualityIssues;
        const dddScore = results.ddd.score.toFixed(0);
        const testCoverage = results.test_analysis.count;

        let summary = '';

        if (totalIssues === 0) {
            summary = `<p>✅ <strong>Excellent!</strong> Code review completed successfully with no critical issues found.
                      The codebase demonstrates good practices with a DDD score of <strong>${dddScore}%</strong>
                      and <strong>${testCoverage} test files</strong> detected.</p>`;
        } else if (totalIssues <= 5) {
            summary = `<p>✅ <strong>Good!</strong> Code review completed with <strong>${totalIssues} minor ${totalIssues === 1 ? 'issue' : 'issues'}</strong> identified.
                      ${securityIssues > 0 ? `Includes ${securityIssues} security ${securityIssues === 1 ? 'concern' : 'concerns'}. ` : ''}
                      DDD score: <strong>${dddScore}%</strong>. Review the findings below for recommendations.</p>`;
        } else {
            summary = `<p>⚠️ <strong>Action Required:</strong> Code review found <strong>${totalIssues} ${totalIssues === 1 ? 'issue' : 'issues'}</strong>
                      ${securityIssues > 0 ? `including <strong>${securityIssues} security ${securityIssues === 1 ? 'concern' : 'concerns'}</strong>` : ''}.
                      Please review the detailed findings below and address critical issues before merging.</p>`;
        }

        summaryEl.innerHTML = summary;
    }

    updateStatusBadge(results) {
        const statusBadge = document.getElementById('overallStatus');
        if (!statusBadge) return;

        const securityIssues = this.countIssues(results.security);
        const bugIssues = this.countIssues(results.bugs);
        const qualityIssues = this.countIssues(results.style);

        const totalIssues = securityIssues + bugIssues + qualityIssues;
        const dddScore = results.ddd.score;

        let statusClass = 'status-success';
        let statusText = 'Ready for Merge';

        if (securityIssues > 0 || totalIssues > 10 || dddScore < 50) {
            statusClass = 'status-error';
            statusText = 'Needs Attention';
        } else if (totalIssues > 5 || dddScore < 70) {
            statusClass = 'status-warning';
            statusText = 'Review Recommended';
        }

        const indicator = statusBadge.querySelector('.status-indicator');
        const text = statusBadge.querySelector('.status-text');

        if (indicator) {
            indicator.className = `status-indicator ${statusClass}`;
        }
        if (text) {
            text.textContent = statusText;
        }
    }

    updateIssueCounts(results) {
        // Count issues for each category
        const counts = {
            security: this.countIssues(results.security),
            bugs: this.countIssues(results.bugs),
            quality: this.countIssues(results.style),
            performance: this.countIssues(results.performance),
            tests: this.countIssues(results.tests)
        };

        // Update the count displays
        const securityCountEl = document.getElementById('securityCount');
        const bugsCountEl = document.getElementById('bugsCount');
        const qualityCountEl = document.getElementById('qualityCount');
        const performanceCountEl = document.getElementById('performanceCount');
        const testsCountEl = document.getElementById('testsCount');

        if (securityCountEl) {
            securityCountEl.textContent = `${counts.security} ${counts.security === 1 ? 'issue' : 'issues'}`;
        }
        if (bugsCountEl) {
            bugsCountEl.textContent = `${counts.bugs} ${counts.bugs === 1 ? 'issue' : 'issues'}`;
        }
        if (qualityCountEl) {
            qualityCountEl.textContent = `${counts.quality} ${counts.quality === 1 ? 'suggestion' : 'suggestions'}`;
        }
        if (performanceCountEl) {
            performanceCountEl.textContent = `${counts.performance} ${counts.performance === 1 ? 'issue' : 'issues'}`;
        }
        if (testsCountEl) {
            testsCountEl.textContent = `${counts.tests} ${counts.tests === 1 ? 'suggestion' : 'suggestions'}`;
        }
    }

    // Helper function to detect issue pattern in text
    detectIssuePattern(text) {
        if (!text || text.trim() === '') {
            return { pattern: null, count: 0 };
        }

        // Check for "No issues" or similar messages first
        if (text.toLowerCase().includes('no issues found') ||
            text.toLowerCase().includes('no issues') ||
            text.toLowerCase().includes('no problems') ||
            text.toLowerCase().includes('looks good') ||
            text.toLowerCase().includes('no concerns')) {
            return { pattern: null, count: 0 };
        }

        // Pattern 1: Numbered lists (1., 2., 3., etc.) - most common AI format
        const numberedMatches = text.match(/^\s*\d+\.\s+/gm);
        if (numberedMatches && numberedMatches.length > 0) {
            return { pattern: 'numbered', count: numberedMatches.length, regex: /^\s*\d+\.\s+/gm };
        }

        // Pattern 2: Bullet points (-, *, •)
        const bulletMatches = text.match(/^\s*[-*•]\s+/gm);
        if (bulletMatches && bulletMatches.length > 0) {
            return { pattern: 'bullet', count: bulletMatches.length, regex: /^\s*[-*•]\s+/gm };
        }

        // Pattern 3: Headers with issue indicators (## Issue 1, ### Problem:, etc.)
        const headerMatches = text.match(/^#{2,4}\s+/gm);
        if (headerMatches && headerMatches.length > 0) {
            return { pattern: 'header', count: headerMatches.length, regex: /^#{2,4}\s+/gm };
        }

        // Pattern 4: Severity emojis (🔴, 🟠, 🟡, etc.)
        const severityMatches = text.match(/^[🔴🟠🟡🟢]\s+/gm);
        if (severityMatches && severityMatches.length > 0) {
            return { pattern: 'severity_emoji', count: severityMatches.length, regex: /^[🔴🟠🟡🟢]\s+/gm };
        }

        // Pattern 5: Severity labels (**Severity**:)
        const labelMatches = text.match(/\*\*Severity\*\*:/gi);
        if (labelMatches && labelMatches.length > 0) {
            return { pattern: 'severity_label', count: labelMatches.length, regex: /\*\*Severity\*\*:/gi };
        }

        // Pattern 6: Issue/Problem/Warning keywords
        const keywordMatches = text.match(/^(Issue|Problem|Warning|Error|Bug|Concern)[\s:#-]/gmi);
        if (keywordMatches && keywordMatches.length > 0) {
            return { pattern: 'keyword', count: keywordMatches.length, regex: /^(Issue|Problem|Warning|Error|Bug|Concern)[\s:#-]/gmi };
        }

        // If still no pattern found but has substantial content, count as 1
        if (text.trim().length > 100) {
            return { pattern: 'single', count: 1, regex: null };
        }

        return { pattern: null, count: 0, regex: null };
    }

    countIssues(data) {
        if (!data) return 0;

        // Handle structured data
        if (typeof data === 'object' && data.findings) {
            return data.findings.length;
        }

        // Handle string data (fallback or legacy)
        if (typeof data === 'string') {
            if (data === 'No issues found' || data.trim() === '' || data.startsWith('Skipped:')) {
                return 0;
            }

            const result = this.detectIssuePattern(data);

            // Debug logging to help track issue counting
            if (result.count > 0) {
                console.log(`[Issue Count] Pattern: ${result.pattern}, Count: ${result.count}`);
            }

            return result.count;
        }

        return 0;
    }

    updateDetailedReport(elementId, data) {
        const element = document.getElementById(elementId);
        if (!element) return;

        if (!data) {
            element.innerHTML = '<div class="no-findings-pro">No analysis data available for this stage.</div>';
            return;
        }

        // Handle string data (standard markdown report)
        if (typeof data === 'string' || (typeof data === 'object' && !data.findings)) {
            const content = typeof data === 'string' ? data : (data.summary || '');

            if (content === 'No issues found' || content.trim() === '' || content.startsWith('Skipped:')) {
                element.innerHTML = `
                    <div class="no-issues-placeholder-pro">
                        <div class="placeholder-icon">✅</div>
                        <div class="placeholder-text">
                            <h4>Quality Standard Met</h4>
                            <p>No issues were identified in this category. The code follows recommended practices.</p>
                        </div>
                    </div>`;
            } else {
                element.innerHTML = `
                    <div class="markdown-report-container">
                        <div class="report-actions-overlay">
                            <button class="copy-report-minimal" onclick="app.copyText('${this.escapeHtml(content).replace(/'/g, "\\'")}')" title="Copy Raw Markdown">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M4 1.5H3a2 2 0 00-2 2V14a2 2 0 002 2h10a2 2 0 002-2V3.5a2 2 0 00-2-2h-1v1h1a1 1 0 011 1V14a1 1 0 01-1 1H3a1 1 0 01-1-1V3.5a1 1 0 011-1h1v-1z"/></svg>
                                Copy Markdown
                            </button>
                        </div>
                        ${this.highlightCodeInReport(content)}
                    </div>`;
            }
            return;
        }

        // Handle structured data (legacy support)
        if (typeof data === 'object' && data.findings) {
            let html = '';

            if (data.summary) {
                html += `<div class="stage-summary-pro">${this.highlightCodeInReport(data.summary)}</div>`;
            }

            if (data.findings.length > 0) {
                html += '<div class="findings-list-pro">';
                data.findings.forEach((finding, index) => {
                    const severityClass = finding.severity ? finding.severity.toLowerCase() : 'low';
                    html += `
                        <div class="finding-item-pro severity-${severityClass}">
                            <div class="finding-item-header">
                                <div class="finding-item-title">
                                    <span class="finding-number">#${index + 1}</span>
                                    ${this.escapeHtml(finding.title)}
                                </div>
                                <span class="finding-severity-badge severity-${severityClass}">${this.escapeHtml(finding.severity)}</span>
                            </div>
                            <div class="finding-item-location">
                                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                                    <path d="M1 3.5A1.5 1.5 0 012.5 2h2.764c.958 0 1.76.56 2.311 1.184C7.985 3.648 8.48 4 9 4h4.5A1.5 1.5 0 0115 5.5v7a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12.5v-9z"/>
                                </svg>
                                <span class="file-path">${this.escapeHtml(finding.file)}</span>
                                <span class="line-number-label">Line ${finding.line}</span>
                            </div>
                            <div class="finding-item-description">
                                ${this.highlightCodeInReport(finding.description)}
                            </div>
                            ${finding.suggestion ? `
                            <div class="finding-item-suggestion">
                                <div class="suggestion-label">💡 Suggestion:</div>
                                <div class="suggestion-content">${this.highlightCodeInReport(finding.suggestion)}</div>
                            </div>` : ''}
                        </div>
                    `;
                });
                html += '</div>';
            } else if (data.status === 'success') {
                html += '<div class="no-issues-placeholder">✅ No specific findings or issues detected in this category.</div>';
            } else if (data.status === 'skipped') {
                html += '<div class="skipped-placeholder">ℹ️ This analysis stage was skipped.</div>';
            } else if (data.status === 'error') {
                html += `<div class="error-placeholder">❌ Analysis failed: ${this.escapeHtml(data.error_message || 'Unknown error')}</div>`;
            } else if (!data.summary) {
                html += '<div class="no-issues-placeholder">No issues found in this category.</div>';
            }

            element.innerHTML = html;
        }
    }

    highlightCodeInReport(text) {
        if (!text) return '';

        // Special case for "Skipped" message
        if (text.startsWith('Skipped:')) {
            return `<div class="skipped-message-pro">${text}</div>`;
        }

        let escaped = this.escapeHtml(text);

        // Convert code blocks with syntax highlighting
        escaped = escaped.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            const language = lang || 'javascript';
            const codeId = 'code-' + Math.random().toString(36).substr(2, 9);

            // Add line numbers to code
            const lines = code.trim().split('\n');
            const numberedCode = lines.map((line, i) =>
                `<div class="code-line"><span class="line-number">${i + 1}</span>${line}</div>`
            ).join('');

            return `<div class="code-snippet-container">
                <div class="code-snippet-header">
                    <span class="code-snippet-lang">${language.toUpperCase()}</span>
                    <button class="code-snippet-copy" onclick="app.copyCodeSnippet('${codeId}')" title="Copy code">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25v-7.5z"/>
                            <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 1.75 0 015 9.25v-7.5zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25v-7.5z"/>
                        </svg>
                    </button>
                </div>
                <pre class="code-snippet-body"><code id="${codeId}" class="language-${language}">${numberedCode}</code></pre>
            </div>`;
        });

        // Convert markdown headers
        escaped = escaped.replace(/^####\s+(.*)$/gm, '<h4 class="md-h4">$1</h4>');
        escaped = escaped.replace(/^###\s+(.*)$/gm, '<h3 class="md-h3">$1</h3>');
        escaped = escaped.replace(/^##\s+(.*)$/gm, '<h2 class="md-h2">$1</h2>');
        escaped = escaped.replace(/^#\s+(.*)$/gm, '<h1 class="md-h1">$1</h1>');

        // Convert markdown blockquotes
        escaped = escaped.replace(/^>\s+(.*)$/gm, '<blockquote class="md-blockquote">$1</blockquote>');

        // Convert markdown lists
        let inList = false;
        const lines = escaped.split('\n');
        const processedLines = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const bulletMatch = line.match(/^[-*•]\s+(.*)$/);
            const numberMatch = line.match(/^\d+\.\s+(.*)$/);

            if (bulletMatch) {
                if (!inList || inList === 'ol') {
                    if (inList === 'ol') processedLines.push('</ol>');
                    processedLines.push('<ul class="md-ul">');
                    inList = 'ul';
                }
                processedLines.push(`<li>${bulletMatch[1]}</li>`);
            } else if (numberMatch) {
                if (!inList || inList === 'ul') {
                    if (inList === 'ul') processedLines.push('</ul>');
                    processedLines.push('<ol class="md-ol">');
                    inList = 'ol';
                }
                processedLines.push(`<li>${numberMatch[1]}</li>`);
            } else {
                if (inList) {
                    processedLines.push(inList === 'ul' ? '</ul>' : '</ol>');
                    inList = false;
                }
                processedLines.push(line);
            }
        }
        if (inList) {
            processedLines.push(inList === 'ul' ? '</ul>' : '</ol>');
        }
        escaped = processedLines.join('\n');

        // Inline formatting
        escaped = escaped.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // File references
        escaped = escaped.replace(/([a-zA-Z0-9_\-\/\.]+\.[a-zA-Z0-9]+):(\d+)/g,
            '<span class="file-reference"><span class="file-name">$1</span><span class="line-ref">:$2</span></span>');

        // Professional Panel Boxes
        escaped = escaped.replace(/^(ℹ️|⚠️|❌|✅|💡)\s+(.*)$/gm, (match, emoji, text) => {
            const typeMap = { 'ℹ️': 'info', '⚠️': 'warning', '❌': 'error', '✅': 'success', '💡': 'tip' };
            const type = typeMap[emoji] || 'info';
            return `<div class="md-panel panel-${type}"><div class="panel-icon">${emoji}</div><div class="panel-content">${text}</div></div>`;
        });

        // Severity indicators
        escaped = escaped.replace(/^(🔴|🟠|🟡|🟢)\s+(.*)$/gm,
            '<div class="md-severity-row"><span class="severity-bullet">$1</span><span class="severity-text">$2</span></div>');

        // Horizontal rules
        escaped = escaped.replace(/^---+$/gm, '<hr class="md-hr">');

        // Wrap paragraphs
        escaped = escaped.split('\n').map(line => {
            const trimmed = line.trim();
            if (!trimmed) return '';
            if (trimmed.startsWith('<') || trimmed.endsWith('>') || trimmed.includes('</')) return trimmed;
            return `<p class="md-p">${trimmed}</p>`;
        }).join('\n');

        return escaped;
    }

    escapeHtml(text) {
        if (!text) return '';
        return text.toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    copyText(text) {
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            this.showSuccess('Copied to clipboard');
        }).catch(err => {
            console.error('Failed to copy text:', err);
            this.showError('Failed to copy to clipboard');
        });
    }

    renderRecommendationsHub(results) {
        const hubEl = document.getElementById('recommendationsHub');
        const snippets = results.all_snippets || [];
        const findings = results.all_findings || [];

        if (hubEl) {
            hubEl.style.display = (snippets.length > 0 || findings.length > 0) ? 'block' : 'none';
        }

        // Update badges
        document.getElementById('suggestionsBadge').textContent = snippets.length;
        const criticalCount = findings.filter(f => f.severity === 'critical' || f.severity === 'high').length;
        document.getElementById('criticalBadge').textContent = criticalCount;

        // Render Suggestions Grid
        const grid = document.getElementById('suggestionsGrid');
        if (grid) {
            if (snippets.length === 0) {
                grid.innerHTML = '<div class="empty-hub-state">No specific code suggestions extracted. Review the detailed reports for general advice.</div>';
            } else {
                grid.innerHTML = snippets.map(snip => `
                    <div class="suggestion-card-pro">
                        <div class="suggestion-card-header">
                            <span class="suggestion-stage-badge stage-${snip.stage}">${snip.stage.toUpperCase()}</span>
                            <span class="suggestion-lang-badge">${snip.language.toUpperCase()}</span>
                        </div>
                        <div class="suggestion-card-body">
                            <div class="code-snippet-container">
                                <div class="code-snippet-header">
                                    <span class="code-snippet-lang">SUGGESTED CHANGE</span>
                                    <button class="code-snippet-copy" onclick="app.copyCodeSnippet('${snip.id}')" title="Copy Suggestion">
                                        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                            <path d="M4 1.5H3a2 2 0 00-2 2V14a2 2 0 002 2h10a2 2 0 002-2V3.5a2 2 0 00-2-2h-1v1h1a1 1 0 011 1V14a1 1 0 01-1 1H3a1 1 0 01-1-1V3.5a1 1 0 011-1h1v-1z"/>
                                        </svg>
                                    </button>
                                </div>
                                <pre class="code-snippet-body"><code id="${snip.id}" class="language-${snip.language}">${this.formatNumberedCode(snip.content)}</code></pre>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }

        // Render Critical Findings
        const critList = document.getElementById('criticalFindingsList');
        if (critList) {
            const highPrio = findings.filter(f => f.severity === 'critical' || f.severity === 'high');
            if (highPrio.length === 0) {
                critList.innerHTML = '<div class="empty-hub-state">No critical or high-priority findings detected. Good job!</div>';
            } else {
                critList.innerHTML = highPrio.map(fnd => `
                    <div class="critical-finding-item-pro severity-${fnd.severity}">
                        <div class="crit-icon">${fnd.severity === 'critical' ? '🔴' : '🟠'}</div>
                        <div class="crit-content">
                            <div class="crit-header">
                                <span class="crit-stage">${fnd.stage.toUpperCase()}</span>
                                <h4 class="crit-title">${this.escapeHtml(fnd.title)}</h4>
                            </div>
                            <div class="crit-desc">${this.highlightCodeInReport(fnd.description)}</div>
                        </div>
                    </div>
                `).join('');
            }
        }
    }

    formatNumberedCode(code) {
        if (!code) return '';
        const lines = code.trim().split('\n');
        return lines.map((line, i) =>
            `<div class="code-line"><span class="line-number">${i + 1}</span>${this.escapeHtml(line)}</div>`
        ).join('');
    }

    switchHubTab(tabId) {
        // Update buttons
        document.querySelectorAll('.hub-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('onclick').includes(tabId));
        });

        // Update content
        document.querySelectorAll('.hub-content').forEach(content => {
            content.classList.toggle('active', content.id === `hub-${tabId}`);
        });
    }

    copyCodeSnippet(codeId) {
        const codeElement = document.getElementById(codeId);
        if (!codeElement) return;

        // Extract only the code content without line numbers
        const codeLines = codeElement.querySelectorAll('.code-line');
        const code = Array.from(codeLines).map(line => {
            // Remove the line number span and get only the code text
            const lineNumber = line.querySelector('.line-number');
            if (lineNumber) {
                return line.textContent.replace(lineNumber.textContent, '').trimStart();
            }
            return line.textContent;
        }).join('\n');

        navigator.clipboard.writeText(code).then(() => {
            // Find the copy button for this code block
            const container = codeElement.closest('.code-snippet-container');
            const copyButton = container?.querySelector('.code-snippet-copy');

            if (copyButton) {
                const originalHTML = copyButton.innerHTML;
                copyButton.innerHTML = `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/>
                </svg>`;
                copyButton.style.color = '#10b981';
                copyButton.title = 'Copied!';

                setTimeout(() => {
                    copyButton.innerHTML = originalHTML;
                    copyButton.style.color = '';
                    copyButton.title = 'Copy code';
                }, 2000);
            }
        }).catch(err => {
            console.error('Failed to copy code:', err);
            this.showError('Failed to copy code to clipboard');
        });
    }

    updateAnalysisBrowser(results) {
        if (!results) return;

        // Update Sidebar Badges
        const stages = ['security', 'bugs', 'quality', 'performance', 'tests'];
        stages.forEach(stage => {
            const data = stage === 'quality' ? results.style : results[stage];
            const badge = document.getElementById(`cat-badge-${stage}`);
            const count = this.countIssues(data);
            if (badge) {
                if (count > 0) {
                    badge.textContent = count;
                    badge.style.display = 'inline-flex';
                } else {
                    badge.style.display = 'none';
                }
                const item = document.getElementById(`cat-${stage}`);
                if (item) item.classList.toggle('has-issues', count > 0);
            }
        });

        // Handle Target Branch visibility
        const targetBtn = document.getElementById('cat-target-branch');
        if (targetBtn) {
            targetBtn.style.display = results.target_branch_analysis ? 'flex' : 'none';
        }

        // Update prompt versions from results if available
        if (results.token_usage) {
            stages.forEach(stage => {
                const metaEl = document.getElementById(`cat-meta-${stage}`);
                if (metaEl && results.token_usage[stage]) {
                    const model = results.token_usage[stage].model || 'AI';
                    metaEl.textContent = model.replace('gpt-', '').replace('claude-', '');
                }
            });
        }

        // Auto-select first active category if nothing is selected or keep current
        const activeItem = document.querySelector('.category-item.active');
        if (activeItem && activeItem.style.display !== 'none') {
            const currentStage = activeItem.id.replace('cat-', '');
            this.switchAnalysisCategory(currentStage);
        } else {
            this.switchAnalysisCategory('security');
        }
    }

    switchAnalysisCategory(category) {
        // Update active class on sidebar
        document.querySelectorAll('.category-item').forEach(item => {
            item.classList.toggle('active', item.id === `cat-${category}`);
        });

        if (!this.currentReview) return;

        const viewerContent = document.getElementById('activeReportViewer');
        const titleEl = document.getElementById('viewerTitle');
        const subtitleEl = document.getElementById('viewerSubtitle');
        const countEl = document.getElementById('viewerIssueCount');
        const severityEl = document.getElementById('viewerSeverityText');

        if (!viewerContent || !titleEl) return;

        // Clear search state when switching
        if (viewerContent.dataset.originalHtml) {
            viewerContent.innerHTML = viewerContent.dataset.originalHtml;
            delete viewerContent.dataset.originalHtml;
        }
        const searchInput = document.getElementById('reportSearchInput');
        if (searchInput) searchInput.value = '';
        document.querySelectorAll('.category-item').forEach(btn => btn.style.opacity = '1');

        // Map categories to titles/subtitles
        const meta = {
            'security': { title: 'Security Analysis', subtitle: 'Vulnerability detection and threat mitigation' },
            'bugs': { title: 'Bug Detection', subtitle: 'Logic errors, edge cases, and runtime risks' },
            'quality': { title: 'Code Quality', subtitle: 'Maintainability, style, and best practices' },
            'performance': { title: 'Performance Analysis', subtitle: 'Optimization opportunities and resource leaks' },
            'tests': { title: 'Test Suggestions', subtitle: 'Coverage gaps and unit test recommendations' },
            'target-branch': { title: 'Base Branch Context', subtitle: 'Comparison with target branch architecture' }
        };

        const config = meta[category] || meta['security'];
        titleEl.textContent = config.title;
        subtitleEl.textContent = config.subtitle;

        // Get data
        let stageData = null;
        if (category === 'security') stageData = this.currentReview.security;
        else if (category === 'bugs') stageData = this.currentReview.bugs;
        else if (category === 'quality') stageData = this.currentReview.style;
        else if (category === 'performance') stageData = this.currentReview.performance;
        else if (category === 'tests') stageData = this.currentReview.tests;
        else if (category === 'target-branch') stageData = this.currentReview.target_branch_analysis;

        // Render content
        const content = typeof stageData === 'string' ? stageData : (stageData?.summary || '');

        if (!content || content.startsWith('Skipped:')) {
            viewerContent.innerHTML = `<div class="no-issues-placeholder-pro">
                <div class="placeholder-icon">✅</div>
                <div class="placeholder-text">
                    <h4>No issues identified</h4>
                    <p>This category passed all automated checks with no findings to report.</p>
                </div>
            </div>`;
            if (countEl) countEl.parentElement.style.display = 'none';
            if (severityEl) severityEl.parentElement.style.display = 'none';
        } else {
            // Apply animation class
            viewerContent.classList.remove('active-report-pane');
            void viewerContent.offsetWidth; // Trigger reflow
            viewerContent.classList.add('active-report-pane');

            viewerContent.innerHTML = `
                <div class="markdown-report-container">
                    <div class="report-actions-overlay">
                        <button class="copy-report-minimal" onclick="app.copyText('${this.escapeHtml(content).replace(/'/g, "\\'").replace(/\n/g, "\\n")}')">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M4 1.5H3a2 2 0 00-2 2V14a2 2 0 002 2h10a2 2 0 002-2V3.5a2 2 0 00-2-2h-1v1h1a1 1 0 011 1V14a1 1 0 01-1 1H3a1 1 0 01-1-1V3.5a1 1 0 011-1h1v-1z"/></svg>
                            Copy Markdown
                        </button>
                    </div>
                    ${this.highlightCodeInReport(content)}
                </div>`;

            // Update metadata
            const issueCount = this.countIssues(stageData);

            if (countEl) {
                if (issueCount > 0) {
                    countEl.textContent = issueCount;
                    countEl.parentElement.style.display = 'flex';
                } else {
                    countEl.parentElement.style.display = 'none';
                }
            }

            if (severityEl) {
                const sev = this.determineSeverity(stageData, issueCount);
                if (issueCount > 0 && sev.label !== 'None') {
                    severityEl.textContent = sev.label;
                    severityEl.className = `pill-value severity-${sev.class}`;
                    severityEl.parentElement.style.display = 'flex';
                } else {
                    severityEl.parentElement.style.display = 'none';
                }
            }
        }
    }

    copyAllReports() {
        if (!this.currentReview) {
            this.showError('No review data available to copy');
            return;
        }

        // Use the comprehensive markdown generator for a complete export
        const fullReport = this.generateMarkdownReport();
        this.copyText(fullReport);
    }

    searchInReport(searchText) {
        // Get current active report
        const activePane = document.querySelector('.tab-pane-pro.active');
        if (!activePane) return;

        const reportContent = activePane.querySelector('.report-content-pro');
        if (!reportContent) return;

        const clearBtn = document.getElementById('clearSearchBtn');

        // Show/hide clear button
        if (searchText) {
            clearBtn.style.display = 'flex';
        } else {
            clearBtn.style.display = 'none';
            // Reset highlighting
            this.clearSearch();
            return;
        }

        // Get original HTML content (stored as data attribute)
        if (!reportContent.dataset.originalHtml) {
            reportContent.dataset.originalHtml = reportContent.innerHTML;
        }

        const originalHtml = reportContent.dataset.originalHtml;

        if (!searchText.trim()) {
            reportContent.innerHTML = originalHtml;
            return;
        }

        // Create a temporary div to work with the HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = originalHtml;

        // Create regex for highlighting
        const regex = new RegExp(searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');

        // Recursively highlight text nodes
        this.highlightTextNodes(tempDiv, regex);

        reportContent.innerHTML = tempDiv.innerHTML;

        // Scroll to first match
        const firstMatch = reportContent.querySelector('.search-highlight');
        if (firstMatch) {
            firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    highlightTextNodes(element, regex) {
        // Walk through all child nodes
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        const nodesToReplace = [];
        let node;

        while (node = walker.nextNode()) {
            if (regex.test(node.textContent)) {
                nodesToReplace.push(node);
            }
        }

        // Replace text nodes with highlighted HTML
        nodesToReplace.forEach(node => {
            const span = document.createElement('span');
            span.innerHTML = node.textContent.replace(regex, '<mark class="search-highlight">$&</mark>');
            node.parentNode.replaceChild(span, node);
        });
    }

    clearSearch() {
        const searchInput = document.getElementById('reportSearchInput');
        const clearBtn = document.getElementById('clearSearchBtn');
        const activePane = document.querySelector('.tab-pane-pro.active');

        if (searchInput) searchInput.value = '';
        if (clearBtn) clearBtn.style.display = 'none';

        if (activePane) {
            const reportContent = activePane.querySelector('.report-content-pro');
            if (reportContent && reportContent.dataset.originalHtml) {
                reportContent.innerHTML = reportContent.dataset.originalHtml;
            }
        }
    }

    // Table View Functions
    updateReportsTable(results) {
        const stages = [
            { id: 'security', data: results.security, name: 'Security Analysis' },
            { id: 'bugs', data: results.bugs, name: 'Bug Detection' },
            { id: 'quality', data: results.style, name: 'Code Quality' },
            { id: 'performance', data: results.performance, name: 'Performance Analysis' },
            { id: 'tests', data: results.tests, name: 'Test Suggestions' }
        ];

        stages.forEach(stage => {
            const count = this.countIssues(stage.data);
            const severity = this.determineSeverity(stage.data, count);

            const countEl = document.getElementById(`${stage.id}IssueCount`);
            const severityEl = document.getElementById(`${stage.id}Severity`);

            if (countEl) countEl.textContent = count;
            if (severityEl) {
                severityEl.textContent = severity.label;
                severityEl.className = `severity-badge ${severity.class}`;
            }
        });

        // Handle target branch if present
        if (results.target_branch_analysis) {
            const targetBranchRow = document.getElementById('targetBranchRow');
            const targetBranchDetailsRow = document.getElementById('targetBranchDetailsRow');
            if (targetBranchRow) targetBranchRow.style.display = '';
            if (targetBranchDetailsRow) targetBranchDetailsRow.style.display = 'none';

            const countEl = document.getElementById('targetBranchIssueCount');
            if (countEl) countEl.textContent = this.countIssues(results.target_branch_analysis);

            this.updateDetailedReport('targetBranchDetails', results.target_branch_analysis);
        }
    }

    determineSeverity(data, count) {
        if (!data || count === 0) return { label: 'Low', class: 'low' };

        // Handle structured data
        if (typeof data === 'object' && data.findings && data.findings.length > 0) {
            const severities = data.findings.map(f => (f.severity || '').toLowerCase());
            if (severities.includes('critical')) return { label: 'Critical', class: 'critical' };
            if (severities.includes('high')) return { label: 'High', class: 'high' };
            if (severities.includes('medium')) return { label: 'Medium', class: 'medium' };
            return { label: 'Low', class: 'low' };
        }

        // Handle string data (fallback or from summary)
        let text = '';
        if (typeof data === 'string') {
            text = data.toLowerCase();
        } else if (typeof data === 'object' && data.summary) {
            text = data.summary.toLowerCase();
        } else {
            return { label: 'Low', class: 'low' };
        }

        if (text.includes('🔴') || text.includes('critical')) {
            return { label: 'Critical', class: 'critical' };
        }
        if (text.includes('🟠') || text.includes('high priority')) {
            return { label: 'High', class: 'high' };
        }
        if (text.includes('🟡') || text.includes('medium')) {
            return { label: 'Medium', class: 'medium' };
        }
        if (count > 0) {
            return { label: 'Low', class: 'low' };
        }

        return { label: 'Info', class: 'info' };
    }

    toggleReportRow(stage) {
        if (!this.currentReview) return;

        // Map stage names to data keys
        const stageKeyMap = {
            'target-branch': 'target_branch_analysis',
            'security': 'security',
            'bugs': 'bugs',
            'quality': 'style',
            'performance': 'performance',
            'tests': 'tests'
        };

        const key = stageKeyMap[stage];
        if (!key) return;

        const data = this.currentReview[key];
        const stageInfo = this.getStageInfo(stage);

        // If it's structured data, we'll handle it specially in openAnalysisModal
        this.openAnalysisModal(stage, data, stageInfo.title, stageInfo.subtitle);
    }

    getStageInfo(stage) {
        const stageMap = {
            'target-branch': {
                title: 'Target Branch Analysis',
                subtitle: 'Branch comparison and impact assessment',
                icon: '<path d="M5 3a2 2 0 0 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 0 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 0 0 0 4 2 2 0 0 0 0-4zm9-12a2 2 0 0 0 0 4 2 2 0 0 0 0-4z"/>',
                color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            },
            'security': {
                title: 'Security Analysis',
                subtitle: 'Comprehensive security vulnerability assessment',
                icon: '<path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5zm0 10l-4 4-1.41-1.41L9.17 12l-2.58-2.59L8 8l4 4z"/>',
                color: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
            },
            'bugs': {
                title: 'Bug Analysis',
                subtitle: 'Potential issues and error detection',
                icon: '<path d="M20 8h-2.81c-.45-.78-1.07-1.45-1.82-1.96L17 4.41 15.59 3l-2.17 2.17C12.96 5.06 12.49 5 12 5c-.49 0-.96.06-1.41.17L8.41 3 7 4.41l1.62 1.63C7.88 6.55 7.26 7.22 6.81 8H4v2h2.09c-.05.33-.09.66-.09 1v1H4v2h2v1c0 .34.04.67.09 1H4v2h2.81c1.04 1.79 2.97 3 5.19 3s4.15-1.21 5.19-3H20v-2h-2.09c.05-.33.09-.66.09-1v-1h2v-2h-2v-1c0-.34-.04-.67-.09-1H20V8zm-6 8h-4v-2h4v2zm0-4h-4v-2h4v2z"/>',
                color: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
            },
            'quality': {
                title: 'Code Quality Analysis',
                subtitle: 'Style, maintainability, and best practices review',
                icon: '<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>',
                color: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
            },
            'performance': {
                title: 'Performance Analysis',
                subtitle: 'Optimization opportunities and efficiency insights',
                icon: '<path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>',
                color: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'
            },
            'tests': {
                title: 'Test Analysis',
                subtitle: 'Test coverage and quality assessment',
                icon: '<path d="M19.5 3.5L18 2l-1.5 1.5L15 2l-1.5 1.5L12 2l-1.5 1.5L9 2 7.5 3.5 6 2v14H3v3c0 1.66 1.34 3 3 3h12c1.66 0 3-1.34 3-3V2l-1.5 1.5zM19 19c0 .55-.45 1-1 1s-1-.45-1-1v-3H8V5h11v14z"/><path d="M9 7h6v2H9zm0 4h6v2H9z"/>',
                color: 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
            }
        };

        return stageMap[stage] || {
            title: 'Analysis Report',
            subtitle: 'Detailed analysis results',
            icon: '<path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>',
            color: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)'
        };
    }

    openAnalysisModal(stage, data, title, subtitle) {
        const modal = document.getElementById('analysisModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalSubtitle = document.getElementById('modalSubtitle');
        const modalContent = document.getElementById('modalContent');
        const modalIcon = document.getElementById('modalIcon');
        const modalFooter = document.getElementById('modalFooter');

        if (!modal) return;

        // Reset state
        this.currentModalIssues = [];
        this.currentIssueIndex = 0;
        this.currentModalStage = stage;
        this.currentModalData = data; // Store the original data object

        // Handle data based on type
        if (typeof data === 'string') {
            this.currentModalIssues = this.parseIssuesFromContent(data);
        } else if (typeof data === 'object' && data.findings) {
            this.currentModalIssues = data.findings;
        }

        // Set modal header
        modalTitle.textContent = title;
        modalSubtitle.textContent = subtitle;

        // Set icon and color
        const stageInfo = this.getStageInfo(stage);
        modalIcon.style.background = stageInfo.color;
        modalIcon.querySelector('svg').innerHTML = stageInfo.icon;

        // Show first issue or summary if no findings
        if (this.currentModalIssues.length > 0) {
            this.showIssueAtIndex(0);
            modalFooter.style.display = 'block';
        } else {
            const content = typeof data === 'string' ? data : (data.summary || 'No issues found.');
            modalContent.innerHTML = `<div class="modal-summary-only">${this.highlightCodeInReport(content)}</div>`;
            modalFooter.style.display = 'none';
        }

        // Show modal
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Setup ESC key to close
        this.modalEscHandler = (e) => {
            if (e.key === 'Escape') {
                this.closeAnalysisModal();
            }
        };
        document.addEventListener('keydown', this.modalEscHandler);
    }

    parseIssuesFromContent(content) {
        if (!content) return [];
        if (typeof content !== 'string') return [];

        // If content is already HTML formatted (unlikely here but just in case), 
        // extract text for pattern detection
        let rawText = content;
        if (content.includes('<') && content.includes('>')) {
            const temp = document.createElement('div');
            temp.innerHTML = content;
            rawText = temp.textContent || temp.innerText;
        }

        // Use the same pattern detection logic as countIssues
        const patternResult = this.detectIssuePattern(rawText);

        // Debug logging
        console.log(`[Parse Issues] Pattern: ${patternResult.pattern}, Expected Count: ${patternResult.count}`);

        // If no pattern detected or count is 0 or 1, return entire content
        if (!patternResult.pattern || patternResult.count <= 1) {
            console.log(`[Parse Issues] Returning single block (no split needed)`);
            return [content];
        }

        // Split content based on the detected pattern
        let issueBlocks = [];

        switch (patternResult.pattern) {
            case 'numbered':
                issueBlocks = this.splitByPattern(content, /(?=^\s*\d+\.\s+)/gm);
                break;
            case 'bullet':
                issueBlocks = this.splitByPattern(content, /(?=^\s*[-*•]\s+)/gm);
                break;
            case 'header':
                issueBlocks = this.splitByPattern(content, /(?=^#{2,4}\s+)/gm);
                break;
            case 'severity':
                issueBlocks = this.splitByPattern(content, /(?=^[🔴🟠🟡🟢]\s+)/gm);
                break;
            case 'keyword':
                issueBlocks = this.splitByPattern(content, /(?=^(?:Issue|Problem|Warning|Error|Bug|Concern)[\s:#-])/gmi);
                break;
            default:
                return [content];
        }

        // Filter out empty blocks
        const filteredIssues = issueBlocks
            .map(block => block.trim())
            .filter(block => {
                // Remove HTML to check if block has actual content
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = block;
                const text = (tempDiv.textContent || tempDiv.innerText || '').trim();
                return text.length > 0;
            });

        // Debug logging for verification
        console.log(`[Parse Issues] Actual Split Count: ${filteredIssues.length}`);

        // Verify count matches
        if (filteredIssues.length !== patternResult.count) {
            console.warn(`[Parse Issues] Count mismatch! Expected ${patternResult.count} but got ${filteredIssues.length}`);
        }

        // If we found multiple issues, return them
        if (filteredIssues.length > 1) {
            return filteredIssues;
        }

        // Otherwise, return the entire content as a single issue
        return [content];
    }

    splitByPattern(content, pattern) {
        // Convert HTML to text while preserving structure
        const lines = content.split('\n');
        const blocks = [];
        let currentBlock = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const testLine = line.replace(/<[^>]*>/g, '').trim(); // Remove HTML tags for testing

            // Check if line matches the pattern
            if (pattern.test(testLine) && currentBlock.length > 0) {
                // Start a new block
                blocks.push(currentBlock.join('\n'));
                currentBlock = [line];
            } else {
                currentBlock.push(line);
            }
        }

        // Add the last block
        if (currentBlock.length > 0) {
            blocks.push(currentBlock.join('\n'));
        }

        return blocks;
    }

    showIssueAtIndex(index) {
        if (!this.currentModalIssues || index < 0 || index >= this.currentModalIssues.length) return;

        this.currentIssueIndex = index;
        const modalContent = document.getElementById('modalContent');
        const pageInfo = document.getElementById('pageInfo');
        const prevBtn = document.getElementById('prevIssueBtn');
        const nextBtn = document.getElementById('nextIssueBtn');

        const issue = this.currentModalIssues[index];
        let html = '';

        if (typeof issue === 'object') {
            // Structured finding
            const severityClass = (issue.severity || 'low').toLowerCase();
            html = `
                <div class="modal-finding">
                    <div class="modal-finding-header">
                        <span class="modal-finding-badge severity-${severityClass}">${this.escapeHtml(issue.severity || 'Low')}</span>
                        <h4 class="modal-finding-title">${this.escapeHtml(issue.title)}</h4>
                    </div>
                    <div class="modal-finding-location">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M1 3.5A1.5 1.5 0 012.5 2h2.764c.958 0 1.76.56 2.311 1.184C7.985 3.648 8.48 4 9 4h4.5A1.5 1.5 0 0115 5.5v7a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12.5v-9z"/>
                        </svg>
                        <span class="modal-file-path">${this.escapeHtml(issue.file)}</span>
                        <span class="modal-line-number">Line ${issue.line}</span>
                    </div>
                    <div class="modal-finding-description">
                        ${this.highlightCodeInReport(issue.description)}
                    </div>
                    ${issue.suggestion ? `
                    <div class="modal-finding-suggestion">
                        <div class="modal-suggestion-label">💡 Recommendation</div>
                        <div class="modal-suggestion-content">
                            ${this.highlightCodeInReport(issue.suggestion)}
                        </div>
                    </div>` : ''}
                </div>
            `;
        } else {
            // String issue (from legacy parsing)
            html = `<div class="modal-finding-legacy">${this.highlightCodeInReport(issue)}</div>`;
        }

        modalContent.innerHTML = html;

        // Update pagination info
        if (pageInfo) {
            pageInfo.textContent = `Finding ${index + 1} of ${this.currentModalIssues.length}`;
        }

        // Update button states
        if (prevBtn) prevBtn.disabled = (index === 0);
        if (nextBtn) nextBtn.disabled = (index === this.currentModalIssues.length - 1);

        // Scroll modal to top
        modalContent.scrollTop = 0;
    }

    showPreviousIssue() {
        if (this.currentIssueIndex > 0) {
            this.showIssueAtIndex(this.currentIssueIndex - 1);
        }
    }

    showNextIssue() {
        if (this.currentIssueIndex < this.currentModalIssues.length - 1) {
            this.showIssueAtIndex(this.currentIssueIndex + 1);
        }
    }

    closeAnalysisModal() {
        const modal = document.getElementById('analysisModal');
        if (!modal) return;

        modal.classList.remove('active');
        document.body.style.overflow = '';

        // Remove ESC key listener
        if (this.modalEscHandler) {
            document.removeEventListener('keydown', this.modalEscHandler);
            this.modalEscHandler = null;
        }

        // Clear pagination state
        this.currentModalStage = null;
        this.currentModalIssues = [];
        this.currentIssueIndex = 0;
    }

    copyModalContent() {
        if (!this.currentModalStage) return;

        const modalContent = document.getElementById('modalContent');
        if (!modalContent) return;

        // Get text content, preserving structure
        const text = modalContent.innerText || modalContent.textContent;

        navigator.clipboard.writeText(text).then(() => {
            // Show success feedback on copy button
            const copyBtn = document.querySelector('.analysis-modal .modal-action-btn');
            if (copyBtn) {
                const originalHTML = copyBtn.innerHTML;
                copyBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>';
                copyBtn.style.color = '#10b981';

                setTimeout(() => {
                    copyBtn.innerHTML = originalHTML;
                    copyBtn.style.color = '';
                }, 2000);
            }

            this.showToast('Report copied to clipboard!', 'success');
        }).catch(err => {
            this.showToast('Failed to copy report', 'error');
        });
    }

    copyStageReport(stage) {
        if (!this.currentReview) return;

        // Map UI stage names to internal data names
        const internalStageMap = {
            'security': 'security',
            'bugs': 'bugs',
            'quality': 'style',
            'performance': 'performance',
            'tests': 'tests',
            'target-branch': 'target_branch_analysis'
        };

        const internalStage = internalStageMap[stage] || stage;
        const data = this.currentReview[internalStage];

        if (!data) {
            this.showToast('No report data to copy', 'error');
            return;
        }

        let text = '';
        if (typeof data === 'string') {
            text = data;
        } else if (typeof data === 'object') {
            text = data.summary || '';
            if (data.findings && data.findings.length > 0) {
                text += '\n\nFindings:\n' + data.findings.map((f, i) => `${i + 1}. ${f.title}\n${f.description}`).join('\n\n');
            }
        }

        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Report copied to clipboard!', 'success');
        }).catch(err => {
            this.showToast('Failed to copy report', 'error');
        });
    }

    copyAllReports() {
        if (!this.currentReview) return;

        const stages = ['security', 'bugs', 'style', 'performance', 'tests'];
        let allReports = '# Pull Request Review - Detailed Analysis\n\n';

        stages.forEach(stage => {
            const data = this.currentReview[stage];
            if (data) {
                let text = '';
                if (typeof data === 'string') {
                    text = data;
                } else if (typeof data === 'object') {
                    text = data.summary || 'No issues found.';
                    if (data.findings && data.findings.length > 0) {
                        text += '\n\nFindings:\n' + data.findings.map((f, i) => `${i + 1}. ${f.title}\n${f.description}`).join('\n\n');
                    }
                }
                allReports += `\n## ${stage.charAt(0).toUpperCase() + stage.slice(1)}\n${text}\n`;
            }
        });

        navigator.clipboard.writeText(allReports).then(() => {
            this.showToast('All reports copied to clipboard!', 'success');
        }).catch(err => {
            this.showToast('Failed to copy reports', 'error');
        });
    }

    expandAllReports() {
        const detailsRows = document.querySelectorAll('.report-details-row');
        const expandBtns = document.querySelectorAll('.expand-btn');

        detailsRows.forEach(row => {
            row.style.display = 'table-row';
        });

        expandBtns.forEach(btn => {
            btn.classList.add('expanded');
        });
    }

    collapseAllReports() {
        const detailsRows = document.querySelectorAll('.report-details-row');
        const expandBtns = document.querySelectorAll('.expand-btn');

        detailsRows.forEach(row => {
            row.style.display = 'none';
        });

        expandBtns.forEach(btn => {
            btn.classList.remove('expanded');
        });
    }

    searchInReportsTable(searchText) {
        if (!this.currentReview) return;
        const searchLower = searchText.toLowerCase();

        // 1. Update Sidebar visibility/emphasis
        const stages = ['security', 'bugs', 'quality', 'performance', 'tests'];
        stages.forEach(stage => {
            const btn = document.getElementById(`cat-${stage}`);
            if (!btn) return;

            const data = stage === 'quality' ? this.currentReview.style : this.currentReview[stage];
            const content = typeof data === 'string' ? data : (data?.summary || '');
            const stageName = btn.querySelector('.cat-name')?.textContent || '';

            const hasMatch = stageName.toLowerCase().includes(searchLower) || content.toLowerCase().includes(searchLower);
            btn.style.opacity = hasMatch || !searchText ? '1' : '0.4';
            btn.style.transform = (hasMatch && searchText) ? 'scale(1.02)' : 'scale(1)';
        });

        // 2. Search in active view if there's text
        const reportContent = document.getElementById('activeReportViewer');
        if (!reportContent) return;

        if (!reportContent.dataset.originalHtml) {
            reportContent.dataset.originalHtml = reportContent.innerHTML;
        }

        const originalHtml = reportContent.dataset.originalHtml;

        if (!searchText.trim()) {
            reportContent.innerHTML = originalHtml;
            return;
        }

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = originalHtml;
        const regex = new RegExp(searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        this.highlightTextNodes(tempDiv, regex);
        reportContent.innerHTML = tempDiv.innerHTML;

        const firstMatch = reportContent.querySelector('.search-highlight');
        if (firstMatch) {
            firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    clearSearchTable() {
        const searchInput = document.getElementById('reportSearchInput');
        const clearBtn = document.getElementById('clearSearchBtn');
        const rows = document.querySelectorAll('.report-row');

        if (searchInput) searchInput.value = '';
        if (clearBtn) clearBtn.style.display = 'none';

        rows.forEach(row => {
            row.style.display = '';
        });
    }

    updateFindingCardsVisibility() {
        // Map of card IDs to their corresponding toggle IDs
        const cardToggles = {
            'securityCard': 'enableSecurity',
            'bugsCard': 'enableBugs',
            'qualityCard': 'enableStyle',
            'performanceCard': 'enablePerformance',
            'testsCard': 'enableTests'
        };

        Object.entries(cardToggles).forEach(([cardId, toggleId]) => {
            const card = document.getElementById(cardId);
            const toggle = document.getElementById(toggleId);

            if (card && toggle) {
                card.style.display = toggle.checked ? '' : 'none';
            }
        });
    }

    initProgressOrientation() {
        const horizontalTimeline = document.querySelector('.timeline-horizontal');
        const verticalTimeline = document.querySelector('.timeline-vertical');

        // Apply saved orientation preference
        if (this.progressOrientation === 'vertical') {
            if (horizontalTimeline) horizontalTimeline.style.display = 'none';
            if (verticalTimeline) verticalTimeline.style.display = 'flex';
        } else {
            if (horizontalTimeline) horizontalTimeline.style.display = 'flex';
            if (verticalTimeline) verticalTimeline.style.display = 'none';
        }
    }

    toggleProgressOrientation() {
        const horizontalTimeline = document.querySelector('.timeline-horizontal');
        const verticalTimeline = document.querySelector('.timeline-vertical');

        if (this.progressOrientation === 'horizontal') {
            // Switch to vertical
            this.progressOrientation = 'vertical';
            horizontalTimeline.style.display = 'none';
            verticalTimeline.style.display = 'flex';
        } else {
            // Switch to horizontal
            this.progressOrientation = 'horizontal';
            horizontalTimeline.style.display = 'flex';
            verticalTimeline.style.display = 'none';
        }

        // Save preference
        localStorage.setItem('progressOrientation', this.progressOrientation);
    }

    updateCurrentStageDescription(stageName, description) {
        const descSection = document.getElementById('currentStageDescription');
        const titleEl = document.getElementById('currentStageTitle');
        const textEl = document.getElementById('currentStageText');

        if (descSection && titleEl && textEl) {
            titleEl.textContent = stageName;
            textEl.textContent = description;
            descSection.style.display = 'flex';
        }
    }

    hideCurrentStageDescription() {
        const descSection = document.getElementById('currentStageDescription');
        if (descSection) {
            descSection.style.display = 'none';
        }
    }

    setupProgressStickyBehavior() {
        // Remove any existing scroll listener
        if (this.progressScrollListener) {
            window.removeEventListener('scroll', this.progressScrollListener);
        }

        // Create new scroll listener
        this.progressScrollListener = () => {
            const progressSection = document.getElementById('progressSection');
            if (!progressSection || progressSection.classList.contains('hidden')) {
                return;
            }

            // Make sticky when scrolled down more than 100px
            if (window.scrollY > 100) {
                this.makeProgressSticky();
            } else {
                this.removeProgressSticky();
            }
        };

        // Add scroll listener
        window.addEventListener('scroll', this.progressScrollListener);
    }

    makeProgressSticky() {
        const progressSection = document.getElementById('progressSection');
        if (progressSection && !progressSection.classList.contains('sticky')) {
            progressSection.classList.add('sticky');
        }
    }

    removeProgressSticky() {
        const progressSection = document.getElementById('progressSection');
        if (progressSection) {
            progressSection.classList.remove('sticky');
        }
    }

    cleanupProgressStickyBehavior() {
        // Remove scroll listener when review is complete
        if (this.progressScrollListener) {
            window.removeEventListener('scroll', this.progressScrollListener);
            this.progressScrollListener = null;
        }
        this.removeProgressSticky();
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
            timeline: 'timelineChart',
            findingsRadar: 'findingsRadarChart',
            severityDonut: 'severityDonutChart',
            dddTrend: 'dddTrendChart',
            volume: 'volumeChart',
            historySeverity: 'historySeverityChart'
        };
    }

    getChartLayout(title, height = 350) {
        const isDark = document.body.classList.contains('dark-mode');
        const textColor = isDark ? '#f1f5f9' : '#111827';
        const gridColor = isDark ? '#334155' : '#e5e7eb';

        return {
            title: {
                text: `<b>${title}</b>`,
                font: { size: 16, family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto', color: textColor },
                x: 0.05,
                xanchor: 'left'
            },
            height: height,
            margin: { t: 60, b: 50, l: 60, r: 40 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto', size: 12, color: textColor },
            xaxis: {
                gridcolor: gridColor,
                zerolinecolor: gridColor
            },
            yaxis: {
                gridcolor: gridColor,
                zerolinecolor: gridColor
            }
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
        if (!data) {
            console.error('renderCharts: No data provided');
            return;
        }

        console.log('renderCharts: Rendering charts');

        // Helper to safely render if element exists
        const safeRender = (containerKey, renderFn, ...args) => {
            const containerId = this.chartContainers[containerKey];
            if (document.getElementById(containerId)) {
                try {
                    renderFn.call(this, ...args);
                } catch (e) {
                    console.error(`Error rendering ${containerKey} chart:`, e);
                }
            }
        };

        // Render all charts safely
        safeRender('test', this.renderTestGauge, data.test_analysis);
        safeRender('ddd', this.renderDDDGauge, data.ddd);
        safeRender('extensions', this.renderFileDistribution, data.files);
        safeRender('changes', this.renderChangesBar, data.files);
        safeRender('testRatio', this.renderTestRatio, data.test_analysis, data.structure);
        safeRender('dddRadar', this.renderDDDRadar, data.ddd);
        safeRender('fileSizes', this.renderFileSizes, data.files);
        safeRender('timeline', this.renderTimeline, data.files);
        safeRender('findingsRadar', this.renderFindingsRadar, data);
        safeRender('severityDonut', this.renderSeverityDonut, data);
    }

    renderTestGauge(testAnalysis) {
        if (!testAnalysis) {
            console.error('renderTestGauge: No test analysis data');
            return;
        }
        const data = [{
            type: 'indicator',
            mode: 'gauge+number+delta',
            value: testAnalysis.count || 0,
            title: {
                text: '<b>Test Coverage</b><br><span style="font-size:0.8em;color:gray">Number of Test Files</span>',
                font: { size: 16, family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto' }
            },
            delta: { reference: 5, increasing: { color: '#10b981' } },
            gauge: {
                axis: {
                    range: [null, Math.max(10, (testAnalysis.count || 0) + 5)],
                    tickwidth: 1,
                    tickcolor: '#e5e7eb'
                },
                bar: { color: '#8b5cf6', thickness: 0.75 },
                bgcolor: '#f9fafb',
                borderwidth: 2,
                bordercolor: '#e5e7eb',
                steps: [
                    { range: [0, 3], color: '#fecaca' },
                    { range: [3, 7], color: '#fcd34d' },
                    { range: [7, Math.max(10, (testAnalysis.count || 0) + 5)], color: '#a7f3d0' }
                ],
                threshold: {
                    line: { color: '#ef4444', width: 4 },
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
        if (!ddd) {
            console.error('renderDDDGauge: No DDD data');
            return;
        }
        const data = [{
            type: 'indicator',
            mode: 'gauge+number+delta',
            value: ddd.score || 0,
            title: {
                text: '<b>DDD Score</b><br><span style="font-size:0.8em;color:gray">Domain-Driven Design Compliance</span>',
                font: { size: 16, family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto' }
            },
            number: { suffix: '%', font: { size: 40 } },
            delta: { reference: 60, increasing: { color: '#10b981' } },
            gauge: {
                axis: { range: [null, 100] },
                bar: { color: '#3b82f6' },
                steps: [
                    { range: [0, 30], color: '#fecaca' },
                    { range: [30, 60], color: '#fcd34d' },
                    { range: [60, 100], color: '#a7f3d0' }
                ]
            }
        }];

        const layout = { height: 300, margin: { t: 50, b: 0, l: 50, r: 50 } };
        Plotly.newPlot(this.chartContainers.ddd, data, layout, { responsive: true });
    }

    renderFileDistribution(files) {
        if (!files || !Array.isArray(files)) {
            console.error('renderFileDistribution: Invalid files data');
            return;
        }
        const extensions = {};
        files.forEach(f => {
            const filename = f.filename || '';
            const ext = filename.includes('.') ? filename.split('.').pop() : 'other';
            extensions[ext] = (extensions[ext] || 0) + 1;
        });

        // Professional color palette - Modern gradient scheme
        const colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981',
            '#06b6d4', '#6366f1', '#f97316', '#14b8a6', '#a855f7',
            '#0ea5e9', '#d946ef', '#84cc16', '#f43f5e', '#22d3ee'];

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
        if (!files || !Array.isArray(files)) {
            console.error('renderChangesBar: Invalid files data');
            return;
        }
        const additions = files.reduce((sum, f) => sum + (f.additions || 0), 0);
        const deletions = files.reduce((sum, f) => sum + (f.deletions || 0), 0);

        console.log('renderChangesBar: additions=' + additions + ', deletions=' + deletions);

        const data = [
            {
                x: ['Changes'],
                y: [additions],
                name: 'Additions',
                type: 'bar',
                marker: { color: '#10b981' }
            },
            {
                x: ['Changes'],
                y: [deletions],
                name: 'Deletions',
                type: 'bar',
                marker: { color: '#ef4444' }
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
        if (!testAnalysis || !structure) {
            console.error('renderTestRatio: Missing data');
            return;
        }
        const data = [{
            type: 'pie',
            labels: ['Test Files', 'Source Files'],
            values: [testAnalysis.count || 0, (structure.total || 0) - (testAnalysis.count || 0)],
            hole: 0.4,
            marker: { colors: ['#8b5cf6', '#3b82f6'] },
            textposition: 'inside'
        }];

        const layout = {
            title: 'Test Coverage Ratio',
            height: 300,
            annotations: [{
                text: `${testAnalysis.count || 0}/${structure.total || 0}`,
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
        if (!ddd || !ddd.indicators) {
            console.error('renderDDDRadar: Missing DDD data or indicators');
            return;
        }
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
            marker: { color: '#3b82f6', size: 8 },
            line: { color: '#2563eb', width: 2 },
            fillcolor: 'rgba(59, 130, 246, 0.3)'
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
        if (!files || !Array.isArray(files)) {
            console.error('renderFileSizes: Invalid files data');
            return;
        }
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
            marker: {
                color: fileSizes.map(f => f.size),
                colorscale: [
                    [0, '#a7f3d0'],
                    [0.5, '#fcd34d'],
                    [1, '#fca5a5']
                ],
                showscale: false
            },
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
        if (!files || !Array.isArray(files)) {
            console.error('renderTimeline: Invalid files data');
            return;
        }
        const sortedFiles = files
            .sort((a, b) => ((b.additions || 0) + (b.deletions || 0)) - ((a.additions || 0) + (a.deletions || 0)))
            .slice(0, 8);

        const data = [
            {
                x: sortedFiles.map(f => (f.filename || '').substring(0, 30)),
                y: sortedFiles.map(f => f.additions || 0),
                name: 'Additions',
                mode: 'lines+markers',
                line: { color: '#10b981', width: 3 },
                marker: { size: 10, color: '#10b981', symbol: 'circle' }
            },
            {
                x: sortedFiles.map(f => (f.filename || '').substring(0, 30)),
                y: sortedFiles.map(f => f.deletions || 0),
                name: 'Deletions',
                mode: 'lines+markers',
                line: { color: '#ef4444', width: 3 },
                marker: { size: 10, color: '#ef4444', symbol: 'circle' }
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

    renderFindingsRadar(data) {
        if (!data) return;
        const categories = ['security', 'bugs', 'quality', 'performance', 'tests'];
        const labels = ['Security', 'Bugs', 'Quality', 'Performance', 'Tests'];
        const values = categories.map(cat => this.countIssues(data[cat]));

        const radarData = [{
            type: 'scatterpolar',
            r: [...values, values[0]],
            theta: [...labels, labels[0]],
            fill: 'toself',
            marker: { color: '#8b5cf6', size: 8 },
            line: { color: '#7c3aed', width: 2 },
            fillcolor: 'rgba(139, 92, 246, 0.3)'
        }];

        const layout = this.getChartLayout('Findings Analysis Across Categories');
        layout.polar = {
            radialaxis: { visible: true, range: [0, Math.max(...values, 5)], showticklabels: true },
            angularaxis: { gridcolor: '#e5e7eb' }
        };
        layout.height = 350;

        Plotly.newPlot(this.chartContainers.findingsRadar, radarData, layout, this.getChartConfig());
    }

    renderSeverityDonut(data) {
        if (!data) return;
        const severities = { critical: 0, high: 0, medium: 0, low: 0 };
        ['security', 'bugs', 'quality', 'performance', 'tests'].forEach(cat => {
            const findings = data[cat]?.findings || [];
            findings.forEach(f => {
                const s = (f.severity || '').toLowerCase();
                if (severities.hasOwnProperty(s)) severities[s]++;
            });
        });

        const labels = Object.keys(severities).map(s => s.charAt(0).toUpperCase() + s.slice(1));
        const values = Object.values(severities);
        const hasData = values.some(v => v > 0);

        const donutData = [{
            type: 'pie',
            labels: labels,
            values: hasData ? values : [1],
            hole: 0.6,
            marker: {
                colors: hasData ? ['#ef4444', '#f97316', '#f59e0b', '#3b82f6'] : ['#e5e7eb']
            },
            textinfo: hasData ? 'percent' : 'none',
            hoverinfo: hasData ? 'label+value+percent' : 'none'
        }];

        const layout = this.getChartLayout('Issue Severity Breakdown');
        if (!hasData) {
            layout.annotations = [{
                text: 'No issues found',
                showarrow: false,
                font: { size: 14, color: '#9ca3af' }
            }];
        }

        Plotly.newPlot(this.chartContainers.severityDonut, donutData, layout, this.getChartConfig());
    }

    async renderHistoryTrendCharts() {
        try {
            const response = await fetch('/api/sessions/recent?limit=50');
            const data = await response.json();

            if (!data.success || !data.sessions || data.sessions.length === 0) return;

            const sessions = [...data.sessions].reverse(); // Chronological

            // 1. DDD Score Trend
            const dddTrendData = [{
                x: sessions.map((s, i) => i + 1),
                y: sessions.map(s => s.ddd_score || 0),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'DDD Score',
                line: { color: '#3b82f6', shape: 'spline', width: 3 },
                marker: { size: 8, color: '#2563eb' },
                fill: 'tozeroy',
                fillcolor: 'rgba(59, 130, 246, 0.1)',
                text: sessions.map(s => s.pr_title || 'Review')
            }];

            const dddLayout = this.getChartLayout('DDD Quality Trend');
            dddLayout.yaxis = { ...dddLayout.yaxis, range: [0, 100], title: 'Score (%)' };
            dddLayout.xaxis = { ...dddLayout.xaxis, title: 'Reviews (last 50)' };

            Plotly.newPlot(this.chartContainers.dddTrend, dddTrendData, dddLayout, this.getChartConfig());

            // 2. Review Volume (last 14 days)
            const volumeMap = {};
            const last14Days = Array.from({ length: 14 }, (_, i) => {
                const d = new Date();
                d.setDate(d.getDate() - i);
                return d.toLocaleDateString();
            }).reverse();

            last14Days.forEach(date => volumeMap[date] = 0);
            sessions.forEach(s => {
                const date = new Date(s.timestamp || s.created_at).toLocaleDateString();
                if (volumeMap.hasOwnProperty(date)) volumeMap[date]++;
            });

            const volumeData = [{
                x: Object.keys(volumeMap),
                y: Object.values(volumeMap),
                type: 'bar',
                marker: {
                    color: '#8b5cf6',
                    line: { width: 1, color: '#7c3aed' }
                }
            }];

            Plotly.newPlot(this.chartContainers.volume, volumeData, this.getChartLayout('Review Volume (Last 14 Days)'), this.getChartConfig());

            // 3. Historical Severity Distribution
            const severityTotals = { critical: 0, high: 0, medium: 0, low: 0 };
            sessions.forEach(s => {
                // If session doesn't have aggregate severity, we'd need to calculate it or just use counts
                // Modern structure or older fallback
                if (s.results) {
                    ['security', 'bugs', 'quality', 'performance', 'test_analysis'].forEach(cat => {
                        const findings = (s.results[cat]?.findings || []);
                        findings.forEach(f => {
                            const sev = (f.severity || '').toLowerCase();
                            if (severityTotals.hasOwnProperty(sev)) severityTotals[sev]++;
                        });
                    });
                }
            });

            const histSevData = [{
                x: ['Critical', 'High', 'Medium', 'Low'],
                y: [severityTotals.critical, severityTotals.high, severityTotals.medium, severityTotals.low],
                type: 'bar',
                marker: {
                    color: ['#ef4444', '#f97316', '#f59e0b', '#3b82f6']
                }
            }];

            Plotly.newPlot(this.chartContainers.historySeverity, histSevData, this.getChartLayout('Historical Findings by Severity'), this.getChartConfig());

        } catch (e) {
            console.error('Error rendering history trend charts:', e);
        }
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

        const formatSection = (data) => {
            if (!data) return 'No data available';
            if (typeof data === 'string') return data;

            let section = '';
            if (data.summary) {
                section += data.summary + '\n\n';
            }

            if (data.findings && data.findings.length > 0) {
                section += '### Findings\n\n';
                data.findings.forEach((f, i) => {
                    section += `#### ${i + 1}. ${f.title}\n`;
                    section += `- **Severity**: ${f.severity || 'Low'}\n`;
                    section += `- **Location**: \`${f.file}\` (Line ${f.line})\n\n`;
                    section += `${f.description}\n\n`;
                    if (f.suggestion) {
                        section += `> **Suggestion**: ${f.suggestion}\n\n`;
                    }
                    section += '---\n\n';
                });
            } else if (data.status === 'skipped') {
                section += '_Analysis skipped._\n';
            } else if (data.status === 'error') {
                section += `_Error: ${data.error_message || 'Unknown error'}_ \n`;
            } else if (!data.summary) {
                section += '_No issues found._\n';
            }

            return section;
        };

        return `# Code Review Report
Generated: ${new Date().toLocaleString()}

## Summary Metrics
- **Total Files**: ${r.structure.total}
- **Test Files**: ${r.test_analysis.count} (${r.test_analysis.status})
- **DDD Score**: ${r.ddd.score.toFixed(0)}% (${r.ddd.rating})
- **Directories**: ${r.structure.dirs}

## Security Analysis
${formatSection(r.security)}

## Bug Detection
${formatSection(r.bugs)}

## Code Quality
${formatSection(r.style)}

## Performance Analysis
${formatSection(r.performance)}

## Test Suggestions
${formatSection(r.tests)}

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

        // Setup clickable professional finding cards
        const findingCards = document.querySelectorAll('.finding-card-pro.clickable-card');
        console.log(`Found ${findingCards.length} finding cards`);
        findingCards.forEach(card => {
            // Remove existing click handlers by cloning
            const newCard = card.cloneNode(true);
            card.parentNode.replaceChild(newCard, card);

            // Add new click handler
            newCard.addEventListener('click', () => {
                const category = newCard.getAttribute('data-tab');
                console.log('Finding card clicked, category:', category);
                if (category) {
                    // Normalize category names if necessary
                    const categoryMap = {
                        'style': 'quality',
                        'quality': 'quality'
                    };
                    const normalizedCategory = categoryMap[category] || category;

                    // Switch to Analysis Browser and select the category
                    this.switchAnalysisCategory(normalizedCategory);

                    // Scroll to it
                    const browserSection = document.querySelector('.detailed-reports-pro');
                    if (browserSection) {
                        browserSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
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
                const section = link.getAttribute('data-section');

                // If link has no data-section attribute, it's an external link (like AI Stats page)
                // Let it navigate naturally without preventDefault
                if (!section) {
                    return; // Allow default navigation
                }

                e.preventDefault();

                // Update the hash, which will trigger handleHashChange
                window.location.hash = section;
            });
        });

        // Sidebar toggle for mobile and desktop
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.querySelector('.sidebar');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => {
                // On mobile (width < 768px), toggle 'open' class
                // On desktop, toggle 'collapsed' class
                if (window.innerWidth < 768) {
                    sidebar.classList.toggle('open');
                } else {
                    sidebar.classList.toggle('collapsed');
                }
            });
        }
    }

    showSection(sectionId) {
        this.currentSection = sectionId;
        console.log('=== showSection called ===');
        console.log('Section ID:', sectionId);

        // Hide all sections
        const allSections = document.querySelectorAll('.content-section');
        console.log('Total content sections found:', allSections.length);

        allSections.forEach(section => {
            section.classList.remove('active');
            section.style.display = ''; // Clear inline style
        });

        // Hide progress and summary sections when navigating away (with null checks)
        // BUT keep progress visible if a review is currently in progress
        const progressSection = document.getElementById('progressSection');
        const summarySection = document.getElementById('summarySection');

        if (progressSection) {
            // Only hide progress if there's no active polling (review in progress)
            if (!this.pollInterval) {
                progressSection.classList.add('hidden');
            }
        }
        if (summarySection) {
            summarySection.classList.add('hidden');
        }

        // Show selected section
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            console.log('Target section found:', sectionId);
            console.log('Target section element:', targetSection);
            console.log('Target section classes before:', targetSection.className);

            targetSection.classList.add('active');

            // Force display block to ensure section is visible
            // This helps with any CSS specificity issues
            targetSection.style.display = 'block';

            console.log('Target section classes after:', targetSection.className);
            console.log('Target section display:', targetSection.style.display);
            console.log('=== Section switch complete ===');
        } else {
            console.error('ERROR: Section not found:', sectionId);
            console.error('Available section IDs:', Array.from(allSections).map(s => s.id));
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
        } else if (sectionId === 'ai-stats') {
            console.log('Loading AI Token Stats...');
            // Initialize AI Stats app if available
            if (typeof window.aiStatsApp !== 'undefined') {
                window.aiStatsApp.loadStats();
            }

        } else if (sectionId === 'onboarding') {
            console.log('Loading Onboarding...');
            // Load onboarding list if available
            if (typeof window.onboardingApp !== 'undefined') {
                window.onboardingApp.loadOnboardingList();
            }

        }
    }

    // MongoDB Status Check
    async checkMongoDBStatus() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            const statusElement = document.getElementById('mongoStatus');
            const statusDot = document.getElementById('statusDot');
            const statMongoStatusEl = document.getElementById('statMongoStatus');

            // The server returns 'database_status' and 'database_type'
            const isConnected = data.database_status === 'connected' || data.status === 'ok';

            if (statusElement) {
                statusElement.textContent = isConnected ? 'Connected' : 'Disconnected';
            }

            if (statusDot) {
                if (isConnected) {
                    statusDot.classList.add('connected');
                    statusDot.classList.remove('disconnected');
                } else {
                    statusDot.classList.add('disconnected');
                    statusDot.classList.remove('connected');
                }
            }

            // Also update the statistics section status if it exists
            if (statMongoStatusEl) {
                statMongoStatusEl.textContent = isConnected ? 'Connected ✅' : 'Disconnected ⚠️';
            }
        } catch (error) {
            console.error('Failed to check MongoDB status:', error);
            const statusElement = document.getElementById('mongoStatus');
            const statusDot = document.getElementById('statusDot');
            const statMongoStatusEl = document.getElementById('statMongoStatus');

            if (statusElement) statusElement.textContent = 'Error';
            if (statusDot) {
                statusDot.classList.add('disconnected');
                statusDot.classList.remove('connected');
            }
            if (statMongoStatusEl) {
                statMongoStatusEl.textContent = 'Connection Error ❌';
            }
        }
    }

    // Dashboard Stats
    async loadDashboardStats() {
        try {
            const response = await fetch('/api/sessions/statistics');
            const data = await response.json();

            if (data.success) {
                const stats = data.statistics || {};
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

                // Calculate average DDD score (handle missing stats safely)
                const avgDDD = stats.average_ddd_score || 0;
                document.getElementById('avgDDDScore').textContent = Math.round(avgDDD) + '%';

                // Show top repository
                if (stats.top_repos && stats.top_repos.length > 0) {
                    const topRepo = stats.top_repos[0];
                    const repoName = topRepo._id ? topRepo._id.split('/').pop() : '-';
                    document.getElementById('topRepo').textContent = repoName;
                } else {
                    document.getElementById('topRepo').textContent = '-';
                }

                // Load other dashboard components independently
                try {
                    await this.loadDashboardRepositories();
                } catch (e) { console.error('Error loading dashboard repos:', e); }

                try {
                    await this.loadTrends();
                } catch (e) { console.error('Error loading dashboard trends:', e); }

                try {
                    await this.renderDashboardCharts();
                } catch (e) { console.error('Error rendering dashboard charts:', e); }

                try {
                    await this.loadDashboardRecentReviews();
                } catch (e) { console.error('Error loading recent reviews:', e); }
            }
        } catch (error) {
            console.error('Failed to load dashboard stats:', error);
        }
    }

    // Load trend indicators
    async loadTrends() {
        try {
            const response = await fetch('/api/statistics/trends');
            const data = await response.json();

            if (data.success && data.trends) {
                const trends = data.trends;

                // Update total reviews trend
                if (trends.total_sessions) {
                    this.updateTrendIndicator('totalReviewsTrend', trends.total_sessions);
                }

                // Update DDD score trend
                if (trends.average_ddd_score) {
                    this.updateTrendIndicator('avgDDDScoreTrend', trends.average_ddd_score);
                }
            }
        } catch (error) {
            console.error('Failed to load trends:', error);
        }
    }

    // Update a trend indicator element
    updateTrendIndicator(elementId, trendData) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const { trend, percentage_change, message } = trendData;

        // If no historical data, show message
        if (message && message.includes('No historical data')) {
            element.textContent = 'All time total';
            element.className = 'stat-trend';
            return;
        }

        // Format percentage
        const absPercentage = Math.abs(percentage_change).toFixed(1);

        // Determine trend class and arrow
        let trendClass = 'stat-trend';
        let arrow = '';

        if (trend === 'up') {
            trendClass = 'stat-trend stat-trend-up';
            arrow = '↗';
        } else if (trend === 'down') {
            trendClass = 'stat-trend stat-trend-down';
            arrow = '↘';
        } else {
            trendClass = 'stat-trend stat-trend-neutral';
            arrow = '→';
        }

        // Update element
        element.className = trendClass;
        element.textContent = `${arrow} ${absPercentage}% from last week`;
    }

    // Render Dashboard Charts
    async renderDashboardCharts() {
        try {
            const response = await fetch('/api/sessions/recent?limit=50');
            const data = await response.json();

            if (data.success && data.sessions && data.sessions.length > 0) {
                const sessions = data.sessions;

                // Render all 5 dashboard charts with individual error handling
                const charts = [
                    { name: 'Reviews Over Time', fn: () => this.renderDashReviewsOverTime(sessions) },
                    { name: 'Avg Scores Trend', fn: () => this.renderDashAvgScoresTrend(sessions) },
                    { name: 'Top Repos', fn: () => this.renderDashTopRepos(sessions) },
                    { name: 'Issues Breakdown', fn: () => this.renderDashIssuesBreakdown(sessions) },
                    { name: 'File Size Analysis', fn: () => this.renderDashFileSizeAnalysis(sessions) }
                ];

                for (const chart of charts) {
                    try {
                        chart.fn();
                    } catch (err) {
                        console.error(`Failed to render dashboard chart "${chart.name}":`, err);
                    }
                }
            } else {
                console.log('No sessions found for dashboard charts');
                this.renderEmptyDashboardCharts();
            }
        } catch (error) {
            console.error('Failed to load data for dashboard charts:', error);
        }
    }

    // Render empty state for dashboard charts
    renderEmptyDashboardCharts() {
        const containers = [
            'dashReviewsOverTime',
            'dashAvgScoresTrend',
            'dashTopRepos',
            'dashIssuesBreakdown',
            'dashFileSizeAnalysis'
        ];

        containers.forEach(id => {
            const layout = this.getChartLayout('No Data Available', 300);
            layout.annotations = [{
                text: 'No review history found. Start a new review to see analytics.',
                x: 0.5,
                y: 0.5,
                xref: 'paper',
                yref: 'paper',
                showarrow: false,
                font: { size: 14, color: '#94a3b8' }
            }];
            Plotly.newPlot(id, [], layout, this.getChartConfig());
        });
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
                color: '#3b82f6',
                width: 3,
                shape: 'spline'
            },
            marker: {
                size: 8,
                color: '#3b82f6',
                line: {
                    color: '#fff',
                    width: 2
                }
            },
            fill: 'tozeroy',
            fillcolor: 'rgba(59, 130, 246, 0.1)'
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
                line: { color: '#8b5cf6', width: 3 },
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
                    const colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#6366f1', '#f97316', '#14b8a6', '#a855f7'];
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

    // Chart 4: Issues Breakdown (Bar Chart showing actual counts)
    renderDashIssuesBreakdown(sessions) {
        // Count reviews with actual issues/suggestions in each category
        let withSecurityIssues = 0;
        let withBugIssues = 0;
        let withQualityIssues = 0;
        let withTestSuggestions = 0;

        sessions.forEach(session => {
            // Count sessions that have meaningful content (not just empty reviews)
            // Check for actual issues by looking for substantive content
            if (session.results) {
                // Helper to get text from result whether it's a string or object
                const getResultText = (res) => {
                    if (!res) return '';
                    if (typeof res === 'string') return res;
                    if (typeof res === 'object') return res.summary || '';
                    return '';
                };

                const securityText = getResultText(session.results.security).trim();
                if (securityText.length > 50 &&
                    !securityText.toLowerCase().includes('no security issues') &&
                    !securityText.toLowerCase().includes('no issues found')) {
                    withSecurityIssues++;
                }

                const bugsText = getResultText(session.results.bugs).trim();
                if (bugsText.length > 50 &&
                    !bugsText.toLowerCase().includes('no bugs') &&
                    !bugsText.toLowerCase().includes('no issues found')) {
                    withBugIssues++;
                }

                const styleText = getResultText(session.results.style).trim();
                if (styleText.length > 50 &&
                    !styleText.toLowerCase().includes('no style issues') &&
                    !styleText.toLowerCase().includes('no issues found')) {
                    withQualityIssues++;
                }

                const testsText = getResultText(session.results.tests).trim();
                if (testsText.length > 50 &&
                    !testsText.toLowerCase().includes('no test suggestions') &&
                    !testsText.toLowerCase().includes('no suggestions')) {
                    withTestSuggestions++;
                }
            }
        });

        const totalIssues = withSecurityIssues + withBugIssues + withQualityIssues + withTestSuggestions;
        const hasData = totalIssues > 0;

        // Use a horizontal bar chart to show actual counts (not percentages)
        const data = [{
            x: [withSecurityIssues, withBugIssues, withQualityIssues, withTestSuggestions],
            y: ['Security', 'Bugs', 'Quality', 'Tests'],
            type: 'bar',
            orientation: 'h',
            marker: {
                color: ['#ef4444', '#f59e0b', '#3b82f6', '#10b981'],
                line: {
                    color: 'rgba(255, 255, 255, 0.8)',
                    width: 1
                }
            },
            text: [
                `${withSecurityIssues} (${totalIssues > 0 ? ((withSecurityIssues / totalIssues) * 100).toFixed(0) : 0}%)`,
                `${withBugIssues} (${totalIssues > 0 ? ((withBugIssues / totalIssues) * 100).toFixed(0) : 0}%)`,
                `${withQualityIssues} (${totalIssues > 0 ? ((withQualityIssues / totalIssues) * 100).toFixed(0) : 0}%)`,
                `${withTestSuggestions} (${totalIssues > 0 ? ((withTestSuggestions / totalIssues) * 100).toFixed(0) : 0}%)`
            ],
            textposition: 'outside',
            hovertemplate: '<b>%{y}</b><br>Reviews with issues: %{x}<br><extra></extra>'
        }];

        const layout = this.getChartLayout('Issues Distribution - Reviews with Findings', 350);
        layout.xaxis = {
            title: 'Number of Reviews with Issues',
            showgrid: true,
            gridcolor: '#e5e7eb',
            zeroline: true
        };
        layout.yaxis = {
            title: '',
            automargin: true
        };
        layout.margin = { t: 60, b: 50, l: 80, r: 100 };
        layout.showlegend = false;

        // Add annotation if no data
        if (!hasData) {
            layout.annotations = [{
                text: 'No issues found in recent reviews',
                x: 0.5,
                y: 0.5,
                xref: 'paper',
                yref: 'paper',
                font: { size: 14, color: '#9ca3af' },
                showarrow: false
            }];
        }

        Plotly.newPlot('dashIssuesBreakdown', data, layout, this.getChartConfig());
    }

    // Chart 5: File Size Analysis (Scatter Chart)
    renderDashFileSizeAnalysis(sessions) {
        // Analyze file size distribution across reviews
        const fileData = [];

        sessions.forEach(session => {
            const filesCount = session.files_count || 0;
            const dddScore = session.ddd_score || 0;
            const testCount = session.test_count || 0;
            const repoName = session.repo_url ? session.repo_url.split('/').slice(-2).join('/') : 'Unknown';

            if (filesCount > 0) {
                fileData.push({
                    x: filesCount,
                    y: dddScore,
                    size: testCount,
                    repo: repoName,
                    date: new Date(session.created_at || session.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                });
            }
        });

        if (fileData.length === 0) {
            const layout = this.getChartLayout('Review Complexity Analysis', 350);
            layout.annotations = [{
                text: 'No review data available',
                x: 0.5,
                y: 0.5,
                xref: 'paper',
                yref: 'paper',
                font: { size: 14, color: '#9ca3af' },
                showarrow: false
            }];
            Plotly.newPlot('dashFileSizeAnalysis', [], layout, this.getChartConfig());
            return;
        }

        const data = [{
            x: fileData.map(d => d.x),
            y: fileData.map(d => d.y),
            mode: 'markers',
            type: 'scatter',
            marker: {
                size: fileData.map(d => Math.max(8, Math.min(d.size * 2, 30))),
                color: fileData.map(d => d.y),
                colorscale: [
                    [0, '#ef4444'],      // Red for low scores
                    [0.5, '#f59e0b'],    // Orange for medium
                    [1, '#10b981']       // Green for high scores
                ],
                showscale: true,
                colorbar: {
                    title: 'DDD Score',
                    thickness: 15,
                    len: 0.7
                },
                line: {
                    color: 'rgba(255, 255, 255, 0.8)',
                    width: 2
                }
            },
            text: fileData.map(d => `${d.repo}<br>${d.date}<br>Files: ${d.x}<br>DDD: ${d.y}%<br>Tests: ${d.size}`),
            hovertemplate: '%{text}<extra></extra>'
        }];

        const layout = this.getChartLayout('Review Complexity Analysis', 350);
        layout.xaxis = {
            title: 'Files Changed',
            showgrid: true,
            gridcolor: '#e5e7eb'
        };
        layout.yaxis = {
            title: 'DDD Score (%)',
            showgrid: true,
            gridcolor: '#e5e7eb',
            range: [0, 100]
        };
        layout.margin = { t: 60, b: 60, l: 60, r: 60 };

        Plotly.newPlot('dashFileSizeAnalysis', data, layout, this.getChartConfig());
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
                    <div class="history-item-title">${this.escapeHtml(session.pr_title || 'Untitled Review')}</div>
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
                    <span class="history-stat-value">${Math.round(session.ddd_score || 0)}%</span>
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

    // Switch History Tab
    switchHistoryTab(tabName) {
        // Only support standard PR review history
        if (tabName !== 'pr-reviews') {
            console.warn('Tab not supported:', tabName);
            return;
        }

        // Update tab buttons
        document.querySelectorAll('.history-tab-btn').forEach(btn => {
            if (btn.getAttribute('data-tab') === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update tab content
        document.querySelectorAll('.history-tab-content').forEach(content => {
            content.classList.remove('active');
            content.style.display = 'none';
        });

        const activeTab = document.getElementById(`${tabName}-tab`);
        if (activeTab) {
            activeTab.classList.add('active');
            activeTab.style.display = 'block';
        }

        // Load data
        this.loadHistory();
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

                    // Update version badges with prompt version data from session
                    this.updateVersionBadges(session);

                    // Show summary section with charts
                    this.showSummary(results);

                    // Show success message
                    this.showSuccess(`Loaded report for: ${session.pr_title || 'Review'} `);

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
            this.showError(`Failed to load report: ${error.message} `);
            document.getElementById('summarySection').classList.add('hidden');
        }
    }

    // Statistics Functions
    async loadStatistics() {
        try {
            const response = await fetch('/api/sessions/statistics');
            const data = await response.json();

            if (data.success) {
                const stats = data.statistics || {};

                // Update database stats
                const totalSessionsEl = document.getElementById('statTotalSessions');
                const mongoStatusEl = document.getElementById('statMongoStatus');
                if (totalSessionsEl) totalSessionsEl.textContent = stats.total_sessions || 0;
                if (mongoStatusEl) mongoStatusEl.textContent = stats.connected ? 'Connected ✅' : 'Disconnected ⚠️';

                // Update top repos list
                const topReposList = document.getElementById('topReposList');
                if (topReposList) {
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

                // Load historical trend charts
                this.renderHistoryTrendCharts();
            }
        } catch (error) {
            console.error('Failed to load statistics:', error);
            const list = document.getElementById('topReposList');
            if (list) list.innerHTML = '<div class="empty-message">❌ Failed to load statistics</div>';
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
            this.showError(`Failed to filter reports: ${error.message} `);
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

    // Load repositories into dashboard filter dropdown
    async loadDashboardRepositories() {
        try {
            const response = await fetch('/api/repositories');
            const data = await response.json();

            if (data.success && data.repositories) {
                const checkboxContainer = document.getElementById('dashboardRepoFilterCheckboxes');
                checkboxContainer.innerHTML = '';

                if (data.repositories.length === 0) {
                    checkboxContainer.innerHTML = '<div class="filter-loading">No repositories found</div>';
                    return;
                }

                data.repositories.forEach((repo, index) => {
                    const repoName = repo.split('/').slice(-2).join('/');

                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'filter-checkbox-item';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = `repo - checkbox - ${index} `;
                    checkbox.value = repo;
                    checkbox.className = 'repo-checkbox';

                    const label = document.createElement('label');
                    label.htmlFor = `repo - checkbox - ${index} `;
                    label.className = 'filter-checkbox-label';
                    label.textContent = repoName;

                    itemDiv.appendChild(checkbox);
                    itemDiv.appendChild(label);
                    checkboxContainer.appendChild(itemDiv);
                });
            }
        } catch (error) {
            console.error('Failed to load repositories:', error);
            const checkboxContainer = document.getElementById('dashboardRepoFilterCheckboxes');
            checkboxContainer.innerHTML = '<div class="filter-loading">Error loading repositories</div>';
        }
    }

    // Apply dashboard filter
    async applyDashboardFilter() {
        const checkboxes = document.querySelectorAll('.repo-checkbox:checked');
        const selectedRepos = Array.from(checkboxes).map(cb => cb.value);

        if (selectedRepos.length === 0) {
            const statusSpan = document.getElementById('filterStatus');
            statusSpan.textContent = '⚠️ Select at least one repository';
            statusSpan.className = 'filter-dropdown-status error';
            return;
        }

        try {
            const statusSpan = document.getElementById('filterStatus');
            statusSpan.textContent = 'Applying filter...';
            statusSpan.className = 'filter-dropdown-status loading';
            statusSpan.style.color = 'var(--text-secondary)';

            // Fetch filtered statistics
            const response = await fetch('/api/statistics/filtered', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repo_urls: selectedRepos })
            });

            const data = await response.json();

            if (data.success && data.statistics) {
                const stats = data.statistics;

                // Update dashboard cards with filtered data
                document.getElementById('totalReviews').textContent = stats.total_sessions || 0;
                document.getElementById('recentReviews').textContent = stats.recent_sessions || 0;

                const avgDDD = stats.average_ddd_score || 0;
                document.getElementById('avgDDDScore').textContent = avgDDD.toFixed(0) + '%';

                if (stats.top_repos && stats.top_repos.length > 0) {
                    const topRepo = stats.top_repos[0];
                    const repoName = topRepo._id ? topRepo._id.split('/').pop() : '-';
                    document.getElementById('topRepo').textContent = repoName;
                } else {
                    document.getElementById('topRepo').textContent = '-';
                }

                // Fetch filtered sessions for charts
                const sessionsResponse = await fetch('/api/sessions/filtered', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ repo_urls: selectedRepos })
                });

                const sessionsData = await sessionsResponse.json();

                if (sessionsData.success && sessionsData.sessions) {
                    // Re-render dashboard charts with filtered data
                    const sessions = sessionsData.sessions;
                    this.renderDashReviewsOverTime(sessions);
                    this.renderDashAvgScoresTrend(sessions);
                    this.renderDashTopRepos(sessions);
                    this.renderDashIssuesBreakdown(sessions);
                    this.renderDashFileSizeAnalysis(sessions);

                    // Update recent reviews list
                    await this.loadDashboardRecentReviews(selectedRepos);
                }

                const repoCount = selectedRepos.length;
                statusSpan.className = 'filter-dropdown-status success';
                statusSpan.innerHTML = `
    < svg width = "14" height = "14" viewBox = "0 0 20 20" fill = "currentColor" >
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg >
    ${stats.total_sessions} reviews from ${repoCount} ${repoCount === 1 ? 'repo' : 'repos'}
`;

                // Update button state
                this.updateFilterButtonState();

                // Close dropdown after successful filter
                setTimeout(() => {
                    this.toggleFilterDropdown();
                }, 1000);

                this.showSuccess(`Filter applied: ${repoCount} ${repoCount === 1 ? 'repository' : 'repositories'} selected`);
            }
        } catch (error) {
            console.error('Failed to apply filter:', error);
            console.error('Error details:', error.message, error.stack);
            this.showError(`Failed to apply filter: ${error.message} `);
            const statusSpan = document.getElementById('filterStatus');
            statusSpan.className = 'filter-dropdown-status error';
            statusSpan.innerHTML = `
    < svg width = "14" height = "14" viewBox = "0 0 20 20" fill = "currentColor" >
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg >
    ${error.message || 'Error applying filter'}
`;
        }
    }

    // Clear dashboard filter
    async clearDashboardFilter() {
        // Uncheck all checkboxes
        const checkboxes = document.querySelectorAll('.repo-checkbox');
        checkboxes.forEach(cb => cb.checked = false);

        const statusSpan = document.getElementById('filterStatus');
        statusSpan.textContent = '';
        statusSpan.className = 'filter-dropdown-status';

        // Update button state to remove active styling
        this.updateFilterButtonState();

        // Close dropdown
        const menu = document.getElementById('filterDropdownMenu');
        if (menu.classList.contains('show')) {
            setTimeout(() => {
                this.toggleFilterDropdown();
            }, 500);
        }

        // Reload all dashboard data without filter
        await this.loadDashboardStats();

        this.showSuccess('Filter cleared - showing all repositories');
    }

    // Load dashboard recent reviews (with optional filter)
    async loadDashboardRecentReviews(repoUrls = null) {
        try {
            let sessions;

            if (repoUrls && repoUrls.length > 0) {
                // Fetch filtered sessions
                const response = await fetch('/api/sessions/filtered', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ repo_urls: repoUrls })
                });
                const data = await response.json();
                sessions = data.success ? data.sessions.slice(0, 5) : [];
            } else {
                // Fetch recent sessions (unfiltered)
                const response = await fetch('/api/sessions/recent?limit=5');
                const data = await response.json();
                sessions = data.success ? data.sessions : [];
            }

            const recentList = document.getElementById('dashboardRecentList');

            if (sessions.length === 0) {
                recentList.innerHTML = '<div class="empty-message">No recent reviews</div>';
                return;
            }

            recentList.innerHTML = '';
            sessions.forEach(session => {
                const item = this.createHistoryItem(session);
                recentList.appendChild(item);
            });

        } catch (error) {
            console.error('Failed to load recent reviews:', error);
            document.getElementById('dashboardRecentList').innerHTML = '<div class="empty-message">Failed to load recent reviews</div>';
        }
    }

    // Toggle filter dropdown visibility
    toggleFilterDropdown() {
        const menu = document.getElementById('filterDropdownMenu');
        const btn = document.getElementById('filterToggleBtn');
        const isVisible = menu.classList.contains('show');

        if (isVisible) {
            // Close dropdown
            menu.classList.remove('show');
            btn.classList.remove('active');
            this.removeFilterOverlay();
        } else {
            // Open dropdown
            menu.classList.add('show');

            // Update button to show active state
            this.updateFilterButtonState();

            // Add overlay to close on click outside
            this.addFilterOverlay();
        }
    }

    // Update filter button state based on selection
    updateFilterButtonState() {
        const checkboxes = document.querySelectorAll('.repo-checkbox:checked');
        const btn = document.getElementById('filterToggleBtn');
        const btnText = document.getElementById('filterBtnText');
        const selectedCount = checkboxes.length;

        if (selectedCount > 0) {
            btn.classList.add('active');
            btnText.textContent = `Filter(${selectedCount})`;
        } else {
            btn.classList.remove('active');
            btnText.textContent = 'Filter';
        }
    }

    // Add overlay to close dropdown when clicking outside
    addFilterOverlay() {
        let overlay = document.getElementById('filterDropdownOverlay');

        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'filterDropdownOverlay';
            overlay.className = 'filter-dropdown-overlay';
            document.body.appendChild(overlay);
        }

        overlay.classList.add('show');
        overlay.addEventListener('click', () => this.toggleFilterDropdown());
    }

    // Remove overlay
    removeFilterOverlay() {
        const overlay = document.getElementById('filterDropdownOverlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
    }

    // ============================================================================
    // PROMPT VERSION SYSTEM
    // ============================================================================

    initPromptVersionBadges() {
        // Attach click handlers to all version badges
        document.querySelectorAll('.version-badge').forEach(badge => {
            badge.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent card click event
                const stage = badge.dataset.stage;
                this.showPromptModal(stage);
            });
        });
    }

    showPromptModal(stage) {
        // Get prompt version data from either current session or progress versions
        let versionData = null;

        if (this.currentSession && this.currentSession.prompt_versions) {
            // Use session data for completed reviews
            versionData = this.currentSession.prompt_versions[stage];
        } else if (this.progressPromptVersions) {
            // Use progress data during active review
            versionData = this.progressPromptVersions[stage];
        }

        if (!versionData) {
            console.warn(`No version data available for stage: ${stage} `);
            return;
        }

        // Stage display names
        const stageNames = {
            'security': 'Security Analysis',
            'bugs': 'Bug Detection',
            'style': 'Code Quality & Style',
            'tests': 'Test Suggestions'
        };

        // Update modal content
        document.getElementById('modalPromptTitle').textContent = `${stageNames[stage] || stage} - Prompt Details`;
        document.getElementById('modalPromptVersion').textContent = `v${versionData.version} `;
        document.getElementById('modalPromptStage').textContent = stageNames[stage] || stage;
        document.getElementById('modalPromptDescription').textContent = versionData.description || 'No description available';

        // Update criteria list
        const criteriaList = document.getElementById('modalPromptCriteria');
        criteriaList.innerHTML = '';

        if (versionData.criteria && versionData.criteria.length > 0) {
            versionData.criteria.forEach(criterion => {
                const li = document.createElement('li');
                li.textContent = criterion;
                criteriaList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'No specific criteria defined';
            li.style.fontStyle = 'italic';
            criteriaList.appendChild(li);
        }

        // Show modal
        const modal = document.getElementById('promptVersionModal');
        modal.classList.add('show');

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closePromptModal();
            }
        });
    }

    closePromptModal() {
        const modal = document.getElementById('promptVersionModal');
        modal.classList.remove('show');
    }

    updateVersionBadges(sessionData) {
        // Update version badges with data from session
        if (!sessionData.prompt_versions) {
            return;
        }

        // Update security badge
        if (sessionData.prompt_versions.security) {
            const badge = document.getElementById('securityVersionBadge');
            if (badge) {
                badge.textContent = `v${sessionData.prompt_versions.security.version} `;
            }
        }

        // Update bugs badge
        if (sessionData.prompt_versions.bugs) {
            const badge = document.getElementById('bugsVersionBadge');
            if (badge) {
                badge.textContent = `v${sessionData.prompt_versions.bugs.version} `;
            }
        }

        // Update style badge
        if (sessionData.prompt_versions.style) {
            const badge = document.getElementById('styleVersionBadge');
            if (badge) {
                badge.textContent = `v${sessionData.prompt_versions.style.version} `;
            }
        }

        // Update tests badge
        if (sessionData.prompt_versions.tests) {
            const badge = document.getElementById('testsVersionBadge');
            if (badge) {
                badge.textContent = `v${sessionData.prompt_versions.tests.version} `;
            }
        }

        // Store session data for modal use
        this.currentSession = sessionData;

        // Initialize badge click handlers
        this.initPromptVersionBadges();
    }

    // ============================================================================
    // PROMPT MANAGEMENT Logic
    // ============================================================================

    initPromptManagement() {
        console.log('Initializing Prompt Management...');
        this.setupPromptUpload();
        this.setupActivePromptTabs();
        this.loadActivePrompts();
        this.loadPromptCandidates();
    }

    setupPromptUpload() {
        const fileInput = document.getElementById('rulesFileInput');
        const uploadContainer = document.getElementById('rulesUploadContainer');
        const generateBtn = document.getElementById('generatePromptsBtn');
        const fileNameDisplay = document.getElementById('rulesFileNameDisplay');
        const fileSelectedView = document.getElementById('selectedRulesFile');
        const removeFileBtn = document.getElementById('removeRulesFileBtn');
        // Support both old and new HTML structure
        const uploadArea = uploadContainer ?
            (uploadContainer.querySelector('.upload-dropzone') || uploadContainer.querySelector('.upload-area-pro') || uploadContainer.querySelector('label[for="rulesFileInput"]'))
            : null;

        if (!fileInput) return;

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                if (fileNameDisplay) fileNameDisplay.textContent = file.name;
                if (fileSelectedView) fileSelectedView.style.display = 'flex';
                if (uploadArea) uploadArea.style.display = 'none';
                if (generateBtn) generateBtn.disabled = false;
            }
        });

        if (removeFileBtn) {
            removeFileBtn.addEventListener('click', () => {
                fileInput.value = '';
                if (fileSelectedView) fileSelectedView.style.display = 'none';
                if (uploadArea) uploadArea.style.display = 'flex';
                if (generateBtn) generateBtn.disabled = true;
            });
        }

        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateNewPrompts());
        }
    }

    async generateNewPrompts() {
        const fileInput = document.getElementById('rulesFileInput');
        const generateBtn = document.getElementById('generatePromptsBtn');
        const btnText = generateBtn.querySelector('.btn-text');
        const btnLoader = generateBtn.querySelector('.btn-loader');
        const categorySelect = document.getElementById('promptCategorySelect');

        if (fileInput.files.length === 0) return;

        const selectedCategory = categorySelect ? categorySelect.value : 'all';

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('category', selectedCategory);

        try {
            // UI Loading state
            generateBtn.disabled = true;
            const categoryName = selectedCategory === 'all' ? 'All Prompts' : this.getCategoryDisplayName(selectedCategory);
            btnText.textContent = `Generating ${categoryName}...`;
            btnLoader.style.display = 'inline-block';

            const response = await fetch('/api/prompts/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Store the generated data for modal
                this.generatedPromptData = {
                    prompts: data.prompts || {},
                    candidateId: data.job_id,
                    sourceFile: fileInput.files[0].name,
                    category: selectedCategory
                };

                // Show the generated prompt in modal
                this.showGeneratedPromptModal(selectedCategory);

                this.showSuccess('Prompts generated successfully! Review them in the modal.');

                // Refresh candidates list in background
                this.loadPromptCandidates();
            } else {
                this.showError(data.error || 'Failed to generate prompts');
            }
        } catch (err) {
            console.error('Error generating prompts:', err);
            this.showError('Connection error during prompt generation');
        } finally {
            btnText.textContent = 'Generate New Prompts';
            btnLoader.style.display = 'none';
            generateBtn.disabled = false;
        }
    }

    getCategoryDisplayName(category) {
        const names = {
            'security': '🛡️ Security',
            'bugs': '🐛 Bug Detection',
            'style': '✨ Code Quality',
            'performance': '⚡ Performance',
            'tests': '🧪 Test Suggestions'
        };
        return names[category] || category;
    }

    showGeneratedPromptModal(category) {
        const modal = document.getElementById('generatedPromptModal');
        const tabs = document.getElementById('generatedPromptTabs');
        const contentEl = document.getElementById('generatedPromptContent');
        const subtitleEl = document.getElementById('generatedPromptSubtitle');
        const sourceEl = document.getElementById('generatedPromptSource');

        if (!this.generatedPromptData) return;

        // Set source file
        sourceEl.textContent = this.generatedPromptData.sourceFile || '-';

        if (category === 'all') {
            // Show tabs for all categories
            tabs.style.display = 'flex';
            subtitleEl.textContent = 'Click on tabs to view each generated prompt';

            // Reset tabs to first active
            const tabBtns = tabs.querySelectorAll('.generated-prompt-tab');
            tabBtns.forEach((btn, idx) => {
                btn.classList.toggle('active', idx === 0);
            });

            // Show first category content
            this.currentGeneratedCategory = 'security';
            this.displayGeneratedPromptContent('security');
        } else {
            // Hide tabs, show single category
            tabs.style.display = 'none';
            subtitleEl.textContent = `Generated prompt for ${this.getCategoryDisplayName(category)}`;
            this.currentGeneratedCategory = category;
            this.displayGeneratedPromptContent(category);
        }

        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    displayGeneratedPromptContent(category) {
        const contentEl = document.getElementById('generatedPromptContent');

        if (!this.generatedPromptData || !this.generatedPromptData.prompts) {
            contentEl.textContent = 'No prompt content available.';
            return;
        }

        const prompt = this.generatedPromptData.prompts[category];
        if (prompt) {
            contentEl.textContent = prompt;
        } else {
            contentEl.textContent = `No prompt generated for ${this.getCategoryDisplayName(category)}.`;
        }
    }

    switchGeneratedPromptTab(category) {
        const tabs = document.getElementById('generatedPromptTabs');
        const tabBtns = tabs.querySelectorAll('.generated-prompt-tab');

        tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.category === category);
        });

        this.currentGeneratedCategory = category;
        this.displayGeneratedPromptContent(category);
    }

    closeGeneratedPromptModal() {
        const modal = document.getElementById('generatedPromptModal');
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }

    copyGeneratedPrompt() {
        const contentEl = document.getElementById('generatedPromptContent');
        const text = contentEl.textContent;

        navigator.clipboard.writeText(text).then(() => {
            this.showSuccess('Prompt copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
            this.showError('Failed to copy prompt');
        });
    }

    async acceptGeneratedPromptFromModal() {
        if (!this.generatedPromptData || !this.generatedPromptData.candidateId) {
            this.showError('No generated prompt to accept');
            return;
        }

        await this.acceptCandidate(this.generatedPromptData.candidateId);
        this.closeGeneratedPromptModal();

        // Clear file selection
        document.getElementById('removeRulesFileBtn').click();
    }

    async loadPromptCandidates() {
        try {
            const response = await fetch('/api/prompts/candidates');
            const data = await response.json();

            const tableBody = document.getElementById('candidateTableBody');
            const tableWrapper = document.querySelector('.candidates-table-responsive');
            const emptyState = document.getElementById('candidatesEmpty');
            const tabBadge = document.getElementById('candidatesTabBadge');
            const headerBadge = document.getElementById('candidatesHeaderBadge');

            if (data.success && data.candidates.length > 0) {
                if (tableWrapper) tableWrapper.style.display = 'block';
                if (emptyState) emptyState.style.display = 'none';

                // Update badges
                const count = data.candidates.length;
                if (tabBadge) {
                    tabBadge.textContent = count;
                    tabBadge.style.display = 'inline-flex';
                }
                if (headerBadge) headerBadge.textContent = count;

                tableBody.innerHTML = data.candidates.map(c => {
                    const createdDate = new Date(c.created_at);
                    const formattedDate = createdDate.toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                    });
                    const formattedTime = createdDate.toLocaleTimeString(undefined, {
                        hour: '2-digit',
                        minute: '2-digit'
                    });

                    const category = c.category || 'all';
                    const categoryLabel = category === 'all' ? 'All Categories' : this.getCategoryDisplayName(category);
                    const status = c.accepted ? 'Accepted' : 'Pending';
                    const statusClass = c.accepted ? 'status-accepted' : 'status-pending';

                    return `
                        <tr class="candidate-row" onclick="app.viewCandidateDetails('${c._id}')" data-candidate-id="${c._id}">
                            <td class="candidate-file-cell">
                                <div class="file-info">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"></path>
                                        <polyline points="14 2 14 8 20 8"></polyline>
                                    </svg>
                                    <span class="file-name">${this.escapeHtml(c.source_filename)}</span>
                                </div>
                            </td>
                            <td class="candidate-date-cell">
                                <div class="date-info">
                                    <span class="date-value">${formattedDate}</span>
                                    <span class="time-value">${formattedTime}</span>
                                </div>
                            </td>
                            <td class="candidate-category-cell">
                                <span class="category-badge">${categoryLabel}</span>
                            </td>
                            <td class="candidate-status-cell">
                                <span class="status-badge ${statusClass}">${status}</span>
                            </td>
                            <td class="candidate-actions-cell" onclick="event.stopPropagation()">
                                <button class="table-action-btn view-btn" onclick="app.viewCandidateDetails('${c._id}')" title="View Details">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                        <circle cx="12" cy="12" r="3"></circle>
                                    </svg>
                                </button>
                                <button class="table-action-btn accept-btn" onclick="app.acceptCandidate('${c._id}')" title="Accept & Activate">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                                        <polyline points="20 6 9 17 4 12"></polyline>
                                    </svg>
                                </button>
                                <button class="table-action-btn delete-btn" onclick="app.deleteCandidate('${c._id}')" title="Delete">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                                    </svg>
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            } else {
                if (tableWrapper) tableWrapper.style.display = 'none';
                if (emptyState) emptyState.style.display = 'flex';
                if (tabBadge) tabBadge.style.display = 'none';
                if (headerBadge) headerBadge.textContent = '0';
            }
        } catch (err) {
            console.error('Error loading candidates:', err);
        }
    }

    async viewCandidateDetails(candidateId) {
        try {
            const response = await fetch(`/api/prompts/candidates`);
            const data = await response.json();
            const candidate = data.candidates.find(c => c._id === candidateId);

            if (candidate) {
                // Store for modal use
                this.generatedPromptData = {
                    prompts: candidate.prompts,
                    candidateId: candidate._id,
                    sourceFile: candidate.source_filename,
                    category: candidate.category || 'all'
                };

                // Show in modal
                this.showGeneratedPromptModal(candidate.category || 'all');
            } else {
                this.showError('Candidate not found');
            }
        } catch (err) {
            console.error('Error viewing candidate:', err);
            this.showError('Failed to load candidate details');
        }
    }

    async deleteCandidate(candidateId) {
        if (!confirm('Are you sure you want to delete this candidate?')) {
            return;
        }

        try {
            const response = await fetch(`/api/prompts/candidate/${candidateId}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (data.success) {
                this.showSuccess('Candidate deleted');
                this.loadPromptCandidates();
            } else {
                this.showError(data.error || 'Failed to delete candidate');
            }
        } catch (err) {
            console.error('Error deleting candidate:', err);
            this.showError('Failed to delete candidate');
        }
    }

    async loadActivePrompts() {
        try {
            const response = await fetch('/api/prompts/active');
            const data = await response.json();

            if (data.success) {
                this.activePromptsData = data;
                this.displayActivePrompt('security');
            }
        } catch (err) {
            console.error('Error loading active prompts:', err);
        }
    }

    setupActivePromptTabs() {
        const tabs = document.querySelectorAll('.active-prompt-tab-btn');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.displayActivePrompt(tab.getAttribute('data-stage'));
            });
        });
    }

    displayActivePrompt(stage) {
        if (!this.activePromptsData) return;

        const promptText = this.activePromptsData.prompts[stage] || 'No prompt content available';
        const versionInfo = this.activePromptsData.versions[stage] || {};

        const textField = document.getElementById('activePromptText');
        const versionField = document.getElementById('activePromptVersion');
        const dateField = document.getElementById('activePromptDate');

        if (textField) {
            // Check if using new structure with pre/code
            const codeEl = textField.querySelector('code');
            if (codeEl) {
                codeEl.textContent = promptText;
            } else {
                textField.textContent = promptText;
            }
        }
        if (versionField) versionField.textContent = versionInfo.version || 'v1.0.0';
        if (dateField) dateField.textContent = versionInfo.timestamp ? new Date(versionInfo.timestamp).toLocaleDateString() : 'Default';
    }

    async acceptCandidate(candidateId) {
        if (!confirm('Are you sure you want to activate these prompts? This will replace the current review logic for all new reviews.')) {
            return;
        }

        try {
            const response = await fetch(`/api/prompts/accept/${candidateId}`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('New prompts activated successfully!');
                this.loadActivePrompts();
                this.loadPromptCandidates();
            } else {
                this.showError(data.error || 'Failed to accept prompts');
            }
        } catch (err) {
            console.error('Error accepting candidate:', err);
            this.showError('Connection error');
        }
    }

    async viewCandidate(candidateId) {
        try {
            const response = await fetch(`/api/prompts/candidates`);
            const data = await response.json();
            const candidate = data.candidates.find(c => c._id === candidateId);

            if (candidate) {
                // Show in active prompts area temporarily for preview
                this.activePromptsData = {
                    prompts: candidate.prompts,
                    versions: {}
                };
                this.displayActivePrompt('security');
                this.showSuccess('Previewing selected candidate in the Active Prompts area.');
            }
        } catch (err) {
            console.error('Error viewing candidate:', err);
        }
    }

    // Tab switching for Prompt Management page
    switchPromptTab(tabName) {
        // Update tab buttons
        const tabBtns = document.querySelectorAll('.prompt-tab-btn');
        tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab content
        const tabContents = document.querySelectorAll('.prompt-tab-content');
        tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `tab-${tabName}`);
        });

        // Refresh data when switching to candidates or active tabs
        if (tabName === 'candidates') {
            this.loadPromptCandidates();
        } else if (tabName === 'active') {
            this.loadActivePrompts();
        }
    }

    // Category selection for Active Prompts tab
    selectActivePromptCategory(category) {
        // Update category tabs
        const categoryTabs = document.querySelectorAll('.category-tab');
        categoryTabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.stage === category);
        });

        // Display the selected category's prompt
        this.displayActivePrompt(category);
    }

}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PRReviewApp();
});
