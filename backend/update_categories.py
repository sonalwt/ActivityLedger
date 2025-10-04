#!/usr/bin/env python3
"""
Update Categories for Existing Activity Records
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from activity_categorizer import ActivityCategorizer

def update_categories():
    """Update categories for all activity records"""
    
    # Database connection
    db_config = {
        'host': 'localhost',
        'database': 'timesheet',
        'user': 'postgres',
        'password': 'postgres',  # Update with your password
        'port': '5432'
    }
    
    try:
        # Connect to database
        conn = psycopg2.connect(**db_config, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # First, check if the category columns exist
        print("📊 Checking database schema...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'activity_records' 
            AND column_name IN ('category', 'subcategory', 'category_confidence')
        """)
        existing_columns = [row['column_name'] for row in cur.fetchall()]
        
        # Add missing columns if needed
        if 'category' not in existing_columns:
            print("➕ Adding category column...")
            cur.execute("ALTER TABLE activity_records ADD COLUMN category VARCHAR(50)")
        
        if 'subcategory' not in existing_columns:
            print("➕ Adding subcategory column...")
            cur.execute("ALTER TABLE activity_records ADD COLUMN subcategory VARCHAR(50)")
        
        if 'category_confidence' not in existing_columns:
            print("➕ Adding category_confidence column...")
            cur.execute("ALTER TABLE activity_records ADD COLUMN category_confidence FLOAT")
        
        conn.commit()
        
        # Initialize categorizer
        categorizer = ActivityCategorizer()
        
        # Get all records that need categorization
        print("\n🔍 Fetching records to categorize...")
        cur.execute("""
            SELECT id, application_name, window_title 
            FROM activity_records 
            WHERE category IS NULL 
               OR category = ''
               OR category = 'uncategorized'
            LIMIT 1000
        """)
        
        records = cur.fetchall()
        print(f"📦 Found {len(records)} records to categorize")
        
        # Update each record
        updated_count = 0
        category_counts = {}
        
        for record in records:
            # Get category info
            category_info = categorizer.get_detailed_category(
                record['window_title'] or '',
                record['application_name'] or ''
            )
            
            # Update record
            cur.execute("""
                UPDATE activity_records 
                SET 
                    category = %s,
                    subcategory = %s,
                    category_confidence = %s
                WHERE id = %s
            """, (
                category_info['category'],
                category_info['subcategory'],
                category_info['confidence'],
                record['id']
            ))
            
            # Track categories
            cat = category_info['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
            
            updated_count += 1
            
            # Progress indicator
            if updated_count % 100 == 0:
                print(f"✅ Updated {updated_count} records...")
        
        # Commit changes
        conn.commit()
        
        print(f"\n✨ Successfully updated {updated_count} records!")
        print("\n📈 Category breakdown:")
        for category, count in sorted(category_counts.items()):
            print(f"   - {category}: {count} records")
        
        # Show sample of categorized data
        print("\n📋 Sample of categorized activities:")
        cur.execute("""
            SELECT 
                application_name,
                window_title,
                category,
                subcategory,
                category_confidence
            FROM activity_records 
            WHERE category IS NOT NULL 
               AND category != 'uncategorized'
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        for row in cur.fetchall():
            print(f"\n   App: {row['application_name']}")
            print(f"   Title: {row['window_title'][:60]}...")
            print(f"   Category: {row['category']} ({row['subcategory']})")
            print(f"   Confidence: {row['category_confidence']:.2f}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_categories()
