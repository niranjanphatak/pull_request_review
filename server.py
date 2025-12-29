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
    API endpoint for code review - starts async review and returns job ID
    Supports GitLab MRs, GitHub PRs, and other Git platforms
    Expects JSON: {"pr_url": "...", "repo_url": "..."}
    Returns JSON with job_id for tracking progress
    """
    try:
        # Get request data
        data = request.get_json()
        pr_url = data.get('pr_url')
        repo_url = data.get('repo_url')
        analyze_target_branch = data.get('analyze_target_branch', False)
        enabled_stages = data.get('enabled_stages', {
            'security': True,
            'bugs': True,
            'style': True,
            'tests': True
        })

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
            'analyze_target_branch': analyze_target_branch,
            'enabled_stages': enabled_stages,
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
                result = workflow.run(pr_url, repo_url, analyze_target_branch, enabled_stages)

                # Check if successful
                status = result.get('status', '')
                if 'completed successfully' not in status.lower():
                    review_progress[job_id]['status'] = 'failed'
                    review_progress[job_id]['error'] = f'Review workflow failed: {status}'
                    return

                # Format response
                pr_details = result.get('pr_details', {})
                files = pr_details.get('files_changed', [])

                print(f"Server: Processing {len(files)} files from PR details")
                if len(files) > 0:
                    sample_file = files[0]
                    print(f"Server: Sample file structure: {sample_file.keys()}")
                    print(f"Server: Sample file: {sample_file.get('filename')} - additions={sample_file.get('additions')}, deletions={sample_file.get('deletions')}")

                # Perform analysis
                structure_info = analyze_structure(files)
                test_analysis = analyze_unit_tests(files)
                ddd_analysis = analyze_ddd(files)

                update_progress('Preparing review report', 96)

                response_data = {
                    'success': True,
                    'results': {
                        'pr_details': pr_details,
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
                        'tests': result.get('test_suggestions', 'No test suggestions available'),
                        'target_branch_analysis': result.get('target_branch_analysis'),
                        'token_usage': result.get('token_usage', {})
                    }
                }

                print(f"Server: Response data files count: {len(response_data['results']['files'])}")

                update_progress('Saving to database', 98)

                # Get prompt versions from workflow
                prompt_versions = workflow.review_agents.get_prompt_versions()

                # Save session to MongoDB
                # Extract branch names (support both GitLab and GitHub formats)
                source_branch = pr_details.get('source_branch') or pr_details.get('head_branch') or pr_details.get('head', {}).get('ref')
                target_branch = pr_details.get('target_branch') or pr_details.get('base_branch') or pr_details.get('base', {}).get('ref')

                session_data = {
                    'pr_url': pr_url,
                    'repo_url': repo_url,
                    'pr_title': pr_details.get('title', ''),
                    'pr_author': pr_details.get('author', ''),
                    'source_branch': source_branch,
                    'target_branch': target_branch,
                    'files_count': len(files),
                    'test_count': test_analysis['count'],
                    'ddd_score': ddd_analysis['score'],
                    'results': response_data['results'],
                    'triggered_by': 'manual',
                    'status': result.get('status', 'completed'),
                    'token_usage': result.get('token_usage', {}),
                    'prompt_versions': {
                        'security': prompt_versions.get('security', {'version': '1.0.0', 'description': '', 'criteria': []}),
                        'bugs': prompt_versions.get('bug', {'version': '1.0.0', 'description': '', 'criteria': []}),
                        'style': prompt_versions.get('style', {'version': '1.0.0', 'description': '', 'criteria': []}),
                        'tests': prompt_versions.get('test', {'version': '1.0.0', 'description': '', 'criteria': []})
                    }
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

@app.route('/api/repositories', methods=['GET'])
def get_repositories():
    """Get all unique repositories from sessions"""
    try:
        repos = session_storage.get_all_repositories()
        return jsonify({
            'success': True,
            'repositories': repos
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sessions/filtered', methods=['POST'])
def get_filtered_sessions():
    """Get sessions filtered by repositories"""
    try:
        data = request.get_json()
        repo_urls = data.get('repo_urls', [])

        if not repo_urls:
            # Return all sessions if no filter
            sessions = session_storage.get_recent_sessions(limit=100)
        else:
            sessions = session_storage.get_sessions_by_repositories(repo_urls)

        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/statistics/filtered', methods=['POST'])
def get_filtered_statistics():
    """Get statistics for selected repositories"""
    try:
        data = request.get_json()
        repo_urls = data.get('repo_urls', [])

        stats = session_storage.get_filtered_statistics(repo_urls)
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/statistics/snapshot', methods=['POST'])
def create_statistics_snapshot():
    """Manually create a statistics snapshot"""
    try:
        data = request.get_json() or {}
        snapshot_type = data.get('snapshot_type', 'daily')

        snapshot_id = session_storage.save_statistics_snapshot(snapshot_type)

        if snapshot_id:
            return jsonify({
                'success': True,
                'snapshot_id': snapshot_id,
                'message': f'{snapshot_type.capitalize()} snapshot created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create snapshot'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/statistics/trends', methods=['GET'])
def get_trends():
    """Get trend data for dashboard metrics"""
    try:
        # Calculate trends for key metrics
        trends = {
            'total_sessions': session_storage.calculate_trend('total_sessions', days_back=7),
            'average_ddd_score': session_storage.calculate_trend('average_ddd_score', days_back=7)
        }

        return jsonify({
            'success': True,
            'trends': trends
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sessions/token-stats', methods=['GET'])
def get_sessions_with_token_stats():
    """Get recent sessions with token usage statistics for the statistics table"""
    try:
        limit = int(request.args.get('limit', 50))
        sessions = session_storage.get_sessions_with_token_stats(limit)

        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/prompt-versions', methods=['GET'])
def get_prompt_versions():
    """Get prompt versions for all stages or a specific stage"""
    try:
        stage = request.args.get('stage', None)

        if stage:
            # Get versions for a specific stage
            versions = session_storage.get_all_prompt_versions(stage)
            return jsonify({stage: versions})
        else:
            # Get versions for all stages
            all_versions = {}
            for stage_name in ['security', 'bugs', 'style', 'tests']:
                versions = session_storage.get_all_prompt_versions(stage_name)
                all_versions[stage_name] = versions

            return jsonify(all_versions)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/onboarding', methods=['POST'])
def create_onboarding():
    """Create new onboarding entry"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('team_name'):
            return jsonify({
                'success': False,
                'error': 'Team name is required'
            }), 400

        if not data.get('repositories') or len(data.get('repositories', [])) == 0:
            return jsonify({
                'success': False,
                'error': 'At least one repository is required'
            }), 400

        # Save to database
        onboarding_id = session_storage.save_onboarding(data)

        if onboarding_id:
            return jsonify({
                'success': True,
                'onboarding_id': onboarding_id,
                'message': 'Onboarding saved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save onboarding'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/onboarding', methods=['GET'])
def get_onboarding():
    """Get onboarding data (latest or by ID)"""
    try:
        onboarding_id = request.args.get('id')

        if onboarding_id:
            data = session_storage.get_onboarding(onboarding_id)
        else:
            data = session_storage.get_onboarding()

        if data:
            return jsonify({
                'success': True,
                'data': data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No onboarding data found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/onboarding/all', methods=['GET'])
def get_all_onboardings():
    """Get all onboarding entries"""
    try:
        limit = int(request.args.get('limit', 50))
        data = session_storage.get_all_onboardings(limit)

        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/onboarding/<onboarding_id>', methods=['PUT'])
def update_onboarding(onboarding_id):
    """Update existing onboarding"""
    try:
        data = request.get_json()

        # Remove _id if present (can't update _id)
        data.pop('_id', None)

        success = session_storage.update_onboarding(onboarding_id, data)

        if success:
            return jsonify({
                'success': True,
                'message': 'Onboarding updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update onboarding'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/onboarding/<onboarding_id>', methods=['DELETE'])
def delete_onboarding(onboarding_id):
    """Delete onboarding entry"""
    try:
        success = session_storage.delete_onboarding(onboarding_id)

        if success:
            return jsonify({
                'success': True,
                'message': 'Onboarding deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete onboarding'
            }), 500

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

# Store for tracking code analysis progress
analysis_progress = {}

@app.route('/api/analyze-repo', methods=['POST'])
def analyze_repository():
    """
    API endpoint for code analysis and test generation
    Expects JSON: {"repo_url": "...", "branch_name": "...", "generate_tests": true/false}
    Returns JSON with task_id for tracking progress
    """
    try:
        import subprocess
        import tempfile
        import shutil
        from pathlib import Path

        # Get request data
        data = request.get_json()
        repo_url = data.get('repo_url')
        branch_name = data.get('branch_name', 'main')
        generate_tests = data.get('generate_tests', False)
        ai_analysis = data.get('ai_analysis', False)

        if not repo_url:
            return jsonify({
                'success': False,
                'error': 'repo_url is required'
            }), 400

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Initialize progress tracking
        analysis_progress[task_id] = {
            'status': 'in_progress',
            'progress': 0,
            'message': 'Starting analysis...',
            'error': None,
            'result': None
        }

        # Start analysis in background thread
        def run_analysis():
            temp_dir = None
            try:
                # Update progress: Cloning
                analysis_progress[task_id]['message'] = 'Cloning repository...'
                analysis_progress[task_id]['progress'] = 10

                # Create temp_repos directory in project root
                project_root = Path(__file__).parent
                temp_repos_dir = project_root / 'temp_repos'
                temp_repos_dir.mkdir(exist_ok=True)

                # Clean up old clones of the same repository and branch
                import hashlib
                repo_hash = hashlib.md5(f"{repo_url}:{branch_name}".encode()).hexdigest()[:8]

                print(f"🧹 Cleaning up old clones for {repo_url} (branch: {branch_name})...")

                # Find and remove old directories for this repo/branch combination
                for existing_dir in temp_repos_dir.glob(f'analysis_*'):
                    if existing_dir.is_dir():
                        try:
                            # Check if this directory contains the same repo/branch
                            git_config = existing_dir / '.git' / 'config'
                            if git_config.exists():
                                with open(git_config, 'r') as f:
                                    config_content = f.read()
                                    # Check if URL matches
                                    if repo_url in config_content:
                                        # Check branch by reading HEAD
                                        head_file = existing_dir / '.git' / 'HEAD'
                                        if head_file.exists():
                                            with open(head_file, 'r') as f:
                                                head_content = f.read().strip()
                                                # Extract branch name from HEAD
                                                if f'refs/heads/{branch_name}' in head_content:
                                                    print(f"   🗑️  Removing old clone: {existing_dir.name}")
                                                    shutil.rmtree(existing_dir)
                        except Exception as e:
                            print(f"   ⚠️  Could not check/remove {existing_dir.name}: {e}")
                            continue

                # Create unique directory for this analysis
                temp_dir = temp_repos_dir / f'analysis_{task_id}'
                temp_dir.mkdir(exist_ok=True)

                # Clone repository
                clone_cmd = ['git', 'clone', '--depth', '1', '--branch', branch_name, repo_url, str(temp_dir)]
                result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=300)

                if result.returncode != 0:
                    raise Exception(f"Git clone failed: {result.stderr}")

                # Update progress: Analyzing
                analysis_progress[task_id]['message'] = 'Analyzing code structure...'
                analysis_progress[task_id]['progress'] = 30

                # Analyze repository
                repo_path = Path(temp_dir)

                # Count files
                all_files = []
                code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rb', '.php', '.cs', '.cpp', '.c', '.h', '.hpp'}
                test_patterns = ['test_', '_test.', 'test/', '/tests/', 'spec.', '.spec.', '.test.']

                for file_path in repo_path.rglob('*'):
                    if file_path.is_file():
                        # Skip hidden files and common directories
                        if any(part.startswith('.') for part in file_path.parts):
                            continue
                        if any(exclude in str(file_path) for exclude in ['node_modules', '__pycache__', 'venv', 'dist', 'build']):
                            continue
                        all_files.append(file_path)

                total_files = len(all_files)
                code_files = [f for f in all_files if f.suffix in code_extensions]
                test_files = [f for f in code_files if any(pattern in str(f).lower() for pattern in test_patterns)]

                # Separate non-test code files (actual source code)
                non_test_code_files = [f for f in code_files if not any(pattern in str(f).lower() for pattern in test_patterns)]

                code_file_count = len(code_files)
                test_file_count = len(test_files)
                non_test_code_file_count = len(non_test_code_files)

                # Calculate test coverage estimate (test files / non-test code files)
                # This gives a more accurate representation of how much source code has tests
                test_coverage = round((test_file_count / non_test_code_file_count * 100) if non_test_code_file_count > 0 else 0, 1)

                analysis_progress[task_id]['message'] = 'Detecting code quality issues...'
                analysis_progress[task_id]['progress'] = 50

                # Detect common issues
                issues = []

                # Check for missing README
                has_readme = any(f.name.lower().startswith('readme') for f in all_files)
                if not has_readme:
                    issues.append({
                        'severity': 'Medium',
                        'file': 'Root directory',
                        'description': 'No README file found',
                        'suggestion': 'Add a README.md to document the project'
                    })

                # Check for missing .gitignore
                has_gitignore = any(f.name == '.gitignore' for f in all_files)
                if not has_gitignore:
                    issues.append({
                        'severity': 'Low',
                        'file': 'Root directory',
                        'description': 'No .gitignore file found',
                        'suggestion': 'Add a .gitignore to exclude unnecessary files'
                    })

                # Check for low test coverage
                if test_coverage < 30 and code_file_count > 0:
                    issues.append({
                        'severity': 'High',
                        'file': 'Repository',
                        'description': f'Low test coverage ({test_coverage}%)',
                        'suggestion': 'Add more unit tests to improve code quality'
                    })
                elif test_coverage < 60 and code_file_count > 0:
                    issues.append({
                        'severity': 'Medium',
                        'file': 'Repository',
                        'description': f'Moderate test coverage ({test_coverage}%)',
                        'suggestion': 'Consider adding more tests for critical paths'
                    })

                # Log coverage calculation for debugging
                print(f"📊 BEFORE Analysis:")
                print(f"   Total files: {total_files}")
                print(f"   All code files (including tests): {code_file_count}")
                print(f"   Non-test code files: {non_test_code_file_count}")
                print(f"   Test files: {test_file_count}")
                print(f"   Coverage: {test_file_count}/{non_test_code_file_count} = {test_coverage}%")

                # AI-Enhanced Code Analysis (Optional)
                ai_quality_issues = []
                if ai_analysis:
                    analysis_progress[task_id]['message'] = 'Running AI code quality analysis...'
                    analysis_progress[task_id]['progress'] = 55

                    print(f"🤖 Running AI-Enhanced Analysis...")

                    # Get AI API key
                    ai_key = Config.get_ai_api_key()

                    if ai_key and ai_key != 'your_api_key_here':
                        try:
                            from langchain_openai import ChatOpenAI

                            # Initialize AI model
                            llm = ChatOpenAI(
                                model=Config.get_ai_model(),
                                api_key=ai_key,
                                base_url=Config.get_ai_base_url(),
                                temperature=Config.get_ai_analysis_temperature()
                            )

                            # Analyze up to 3 files without tests for quality issues
                            files_to_analyze = [f for f in non_test_code_files if not any(pattern in str(f).lower() for pattern in test_patterns)][:3]

                            for idx, file_path in enumerate(files_to_analyze):
                                analysis_progress[task_id]['message'] = f'AI analyzing code quality ({idx+1}/{len(files_to_analyze)})...'
                                analysis_progress[task_id]['progress'] = 55 + (idx / len(files_to_analyze) * 10)

                                try:
                                    # Read file content
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        code_content = f.read()

                                    # Skip if file is too large
                                    if len(code_content) > 5000:
                                        code_content = code_content[:5000]

                                    # AI analysis prompt
                                    ai_prompt = f"""Analyze this code for quality issues, security vulnerabilities, and complexity. Be critical and thorough.

File: {file_path.name}
Code:
```
{code_content}
```

You MUST provide a detailed analysis in JSON format with this EXACT structure (no markdown, just JSON):
{{
  "security_issues": ["issue1", "issue2"],
  "code_quality": ["quality1", "quality2"],
  "complexity": "low|medium|high",
  "suggestions": ["suggestion1", "suggestion2"]
}}

CRITICAL: Analyze EVERY aspect and find potential issues:

Security Analysis:
- Hardcoded credentials, API keys, secrets, passwords
- SQL injection vulnerabilities (string concatenation in queries)
- XSS risks (unsanitized user input in HTML)
- Path traversal risks (user input in file paths)
- Command injection risks
- Weak cryptography or insecure random
- Missing authentication/authorization checks
- Insecure deserialization

Code Quality Analysis:
- Functions longer than 20 lines (should be broken down)
- Duplicated code blocks
- Magic numbers without constants
- Deep nesting (>3 levels)
- Complex conditionals that need refactoring
- Missing error handling (try/catch, null checks)
- Poor variable/function naming
- Commented-out code
- Missing input validation
- Global variables misuse

Performance Issues:
- N+1 query patterns
- Inefficient loops or algorithms
- Missing caching opportunities
- Memory leaks
- Blocking I/O in async code

Best Practices:
- Missing type hints/annotations
- Missing docstrings/comments
- Violation of SOLID principles
- Missing unit tests
- Code that's hard to test (tight coupling)

IMPORTANT: Even for well-written code, find at least 2-3 suggestions for improvement. Be thorough and critical."""

                                    response = llm.invoke(ai_prompt)
                                    ai_result = response.content

                                    print(f"   📝 AI Response for {file_path.name}:")
                                    print(f"   {ai_result[:500]}...")  # Show first 500 chars

                                    # Parse AI response and add to issues
                                    try:
                                        import json
                                        import re

                                        # Extract JSON from response (might have markdown formatting)
                                        json_match = re.search(r'\{.*\}', ai_result, re.DOTALL)
                                        if json_match:
                                            ai_data = json.loads(json_match.group(0))

                                            print(f"   🔍 Parsed AI data: {ai_data}")
                                            print(f"   📊 Found: {len(ai_data.get('security_issues', []))} security, {len(ai_data.get('code_quality', []))} quality issues")

                                            # Add security issues
                                            for issue in ai_data.get('security_issues', [])[:2]:
                                                ai_quality_issues.append({
                                                    'severity': 'High',
                                                    'file': str(file_path.relative_to(repo_path)),
                                                    'description': f'Security: {issue}',
                                                    'suggestion': 'Review and fix security vulnerability',
                                                    'source': 'AI Analysis'
                                                })

                                            # Add code quality issues
                                            for issue in ai_data.get('code_quality', [])[:2]:
                                                ai_quality_issues.append({
                                                    'severity': 'Medium',
                                                    'file': str(file_path.relative_to(repo_path)),
                                                    'description': f'Quality: {issue}',
                                                    'suggestion': 'Refactor to improve code quality',
                                                    'source': 'AI Analysis'
                                                })

                                            # Add complexity warning
                                            if ai_data.get('complexity') == 'high':
                                                ai_quality_issues.append({
                                                    'severity': 'Medium',
                                                    'file': str(file_path.relative_to(repo_path)),
                                                    'description': 'High code complexity detected',
                                                    'suggestion': ai_data.get('suggestions', ['Consider breaking down into smaller functions'])[0] if ai_data.get('suggestions') else 'Consider refactoring',
                                                    'source': 'AI Analysis'
                                                })

                                            print(f"   ✓ AI analyzed: {file_path.relative_to(repo_path)}")
                                        else:
                                            print(f"   ⚠ No JSON found in AI response for {file_path.name}")
                                            print(f"   Raw response: {ai_result[:200]}...")
                                    except (json.JSONDecodeError, Exception) as parse_error:
                                        print(f"   ⚠ Could not parse AI response for {file_path.name}: {parse_error}")
                                        print(f"   Raw response: {ai_result[:200]}...")

                                except Exception as e:
                                    print(f"   ⚠ AI analysis error for {file_path.name}: {e}")
                                    continue

                            print(f"🤖 AI Analysis Complete: Found {len(ai_quality_issues)} issues")

                        except Exception as e:
                            print(f"AI analysis failed: {e}")
                            ai_quality_issues.append({
                                'severity': 'Low',
                                'file': 'AI Analysis',
                                'description': f'AI analysis failed: {str(e)}',
                                'suggestion': 'Check AI API configuration'
                            })
                    else:
                        ai_quality_issues.append({
                            'severity': 'Low',
                            'file': 'AI Analysis',
                            'description': 'AI analysis enabled but API key not configured',
                            'suggestion': 'Configure AI_API_KEY in config.py'
                        })

                # Merge AI issues with local issues
                all_issues = issues + ai_quality_issues

                # Prepare initial analysis result (BEFORE test generation)
                analysis_result_before = {
                    'total_files': total_files,
                    'code_files': code_file_count,
                    'non_test_code_files': non_test_code_file_count,
                    'test_files': test_file_count,
                    'test_coverage': test_coverage,
                    'files_without_tests': len([f for f in code_files if not any(pattern in str(f).lower() for pattern in test_patterns) and not any(f.stem in tf.stem for tf in test_files)]),
                    'issues': all_issues,
                    'ai_analysis_enabled': ai_analysis,
                    'ai_issues_found': len(ai_quality_issues)
                }

                test_cases = []
                analysis_result_after = None

                # Generate test cases if requested
                if generate_tests:
                    analysis_progress[task_id]['message'] = 'Generating test cases...'
                    analysis_progress[task_id]['progress'] = 70

                    # Get AI API key
                    ai_key = Config.get_ai_api_key()

                    if ai_key and ai_key != 'your_api_key_here':
                        try:
                            from langchain_openai import ChatOpenAI

                            # Load test generation prompt from file
                            prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
                            test_gen_prompt_file = os.path.join(prompts_dir, 'test_generation.txt')

                            test_gen_prompt_template = ""
                            try:
                                with open(test_gen_prompt_file, 'r', encoding='utf-8') as f:
                                    test_gen_prompt_template = f.read().strip()
                            except Exception as e:
                                print(f"Warning: Could not load test generation prompt: {e}")
                                # Fallback to inline prompt if file not found
                                test_gen_prompt_template = """Generate a unit test file for the following code.
The test should use common testing frameworks for the language and cover the main functionality.
Generate a complete test file that can be run immediately. Include imports and setup code."""

                            # Initialize AI model
                            llm = ChatOpenAI(
                                model=Config.get_ai_model(),
                                api_key=ai_key,
                                base_url=Config.get_ai_base_url(),
                                temperature=Config.get_ai_temperature()
                            )

                            # Find files that need tests
                            files_needing_tests = []
                            for code_file in code_files:
                                if not any(pattern in str(code_file).lower() for pattern in test_patterns):
                                    # Check if there's a corresponding test file
                                    has_test = False
                                    for test_file in test_files:
                                        if code_file.stem in test_file.stem:
                                            has_test = True
                                            break

                                    if not has_test:
                                        files_needing_tests.append(code_file)

                            # Limit to 5 files for performance
                            files_to_test = files_needing_tests[:5]

                            for idx, file_path in enumerate(files_to_test):
                                analysis_progress[task_id]['message'] = f'Generating tests ({idx+1}/{len(files_to_test)})...'
                                analysis_progress[task_id]['progress'] = 70 + (idx / len(files_to_test) * 20)

                                try:
                                    # Read file content
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        code_content = f.read()

                                    # Skip if file is too large
                                    if len(code_content) > 10000:
                                        continue

                                    # Generate test using AI with loaded prompt template
                                    prompt = f"""{test_gen_prompt_template}

File: {file_path.name}
Code:
```
{code_content[:5000]}
```
"""

                                    response = llm.invoke(prompt)
                                    test_code = response.content

                                    # Determine test filename and location
                                    # Write test file in the same directory as the source file
                                    test_filename = f"test_{file_path.name}"
                                    test_file_path = file_path.parent / test_filename

                                    # Write test file to repository
                                    with open(test_file_path, 'w', encoding='utf-8') as f:
                                        f.write(test_code)

                                    # Get relative path from repo root for display
                                    relative_test_path = test_file_path.relative_to(repo_path)

                                    test_cases.append({
                                        'filename': str(relative_test_path),
                                        'code': test_code,
                                        'description': f'Unit tests for {file_path.name}',
                                        'written_to': str(test_file_path)
                                    })

                                    print(f"✅ Generated test file: {relative_test_path}")

                                except Exception as e:
                                    print(f"Error generating test for {file_path}: {e}")
                                    continue

                        except Exception as e:
                            print(f"Error in test generation: {e}")
                            issues.append({
                                'severity': 'Medium',
                                'file': 'Test Generation',
                                'description': f'Test generation failed: {str(e)}',
                                'suggestion': 'Check AI API configuration'
                            })

                # Re-scan repository to get updated metrics AFTER test generation
                if test_cases:
                    analysis_progress[task_id]['message'] = 'Calculating updated metrics...'
                    analysis_progress[task_id]['progress'] = 95

                    # Re-scan for test files (now includes generated ones)
                    all_files_after = []
                    for file_path in repo_path.rglob('*'):
                        if file_path.is_file():
                            if any(part.startswith('.') for part in file_path.parts):
                                continue
                            if any(exclude in str(file_path) for exclude in ['node_modules', '__pycache__', 'venv', 'dist', 'build']):
                                continue
                            all_files_after.append(file_path)

                    code_files_after = [f for f in all_files_after if f.suffix in code_extensions]
                    test_files_after = [f for f in code_files_after if any(pattern in str(f).lower() for pattern in test_patterns)]

                    # Separate non-test code files (actual source code)
                    non_test_code_files_after = [f for f in code_files_after if not any(pattern in str(f).lower() for pattern in test_patterns)]

                    test_file_count_after = len(test_files_after)
                    non_test_code_file_count_after = len(non_test_code_files_after)

                    # Calculate test coverage estimate (test files / non-test code files)
                    test_coverage_after = round((test_file_count_after / non_test_code_file_count_after * 100) if non_test_code_file_count_after > 0 else 0, 1)

                    # Log coverage calculation for debugging
                    print(f"📊 AFTER Analysis:")
                    print(f"   Total files: {len(all_files_after)}")
                    print(f"   All code files (including tests): {len(code_files_after)}")
                    print(f"   Non-test code files: {non_test_code_file_count_after}")
                    print(f"   Test files: {test_file_count_after}")
                    print(f"   Coverage: {test_file_count_after}/{non_test_code_file_count_after} = {test_coverage_after}%")
                    print(f"📈 IMPROVEMENT: {test_file_count} → {test_file_count_after} tests (+{test_file_count_after - test_file_count}), {test_coverage}% → {test_coverage_after}% coverage (↑{round(test_coverage_after - test_coverage, 1)}%)")

                    analysis_result_after = {
                        'total_files': len(all_files_after),
                        'code_files': len(code_files_after),
                        'non_test_code_files': non_test_code_file_count_after,
                        'test_files': test_file_count_after,
                        'test_coverage': test_coverage_after,
                        'tests_generated': len(test_cases)
                    }

                # Mark as completed
                analysis_progress[task_id]['status'] = 'completed'
                analysis_progress[task_id]['progress'] = 100
                analysis_progress[task_id]['message'] = 'Analysis complete!'
                analysis_progress[task_id]['result'] = {
                    'analysis_before': analysis_result_before,
                    'analysis_after': analysis_result_after,
                    'test_cases': test_cases,
                    'repo_path': str(temp_dir) if temp_dir else None,
                    'comparison': {
                        'tests_added': len(test_cases),
                        'coverage_improvement': round(analysis_result_after['test_coverage'] - analysis_result_before['test_coverage'], 1) if analysis_result_after else 0,
                        'files_now_covered': len(test_cases)
                    } if analysis_result_after else None
                }

                # Print summary
                if temp_dir:
                    print(f"📁 Repository cloned to: {temp_dir}")
                    if test_cases:
                        print(f"✅ Generated {len(test_cases)} test files in the repository")

            except Exception as e:
                analysis_progress[task_id]['status'] = 'failed'
                analysis_progress[task_id]['error'] = str(e)
                analysis_progress[task_id]['message'] = f'Analysis failed: {str(e)}'
                print(f"Analysis error: {e}")
                import traceback
                traceback.print_exc()

                # Cleanup on error only
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        print(f"🗑️ Cleaned up temp directory due to error: {temp_dir}")
                    except Exception as cleanup_error:
                        print(f"Error cleaning up temp directory: {cleanup_error}")

        # Start analysis in background thread
        thread = threading.Thread(target=run_analysis)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Analysis started'
        })

    except Exception as e:
        print(f"Error starting analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analyze-status/<task_id>', methods=['GET'])
def get_analysis_status(task_id):
    """
    Get status of code analysis task
    Returns progress, status, and results when completed
    """
    if task_id not in analysis_progress:
        return jsonify({
            'success': False,
            'error': 'Task not found'
        }), 404

    task = analysis_progress[task_id]

    response = {
        'status': task['status'],
        'progress': task['progress'],
        'message': task['message']
    }

    if task['status'] == 'completed':
        response['result'] = task['result']
    elif task['status'] == 'failed':
        response['error'] = task['error']

    return jsonify(response)

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

                    # Extract branch names (support both GitLab and GitHub formats)
                    source_branch = pr_details.get('source_branch') or pr_details.get('head_branch') or pr_details.get('head', {}).get('ref')
                    target_branch = pr_details.get('target_branch') or pr_details.get('base_branch') or pr_details.get('base', {}).get('ref')

                    session_data = {
                        'pr_url': pr_url,
                        'repo_url': repo_url,
                        'pr_title': pr_details.get('title', ''),
                        'pr_author': pr_details.get('author', ''),
                        'source_branch': source_branch,
                        'target_branch': target_branch,
                        'files_count': len(files),
                        'test_count': test_analysis['count'],
                        'ddd_score': ddd_analysis['score'],
                        'triggered_by': 'github_webhook',
                        'status': result.get('status', 'completed'),
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

                    # Extract branch names (support both GitLab and GitHub formats)
                    source_branch = pr_details.get('source_branch') or pr_details.get('head_branch') or pr_details.get('head', {}).get('ref')
                    target_branch = pr_details.get('target_branch') or pr_details.get('base_branch') or pr_details.get('base', {}).get('ref')

                    session_data = {
                        'pr_url': mr_url,
                        'repo_url': repo_url,
                        'pr_title': pr_details.get('title', ''),
                        'pr_author': pr_details.get('author', ''),
                        'source_branch': source_branch,
                        'target_branch': target_branch,
                        'files_count': len(files),
                        'test_count': test_analysis['count'],
                        'ddd_score': ddd_analysis['score'],
                        'triggered_by': 'gitlab_webhook',
                        'status': result.get('status', 'completed'),
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
