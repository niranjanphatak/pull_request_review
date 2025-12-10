# 🔗 Webhook Setup Guide

This guide explains how to set up automatic PR reviews using GitHub and GitLab webhooks.

## Overview

The PR Review system now supports automatic review triggering via webhooks. When a pull request is created or updated, the webhook will automatically start a code review in the background.

## 📋 Features

- ✅ Automatic review on PR creation
- ✅ Automatic review on PR updates
- ✅ Background processing (non-blocking)
- ✅ Results stored in MongoDB
- ✅ View results in Dashboard
- ✅ Support for both GitHub and GitLab

---

## 🐙 GitHub Webhook Setup

### 1. Prerequisites
- Your server must be publicly accessible (or use ngrok for testing)
- GitHub repository with admin access
- Server running on `http://your-server:5000`

### 2. Configure GitHub Webhook

1. Go to your GitHub repository
2. Click **Settings** → **Webhooks** → **Add webhook**
3. Configure the webhook:

```
Payload URL: http://your-server:5000/api/webhook/github
Content type: application/json
Secret: (optional, recommended for production)
SSL verification: Enable SSL verification (if using HTTPS)
```

4. Select events to trigger:
   - ☑️ Let me select individual events
   - ☑️ Pull requests

5. Click **Add webhook**

### 3. Webhook Events

The webhook will trigger reviews for these PR actions:
- `opened` - When a new PR is created
- `reopened` - When a closed PR is reopened
- `synchronize` - When new commits are pushed to the PR

### 4. Testing

Create a test PR in your repository. You should see:

**In GitHub:**
- Green checkmark ✓ next to the webhook delivery

**In Server Logs:**
```bash
📥 GitHub Webhook: PR opened - https://github.com/user/repo/pull/123
✅ Review completed for https://github.com/user/repo/pull/123
```

**In Dashboard:**
- New review appears in Recent Reviews
- Click "View Report" to see results

---

## 🦊 GitLab Webhook Setup

### 1. Prerequisites
- Your server must be publicly accessible (or use ngrok for testing)
- GitLab project with maintainer access
- Server running on `http://your-server:5000`

### 2. Configure GitLab Webhook

1. Go to your GitLab project
2. Click **Settings** → **Webhooks**
3. Configure the webhook:

```
URL: http://your-server:5000/api/webhook/gitlab
Secret Token: (optional, recommended for production)
```

4. Select trigger events:
   - ☑️ Merge request events

5. Enable SSL verification (if using HTTPS)

6. Click **Add webhook**

### 3. Webhook Events

The webhook will trigger reviews for these MR actions:
- `open` - When a new MR is created
- `reopen` - When a closed MR is reopened
- `update` - When the MR is updated with new commits

### 4. Testing

Create a test MR in your project. You should see:

**In GitLab:**
- Recent Deliveries shows successful webhook calls

**In Server Logs:**
```bash
📥 GitLab Webhook: MR open - https://gitlab.com/user/project/-/merge_requests/1
✅ Review completed for https://gitlab.com/user/project/-/merge_requests/1
```

**In Dashboard:**
- New review appears in Recent Reviews
- Click "View Report" to see results

---

## 🧪 Testing with ngrok

For local development, use ngrok to expose your local server:

### 1. Install ngrok
```bash
brew install ngrok  # macOS
# or download from https://ngrok.com/download
```

### 2. Start ngrok
```bash
ngrok http 5000
```

You'll get a public URL like: `https://abc123.ngrok.io`

### 3. Use ngrok URL in webhook
```
GitHub: https://abc123.ngrok.io/api/webhook/github
GitLab: https://abc123.ngrok.io/api/webhook/gitlab
```

---

## 📊 Webhook API Reference

### GitHub Webhook Endpoint

**URL:** `POST /api/webhook/github`

**Headers:**
```
X-GitHub-Event: pull_request
Content-Type: application/json
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "message": "Review started for PR: https://github.com/user/repo/pull/123",
  "pr_url": "https://github.com/user/repo/pull/123",
  "repo_url": "https://github.com/user/repo"
}
```

**Error Response (400/500):**
```json
{
  "success": false,
  "error": "Error message here"
}
```

### GitLab Webhook Endpoint

**URL:** `POST /api/webhook/gitlab`

**Headers:**
```
X-Gitlab-Event: Merge Request Hook
Content-Type: application/json
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "message": "Review started for MR: https://gitlab.com/user/project/-/merge_requests/1",
  "mr_url": "https://gitlab.com/user/project/-/merge_requests/1",
  "repo_url": "https://gitlab.com/user/project"
}
```

---

## 🔒 Security Best Practices

### 1. Use HTTPS
Always use HTTPS in production to encrypt webhook payloads.

### 2. Configure Webhook Secrets

**GitHub:**
```python
# Add to server.py
import hmac
import hashlib

def verify_github_signature(payload_body, signature_header, secret):
    if not signature_header:
        return False

    hash_object = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)
```

**GitLab:**
```python
# Add to server.py
def verify_gitlab_token(request_token, secret_token):
    return request_token == secret_token
```

### 3. Firewall Configuration
Restrict webhook endpoints to GitHub/GitLab IP ranges:
- [GitHub IP ranges](https://api.github.com/meta)
- [GitLab IP ranges](https://docs.gitlab.com/ee/user/gitlab_com/#ip-range)

### 4. Rate Limiting
Implement rate limiting to prevent abuse:
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@limiter.limit("10 per minute")
@app.route('/api/webhook/github', methods=['POST'])
def github_webhook():
    # ...
```

---

## 🐛 Troubleshooting

### Webhook not triggering

**Check server logs:**
```bash
tail -f server.log
```

**Verify webhook configuration:**
- URL is correct and accessible
- Content-Type is `application/json`
- Correct events are selected

**Test webhook delivery:**
- GitHub: Settings → Webhooks → Recent Deliveries → Redeliver
- GitLab: Settings → Webhooks → Test → Merge request events

### Reviews not appearing

**Check MongoDB connection:**
```bash
curl http://localhost:5000/health
```

Should return:
```json
{
  "status": "ok",
  "mongodb": "connected"
}
```

**Check API configuration:**
- Verify AI API key is set in `config.py`
- Verify GitHub token is set (if using private repos)

### Review fails silently

**Check server logs:**
Look for error messages starting with `❌`

**Common issues:**
- Invalid API key
- Rate limit exceeded
- Network connectivity issues
- Repository not accessible

---

## 📈 Production Deployment

For production use, consider:

### 1. Use a Task Queue
Replace threading with Celery or RQ:

```python
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def run_review_task(pr_url, repo_url):
    # Review logic here
    pass

# In webhook handler:
run_review_task.delay(pr_url, repo_url)
```

### 2. Use a Production WSGI Server
Replace Flask dev server with Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 server:app
```

### 3. Set Up Monitoring
- Use Sentry for error tracking
- Use Prometheus for metrics
- Set up log aggregation

### 4. Scale Horizontally
- Run multiple worker instances
- Use load balancer (nginx)
- Separate webhook receivers from review workers

---

## 🔄 CI/CD Integration Examples

### GitHub Actions
```yaml
name: PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger PR Review
        run: |
          curl -X POST \
            -H "Content-Type: application/json" \
            -d '{"pr_url": "${{ github.event.pull_request.html_url }}", "repo_url": "${{ github.event.repository.html_url }}"}' \
            https://your-server.com/api/review
```

### GitLab CI
```yaml
review:
  stage: test
  script:
    - |
      curl -X POST \
        -H "Content-Type: application/json" \
        -d "{\"pr_url\": \"$CI_MERGE_REQUEST_PROJECT_URL/-/merge_requests/$CI_MERGE_REQUEST_IID\", \"repo_url\": \"$CI_PROJECT_URL\"}" \
        https://your-server.com/api/review
  only:
    - merge_requests
```

---

## 📝 Viewing Results

After a webhook triggers a review:

1. **Dashboard** → See review in "Recent Reviews"
2. Click **"View Report"** to see full analysis
3. Download report as **JSON** or **Markdown**

Results include:
- Security analysis
- Bug detection
- Code quality assessment
- Test coverage analysis
- DDD compliance score
- Visual charts and metrics

---

## 📞 Support

If you encounter issues:

1. Check server logs for errors
2. Verify webhook configuration
3. Test with a simple PR/MR
4. Check GitHub/GitLab webhook delivery logs

For more help, see the main [README.md](README.md)
