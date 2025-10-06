#!/usr/bin/env python
"""Test script to verify PostgreSQL column types"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL directly
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Connecting to: {DATABASE_URL.split('@')[1]}")  # Print host/db only

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Check column types
    print("\n1. Checking column types:")
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name IN ('developers', 'activity_records') 
        AND column_name = 'developer_id'
        ORDER BY table_name
    """)
    for row in cur.fetchall():
        print(f"   {row[0]}: {row[1]}")
    
    # Test simple join
    print("\n2. Testing simple join:")
    try:
        cur.execute("""
            SELECT COUNT(*) 
            FROM developers d 
            JOIN activity_records ar ON d.developer_id = ar.developer_id
        """)
        print(f"   ✅ Simple join works: {cur.fetchone()[0]} records")
    except Exception as e:
        print(f"   ❌ Simple join failed: {e}")
        
        # Try with cast
        print("\n3. Testing join with cast:")
        cur.execute("""
            SELECT COUNT(*) 
            FROM developers d 
            JOIN activity_records ar ON d.developer_id::VARCHAR = ar.developer_id::VARCHAR
        """)
        print(f"   ✅ Join with cast works: {cur.fetchone()[0]} records")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Database error: {e}")
