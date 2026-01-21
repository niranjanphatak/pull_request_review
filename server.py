"""
Flask server for JavaScript UI
"""
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os
from pathlib import Path
from config import Config
from workflow.review_workflow import PRReviewWorkflow

from utils.database_factory import create_database
from utils.document_parser import extract_text_from_file
from werkzeug.utils import secure_filename
import tempfile
import json
import threading
import uuid
import datetime
from typing import List, Dict


# Initialize database (MongoDB or DynamoDB based on config)
session_storage = create_database()


def log_activity(activity_type, message, details=None):
    """Log application activity to file"""
    try:
        log_file = getattr(Config, 'LOG_FILE', 'app_activity.log')
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{activity_type.upper()}] {message}"
        if details:
            log_entry += f" | Details: {json.dumps(details)}"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
        print(f"📝 LOG: {message}")
    except Exception as e:
        print(f"Error writing to log: {e}")


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


def generate_prompts_from_rules(rules_text):
    """Use LLM to generate evaluation prompts for each stage based on rules document"""
    try:
        prompt = f"""
        You are an expert AI prompt engineer. Below is a document containing coding rules, standards, and evaluation criteria for a software development team.
        
        RULES DOCUMENT content:
        ---
        {rules_text}
        ---
        
        Based on the above document, generate 4 specialized prompts for our AI code review system. 
        Each prompt should focus on one of these areas:
        1. Security Review (vulnerabilities, data protection, etc.)
        2. Bug Detection (logic errors, edge cases, state management)
        3. Code Quality (style, readability, DDD adherence, naming)
        4. Test Suggestions (unit testing, mocking, coverage)
        
        The prompts will be used as System Instructions for an LLM that reviews PR code changes.
        Each generated prompt should tell the AI exactly what to look for based on identifying features in the rules document.
        
        Return the result in JSON format:
        {{
            "security": "prompt text...",
            "bugs": "prompt text...",
            "style": "prompt text...",
            "performance": "prompt text...",
            "tests": "prompt text...",
            "analysis_summary": "Short summary of the rules document and how it influenced these prompts"
        }}
        """
        
        from agents.review_agents import ReviewAgents
        agents = ReviewAgents(
            api_key=Config.get_ai_api_key(),
            model=Config.get_ai_model(),
            base_url=Config.get_ai_base_url(),
            temperature=Config.get_ai_temperature()
        )
        
        response = agents.llm.invoke(prompt)
        content = response.content
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        # Fallback if no code blocks
        elif "{" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            content = content[start:end]
            
        return json.loads(content)
    except Exception as e:
        print(f"Error generating prompts: {e}")
        raise e

def generate_single_prompt_from_rules(rules_text, category):
    """Use LLM to generate a single evaluation prompt for a specific category"""
    category_descriptions = {
        'security': 'Security Review - focus on vulnerabilities, data protection, authentication, authorization, injection attacks, and secure coding practices',
        'bugs': 'Bug Detection - focus on logic errors, edge cases, null pointer issues, race conditions, and state management problems',
        'style': 'Code Quality - focus on readability, naming conventions, DDD adherence, SOLID principles, and code organization',
        'performance': 'Performance Analysis - focus on algorithmic efficiency, memory usage, database queries, and optimization opportunities',
        'tests': 'Test Suggestions - focus on unit testing, test coverage, mocking strategies, and edge case testing'
    }
    
    category_desc = category_descriptions.get(category, category)
    
    try:
        prompt = f"""
        You are an expert AI prompt engineer. Below is a document containing coding rules, standards, and evaluation criteria for a software development team.
        
        RULES DOCUMENT content:
        ---
        {rules_text}
        ---
        
        Based on the above document, generate ONE specialized prompt for: {category_desc}
        
        The prompt will be used as a System Instruction for an LLM that reviews PR code changes.
        The generated prompt should tell the AI exactly what to look for based on the rules document.
        Make the prompt detailed, specific, and actionable.
        
        Return the result in JSON format:
        {{
            "{category}": "The full prompt text...",
            "analysis_summary": "Brief summary of how the rules document influenced this prompt"
        }}
        """
        
        from agents.review_agents import ReviewAgents
        agents = ReviewAgents(
            api_key=Config.get_ai_api_key(),
            model=Config.get_ai_model(),
            base_url=Config.get_ai_base_url(),
            temperature=Config.get_ai_temperature()
        )
        
        response = agents.llm.invoke(prompt)
        content = response.content
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        elif "{" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            content = content[start:end]
            
        return json.loads(content)
    except Exception as e:
        print(f"Error generating single prompt: {e}")
        raise e

def extract_markdown_snippets(markdown_text: str) -> List[Dict]:
    """Helper to extract code blocks from markdown for professional display"""
    if not isinstance(markdown_text, str) or not markdown_text:
        return []
    
    import re
    snippets = []
    # Match ```language\ncode```
    pattern = r'```(\w+)?\n([\s\S]*?)```'
    matches = re.finditer(pattern, markdown_text)
    
    for match in matches:
        lang = match.group(1) or 'code'
        code = match.group(2).strip()
        if code:
            snippets.append({
                'language': lang,
                'content': code,
                'id': f"snippet_{os.urandom(4).hex()}"
            })
    return snippets

def parse_findings_from_markdown(markdown_text: str) -> List[Dict]:
    """Extract individual findings from markdown for structured storage"""
    if not isinstance(markdown_text, str) or not markdown_text:
        return []
    
    import re
    findings = []
    
    # Simple regex for finding markers at start of lines
    markers = [r'^\s*\d+\.\s+', r'^[🔴🟠🟡🟢]\s+', r'^#{2,4}\s+']
    combined_pattern = '|'.join(markers)
    
    parts = re.split(f'({combined_pattern})', markdown_text, flags=re.MULTILINE)
    
    for i in range(1, len(parts), 2):
        marker = parts[i]
        content = parts[i+1].strip() if i+1 < len(parts) else ""
        
        if content:
            severity = 'low'
            if '🔴' in marker or 'critical' in content.lower():
                severity = 'critical'
            elif '🟠' in marker or 'high' in content.lower():
                severity = 'high'
            elif '🟡' in marker or 'medium' in content.lower():
                severity = 'medium'
            
            lines = content.split('\n')
            title = lines[0].strip() if lines else "Finding"
            
            findings.append({
                'title': title,
                'description': content,
                'severity': severity,
                'marker': marker.strip()
            })
            
    return findings

@app.route('/api/prompts/generate', methods=['POST'])
def generate_prompts():
    """Upload rules document and generate prompt candidates"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    
    filename = secure_filename(file.filename)
    
    # Get selected category (default to 'all')
    category = request.form.get('category', 'all')
    
    try:
        # Create uploads directory under project tmp folder
        project_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(project_dir, 'tmp', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Save file with timestamp prefix to avoid overwrites
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_filename = f"{timestamp}_{filename}"
        saved_path = os.path.join(uploads_dir, saved_filename)
        file.save(saved_path)
        
        log_activity('UPLOAD', f'File saved: {saved_filename}', {'path': saved_path, 'category': category})
            
        # Extract text
        text = extract_text_from_file(saved_path)
        # File is kept for reference in tmp/uploads/
        
        if not text or len(text.strip()) < 50:
            return jsonify({'success': False, 'error': 'Could not extract sufficient text from document'}), 400
            
        # Generate prompts using LLM
        try:
            if category == 'all':
                generated = generate_prompts_from_rules(text)
            else:
                generated = generate_single_prompt_from_rules(text, category)
        except Exception as e:
            return jsonify({'success': False, 'error': f"AI Generation Failed: {str(e)}"}), 500
            
        # Build prompts dict
        prompts = {
            'security': generated.get('security'),
            'bugs': generated.get('bugs'),
            'style': generated.get('style'),
            'performance': generated.get('performance'),
            'tests': generated.get('tests')
        }
        
        # Save candidates to DB
        candidate_data = {
            'source_filename': filename,
            'prompts': prompts,
            'analysis_summary': generated.get('analysis_summary', 'Generated from team rules document'),
            'category': category
        }
        
        candidate_id = session_storage.save_prompt_candidate(candidate_data)
        
        return jsonify({
            'success': True,
            'job_id': candidate_id,
            'prompts': prompts,  # Include prompts for modal display
            'message': 'Prompts generated successfully'
        })
        
    except Exception as e:
        print(f"Error in prompt generation endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/prompts/candidates', methods=['GET'])
def get_prompt_candidates():
    """Get list of generated prompt candidates"""
    candidates = session_storage.get_prompt_candidates(accepted=False)
    return jsonify({'success': True, 'candidates': candidates})

@app.route('/api/prompts/active', methods=['GET'])
def get_active_prompts():
    """Get currently active prompts from DB and files"""
    from agents.review_agents import ReviewAgents
    agents = ReviewAgents(
        api_key=Config.get_ai_api_key(),
        model=Config.get_ai_model(),
        base_url=Config.get_ai_base_url()
    )
    
    return jsonify({
        'success': True,
        'prompts': agents.prompts,
        'versions': agents.get_prompt_versions()
    })

@app.route('/api/prompts/accept/<candidate_id>', methods=['POST'])
def accept_prompt(candidate_id):
    """Accept a candidate and make it active"""
    candidate = session_storage.get_prompt_candidate(candidate_id)
    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404
        
    try:
        # Mark candidate as accepted
        session_storage.accept_prompt_candidate(candidate_id)
        
        # Save new versions for each stage
        prompts = candidate.get('prompts', {})
        version_num = datetime.datetime.now().strftime("%Y%m%d.%H%M")
        
        for stage, content in prompts.items():
            if content:
                session_storage.save_prompt_version(
                    stage=stage,
                    version=version_num,
                    prompt_content=content,
                    description=f"Generated from {candidate.get('source_filename')}",
                    criteria=[] # Could be improved by extracting criteria
                )
        
        return jsonify({'success': True, 'message': f'Prompts updated to version {version_num}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/prompts/candidate/<candidate_id>', methods=['DELETE'])
def delete_prompt_candidate(candidate_id):
    """Delete a prompt candidate"""
    try:
        candidate = session_storage.get_prompt_candidate(candidate_id)
        if not candidate:
            return jsonify({'success': False, 'error': 'Candidate not found'}), 404
        
        # Delete the candidate
        result = session_storage.delete_prompt_candidate(candidate_id)
        
        if result:
            log_activity('DELETE', f'Deleted prompt candidate: {candidate_id}')
            return jsonify({'success': True, 'message': 'Candidate deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete candidate'}), 500
    except Exception as e:
        print(f"Error deleting candidate: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
            'performance': True,
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

                # Extract structured findings and code snippets from markdown reports
                reports = {
                    'security': result.get('security_review', ''),
                    'bugs': result.get('bug_review', ''),
                    'style': result.get('style_review', ''),
                    'tests': result.get('test_suggestions', '')
                }
                
                all_snippets = []
                all_findings = []
                
                for stage, content in reports.items():
                    if isinstance(content, str) and content:
                        snips = extract_markdown_snippets(content)
                        for s in snips:
                            s['stage'] = stage
                        all_snippets.extend(snips)
                        
                        fnds = parse_findings_from_markdown(content)
                        for f in fnds:
                            f['stage'] = stage
                        all_findings.extend(fnds)

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
                        'security': reports['security'],
                        'bugs': reports['bugs'],
                        'style': reports['style'],
                        'tests': reports['tests'],
                        'target_branch_analysis': result.get('target_branch_analysis'),
                        'token_usage': result.get('token_usage', {}),
                        'all_snippets': all_snippets,
                        'all_findings': all_findings
                    }
                }

                print(f"Server: Response data files count: {len(response_data['results']['files'])}")
                print(f"Server: Extracted {len(all_snippets)} code snippets and {len(all_findings)} structured findings")

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
                        'bugs': prompt_versions.get('bugs', {'version': '1.0.0', 'description': '', 'criteria': []}),
                        'style': prompt_versions.get('style', {'version': '1.0.0', 'description': '', 'criteria': []}),
                        'tests': prompt_versions.get('tests', {'version': '1.0.0', 'description': '', 'criteria': []})
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
    db_status = 'connected' if session_storage.connected else 'disconnected'
    db_type = Config.get_database_type()
    return jsonify({
        'status': 'ok',
        'database_type': db_type,
        'database_status': db_status
    })


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
                            'performance': result.get('performance_review', ''),
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
                            'performance': result.get('performance_review', ''),
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
