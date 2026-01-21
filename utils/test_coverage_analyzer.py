import os
import re
from typing import Dict, List, Any, Optional
from pathlib import Path


class TestCoverageAnalyzer:
    """Analyze test coverage and testing practices in a repository"""
    
    # Test framework patterns
    TEST_FRAMEWORKS = {
        'pytest': [r'import pytest', r'from pytest', r'@pytest\.'],
        'unittest': [r'import unittest', r'from unittest', r'class.*\(unittest\.TestCase\)'],
        'jest': [r'describe\(', r'test\(', r'it\(', r'expect\('],
        'mocha': [r'describe\(', r'it\(', r'before\(', r'after\('],
        'junit': [r'import org\.junit', r'@Test', r'@Before', r'@After'],
        'rspec': [r'describe\s+', r'it\s+', r'expect\('],
        'go_test': [r'func Test', r'testing\.T'],
        'vitest': [r'import.*vitest', r'describe\(', r'test\(']
    }
    
    # Test file patterns
    TEST_FILE_PATTERNS = [
        r'test_.*\.py$',
        r'.*_test\.py$',
        r'.*\.test\.(js|ts|jsx|tsx)$',
        r'.*\.spec\.(js|ts|jsx|tsx)$',
        r'Test.*\.java$',
        r'.*Test\.java$',
        r'.*_test\.go$',
        r'.*_spec\.rb$'
    ]
    
    # Source file extensions
    SOURCE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rb', 
        '.php', '.cpp', '.c', '.cs', '.swift', '.kt', '.rs'
    }
    
    @staticmethod
    def detect_test_frameworks(repo_path: str) -> List[str]:
        """Detect which test frameworks are being used"""
        detected_frameworks = set()
        
        for root, dirs, files in os.walk(repo_path):
            if '.git' in dirs:
                dirs.remove('.git')
            if 'node_modules' in dirs:
                dirs.remove('node_modules')
            if 'venv' in dirs:
                dirs.remove('venv')
                
            for file in files:
                if not any(file.endswith(ext) for ext in TestCoverageAnalyzer.SOURCE_EXTENSIONS):
                    continue
                    
                try:
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(5000)  # Read first 5000 chars
                        
                    for framework, patterns in TestCoverageAnalyzer.TEST_FRAMEWORKS.items():
                        if framework not in detected_frameworks:
                            for pattern in patterns:
                                if re.search(pattern, content):
                                    detected_frameworks.add(framework)
                                    break
                except:
                    continue
                    
        return sorted(list(detected_frameworks))
    
    @staticmethod
    def analyze_test_files(repo_path: str) -> Dict[str, Any]:
        """Analyze test files vs source files"""
        test_files = []
        source_files = []
        test_lines = 0
        source_lines = 0
        
        for root, dirs, files in os.walk(repo_path):
            if '.git' in dirs:
                dirs.remove('.git')
            if 'node_modules' in dirs:
                dirs.remove('node_modules')
            if 'venv' in dirs:
                dirs.remove('venv')
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
                
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1]
                
                if ext not in TestCoverageAnalyzer.SOURCE_EXTENSIONS:
                    continue
                
                # Check if it's a test file
                is_test = any(re.match(pattern, file) for pattern in TestCoverageAnalyzer.TEST_FILE_PATTERNS)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)
                        
                    if is_test:
                        test_files.append(os.path.relpath(file_path, repo_path))
                        test_lines += lines
                    else:
                        source_files.append(os.path.relpath(file_path, repo_path))
                        source_lines += lines
                except:
                    continue
                    
        return {
            'test_file_count': len(test_files),
            'source_file_count': len(source_files),
            'test_lines': test_lines,
            'source_lines': source_lines,
            'test_files': test_files[:50],  # Limit to first 50
            'untested_modules': []  # Will be populated by AI analysis
        }
    
    @staticmethod
    def calculate_coverage_estimate(test_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate estimated test coverage based on heuristics"""
        test_count = test_stats['test_file_count']
        source_count = test_stats['source_file_count']
        test_lines = test_stats['test_lines']
        source_lines = test_stats['source_lines']
        
        # Method 1: File ratio (weighted 40%)
        file_ratio = (test_count / max(source_count, 1)) * 100 if source_count > 0 else 0
        file_coverage = min(file_ratio, 100) * 0.4
        
        # Method 2: Line ratio (weighted 30%)
        line_ratio = (test_lines / max(source_lines, 1)) * 100 if source_lines > 0 else 0
        line_coverage = min(line_ratio * 2, 100) * 0.3  # Multiply by 2 as tests are usually shorter
        
        # Method 3: Presence bonus (weighted 30%)
        presence_score = 0
        if test_count > 0:
            presence_score = 20
        if test_count > source_count * 0.3:
            presence_score = 40
        if test_count > source_count * 0.5:
            presence_score = 60
        if test_count > source_count * 0.7:
            presence_score = 80
        if test_count >= source_count:
            presence_score = 100
        presence_coverage = presence_score * 0.3
        
        # Combined estimate
        estimated_coverage = file_coverage + line_coverage + presence_coverage
        
        # Quality assessment
        quality = 'Poor'
        if estimated_coverage >= 80:
            quality = 'Excellent'
        elif estimated_coverage >= 60:
            quality = 'Good'
        elif estimated_coverage >= 40:
            quality = 'Fair'
        elif estimated_coverage >= 20:
            quality = 'Limited'
            
        return {
            'estimated_coverage_percent': round(estimated_coverage, 1),
            'quality_rating': quality,
            'test_to_source_ratio': round(test_count / max(source_count, 1), 2),
            'methodology': 'Heuristic-based estimation using file count, line count, and test presence patterns'
        }
    
    @staticmethod
    def get_test_summary(repo_path: str) -> Dict[str, Any]:
        """Get comprehensive test coverage summary"""
        frameworks = TestCoverageAnalyzer.detect_test_frameworks(repo_path)
        test_stats = TestCoverageAnalyzer.analyze_test_files(repo_path)
        coverage_estimate = TestCoverageAnalyzer.calculate_coverage_estimate(test_stats)
        
        return {
            'frameworks_detected': frameworks,
            'has_tests': test_stats['test_file_count'] > 0,
            'test_file_count': test_stats['test_file_count'],
            'source_file_count': test_stats['source_file_count'],
            'test_lines': test_stats['test_lines'],
            'source_lines': test_stats['source_lines'],
            'estimated_coverage': coverage_estimate['estimated_coverage_percent'],
            'quality_rating': coverage_estimate['quality_rating'],
            'test_to_source_ratio': coverage_estimate['test_to_source_ratio'],
            'sample_test_files': test_stats['test_files'],
            'methodology': coverage_estimate['methodology']
        }
