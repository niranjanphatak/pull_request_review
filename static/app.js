// Main Application JavaScript
class PRReviewApp {
    constructor() {
        this.apiEndpoint = '/api/review';
        this.currentReview = null;
        this.charts = {};
        this.currentSection = 'new-review';
        this.currentSession = null; // For viewing historical sessions
        this.progressPromptVersions = null; // For prompt versions during active review
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

        // Handle initial hash or show dashboard
        this.handleHashChange();

        // Setup hash change listener for browser back/forward
        window.addEventListener('hashchange', () => this.handleHashChange());
    }

    handleHashChange() {
        const hash = window.location.hash.slice(1); // Remove the # character

        // Valid sections that can be navigated to
        const validSections = ['dashboard', 'onboarding', 'new-review', 'history', 'statistics', 'ai-stats', 'code-analyzer'];

        if (hash && validSections.includes(hash)) {
            console.log('Navigating to section from hash:', hash);
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
                'code-analyzer': 'Code Analysis'
            };
            document.getElementById('pageTitle').textContent = pageTitles[hash] || 'Dashboard';
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
        if (currentStepEl) {
            const stepNumber = Math.min(Math.floor(progress / 9.09), 11);
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

        // Reset all steps to pending and apply disabled state if needed
        const steps = document.querySelectorAll('.timeline-step-horizontal');
        steps.forEach(step => {
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
        document.getElementById('testSuggestionsSummary').textContent = this.extractSummary(results.tests);

        // Update issue counts in the professional finding cards
        this.updateIssueCounts(results);

        // Update detailed reports with formatted content
        this.updateDetailedReport('securityDetails', results.security);
        this.updateDetailedReport('bugsDetails', results.bugs);
        this.updateDetailedReport('qualityDetails', results.style);
        this.updateDetailedReport('testsDetails', results.tests);

        // Update tab counts
        this.updateTabCounts(results);

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
                targetBranchDetails.textContent = results.target_branch_analysis;
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

    extractSummary(text, maxLength = 100) {
        if (!text) return 'No issues found';
        const clean = text.replace(/[#*`]/g, '');
        const lines = clean.split('\n').filter(line => line.trim().length > 20);
        const summary = lines[0] || clean;
        return summary.length > maxLength ? summary.substring(0, maxLength) + '...' : summary;
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
            tests: this.countIssues(results.tests)
        };

        // Update the count displays
        const securityCountEl = document.getElementById('securityCount');
        const bugsCountEl = document.getElementById('bugsCount');
        const qualityCountEl = document.getElementById('qualityCount');
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
        if (testsCountEl) {
            testsCountEl.textContent = `${counts.tests} ${counts.tests === 1 ? 'suggestion' : 'suggestions'}`;
        }
    }

    countIssues(text) {
        if (!text || text === 'No issues found' || text.trim() === '') {
            return 0;
        }

        // Count numbered items (1., 2., 3., etc.)
        const numberedMatches = text.match(/^\s*\d+\.\s+/gm);
        if (numberedMatches && numberedMatches.length > 0) {
            return numberedMatches.length;
        }

        // Count bullet points (-, *, •)
        const bulletMatches = text.match(/^\s*[-*•]\s+/gm);
        if (bulletMatches && bulletMatches.length > 0) {
            return bulletMatches.length;
        }

        // Count headers (##, ###)
        const headerMatches = text.match(/^#{2,4}\s+/gm);
        if (headerMatches && headerMatches.length > 0) {
            return headerMatches.length;
        }

        // If text is substantial but no patterns found, count as 1 issue
        if (text.trim().length > 50) {
            return 1;
        }

        return 0;
    }

    updateDetailedReport(elementId, content) {
        const element = document.getElementById(elementId);
        if (!element) return;

        if (!content || content === 'No issues found' || content.trim() === '') {
            element.textContent = 'No issues found in this category.\n\n✅ Great work! This area of your code meets quality standards.';
        } else {
            // Format the content with better structure
            element.textContent = content;
        }
    }

    updateTabCounts(results) {
        // Update tab counts for the professional tabs
        const counts = {
            security: this.countIssues(results.security),
            bugs: this.countIssues(results.bugs),
            quality: this.countIssues(results.style),
            tests: this.countIssues(results.tests)
        };

        const securityTabCount = document.getElementById('securityTabCount');
        const bugsTabCount = document.getElementById('bugsTabCount');
        const qualityTabCount = document.getElementById('qualityTabCount');
        const testsTabCount = document.getElementById('testsTabCount');

        if (securityTabCount) securityTabCount.textContent = counts.security;
        if (bugsTabCount) bugsTabCount.textContent = counts.bugs;
        if (qualityTabCount) qualityTabCount.textContent = counts.quality;
        if (testsTabCount) testsTabCount.textContent = counts.tests;
    }

    copyCurrentReport() {
        // Find the active tab
        const activeTab = document.querySelector('.tab-button-pro.active');
        if (!activeTab) return;

        const tabName = activeTab.getAttribute('data-tab');
        let content = '';
        let reportName = '';

        // Get the content based on active tab
        switch(tabName) {
            case 'security':
                content = document.getElementById('securityDetails')?.textContent || '';
                reportName = 'Security Analysis';
                break;
            case 'bugs':
                content = document.getElementById('bugsDetails')?.textContent || '';
                reportName = 'Bug Detection';
                break;
            case 'quality':
                content = document.getElementById('qualityDetails')?.textContent || '';
                reportName = 'Code Quality';
                break;
            case 'tests':
                content = document.getElementById('testsDetails')?.textContent || '';
                reportName = 'Test Suggestions';
                break;
            case 'target-branch':
                content = document.getElementById('targetBranchDetails')?.textContent || '';
                reportName = 'Target Branch Analysis';
                break;
        }

        if (content) {
            const fullReport = `# ${reportName} Report\n\nGenerated: ${new Date().toLocaleString()}\n\n---\n\n${content}`;

            navigator.clipboard.writeText(fullReport).then(() => {
                // Show success message
                this.showToast('✅ Report copied to clipboard!', 'success');
            }).catch(err => {
                console.error('Failed to copy:', err);
                this.showToast('❌ Failed to copy report', 'error');
            });
        }
    }

    expandCurrentReport() {
        // Find the active tab pane
        const activePane = document.querySelector('.tab-pane-pro.active');
        if (!activePane) return;

        const reportContainer = activePane.querySelector('.report-container-pro');
        if (!reportContainer) return;

        // Toggle fullscreen class
        if (reportContainer.classList.contains('fullscreen')) {
            this.exitFullscreen(reportContainer);
        } else {
            this.enterFullscreen(reportContainer);
        }
    }

    enterFullscreen(reportContainer) {
        reportContainer.classList.add('fullscreen');
        reportContainer.style.position = 'fixed';
        reportContainer.style.top = '20px';
        reportContainer.style.left = '20px';
        reportContainer.style.right = '20px';
        reportContainer.style.bottom = '20px';
        reportContainer.style.zIndex = '9999';
        reportContainer.style.maxHeight = 'none';

        // Add ESC key listener
        if (!this.escKeyHandler) {
            this.escKeyHandler = (e) => {
                if (e.key === 'Escape' || e.keyCode === 27) {
                    const fullscreenReport = document.querySelector('.report-container-pro.fullscreen');
                    if (fullscreenReport) {
                        this.exitFullscreen(fullscreenReport);
                    }
                }
            };
        }
        document.addEventListener('keydown', this.escKeyHandler);
    }

    exitFullscreen(reportContainer) {
        reportContainer.classList.remove('fullscreen');
        reportContainer.style.position = '';
        reportContainer.style.top = '';
        reportContainer.style.left = '';
        reportContainer.style.right = '';
        reportContainer.style.bottom = '';
        reportContainer.style.zIndex = '';
        reportContainer.style.maxHeight = '800px';

        // Remove ESC key listener
        if (this.escKeyHandler) {
            document.removeEventListener('keydown', this.escKeyHandler);
        }
    }

    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: ${type === 'success' ? '#10b981' : '#ef4444'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            font-weight: 600;
            animation: slideInRight 0.3s ease;
        `;

        document.body.appendChild(toast);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
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

        console.log('renderCharts: Rendering charts with data:', {
            hasFiles: !!data.files,
            filesCount: data.files?.length || 0,
            hasTestAnalysis: !!data.test_analysis,
            hasDDD: !!data.ddd,
            hasStructure: !!data.structure,
            sampleFile: data.files?.[0]
        });

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
                bar: { color: '#10b981', thickness: 0.75 },
                bgcolor: '#f9fafb',
                borderwidth: 2,
                bordercolor: '#e5e7eb',
                steps: [
                    { range: [0, 3], color: '#fecaca' },
                    { range: [3, 7], color: '#fef3c7' },
                    { range: [7, Math.max(10, (testAnalysis.count || 0) + 5)], color: '#d1fae5' }
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
        if (!testAnalysis || !structure) {
            console.error('renderTestRatio: Missing data');
            return;
        }
        const data = [{
            type: 'pie',
            labels: ['Test Files', 'Source Files'],
            values: [testAnalysis.count || 0, (structure.total || 0) - (testAnalysis.count || 0)],
            hole: 0.4,
            marker: { colors: ['#4caf50', '#2196f3'] },
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
        return `# Code Review Report
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

        // Setup clickable professional finding cards
        const findingCards = document.querySelectorAll('.finding-card-pro.clickable-card');
        console.log(`Found ${findingCards.length} finding cards`);
        findingCards.forEach(card => {
            // Remove existing click handlers by cloning
            const newCard = card.cloneNode(true);
            card.parentNode.replaceChild(newCard, card);

            // Add new click handler
            newCard.addEventListener('click', () => {
                const tabName = newCard.getAttribute('data-tab');
                console.log('Finding card clicked, tab:', tabName);
                if (tabName) {
                    this.navigateToTab(tabName, true); // Pass true for professional tabs
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
        const progressSection = document.getElementById('progressSection');
        const summarySection = document.getElementById('summarySection');

        if (progressSection) {
            progressSection.classList.add('hidden');
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
        } else if (sectionId === 'code-analyzer') {
            console.log('Loading Code Analyzer...');
            // Initialize Test Generator app if available
            if (typeof window.testGenApp !== 'undefined') {
                window.testGenApp.init();
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

                // Calculate average DDD score from actual data
                const avgDDD = stats.average_ddd_score || 0;
                document.getElementById('avgDDDScore').textContent = avgDDD.toFixed(0) + '%';

                // Show top repository
                if (stats.top_repos && stats.top_repos.length > 0) {
                    const topRepo = stats.top_repos[0];
                    const repoName = topRepo._id ? topRepo._id.split('/').pop() : '-';
                    document.getElementById('topRepo').textContent = repoName;
                } else {
                    document.getElementById('topRepo').textContent = '-';
                }

                // Load repository filter dropdown
                await this.loadDashboardRepositories();

                // Load and display trends
                await this.loadTrends();

                // Render dashboard charts
                await this.renderDashboardCharts();

                // Load recent reviews list
                await this.loadDashboardRecentReviews();
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

                // Render all 5 dashboard charts
                this.renderDashReviewsOverTime(sessions);
                this.renderDashAvgScoresTrend(sessions);
                this.renderDashTopRepos(sessions);
                this.renderDashIssuesBreakdown(sessions);
                this.renderDashFileSizeAnalysis(sessions);
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
            if (session.results && session.results.security) {
                const securityText = session.results.security.trim();
                // Check if it has meaningful content (more than just headers or "No issues")
                if (securityText.length > 50 &&
                    !securityText.toLowerCase().includes('no security issues') &&
                    !securityText.toLowerCase().includes('no issues found')) {
                    withSecurityIssues++;
                }
            }

            if (session.results && session.results.bugs) {
                const bugsText = session.results.bugs.trim();
                if (bugsText.length > 50 &&
                    !bugsText.toLowerCase().includes('no bugs') &&
                    !bugsText.toLowerCase().includes('no issues found')) {
                    withBugIssues++;
                }
            }

            if (session.results && session.results.style) {
                const styleText = session.results.style.trim();
                if (styleText.length > 50 &&
                    !styleText.toLowerCase().includes('no style issues') &&
                    !styleText.toLowerCase().includes('no issues found')) {
                    withQualityIssues++;
                }
            }

            if (session.results && session.results.tests) {
                const testsText = session.results.tests.trim();
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
                `${withSecurityIssues} (${totalIssues > 0 ? ((withSecurityIssues/totalIssues)*100).toFixed(0) : 0}%)`,
                `${withBugIssues} (${totalIssues > 0 ? ((withBugIssues/totalIssues)*100).toFixed(0) : 0}%)`,
                `${withQualityIssues} (${totalIssues > 0 ? ((withQualityIssues/totalIssues)*100).toFixed(0) : 0}%)`,
                `${withTestSuggestions} (${totalIssues > 0 ? ((withTestSuggestions/totalIssues)*100).toFixed(0) : 0}%)`
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

                    // Update version badges with prompt version data from session
                    this.updateVersionBadges(session);

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
                    checkbox.id = `repo-checkbox-${index}`;
                    checkbox.value = repo;
                    checkbox.className = 'repo-checkbox';

                    const label = document.createElement('label');
                    label.htmlFor = `repo-checkbox-${index}`;
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
                    <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
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
            this.showError(`Failed to apply filter: ${error.message}`);
            const statusSpan = document.getElementById('filterStatus');
            statusSpan.className = 'filter-dropdown-status error';
            statusSpan.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>
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
            btnText.textContent = `Filter (${selectedCount})`;
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
            console.warn(`No version data available for stage: ${stage}`);
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
        document.getElementById('modalPromptVersion').textContent = `v${versionData.version}`;
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
                badge.textContent = `v${sessionData.prompt_versions.security.version}`;
            }
        }

        // Update bugs badge
        if (sessionData.prompt_versions.bugs) {
            const badge = document.getElementById('bugsVersionBadge');
            if (badge) {
                badge.textContent = `v${sessionData.prompt_versions.bugs.version}`;
            }
        }

        // Update style badge
        if (sessionData.prompt_versions.style) {
            const badge = document.getElementById('styleVersionBadge');
            if (badge) {
                badge.textContent = `v${sessionData.prompt_versions.style.version}`;
            }
        }

        // Update tests badge
        if (sessionData.prompt_versions.tests) {
            const badge = document.getElementById('testsVersionBadge');
            if (badge) {
                badge.textContent = `v${sessionData.prompt_versions.tests.version}`;
            }
        }

        // Store session data for modal use
        this.currentSession = sessionData;

        // Initialize badge click handlers
        this.initPromptVersionBadges();
    }

}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PRReviewApp();
});
