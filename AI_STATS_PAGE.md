# AI Token Statistics Page

## Overview
A dedicated page for tracking AI API token usage across all code reviews.

## Access
- **Menu**: Click "AI Token Stats" in the left sidebar
- **Direct URL**: `http://localhost:5000/static/ai-stats.html`

## Features

### 📊 Summary Cards
- **Total Reviews**: Count of all code reviews
- **Total Tokens Used**: Cumulative token consumption across all reviews
- **Avg Tokens/Review**: Average token usage per review

### 📈 Charts

#### 1. Token Distribution by Stage (Doughnut Chart)
Shows percentage breakdown of tokens used in each review stage:
- Security Review
- Bug Detection
- Style & Quality
- Test Suggestions

#### 2. Token Usage Trend (Line Chart)
Displays token consumption over time (last 30 data points)

### 📋 Detailed Statistics Table

Displays recent reviews with:
- **Date**: When the review was conducted
- **PR Title**: Title of the pull/merge request
- **Source → Target**: Branch information (e.g., `feature-branch → main`)
- **Outcome**: Status badge (Success/Error/Pending)
- **Token Breakdown**: Token count for each stage
  - Security
  - Bugs
  - Style
  - Tests
  - **Total**

## Technical Details

### Files
- **HTML**: `/static/ai-stats.html`
- **JavaScript**: `/static/ai-stats.js`
- **CSS**: Shared `/static/styles.css`

### API Endpoints Used
- `GET /api/sessions/token-stats?limit=N` - Fetches session data with token usage

### Dependencies
- Chart.js (CDN) - For rendering charts

## Troubleshooting

### Empty Page or Missing Data
If the page shows no data or missing columns:

1. **Check Browser Console** (F12):
   - Look for console logs starting with "Loading..."
   - Check for any error messages

2. **Verify MongoDB Connection**:
   - Ensure MongoDB is running
   - Check database status on main page

3. **Run Migrations** (REQUIRED for existing sessions):

   **Status Field Migration** (CRITICAL - fixes blank Outcome column):
   ```bash
   python3 migrate_add_status_field.py
   ```
   This adds the `status` field to old sessions, enabling the Outcome column to display properly.

   **Branch Fields Migration** (optional - fixes blank Source → Target column):
   ```bash
   python3 migrate_add_branch_fields.py
   ```
   This backfills branch information for old sessions from `pr_details`.

4. **Restart Server** (if migrations don't take effect):
   - After running migrations, you may need to restart the Flask server
   - The server caches some data

5. **Create New Review**:
   - New reviews will have complete data automatically
   - Old sessions need migrations to backfill missing fields

### Console Logging
The page includes detailed console logging:
- `AI Stats App initializing...`
- `Loading summary stats...`
- `Loading token statistics table...`
- `Stats: X reviews, Y tokens, Z avg`

Check these logs to diagnose issues.

### Recent Fixes (Dec 20, 2025)
- **Fixed:** Added `status` field to session data (was missing, causing empty Outcome column)
- **Fixed:** Status field now included in all three session creation points (manual, GitHub webhook, GitLab webhook)
- **Fixed:** Branch extraction now correctly handles GitHub PR format (`head_branch` and `base_branch`)
- **Created:** Migration script `migrate_add_status_field.py` to backfill status for existing sessions
- **Note:** Old sessions may show "-" in the Source → Target column if branch info wasn't stored in pr_details. New reviews will display branch information correctly.

## Data Requirements

### New Sessions (✅ Complete Data)
Sessions created after this feature include:
- `pr_title`
- `source_branch`
- `target_branch`
- `status`
- `token_usage` (with breakdown by stage)

### Old Sessions (⚠️ May Have Gaps)
Sessions created before this feature may be missing:
- Branch information (`source_branch`, `target_branch`)
- PR title

**Solution**: Run the migration script to backfill data from `results.pr_details`

## Notes
- Token table is now **separate** from main Statistics page
- Table is expanded by default (can be collapsed with toggle button)
- Charts auto-refresh when data is loaded
- Responsive design works on mobile and desktop
