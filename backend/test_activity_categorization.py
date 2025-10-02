# test_activity_categorization.py
"""
Test script for activity categorization
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from activity_categorizer import ActivityCategorizer
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# Test the categorizer with sample data
def test_categorizer():
    categorizer = ActivityCategorizer()
    
    test_cases = [
        # From your database screenshot
        ("Startup - cFile Explorer", "explorer.exe"),
        ("Termius - Node Server", "Termius.exe"),
        ("timesheet_new - Cursor", "Cursor.exe"),
        ("Chrome - Google Chrome", "chrome.exe"),
        ("Window Dialog", ""),
        ("localhost:3000", "chrome.exe"),
        ("GitHub - microsoft/vscode", "chrome.exe"),
        ("AWS Management Console", "chrome.exe"),
        ("Claude", "chrome.exe"),
        ("Netflix", "chrome.exe"),
        
        # Additional test cases
        ("main.py - Visual Studio Code", "Code.exe"),
        ("FileZilla - SFTP Connection", "filezilla.exe"),
        ("MySQL Workbench", "MySQLWorkbench.exe"),
        ("cpanel.example.com", "chrome.exe"),
        ("EC2 Dashboard - AWS", "chrome.exe"),
        ("Google Cloud Console", "chrome.exe"),
    ]
    
    print("Activity Categorization Test Results")
    print("=" * 80)
    print(f"{'Window Title':<40} {'App':<15} {'Category':<15} {'Confidence':<10}")
    print("-" * 80)
    
    for title, app in test_cases:
        result = categorizer.get_detailed_category(title, app)
        print(f"{title:<40} {app:<15} {result['category']:<15} {result['confidence']:.2f}")
        print(f"  └─ Subcategory: {result['subcategory']}")
    
    print("\n" + "=" * 80)

# Test with real database data if available
def test_with_database():
    try:
        # Connect to database
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/timesheet")
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get sample activities
        result = session.execute(text("""
            SELECT DISTINCT window_title, application_name
            FROM activity_records
            WHERE window_title IS NOT NULL
            LIMIT 20
        """)).fetchall()
        
        if result:
            categorizer = ActivityCategorizer()
            
            print("\nDatabase Activity Categorization")
            print("=" * 80)
            
            for row in result:
                window_title = row[0]
                app_name = row[1] or ""
                
                category_info = categorizer.get_detailed_category(window_title, app_name)
                print(f"\nWindow: {window_title}")
                print(f"App: {app_name}")
                print(f"Category: {category_info['category']} ({category_info['subcategory']})")
                print(f"Confidence: {category_info['confidence']:.2%}")
        
        session.close()
        
    except Exception as e:
        print(f"\nCould not test with database: {e}")

if __name__ == "__main__":
    test_categorizer()
    test_with_database()
