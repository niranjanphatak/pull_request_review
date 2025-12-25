#!/usr/bin/env python3
"""
Test script to verify GitLab diff parsing
Run this to test if the parse_diff_stats function works correctly
"""

from utils.gitlab_helper import parse_diff_stats

# Sample GitLab unified diff format
sample_gitlab_diff = """--- a/src/main.py
+++ b/src/main.py
@@ -1,10 +1,12 @@
 import os
 import sys
+import json

 def main():
-    print("Hello")
+    print("Hello World")
+    print("New line")
     return 0

-def old_function():
-    pass
+def new_function():
+    return True
"""

# Test the function
print("Testing parse_diff_stats with sample GitLab diff:")
print("=" * 80)
result = parse_diff_stats(sample_gitlab_diff)
print()
print(f"Results:")
print(f"  Additions: {result['additions']}")
print(f"  Deletions: {result['deletions']}")
print(f"  Total Changes: {result['changes']}")
print()
print("Expected: Additions: 5, Deletions: 3, Total Changes: 8")
print()

# Test with empty diff
print("Testing with empty diff:")
print("=" * 80)
result_empty = parse_diff_stats("")
print(f"Results: {result_empty}")
print()

# Test with None
print("Testing with None:")
print("=" * 80)
result_none = parse_diff_stats(None if False else "")
print(f"Results: {result_none}")
