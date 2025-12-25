/**
 * Test Generator Application
 * Handles code analysis and test case generation
 */

class TestGenApp {
    constructor() {
        this.analysisData = null;
        this.testCases = null;
        this.init();
    }

    init() {
        console.log('Test Generator App initializing...');

        this.initTheme();
        this.setupEventListeners();

        // Set up form submit handler
        const form = document.getElementById('testGenForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        console.log('Test Generator App initialized');
    }

    initTheme() {
        // Check for saved theme preference or default to light mode
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
        }
    }

    setupEventListeners() {
        // Theme toggle
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }

        // Download tests button
        const downloadTestsBtn = document.getElementById('downloadTestsBtn');
        if (downloadTestsBtn) {
            downloadTestsBtn.addEventListener('click', () => this.downloadTests());
        }
    }

    toggleTheme() {
        const body = document.body;
        body.classList.toggle('dark-mode');

        // Save preference to localStorage
        const isDark = body.classList.contains('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('mainContent');

        sidebar.classList.toggle('collapsed');
        if (sidebar.classList.contains('collapsed')) {
            mainContent.style.marginLeft = '60px';
        } else {
            mainContent.style.marginLeft = '250px';
        }
    }

    async handleSubmit(event) {
        event.preventDefault();

        const repoUrl = document.getElementById('repoUrl').value.trim();
        const branchName = document.getElementById('branchName').value.trim();
        const generateTests = document.getElementById('generateTests').checked;
        const aiAnalysis = document.getElementById('aiAnalysis').checked;

        console.log('Starting analysis:', { repoUrl, branchName, generateTests, aiAnalysis });

        // Reset UI
        this.showProgress(true);
        this.showAnalysis(false);
        this.showTests(false);

        // Disable form
        this.setFormEnabled(false);

        try {
            // Start analysis
            await this.analyzeRepository(repoUrl, branchName, generateTests, aiAnalysis);
        } catch (error) {
            console.error('Analysis failed:', error);
            this.updateProgress(`Error: ${error.message}`, 0);
            alert(`Analysis failed: ${error.message}`);
        } finally {
            this.setFormEnabled(true);
        }
    }

    async analyzeRepository(repoUrl, branchName, generateTests, aiAnalysis) {
        this.updateProgress('Cloning repository...', 10);

        const response = await fetch('/api/analyze-repo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                repo_url: repoUrl,
                branch_name: branchName,
                generate_tests: generateTests,
                ai_analysis: aiAnalysis
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Analysis request failed');
        }

        const data = await response.json();
        console.log('Analysis response:', data);

        if (!data.success) {
            throw new Error(data.error || 'Analysis failed');
        }

        // Poll for progress
        await this.pollProgress(data.task_id, generateTests);
    }

    async pollProgress(taskId, generateTests) {
        const pollInterval = 2000; // 2 seconds
        const maxAttempts = 300; // 10 minutes max
        let attempts = 0;

        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, pollInterval));
            attempts++;

            try {
                const response = await fetch(`/api/analyze-status/${taskId}`);
                const data = await response.json();

                console.log('Progress update:', data);

                if (data.status === 'completed') {
                    this.updateProgress('Analysis complete!', 100);
                    this.displayResults(data.result, generateTests);
                    this.showProgress(false);
                    return;
                } else if (data.status === 'failed') {
                    throw new Error(data.error || 'Analysis failed');
                } else if (data.status === 'in_progress') {
                    this.updateProgress(data.message || 'Analyzing...', data.progress || 50);
                }
            } catch (error) {
                console.error('Poll error:', error);
                throw error;
            }
        }

        throw new Error('Analysis timed out');
    }

    displayResults(result, showTests) {
        console.log('Displaying results:', result);

        // Update header stats
        const generatedCount = result.test_cases ? result.test_cases.length : 0;
        document.getElementById('headerGeneratedTests').textContent = generatedCount;

        // Display code analysis (use analysis_before if available, otherwise analysis for backward compatibility)
        const analysisData = result.analysis_before || result.analysis;
        this.displayAnalysis(analysisData, result.analysis_after, result.comparison, result.repo_path);
        this.showAnalysis(true);

        // DO NOT display generated test files in UI
        // Tests are written to repository and accessible via repo_path
        // User can find them in temp_repos/analysis_<task_id>/
        this.showTests(false);

        // Store data for download
        this.analysisData = analysisData;
        this.testCases = result.test_cases;
        this.repoPath = result.repo_path;
        this.comparison = result.comparison;
    }

    displayAnalysis(analysisBefore, analysisAfter, comparison, repoPath) {
        // Update summary cards with BEFORE data
        document.getElementById('totalFiles').textContent = analysisBefore.total_files || 0;
        document.getElementById('codeFiles').textContent = analysisBefore.code_files || 0;
        document.getElementById('testFiles').textContent = analysisBefore.test_files || 0;
        document.getElementById('testCoverage').textContent = `${analysisBefore.test_coverage || 0}%`;

        // Display issues
        const issuesContainer = document.getElementById('issuesContainer');
        issuesContainer.innerHTML = '';

        // Add detailed repository statistics section
        const detailedStatsHtml = `
            <div style="background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); border: 1px solid #cbd5e0; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 16px 0; color: #2d3748;">📈 Detailed Repository Analysis</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px;">
                    <div style="background: white; padding: 10px; border-radius: 6px; border-left: 3px solid #4299e1;">
                        <div style="font-size: 11px; color: #718096; margin-bottom: 4px; text-transform: uppercase; font-weight: 600;">Total Files</div>
                        <div style="font-size: 24px; font-weight: bold; color: #2d3748;">${analysisBefore.total_files || 0}</div>
                        <div style="font-size: 12px; color: #718096; margin-top: 4px;">All files in repository</div>
                    </div>
                    <div style="background: white; padding: 10px; border-radius: 6px; border-left: 3px solid #9f7aea;">
                        <div style="font-size: 11px; color: #718096; margin-bottom: 4px; text-transform: uppercase; font-weight: 600;">Source Code Files</div>
                        <div style="font-size: 24px; font-weight: bold; color: #2d3748;">${analysisBefore.non_test_code_files || analysisBefore.code_files || 0}</div>
                        <div style="font-size: 12px; color: #718096; margin-top: 4px;">Excluding test files</div>
                    </div>
                    <div style="background: white; padding: 10px; border-radius: 6px; border-left: 3px solid #48bb78;">
                        <div style="font-size: 11px; color: #718096; margin-bottom: 4px; text-transform: uppercase; font-weight: 600;">Test Files</div>
                        <div style="font-size: 24px; font-weight: bold; color: #2d3748;">${analysisBefore.test_files || 0}</div>
                        <div style="font-size: 12px; color: #718096; margin-top: 4px;">Existing test coverage</div>
                    </div>
                    <div style="background: white; padding: 10px; border-radius: 6px; border-left: 3px solid ${analysisBefore.test_coverage >= 80 ? '#48bb78' : analysisBefore.test_coverage >= 50 ? '#ed8936' : '#f56565'};">
                        <div style="font-size: 11px; color: #718096; margin-bottom: 4px; text-transform: uppercase; font-weight: 600;">Test Coverage</div>
                        <div style="font-size: 24px; font-weight: bold; color: #2d3748;">${analysisBefore.test_coverage || 0}%</div>
                        <div style="font-size: 12px; color: ${analysisBefore.test_coverage >= 80 ? '#48bb78' : analysisBefore.test_coverage >= 50 ? '#ed8936' : '#f56565'}; margin-top: 4px; font-weight: 500;">
                            ${analysisBefore.test_coverage >= 80 ? '✓ Excellent' : analysisBefore.test_coverage >= 50 ? '⚠ Moderate' : '✗ Low'}
                        </div>
                    </div>
                </div>
                <details style="margin-top: 16px;">
                    <summary style="cursor: pointer; color: #4299e1; font-weight: 500; font-size: 13px; padding: 8px; background: #ebf8ff; border-radius: 4px;">
                        View detailed file breakdown
                    </summary>
                    <div style="margin-top: 12px; padding: 12px; background: white; border-radius: 4px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                            <div>
                                <h5 style="margin: 0 0 8px 0; color: #2d3748; font-size: 13px;">File Distribution</h5>
                                <table style="width: 100%; font-size: 12px;">
                                    <tr style="border-bottom: 1px solid #e2e8f0;">
                                        <td style="padding: 6px 0; color: #4a5568;">Code Files (total)</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600;">${analysisBefore.code_files || 0}</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid #e2e8f0;">
                                        <td style="padding: 6px 0; color: #4a5568;">Source Files (excl. tests)</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600;">${analysisBefore.non_test_code_files || 0}</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid #e2e8f0;">
                                        <td style="padding: 6px 0; color: #4a5568;">Test Files</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #48bb78;">${analysisBefore.test_files || 0}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #4a5568;">Files Without Tests</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #f56565;">${(analysisBefore.non_test_code_files || 0) - (analysisBefore.test_files || 0)}</td>
                                    </tr>
                                </table>
                            </div>
                            <div>
                                <h5 style="margin: 0 0 8px 0; color: #2d3748; font-size: 13px;">Coverage Metrics</h5>
                                <table style="width: 100%; font-size: 12px;">
                                    <tr style="border-bottom: 1px solid #e2e8f0;">
                                        <td style="padding: 6px 0; color: #4a5568;">Coverage Ratio</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600;">${analysisBefore.test_files || 0}/${analysisBefore.non_test_code_files || 0}</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid #e2e8f0;">
                                        <td style="padding: 6px 0; color: #4a5568;">Coverage Percentage</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600;">${analysisBefore.test_coverage || 0}%</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid #e2e8f0;">
                                        <td style="padding: 6px 0; color: #4a5568;">Quality Issues Found</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600; color: ${(analysisBefore.issues && analysisBefore.issues.length > 0) ? '#ed8936' : '#48bb78'};">${analysisBefore.issues ? analysisBefore.issues.length : 0}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #4a5568;">AI Analysis Status</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600;">${analysisBefore.ai_analysis_enabled ? '<span style="color: #4299e1;">✓ Enabled</span>' : '<span style="color: #a0aec0;">○ Disabled</span>'}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </div>
                </details>
            </div>
        `;
        issuesContainer.innerHTML = detailedStatsHtml;

        // Add repository location banner at the top if tests were generated
        if (analysisAfter && repoPath) {
            const repoInfoHtml = `
                <div style="background: linear-gradient(135deg, #667eea10 0%, #764ba210 100%); border: 2px solid #667eea; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 12px 0; color: #667eea;">📁 Repository Location</h4>
                    <p style="margin: 0 0 8px 0; color: #2d3748; font-size: 14px;">
                        <strong>Cloned Repository:</strong>
                        <code style="background: #e6f3ff; padding: 4px 8px; border-radius: 4px; font-size: 13px; color: #2c5282;">${repoPath}</code>
                    </p>
                    <p style="margin: 0 0 8px 0; color: #4a5568; font-size: 13px;">
                        ✓ Test files have been generated and written directly into the repository<br>
                        ✓ Tests are in the same directories as their source files<br>
                        ✓ Repository is preserved for your review and can be committed to git
                    </p>
                    <details style="margin-top: 12px;">
                        <summary style="cursor: pointer; color: #667eea; font-weight: 500; font-size: 13px;">
                            View generated test files
                        </summary>
                        <div id="testFilesList" style="margin-top: 8px; padding: 12px; background: white; border-radius: 4px;">
                            ${this.testCases ? this.testCases.map(tc => `
                                <div style="padding: 4px 0; border-bottom: 1px solid #e2e8f0; font-size: 12px;">
                                    <code style="color: #48bb78;">✓</code> ${tc.filename || tc.written_to}
                                </div>
                            `).join('') : 'Loading test files...'}
                        </div>
                    </details>
                </div>
            `;
            issuesContainer.innerHTML = repoInfoHtml;
        }

        // If we have after-analysis data, show comparison
        if (analysisAfter && comparison) {
            const comparisonHtml = `
                <div style="background: linear-gradient(135deg, #667eea10 0%, #764ba210 100%); border: 2px solid #667eea; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 16px 0; color: #667eea;">📊 Before & After Comparison</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                        <div style="background: white; padding: 12px; border-radius: 6px; border-left: 4px solid #ed8936;">
                            <div style="font-size: 12px; color: #718096; margin-bottom: 4px;">BEFORE Analysis</div>
                            <div style="font-size: 20px; font-weight: bold; color: #ed8936;">${analysisBefore.test_files} tests</div>
                            <div style="font-size: 14px; color: #718096;">${analysisBefore.test_coverage}% coverage</div>
                        </div>
                        <div style="background: white; padding: 12px; border-radius: 6px; border-left: 4px solid #48bb78;">
                            <div style="font-size: 12px; color: #718096; margin-bottom: 4px;">AFTER Generation</div>
                            <div style="font-size: 20px; font-weight: bold; color: #48bb78;">${analysisAfter.test_files} tests</div>
                            <div style="font-size: 14px; color: #718096;">${analysisAfter.test_coverage}% coverage</div>
                        </div>
                        <div style="background: white; padding: 12px; border-radius: 6px; border-left: 4px solid #667eea;">
                            <div style="font-size: 12px; color: #718096; margin-bottom: 4px;">Tests Generated</div>
                            <div style="font-size: 20px; font-weight: bold; color: #667eea;">+${comparison.tests_added}</div>
                            <div style="font-size: 14px; color: #48bb78;">↑ ${comparison.coverage_improvement}% coverage</div>
                        </div>
                        <div style="background: white; padding: 12px; border-radius: 6px; border-left: 4px solid #9f7aea;">
                            <div style="font-size: 12px; color: #718096; margin-bottom: 4px;">Files Now Covered</div>
                            <div style="font-size: 20px; font-weight: bold; color: #9f7aea;">${comparison.files_now_covered}</div>
                            <div style="font-size: 14px; color: #718096;">new test files</div>
                        </div>
                    </div>
                </div>
            `;
            issuesContainer.innerHTML = comparisonHtml;
        }

        // Display issues below comparison
        if (analysisBefore.issues && analysisBefore.issues.length > 0) {
            // Add AI analysis summary if enabled
            let aiSummary = '';
            if (analysisBefore.ai_analysis_enabled) {
                const aiCount = analysisBefore.ai_issues_found || 0;
                aiSummary = `
                    <div style="background: #e6f3ff; border: 1px solid #4299e1; border-radius: 6px; padding: 12px; margin-bottom: 16px;">
                        <p style="margin: 0; color: #2c5282; font-size: 14px;">
                            <strong>🤖 AI-Enhanced Analysis:</strong> Found ${aiCount} additional issue${aiCount !== 1 ? 's' : ''} through deep code analysis
                        </p>
                    </div>
                `;
            }

            const issuesHtml = `
                ${aiSummary}
                <h4 style="margin-bottom: 12px;">Code Quality Issues</h4>
                <div class="scrollable-table">
                    <table class="token-stats-table">
                        <thead>
                            <tr>
                                <th>Severity</th>
                                <th>Source</th>
                                <th>File</th>
                                <th>Issue</th>
                                <th>Suggestion</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${analysisBefore.issues.map(issue => `
                                <tr>
                                    <td><span class="badge ${issue.severity.toLowerCase()}">${issue.severity}</span></td>
                                    <td>${issue.source ? '<span style="background: #4299e1; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">AI</span>' : '<span style="background: #48bb78; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">Local</span>'}</td>
                                    <td>${issue.file}</td>
                                    <td>${issue.description}</td>
                                    <td>${issue.suggestion || '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            issuesContainer.innerHTML += issuesHtml;
        } else if (!analysisAfter) {
            issuesContainer.innerHTML += '<p style="color: #48bb78;">No major issues found!</p>';
        }
    }

    displayTestCases(testCases, repoPath) {
        const container = document.getElementById('testCasesContainer');

        if (!testCases || testCases.length === 0) {
            container.innerHTML = '<p>No test cases generated.</p>';
            return;
        }

        // Add info banner about repository location
        let infoBanner = '';
        if (repoPath) {
            infoBanner = `
                <div style="background: #e6fffa; border: 1px solid #38b2ac; border-radius: 6px; padding: 12px; margin-bottom: 16px;">
                    <p style="margin: 0; color: #234e52; font-size: 14px;">
                        <strong>📁 Repository Location:</strong> <code style="background: #bee3f8; padding: 2px 6px; border-radius: 3px;">${repoPath}</code>
                    </p>
                    <p style="margin: 8px 0 0 0; color: #234e52; font-size: 13px;">
                        Test files have been written directly into the cloned repository in their respective directories.
                    </p>
                </div>
            `;
        }

        const html = infoBanner + testCases.map((testCase, index) => `
            <div class="test-case-item" style="border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; margin-bottom: 16px;">
                <h4 style="margin: 0 0 8px 0;">${testCase.filename || `Test ${index + 1}`}</h4>
                ${testCase.written_to ? `<p style="margin: 0 0 12px 0; font-size: 12px; color: #718096;">
                    <strong>Location:</strong> <code style="background: #f7fafc; padding: 2px 6px; border-radius: 3px;">${testCase.written_to}</code>
                </p>` : ''}
                <pre style="background: #f7fafc; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 13px;"><code>${this.escapeHtml(testCase.code)}</code></pre>
                <p style="margin: 12px 0 0 0; font-size: 13px; color: #718096;">
                    <strong>Purpose:</strong> ${testCase.description || 'Test case for code coverage'}
                </p>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    downloadTests() {
        if (!this.testCases || this.testCases.length === 0) {
            alert('No test cases to download');
            return;
        }

        // Create a zip-like structure (simplified - just concatenate for now)
        let content = '';
        this.testCases.forEach(testCase => {
            content += `\n// File: ${testCase.filename}\n`;
            content += `${testCase.code}\n\n`;
        });

        // Download as text file
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'generated_tests.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // UI Helper Methods
    showProgress(show) {
        document.getElementById('progressSection').style.display = show ? 'block' : 'none';
    }

    showAnalysis(show) {
        document.getElementById('analysisSection').style.display = show ? 'block' : 'none';
    }

    showTests(show) {
        document.getElementById('testsSection').style.display = show ? 'block' : 'none';
    }

    updateProgress(message, percent) {
        document.getElementById('progressMessage').textContent = message;
        document.getElementById('progressBar').style.width = `${percent}%`;
        document.getElementById('progressPercent').textContent = `${Math.round(percent)}%`;
    }

    setFormEnabled(enabled) {
        const button = document.getElementById('analyzeBtn');
        const inputs = document.querySelectorAll('#testGenForm input');

        button.disabled = !enabled;
        button.style.opacity = enabled ? '1' : '0.6';
        button.style.cursor = enabled ? 'pointer' : 'not-allowed';

        inputs.forEach(input => {
            input.disabled = !enabled;
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.testGenApp = new TestGenApp();
});
