import os
import re
import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path


class APIDetector:
    """Detect and analyze APIs in a repository"""
    
    # API framework patterns
    API_PATTERNS = {
        'flask': {
            'patterns': [r'@app\.route\(["\']([^"\']+)["\'].*methods=\[([^\]]+)\]', r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'],
            'files': ['app.py', 'routes.py', 'api.py']
        },
        'fastapi': {
            'patterns': [r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'],
            'files': ['main.py', 'api.py', 'routers/', 'routes/']
        },
        'express': {
            'patterns': [r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'],
            'files': ['server.js', 'app.js', 'index.js', 'routes/']
        },
        'spring': {
            'patterns': [r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\(["\']([^"\']+)["\']', r'@RequestMapping\(.*path\s*=\s*["\']([^"\']+)["\']'],
            'files': ['Controller.java', 'RestController.java']
        },
        'django': {
            'patterns': [r'path\(["\']([^"\']+)["\']', r'url\(r\'^([^\']+)\''],
            'files': ['urls.py', 'views.py']
        },
        'gin': {
            'patterns': [r'router\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\']', r'r\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\']'],
            'files': ['main.go', 'routes.go', 'router.go']
        }
    }
    
    # GraphQL patterns
    GRAPHQL_PATTERNS = [
        r'type\s+Query\s*{',
        r'type\s+Mutation\s*{',
        r'schema\s*{',
        r'@graphql'
    ]
    
    # OpenAPI/Swagger file patterns
    OPENAPI_FILES = ['openapi.yaml', 'openapi.yml', 'openapi.json', 'swagger.yaml', 'swagger.yml', 'swagger.json', 'api-spec.yaml']
    
    @staticmethod
    def detect_rest_apis(repo_path: str) -> Dict[str, Any]:
        """Detect REST API endpoints in the repository"""
        detected_apis = {
            'frameworks': [],
            'endpoints': [],
            'total_endpoints': 0
        }
        
        for framework, config in APIDetector.API_PATTERNS.items():
            framework_endpoints = []
            
            for root, dirs, files in os.walk(repo_path):
                if '.git' in dirs:
                    dirs.remove('.git')
                if 'node_modules' in dirs:
                    dirs.remove('node_modules')
                if 'venv' in dirs:
                    dirs.remove('venv')
                    
                for file in files:
                    # Check if file matches framework patterns
                    if not any(pattern in file for pattern in config['files']):
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        for pattern in config['patterns']:
                            matches = re.finditer(pattern, content, re.MULTILINE)
                            for match in matches:
                                groups = match.groups()
                                if len(groups) >= 2:
                                    method = groups[0].upper() if groups[0] else 'GET'
                                    path = groups[1] if len(groups) > 1 else groups[0]
                                else:
                                    method = 'GET'
                                    path = groups[0]
                                    
                                framework_endpoints.append({
                                    'method': method,
                                    'path': path,
                                    'file': os.path.relpath(file_path, repo_path),
                                    'framework': framework
                                })
                    except:
                        continue
                        
            if framework_endpoints:
                detected_apis['frameworks'].append(framework)
                detected_apis['endpoints'].extend(framework_endpoints)
                
        detected_apis['total_endpoints'] = len(detected_apis['endpoints'])
        # Limit to first 100 endpoints
        detected_apis['endpoints'] = detected_apis['endpoints'][:100]
        
        return detected_apis
    
    @staticmethod
    def detect_graphql_schemas(repo_path: str) -> Dict[str, Any]:
        """Detect GraphQL schemas in the repository"""
        graphql_info = {
            'has_graphql': False,
            'schema_files': [],
            'queries': [],
            'mutations': []
        }
        
        for root, dirs, files in os.walk(repo_path):
            if '.git' in dirs:
                dirs.remove('.git')
            if 'node_modules' in dirs:
                dirs.remove('node_modules')
                
            for file in files:
                if file.endswith(('.graphql', '.gql')) or 'schema' in file.lower():
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        # Check for GraphQL patterns
                        if any(re.search(pattern, content) for pattern in APIDetector.GRAPHQL_PATTERNS):
                            graphql_info['has_graphql'] = True
                            graphql_info['schema_files'].append(os.path.relpath(file_path, repo_path))
                            
                            # Extract queries
                            query_matches = re.finditer(r'type\s+Query\s*{([^}]+)}', content, re.DOTALL)
                            for match in query_matches:
                                queries = re.findall(r'(\w+)\s*\([^)]*\)\s*:\s*(\w+)', match.group(1))
                                graphql_info['queries'].extend([q[0] for q in queries])
                                
                            # Extract mutations
                            mutation_matches = re.finditer(r'type\s+Mutation\s*{([^}]+)}', content, re.DOTALL)
                            for match in mutation_matches:
                                mutations = re.findall(r'(\w+)\s*\([^)]*\)\s*:\s*(\w+)', match.group(1))
                                graphql_info['mutations'].extend([m[0] for m in mutations])
                    except:
                        continue
                        
        return graphql_info
    
    @staticmethod
    def parse_openapi_specs(repo_path: str) -> Optional[Dict[str, Any]]:
        """Parse OpenAPI/Swagger specification files"""
        for root, dirs, files in os.walk(repo_path):
            if '.git' in dirs:
                dirs.remove('.git')
                
            for file in files:
                if file.lower() in APIDetector.OPENAPI_FILES:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            if file.endswith('.json'):
                                spec = json.load(f)
                            else:
                                spec = yaml.safe_load(f)
                                
                        # Extract basic info
                        openapi_info = {
                            'spec_file': os.path.relpath(file_path, repo_path),
                            'version': spec.get('openapi') or spec.get('swagger', 'unknown'),
                            'title': spec.get('info', {}).get('title', 'Unknown API'),
                            'description': spec.get('info', {}).get('description', ''),
                            'endpoints': []
                        }
                        
                        # Extract paths
                        paths = spec.get('paths', {})
                        for path, methods in paths.items():
                            for method, details in methods.items():
                                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                                    openapi_info['endpoints'].append({
                                        'method': method.upper(),
                                        'path': path,
                                        'summary': details.get('summary', ''),
                                        'description': details.get('description', '')
                                    })
                                    
                        return openapi_info
                    except:
                        continue
                        
        return None
    
    @staticmethod
    def get_api_summary(repo_path: str) -> Dict[str, Any]:
        """Get comprehensive API detection summary"""
        rest_apis = APIDetector.detect_rest_apis(repo_path)
        graphql = APIDetector.detect_graphql_schemas(repo_path)
        openapi_spec = APIDetector.parse_openapi_specs(repo_path)
        
        summary = {
            'has_apis': False,
            'api_types': [],
            'rest_apis': rest_apis,
            'graphql': graphql,
            'openapi_spec': openapi_spec,
            'total_endpoints': rest_apis['total_endpoints']
        }
        
        if rest_apis['total_endpoints'] > 0:
            summary['has_apis'] = True
            summary['api_types'].append('REST')
            
        if graphql['has_graphql']:
            summary['has_apis'] = True
            summary['api_types'].append('GraphQL')
            
        if openapi_spec:
            summary['has_apis'] = True
            summary['api_types'].append('OpenAPI/Swagger')
            
        return summary
