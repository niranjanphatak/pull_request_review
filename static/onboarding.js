/**
 * Onboarding Application
 * Handles team and repository setup
 */

class OnboardingApp {
    constructor() {
        this.repoCount = 1;
        this.currentOnboarding = null;
        this.init();
    }

    init() {
        console.log('Onboarding App initializing...');
        this.setupEventListeners();
        console.log('Onboarding App initialized');
    }

    setupEventListeners() {
        // Form submit
        const form = document.getElementById('onboardingForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        // Add repository button
        const addRepoBtn = document.getElementById('addRepoBtn');
        if (addRepoBtn) {
            addRepoBtn.addEventListener('click', () => this.addRepositoryEntry());
        }

        // Clear form button
        const clearBtn = document.getElementById('clearOnboarding');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearForm());
        }

        // Refresh list button
        const refreshBtn = document.getElementById('refreshOnboardingList');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadOnboardingList());
        }
    }

    addRepositoryEntry() {
        const container = document.getElementById('repositoriesContainer');
        const index = this.repoCount++;

        const entry = document.createElement('div');
        entry.className = 'repository-entry';
        entry.setAttribute('data-index', index);
        entry.style.marginTop = '20px';
        entry.style.paddingTop = '20px';
        entry.style.borderTop = '1px solid #e5e7eb';
        entry.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h4 style="margin: 0; color: #4b5563;">Repository #${index + 1}</h4>
                <button type="button" class="remove-repo-btn" data-index="${index}" style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style="vertical-align: middle;">
                        <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                        <path d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                    </svg>
                    Remove
                </button>
            </div>
            <div class="form-group">
                <label class="form-label">Repository URL *</label>
                <input type="text" class="form-input repo-url" placeholder="https://github.com/username/repository.git" required />
            </div>
            <div class="form-group">
                <label class="form-label">Description</label>
                <textarea class="form-input repo-description" rows="2" placeholder="Brief description of what this repository does"></textarea>
            </div>
        `;

        container.appendChild(entry);

        // Add event listener to remove button
        const removeBtn = entry.querySelector('.remove-repo-btn');
        removeBtn.addEventListener('click', () => this.removeRepositoryEntry(index));
    }

    removeRepositoryEntry(index) {
        const entry = document.querySelector(`.repository-entry[data-index="${index}"]`);
        if (entry) {
            entry.remove();
            this.renumberRepositories();
        }
    }

    renumberRepositories() {
        const entries = document.querySelectorAll('.repository-entry');
        entries.forEach((entry, idx) => {
            const header = entry.querySelector('h4');
            if (header) {
                header.textContent = `Repository #${idx + 1}`;
            }
        });
    }

    async handleSubmit(event) {
        event.preventDefault();

        const teamName = document.getElementById('teamName').value.trim();
        const repositories = this.collectRepositories();

        if (!teamName) {
            alert('Please enter a team name');
            return;
        }

        if (repositories.length === 0) {
            alert('Please add at least one repository');
            return;
        }

        const data = {
            team_name: teamName,
            repositories: repositories
        };

        try {
            const submitBtn = document.getElementById('submitOnboarding');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Saving...';

            const response = await fetch('/api/onboarding', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                alert('✅ Onboarding saved successfully!');
                this.clearForm();
                this.loadOnboardingList();
            } else {
                alert('❌ Failed to save onboarding: ' + result.error);
            }

        } catch (error) {
            console.error('Error saving onboarding:', error);
            alert('❌ Error saving onboarding: ' + error.message);
        } finally {
            const submitBtn = document.getElementById('submitOnboarding');
            submitBtn.disabled = false;
            submitBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style="margin-right: 6px;">
                    <path d="M13.854 3.646a.5.5 0 010 .708l-7 7a.5.5 0 01-.708 0l-3.5-3.5a.5.5 0 11.708-.708L6.5 10.293l6.646-6.647a.5.5 0 01.708 0z"/>
                </svg>
                Save Onboarding
            `;
        }
    }

    collectRepositories() {
        const entries = document.querySelectorAll('.repository-entry');
        const repositories = [];

        entries.forEach(entry => {
            const url = entry.querySelector('.repo-url').value.trim();
            const description = entry.querySelector('.repo-description').value.trim();

            if (url) {
                repositories.push({
                    url: url,
                    description: description || ''
                });
            }
        });

        return repositories;
    }

    clearForm() {
        document.getElementById('teamName').value = '';

        // Remove all but first repository entry
        const container = document.getElementById('repositoriesContainer');
        container.innerHTML = `
            <div class="repository-entry" data-index="0">
                <div class="form-group">
                    <label class="form-label">Repository URL *</label>
                    <input type="text" class="form-input repo-url" placeholder="https://github.com/username/repository.git" required />
                </div>
                <div class="form-group">
                    <label class="form-label">Description</label>
                    <textarea class="form-input repo-description" rows="2" placeholder="Brief description of what this repository does"></textarea>
                </div>
            </div>
        `;

        this.repoCount = 1;
    }

    async loadOnboardingList() {
        const listContainer = document.getElementById('onboardingList');
        listContainer.innerHTML = '<div class="loading-message">Loading onboarding data...</div>';

        try {
            const response = await fetch('/api/onboarding/all');
            const result = await response.json();

            if (result.success && result.data.length > 0) {
                this.renderOnboardingList(result.data);
            } else {
                listContainer.innerHTML = '<div class="loading-message">No onboarding data found. Create your first onboarding above.</div>';
            }

        } catch (error) {
            console.error('Error loading onboarding list:', error);
            listContainer.innerHTML = '<div class="error-message">Failed to load onboarding data</div>';
        }
    }

    renderOnboardingList(data) {
        const listContainer = document.getElementById('onboardingList');
        listContainer.innerHTML = '';

        data.forEach(item => {
            const card = document.createElement('div');
            card.className = 'history-item';
            card.style.marginBottom = '15px';
            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">
                            🏢 ${this.escapeHtml(item.team_name)}
                        </div>
                        <div style="color: #6b7280; font-size: 14px; margin-bottom: 12px;">
                            Created: ${new Date(item.created_at).toLocaleDateString()} at ${new Date(item.created_at).toLocaleTimeString()}
                        </div>
                        <div style="margin-top: 12px;">
                            <strong style="color: #374151;">Repositories (${item.repositories.length}):</strong>
                            <ul style="margin: 8px 0 0 20px; padding: 0;">
                                ${item.repositories.map(repo => `
                                    <li style="margin-bottom: 8px;">
                                        <code style="background: #f3f4f6; padding: 2px 6px; border-radius: 3px; font-size: 13px;">${this.escapeHtml(repo.url)}</code>
                                        ${repo.description ? `<div style="color: #6b7280; font-size: 13px; margin-top: 4px;">${this.escapeHtml(repo.description)}</div>` : ''}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-secondary" onclick="window.onboardingApp.viewOnboarding('${item._id}')" style="padding: 6px 12px; font-size: 13px;">
                            View
                        </button>
                        <button class="btn-secondary" onclick="window.onboardingApp.deleteOnboarding('${item._id}')" style="padding: 6px 12px; font-size: 13px; background: #ef4444; color: white;">
                            Delete
                        </button>
                    </div>
                </div>
            `;
            listContainer.appendChild(card);
        });
    }

    async viewOnboarding(id) {
        try {
            const response = await fetch(`/api/onboarding?id=${id}`);
            const result = await response.json();

            if (result.success) {
                this.showModal(result.data);
            }

        } catch (error) {
            console.error('Error loading onboarding:', error);
            alert('Failed to load onboarding data');
        }
    }

    showModal(data) {
        const modal = document.getElementById('onboardingDetailsModal');
        const content = document.getElementById('onboardingModalContent');
        const title = document.getElementById('onboardingModalTitle');

        if (modal && content) {
            title.textContent = `${data.team_name} Configuration`;
            content.innerHTML = this.renderModalContent(data);
            modal.classList.add('active');
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        }
    }

    closeModal() {
        const modal = document.getElementById('onboardingDetailsModal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = ''; // Restore scrolling
        }
    }

    renderModalContent(data) {
        return `
            <div class="modal-details-grid">
                <div class="modal-detail-item">
                    <label class="modal-detail-label">Team Name</label>
                    <div class="modal-detail-value">${this.escapeHtml(data.team_name)}</div>
                </div>
                <div class="modal-detail-item">
                    <label class="modal-detail-label">Created At</label>
                    <div class="modal-detail-value">${new Date(data.created_at).toLocaleString()}</div>
                </div>
                <div class="modal-detail-item full-width">
                    <label class="modal-detail-label">Configured Repositories (${data.repositories.length})</label>
                    <div class="modal-repos-list">
                        ${data.repositories.map((repo, idx) => `
                            <div class="modal-repo-card">
                                <div class="modal-repo-header">
                                    <span class="modal-repo-number">#${idx + 1}</span>
                                    <code class="modal-repo-url">${this.escapeHtml(repo.url)}</code>
                                </div>
                                ${repo.description ? `
                                    <div class="modal-repo-desc">${this.escapeHtml(repo.description)}</div>
                                ` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    populateForm(data) {
        document.getElementById('teamName').value = data.team_name;

        // Clear existing repositories
        const container = document.getElementById('repositoriesContainer');
        container.innerHTML = '';
        this.repoCount = 0;

        // Add each repository
        data.repositories.forEach((repo, index) => {
            if (index === 0) {
                // First entry
                const entry = document.createElement('div');
                entry.className = 'repository-entry';
                entry.setAttribute('data-index', '0');
                entry.innerHTML = `
                    <div class="form-group">
                        <label class="form-label">Repository URL *</label>
                        <input type="text" class="form-input repo-url" value="${this.escapeHtml(repo.url)}" required />
                    </div>
                    <div class="form-group">
                        <label class="form-label">Description</label>
                        <textarea class="form-input repo-description" rows="2">${this.escapeHtml(repo.description || '')}</textarea>
                    </div>
                `;
                container.appendChild(entry);
                this.repoCount = 1;
            } else {
                // Additional entries
                this.addRepositoryEntry();
                const entries = container.querySelectorAll('.repository-entry');
                const lastEntry = entries[entries.length - 1];
                lastEntry.querySelector('.repo-url').value = repo.url;
                lastEntry.querySelector('.repo-description').value = repo.description || '';
            }
        });
    }

    async deleteOnboarding(id) {
        if (!confirm('Are you sure you want to delete this onboarding entry?')) {
            return;
        }

        try {
            const response = await fetch(`/api/onboarding/${id}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                alert('✅ Onboarding deleted successfully');
                this.loadOnboardingList();
            } else {
                alert('❌ Failed to delete: ' + result.error);
            }

        } catch (error) {
            console.error('Error deleting onboarding:', error);
            alert('❌ Error deleting onboarding');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.onboardingApp = new OnboardingApp();
});
