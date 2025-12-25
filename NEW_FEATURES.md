# New Features - Dashboard Enhancements & Prompt Versioning

This document describes the new features added to the Pull Request Review system.

## 1. Enhanced Dashboard - Review Complexity Analysis Chart

### Overview
A new dynamic chart has been added to the dashboard to visualize the relationship between code review complexity and quality scores.

### What It Shows
- **X-axis**: Number of files changed in each review
- **Y-axis**: DDD (Domain-Driven Design) Score (0-100%)
- **Bubble Size**: Number of test files in the review (larger = more tests)
- **Color Gradient**: Red (low DDD score) to Green (high DDD score)

### How to Use
1. Navigate to the **Dashboard** section
2. Scroll to the "Historical Analytics" section
3. The "Review Complexity Analysis" chart is the 5th chart in the grid
4. **Hover** over any bubble to see:
   - Repository name
   - Date of review
   - Number of files changed
   - DDD score
   - Number of tests

### Insights
This chart helps you:
- Identify patterns between review size and code quality
- See if larger reviews tend to have lower quality scores
- Track test coverage relative to review size
- Compare different repositories at a glance

---

## 2. AI Prompt Versioning System

### Overview
The system now tracks which version of AI prompts was used for each code review stage, allowing you to:
- See exactly how each review stage evaluates code
- Track changes in evaluation criteria over time
- Compare reviews done with different prompt versions
- Understand what the AI is looking for in each analysis

### Components

#### A. MongoDB Storage
**New Collection**: `prompt_versions`

**Schema**:
```javascript
{
  _id: ObjectId,
  stage: String,              // 'security', 'bugs', 'style', 'tests'
  version: String,            // e.g., '1.0.0', '1.1.0'
  prompt_content: String,     // Full prompt text
  description: String,        // How this stage evaluates code
  criteria: Array,            // List of evaluation criteria
  created_at: String,         // ISO timestamp
  timestamp: Date,            // MongoDB date
  active: Boolean             // Whether this version is active
}
```

#### B. Session Storage Enhancement
Each review session now includes:
```javascript
{
  // ... existing fields ...
  prompt_versions: {
    security: {
      version: '1.0.0',
      description: 'Expert security analyst reviewing for vulnerabilities',
      criteria: [
        'SQL injection vulnerabilities',
        'Cross-Site Scripting (XSS) risks',
        'Authentication/Authorization issues',
        // ... more criteria
      ]
    },
    bugs: { /* ... */ },
    style: { /* ... */ },
    tests: { /* ... */ }
  }
}
```

#### C. User Interface Elements

##### Version Badges on Summary Cards
- Each review stage now shows a **version badge** (e.g., "v1.0.0")
- Badges appear on summary cards in the review results
- Styled with a gradient purple background for visibility
- **Interactive**: Click any badge to see details

##### Version Badges on Progress Timeline
- Version information is also displayed during the active review process
- Each review stage (Security, Bug Check, Style, Tests) in the progress timeline shows:
  - **Version badge**: Small badge showing which prompt version is being used
  - **Stage description**: Brief description of what the stage evaluates (visible when step is active or completed)
- The badges automatically load the latest active prompt version when a review starts
- Descriptions are hidden for pending steps and shown for active/completed steps

##### Version Details Modal
When you click a version badge on the summary cards, a modal displays:
- **Version number**: The prompt version used
- **Stage name**: Which review stage (Security, Bugs, Quality, Tests)
- **Description**: How this stage evaluates code
- **Evaluation Criteria**: Bulleted list of what the AI looks for

### How to Use

#### Initial Setup
1. Run the initialization script to load prompt versions:
```bash
python init_prompt_versions.py
```

This reads all prompt files from `prompts/` directory and stores them in MongoDB with version 1.0.0.

#### Viewing Prompt Versions During Active Review
1. Start a new code review by entering a PR/MR URL
2. Click "Start Review"
3. During the review progress, watch the timeline:
   - Each stage (steps 4-7: Security, Bug Check, Style, Tests) displays a **version badge**
   - When a stage becomes **active**, its description appears below the badge
   - Example: "Security" step shows "v1.0.0" and "Security vulnerability analysis"
4. This helps you understand in real-time what criteria the AI is using

#### Viewing Prompt Details After Review
1. Complete a code review (or view an existing report from History)
2. In the review results, you'll see summary cards for each stage:
   - 🔒 Security
   - 🐛 Bugs
   - ✨ Code Quality
   - 🧪 Test Suggestions
3. Each card has a **version badge** in the top-right (e.g., "v1.0.0")
4. **Click the badge** to open the version details modal
5. The modal shows:
   - What version was used
   - How that stage evaluates code
   - Specific criteria the AI looks for

#### Updating Prompt Versions
When you update a prompt file and want to track it as a new version:

```bash
# Create version 1.1.0
python init_prompt_versions.py --version 1.1.0
```

This will:
- Read the updated prompt files
- Save them as version 1.1.0
- Deactivate the old version 1.0.0
- Make 1.1.0 the active version

**Important**: All new reviews will use v1.1.0, but old reviews retain their original version information for historical tracking.

### API Endpoints

#### Get All Prompt Versions
```http
GET /api/prompt-versions
```

Returns all prompt versions for all stages.

**Response Example:**
```json
{
  "security": [
    {
      "_id": "...",
      "stage": "security",
      "version": "1.0.0",
      "description": "Expert security analyst reviewing for vulnerabilities",
      "criteria": ["SQL injection", "XSS risks", "..."],
      "active": true,
      "created_at": "2024-01-01T00:00:00",
      "timestamp": "..."
    }
  ],
  "bugs": [...],
  "style": [...],
  "tests": [...]
}
```

#### Get Specific Stage Versions
```http
GET /api/prompt-versions?stage=security
```

Returns all versions for the security stage.

#### Get Session with Prompt Versions
```http
GET /api/sessions/{session_id}
```

Returns session data including the `prompt_versions` field showing which versions were used.

---

## File Changes Summary

### New Files
1. **[init_prompt_versions.py](init_prompt_versions.py)** - Script to initialize/update prompt versions in MongoDB
2. **[NEW_FEATURES.md](NEW_FEATURES.md)** - This documentation file

### Modified Files

#### Backend
1. **[utils/session_storage.py](utils/session_storage.py)**
   - Added `prompt_versions` collection
   - Added methods: `save_prompt_version()`, `get_prompt_version()`, `get_all_prompt_versions()`, `deactivate_prompt_version()`

2. **[agents/review_agents.py](agents/review_agents.py)**
   - Added `prompt_versions` dictionary to track loaded versions
   - Enhanced `_load_prompts()` to fetch version info from MongoDB
   - Added `get_prompt_versions()` method

3. **[server.py](server.py)**
   - Modified session save to include `prompt_versions` data
   - Added `/api/prompt-versions` endpoint to fetch prompt versions for all stages

#### Frontend
1. **[static/index.html](static/index.html)**
   - Added 5th chart container for Review Complexity Analysis
   - Added version badges to summary cards
   - Added prompt version modal HTML structure
   - Enhanced progress timeline steps (Security, Bug Check, Style, Tests) with:
     - Version badge elements (`step-version-badge`)
     - Description elements (`step-description`)
     - Restructured step labels to support version display

2. **[static/app.js](static/app.js)**
   - Added `renderDashFileSizeAnalysis()` for new chart
   - Added `initPromptVersionBadges()` for badge click handlers
   - Added `loadProgressPromptVersions()` to fetch and display versions during active reviews
   - Modified `showProgress()` to call `loadProgressPromptVersions()` on review start
   - Added `showPromptModal()` to display version details
   - Added `closePromptModal()` to close the modal
   - Added `updateVersionBadges()` to update badge versions from session data
   - Modified `viewSessionReport()` to call `updateVersionBadges()`

3. **[static/styles.css](static/styles.css)**
   - Added `.summary-card-header` styles for badge layout
   - Added `.version-badge` styles for interactive badges on summary cards
   - Added `.modal`, `.modal-content`, `.modal-header`, `.modal-body` for modal
   - Added `.version-info`, `.version-description`, `.version-criteria` for modal content
   - Enhanced `.step-label` to support version display with flexbox layout
   - Added `.step-name` for step title text
   - Added `.step-version-badge` for progress timeline version badges
   - Added `.step-description` for stage descriptions (shown when active/completed)

---

## Benefits

### For Users
- **Transparency**: See exactly what the AI is evaluating in each stage
- **Consistency**: Understand evaluation criteria used for each review
- **Historical Tracking**: Compare how reviews change when prompts are updated
- **Better Insights**: New chart helps identify code quality patterns

### For Administrators
- **Version Control**: Track prompt evolution over time
- **A/B Testing**: Compare results from different prompt versions
- **Auditability**: Know which prompts were used for any past review
- **Flexibility**: Update prompts without losing historical context

---

## Example Workflow

### Scenario: You want to understand why the security review flagged certain issues

1. **View the review results** for your PR
2. **Click the version badge** on the Security card (shows "v1.0.0")
3. **Modal opens** showing:
   - "Security Analysis - Prompt Details"
   - Version: v1.0.0
   - Stage: Security Analysis
   - Description: "Expert security analyst reviewing for vulnerabilities"
   - Criteria:
     - SQL injection vulnerabilities
     - Cross-Site Scripting (XSS) risks
     - Authentication/Authorization issues
     - Sensitive data exposure
     - ... (full list)
4. **Now you understand** what the AI was specifically looking for
5. You can **adjust your code** based on these specific criteria

---

## Troubleshooting

### Version badges show "v1.0.0" but I updated prompts
**Solution**: Run `python init_prompt_versions.py --version 1.1.0` to create a new version. Only new reviews will use v1.1.0.

### Modal shows "No prompt version data available"
**Cause**: This is an old review from before the prompt versioning system was added.
**Solution**: These reviews don't have version data. Only reviews created after running `init_prompt_versions.py` will have version information.

### Initialization script fails with "Cannot connect to MongoDB"
**Cause**: MongoDB is not running.
**Solution**: Start MongoDB: `mongod` (or `brew services start mongodb-community` on Mac)

### New chart is empty
**Cause**: No review sessions in database or all sessions have 0 files.
**Solution**: Complete at least one code review to populate data.

---

## Future Enhancements

Potential additions for the prompt versioning system:
- **Prompt comparison view**: Side-by-side comparison of two versions
- **Performance metrics**: Track which prompt versions produce better results
- **Prompt editor UI**: Edit prompts directly from the dashboard
- **Rollback functionality**: Revert to a previous version easily
- **Export/Import**: Share prompt configurations across installations

---

## Technical Notes

### Why Store Versions in MongoDB?
- Allows querying which reviews used which prompts
- Enables historical analysis and A/B testing
- Keeps prompt changes linked to review results
- Supports future features like prompt comparison and analytics

### Why Track in Session Data?
- Review results remain consistent even if prompts change
- Historical reviews show exactly what criteria were used
- Audit trail for compliance and quality tracking
- No need to re-run old reviews to see their evaluation criteria

---

## Questions or Feedback?

If you have questions about these features or suggestions for improvements, please open an issue in the repository or contact the development team.
