# Dashboard Features - Multi-Repository Filter & Historical Trends

This document describes the new dashboard features for filtering by repositories and tracking historical trends.

## Features Overview

### 1. Multi-Repository Filter

The dashboard now includes a multi-select filter that allows you to:
- Select one or more repositories to analyze
- View filtered statistics and charts for selected repositories only
- Easily compare performance across different projects

**Location**: Analytics Dashboard section at the top

**How to Use**:
1. Navigate to the Dashboard section
2. Use the "Filter by Repositories" dropdown (supports multi-select)
3. Hold Ctrl/Cmd to select multiple repositories
4. Click "Apply Filter" to update the dashboard
5. Click "Clear Filter" to show all repositories again

### 2. Historical Statistics Snapshots

The system now tracks historical statistics over time by creating snapshots:
- **Daily snapshots**: Automatically created every day
- **Weekly snapshots**: Created weekly for long-term trends
- **Monthly snapshots**: Created monthly for strategic analysis

**Tracked Metrics**:
- Total number of reviews
- Average DDD score
- Average test count per review
- Average files per review
- Top repositories by review count

### 3. Dynamic Trend Indicators

Dashboard cards now show real trend indicators instead of hardcoded values:
- **Week-over-week trends**: Compares current stats with data from 7 days ago
- **Visual indicators**:
  - ↗ Green arrow: Metric increased
  - ↘ Red arrow: Metric decreased
  - → Gray arrow: No significant change
- **Percentage changes**: Shows exact percentage difference

## API Endpoints

### Get All Repositories
```
GET /api/repositories
```
Returns a list of all unique repository URLs from review sessions.

**Response**:
```json
{
  "success": true,
  "repositories": [
    "https://gitlab.com/owner/repo1",
    "https://gitlab.com/owner/repo2"
  ]
}
```

### Get Filtered Statistics
```
POST /api/statistics/filtered
Content-Type: application/json

{
  "repo_urls": ["https://gitlab.com/owner/repo1"]
}
```
Returns statistics for specific repositories.

**Response**:
```json
{
  "success": true,
  "statistics": {
    "total_sessions": 25,
    "recent_sessions": 5,
    "average_ddd_score": 75.5,
    "top_repos": [...],
    "filtered": true,
    "filter_count": 1
  }
}
```

### Get Filtered Sessions
```
POST /api/sessions/filtered
Content-Type: application/json

{
  "repo_urls": ["https://gitlab.com/owner/repo1"]
}
```
Returns review sessions for specific repositories.

### Get Trend Data
```
GET /api/statistics/trends
```
Returns trend information for key metrics (week-over-week comparison).

**Response**:
```json
{
  "success": true,
  "trends": {
    "total_sessions": {
      "current": 50,
      "previous": 45,
      "change": 5,
      "percentage_change": 11.1,
      "trend": "up",
      "days_back": 7
    },
    "average_ddd_score": {
      "current": 75.0,
      "previous": 70.0,
      "change": 5.0,
      "percentage_change": 7.14,
      "trend": "up",
      "days_back": 7
    }
  }
}
```

### Create Snapshot (Manual)
```
POST /api/statistics/snapshot
Content-Type: application/json

{
  "snapshot_type": "daily"
}
```
Manually create a statistics snapshot. Types: "daily", "weekly", "monthly".

## Automated Snapshot Creation

### Using the Snapshot Script

Run the snapshot script manually:
```bash
# Create daily snapshot
python create_daily_snapshot.py

# Create weekly snapshot
python create_daily_snapshot.py --weekly

# Create monthly snapshot
python create_daily_snapshot.py --monthly
```

### Setting up Automated Snapshots

#### Using Cron (Linux/Mac)

Edit your crontab:
```bash
crontab -e
```

Add these entries:
```bash
# Daily snapshot at midnight
0 0 * * * cd /path/to/pull_request_review && python create_daily_snapshot.py >> logs/snapshots.log 2>&1

# Weekly snapshot every Sunday at midnight
0 0 * * 0 cd /path/to/pull_request_review && python create_daily_snapshot.py --weekly >> logs/snapshots.log 2>&1

# Monthly snapshot on the 1st of each month at midnight
0 0 1 * * cd /path/to/pull_request_review && python create_daily_snapshot.py --monthly >> logs/snapshots.log 2>&1
```

#### Using Task Scheduler (Windows)

1. Open Task Scheduler
2. Create a new task
3. Set trigger to daily at midnight
4. Set action to run:
   ```
   python C:\path\to\pull_request_review\create_daily_snapshot.py
   ```

#### Using systemd Timer (Linux)

Create `/etc/systemd/system/pr-review-snapshot.service`:
```ini
[Unit]
Description=PR Review Daily Snapshot

[Service]
Type=oneshot
WorkingDirectory=/path/to/pull_request_review
ExecStart=/usr/bin/python3 /path/to/pull_request_review/create_daily_snapshot.py
User=your-username
```

Create `/etc/systemd/system/pr-review-snapshot.timer`:
```ini
[Unit]
Description=Run PR Review Snapshot Daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable pr-review-snapshot.timer
sudo systemctl start pr-review-snapshot.timer
```

## MongoDB Collections

### sessions
Stores individual code review sessions with results.

### statistics_snapshots
Stores historical snapshots of aggregate statistics.

**Schema**:
```javascript
{
  _id: ObjectId,
  snapshot_type: "daily" | "weekly" | "monthly",
  timestamp: ISODate,
  created_at: String (ISO format),
  total_sessions: Number,
  average_ddd_score: Number,
  average_test_count: Number,
  average_files: Number,
  top_repos: Array
}
```

## Troubleshooting

### Trends Show "No historical data available"

**Cause**: No snapshots exist from 7+ days ago.

**Solution**:
1. Manually create an initial snapshot: `python create_daily_snapshot.py`
2. Wait 7 days for trends to become available
3. OR manually create a backdated snapshot for testing (advanced users only)

### Filter dropdown is empty

**Cause**: No repositories have been reviewed yet.

**Solution**: Complete at least one code review first.

### Snapshots not being created automatically

**Cause**: Cron job or task scheduler not set up.

**Solution**:
1. Verify cron/task scheduler is configured correctly
2. Check logs for errors: `tail -f logs/snapshots.log`
3. Manually test the script: `python create_daily_snapshot.py`

## Best Practices

1. **Create initial snapshot**: Run `python create_daily_snapshot.py` after setting up the system
2. **Regular backups**: Back up MongoDB data regularly
3. **Monitor snapshots**: Check logs to ensure snapshots are being created
4. **Clean old snapshots**: Optionally delete snapshots older than 1 year to save space

## Example Usage Workflow

1. **Setup**: Configure automated snapshots using cron
2. **Daily**: Snapshots are created automatically at midnight
3. **Dashboard**: View real-time trends on the dashboard
4. **Filter**: Use multi-select to analyze specific repositories
5. **Compare**: Track week-over-week improvements in DDD scores and test coverage
