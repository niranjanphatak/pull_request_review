"""
Flask server for JavaScript UI
"""
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os
from config import Config
from workflow.review_workflow import PRReviewWorkflow
from utils.session_storage import SessionStorage

# Initialize MongoDB session storage
session_storage = SessionStorage()


def analyze_structure(files):
    """Analyze code structure"""
    dirs = set()
    for f in files:
        filename = f.get('filename', '')
        if '/' in filename:
            dirs.add('/'.join(filename.split('/')[:-1]))

    return {
        'total': len(files),
        'dirs': len(dirs)
    }


def analyze_unit_tests(files):
    """Analyze unit test coverage"""
    test_files = [f for f in files if any(
        pattern in f.get('filename', '').lower()
        for pattern in ['test_', '_test.', 'test/', '/tests/', 'spec.']
    )]

    count = len(test_files)
    if count == 0:
        status = 'none'
    elif count < 3:
        status = 'low'
    elif count < 7:
        status = 'medium'
    else:
        status = 'good'

    return {
        'count': count,
        'status': status
    }


def analyze_ddd(files):
    """Analyze DDD practices"""
    indicators = {
        'entities': False,
        'repos': False,
        'services': False
    }

    for f in files:
        filename = f.get('filename', '').lower()
        if any(p in filename for p in ['entity', 'model', 'domain']):
            indicators['entities'] = True
        if any(p in filename for p in ['repository', 'repo']):
            indicators['repos'] = True
        if any(p in filename for p in ['service', 'handler']):
            indicators['services'] = True

    found = sum(indicators.values())
    score = (found / 3) * 100

    if score >= 66:
        rating = 'good'
    elif score >= 33:
        rating = 'medium'
    else:
        rating = 'low'

    return {
        'score': score,
        'rating': rating,
        'indicators': indicators
    }

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

# Store for tracking review progress
review_progress = {}
import uuid
import threading

@app.route('/api/review', methods=['POST'])
def review_pr():
    """
    API endpoint for PR review - starts async review and returns job ID
    Expects JSON: {"pr_url": "...", "repo_url": "..."}
    Returns JSON with job_id for tracking progress
    """
    try:
        # Get request data
        data = request.get_json()
        pr_url = data.get('pr_url')
        repo_url = data.get('repo_url')

        if not pr_url or not repo_url:
            return jsonify({
                'success': False,
                'error': 'Both pr_url and repo_url are required'
            }), 400

        # Validate configuration
        ai_key = Config.get_ai_api_key()
        if not ai_key or ai_key == 'your_api_key_here':
            return jsonify({
                'success': False,
                'error': 'AI API key not configured. Please set it in config.py'
            }), 400

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Initialize progress tracking
        review_progress[job_id] = {
            'status': 'starting',
            'progress': 0,
            'current_step': 'Initializing',
            'steps_completed': [],
            'pr_url': pr_url,
            'repo_url': repo_url,
            'error': None,
            'results': None
        }

        # Start review in background thread
        def run_review_with_progress():
            try:
                def update_progress(step, progress_pct):
                    """Callback to update progress"""
                    if job_id in review_progress:
                        review_progress[job_id]['current_step'] = step
                        review_progress[job_id]['progress'] = progress_pct
                        review_progress[job_id]['steps_completed'].append(step)
                        print(f"Progress Update [{job_id}]: {step} - {progress_pct}%")

                # Update: Starting
                update_progress('Initializing review workflow', 5)

                # Create workflow with progress callback
                workflow = PRReviewWorkflow(
                    ai_api_key=ai_key,
                    github_token=Config.GITHUB_TOKEN,
                    ai_model=Config.get_ai_model(),
                    ai_base_url=Config.get_ai_base_url(),
                    ai_temperature=Config.get_ai_temperature(),
                    progress_callback=update_progress
                )

                # Run workflow - it will call update_progress at each step
                result = workflow.run(pr_url, repo_url)

                # Check if successful
                status = result.get('status', '')
                if 'completed successfully' not in status.lower():
                    review_progress[job_id]['status'] = 'failed'
                    review_progress[job_id]['error'] = f'Review workflow failed: {status}'
                    return

                # Format response
                pr_details = result.get('pr_details', {})
                files = pr_details.get('files_changed', [])

                # Perform analysis
                structure_info = analyze_structure(files)
                test_analysis = analyze_unit_tests(files)
                ddd_analysis = analyze_ddd(files)

                update_progress('Preparing review report', 96)

                response_data = {
                    'success': True,
                    'results': {
                        'pr_details': {
                            'title': pr_details.get('title', ''),
                            'author': pr_details.get('author', ''),
                            'url': pr_url
                        },
                        'structure': {
                            'total': structure_info['total'],
                            'dirs': structure_info['dirs']
                        },
                        'test_analysis': {
                            'count': test_analysis['count'],
                            'status': test_analysis['status']
                        },
                        'ddd': {
                            'score': ddd_analysis['score'],
                            'rating': ddd_analysis['rating'],
                            'indicators': ddd_analysis['indicators']
                        },
                        'files': files,
                        'security': result.get('security_review', 'No security review available'),
                        'bugs': result.get('bug_review', 'No bug review available'),
                        'style': result.get('style_review', 'No style review available'),
                        'tests': result.get('test_suggestions', 'No test suggestions available')
                    }
                }

                update_progress('Saving to database', 98)

                # Save session to MongoDB
                session_data = {
                    'pr_url': pr_url,
                    'repo_url': repo_url,
                    'pr_title': pr_details.get('title', ''),
                    'pr_author': pr_details.get('author', ''),
                    'files_count': len(files),
                    'test_count': test_analysis['count'],
                    'ddd_score': ddd_analysis['score'],
                    'results': response_data['results'],
                    'triggered_by': 'manual'
                }
                session_id = session_storage.save_session(session_data)

                if session_id:
                    response_data['session_id'] = session_id

                # Mark as completed
                update_progress('Review completed successfully', 100)
                review_progress[job_id]['status'] = 'completed'
                review_progress[job_id]['results'] = response_data

                print(f"✅ Review completed for job {job_id}")

            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback_str = traceback.format_exc()

                print(f"❌ Error in review job {job_id}: {error_msg}")
                print(traceback_str)

                review_progress[job_id]['status'] = 'failed'
                review_progress[job_id]['error'] = f'Server error: {error_msg}'

        # Start background thread
        thread = threading.Thread(target=run_review_with_progress)
        thread.daemon = True
        thread.start()

        # Return job ID immediately
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Review started'
        }), 202

    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()

        print(f"Error starting review: {error_msg}")
        print(traceback_str)

        return jsonify({
            'success': False,
            'error': f'Server error: {error_msg}'
        }), 500

@app.route('/api/review/status/<job_id>', methods=['GET'])
def get_review_status(job_id):
    """
    Get the current status of a review job
    """
    if job_id not in review_progress:
        return jsonify({
            'success': False,
            'error': 'Job not found'
        }), 404

    job_data = review_progress[job_id]

    response = {
        'success': True,
        'status': job_data['status'],
        'progress': job_data['progress'],
        'current_step': job_data['current_step'],
        'steps_completed': job_data['steps_completed']
    }

    # Include results if completed
    if job_data['status'] == 'completed':
        response['results'] = job_data['results']

    # Include error if failed
    if job_data['status'] == 'failed':
        response['error'] = job_data['error']

    return jsonify(response)

@app.route('/api/sessions/recent', methods=['GET'])
def get_recent_sessions():
    """Get recent review sessions"""
    try:
        limit = request.args.get('limit', 10, type=int)
        sessions = session_storage.get_recent_sessions(limit=limit)
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session by ID"""
    try:
        session = session_storage.get_session(session_id)
        if session:
            return jsonify({
                'success': True,
                'session': session
            })
        return jsonify({
            'success': False,
            'error': 'Session not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sessions/statistics', methods=['GET'])
def get_statistics():
    """Get session statistics"""
    try:
        stats = session_storage.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    mongodb_status = 'connected' if session_storage.connected else 'disconnected'
    return jsonify({
        'status': 'ok',
        'mongodb': mongodb_status
    })

@app.route('/api/webhook/github', methods=['POST'])
def github_webhook():
    """
    GitHub webhook endpoint for pull request events
    Configure in GitHub: Settings > Webhooks > Add webhook
    Payload URL: http://your-server:5000/api/webhook/github
    Content type: application/json
    Events: Pull requests
    """
    try:
        # Get the event type
        event_type = request.headers.get('X-GitHub-Event')

        if event_type != 'pull_request':
            return jsonify({
                'success': False,
                'message': f'Unsupported event type: {event_type}'
            }), 400

        # Get the payload
        payload = request.get_json()

        # Check if it's a PR opened or reopened event
        action = payload.get('action')
        if action not in ['opened', 'reopened', 'synchronize']:
            return jsonify({
                'success': False,
                'message': f'Ignoring action: {action}'
            }), 200

        # Extract PR details
        pr = payload.get('pull_request', {})
        pr_url = pr.get('html_url')
        repo = payload.get('repository', {})
        repo_url = repo.get('html_url')

        if not pr_url or not repo_url:
            return jsonify({
                'success': False,
                'error': 'Missing PR URL or repository URL in webhook payload'
            }), 400

        print(f"📥 GitHub Webhook: PR {action} - {pr_url}")

        # Validate configuration
        ai_key = Config.get_ai_api_key()
        if not ai_key or ai_key == 'your_api_key_here':
            return jsonify({
                'success': False,
                'error': 'AI API key not configured'
            }), 500

        # Trigger the review asynchronously (in production, use a task queue like Celery)
        # For now, we'll start it in a background thread
        import threading

        def run_review():
            try:
                workflow = PRReviewWorkflow(
                    ai_api_key=ai_key,
                    github_token=Config.GITHUB_TOKEN,
                    ai_model=Config.get_ai_model(),
                    ai_base_url=Config.get_ai_base_url(),
                    ai_temperature=Config.get_ai_temperature()
                )

                result = workflow.run(pr_url, repo_url)

                # Save to database
                if result.get('status', '').lower().find('completed successfully') != -1:
                    pr_details = result.get('pr_details', {})
                    files = pr_details.get('files_changed', [])
                    test_analysis = analyze_unit_tests(files)
                    ddd_analysis = analyze_ddd(files)

                    session_data = {
                        'pr_url': pr_url,
                        'repo_url': repo_url,
                        'pr_title': pr_details.get('title', ''),
                        'pr_author': pr_details.get('author', ''),
                        'files_count': len(files),
                        'test_count': test_analysis['count'],
                        'ddd_score': ddd_analysis['score'],
                        'triggered_by': 'github_webhook',
                        'results': {
                            'pr_details': pr_details,
                            'structure': analyze_structure(files),
                            'test_analysis': test_analysis,
                            'ddd': ddd_analysis,
                            'files': files,
                            'security': result.get('security_review', ''),
                            'bugs': result.get('bug_review', ''),
                            'style': result.get('style_review', ''),
                            'tests': result.get('test_suggestions', '')
                        }
                    }
                    session_storage.save_session(session_data)
                    print(f"✅ Review completed for {pr_url}")
                else:
                    print(f"❌ Review failed for {pr_url}: {result.get('status')}")

            except Exception as e:
                print(f"❌ Error in background review: {str(e)}")

        # Start review in background
        thread = threading.Thread(target=run_review)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': f'Review started for PR: {pr_url}',
            'pr_url': pr_url,
            'repo_url': repo_url
        }), 202  # 202 Accepted

    except Exception as e:
        print(f"Error processing GitHub webhook: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/webhook/gitlab', methods=['POST'])
def gitlab_webhook():
    """
    GitLab webhook endpoint for merge request events
    Configure in GitLab: Settings > Webhooks > Add new webhook
    URL: http://your-server:5000/api/webhook/gitlab
    Trigger: Merge request events
    """
    try:
        # Get the event type
        event_type = request.headers.get('X-Gitlab-Event')

        if event_type != 'Merge Request Hook':
            return jsonify({
                'success': False,
                'message': f'Unsupported event type: {event_type}'
            }), 400

        # Get the payload
        payload = request.get_json()

        # Extract MR details
        object_attributes = payload.get('object_attributes', {})
        action = object_attributes.get('action')

        if action not in ['open', 'reopen', 'update']:
            return jsonify({
                'success': False,
                'message': f'Ignoring action: {action}'
            }), 200

        mr_url = object_attributes.get('url')
        project = payload.get('project', {})
        repo_url = project.get('web_url')

        if not mr_url or not repo_url:
            return jsonify({
                'success': False,
                'error': 'Missing MR URL or repository URL in webhook payload'
            }), 400

        print(f"📥 GitLab Webhook: MR {action} - {mr_url}")

        # Validate configuration
        ai_key = Config.get_ai_api_key()
        if not ai_key or ai_key == 'your_api_key_here':
            return jsonify({
                'success': False,
                'error': 'AI API key not configured'
            }), 500

        # Trigger the review asynchronously
        import threading

        def run_review():
            try:
                workflow = PRReviewWorkflow(
                    ai_api_key=ai_key,
                    github_token=Config.GITHUB_TOKEN,
                    ai_model=Config.get_ai_model(),
                    ai_base_url=Config.get_ai_base_url(),
                    ai_temperature=Config.get_ai_temperature()
                )

                result = workflow.run(mr_url, repo_url)

                # Save to database
                if result.get('status', '').lower().find('completed successfully') != -1:
                    pr_details = result.get('pr_details', {})
                    files = pr_details.get('files_changed', [])
                    test_analysis = analyze_unit_tests(files)
                    ddd_analysis = analyze_ddd(files)

                    session_data = {
                        'pr_url': mr_url,
                        'repo_url': repo_url,
                        'pr_title': pr_details.get('title', ''),
                        'pr_author': pr_details.get('author', ''),
                        'files_count': len(files),
                        'test_count': test_analysis['count'],
                        'ddd_score': ddd_analysis['score'],
                        'triggered_by': 'gitlab_webhook',
                        'results': {
                            'pr_details': pr_details,
                            'structure': analyze_structure(files),
                            'test_analysis': test_analysis,
                            'ddd': ddd_analysis,
                            'files': files,
                            'security': result.get('security_review', ''),
                            'bugs': result.get('bug_review', ''),
                            'style': result.get('style_review', ''),
                            'tests': result.get('test_suggestions', '')
                        }
                    }
                    session_storage.save_session(session_data)
                    print(f"✅ Review completed for {mr_url}")
                else:
                    print(f"❌ Review failed for {mr_url}: {result.get('status')}")

            except Exception as e:
                print(f"❌ Error in background review: {str(e)}")

        # Start review in background
        thread = threading.Thread(target=run_review)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': f'Review started for MR: {mr_url}',
            'mr_url': mr_url,
            'repo_url': repo_url
        }), 202  # 202 Accepted

    except Exception as e:
        print(f"Error processing GitLab webhook: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 Starting AI PR Code Review Server")
    print("=" * 80)
    print(f"AI Model: {Config.get_ai_model()}")
    print(f"AI Base URL: {Config.get_ai_base_url()}")
    print(f"GitHub Token: {'Set' if Config.GITHUB_TOKEN else 'Not set (public repos only)'}")
    print()
    print("Server running at: http://localhost:5000")
    print("Open your browser and navigate to the URL above")
    print("=" * 80)
    print()

    app.run(debug=True, host='0.0.0.0', port=5000)
