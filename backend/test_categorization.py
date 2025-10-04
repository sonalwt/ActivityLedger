#!/usr/bin/env python3
"""
Test Activity Categorization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from activity_categorizer import ActivityCategorizer

def test_categorization():
    """Test categorization with your actual data"""
    categorizer = ActivityCategorizer()
    
    # Test cases from your actual data
    test_cases = [
        ("Chrome.exe", "Fix missing column error - Google Chrome"),
        ("Termius.exe", "Termius - Node Server"),
        ("Cursor.exe", "timesheet_new - Cursor"),
        ("explorer.exe", "Task Switching"),
        ("Code.exe", "main.py - Visual Studio Code"),
        ("firefox.exe", "GitHub - microsoft/vscode"),
        ("chrome.exe", "localhost:3000 - React App"),
        ("Slack.exe", "general - Slack"),
    ]
    
    print("=" * 60)
    print("ACTIVITY CATEGORIZATION TEST")
    print("=" * 60)
    
    for app_name, window_title in test_cases:
        result = categorizer.get_detailed_category(window_title, app_name)
        
        print(f"\n📱 App: {app_name}")
        print(f"📄 Title: {window_title}")
        print(f"📊 Category: {result['category']}")
        print(f"📂 Subcategory: {result['subcategory']}")
        print(f"✨ Confidence: {result['confidence']:.2f}")
        print("-" * 40)

if __name__ == "__main__":
    test_categorization()
