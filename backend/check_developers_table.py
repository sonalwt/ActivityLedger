import sqlite3
import json

# Connect to the database
conn = sqlite3.connect('timesheet.db')
cursor = conn.cursor()

print("=== CHECKING DEVELOPERS TABLE ===")
# Check developers table
cursor.execute("SELECT * FROM developers")
developers = cursor.fetchall()

# Get column names
cursor.execute("PRAGMA table_info(developers)")
columns = cursor.fetchall()
print("\nDevelopers table columns:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

print(f"\nTotal developers in 'developers' table: {len(developers)}")
if developers:
    print("\nDevelopers:")
    for dev in developers:
        print(f"  - {dev}")

print("\n=== CHECKING DISCOVERED_DEVELOPERS_ENHANCED TABLE ===")
try:
    cursor.execute("SELECT * FROM discovered_developers_enhanced")
    discovered = cursor.fetchall()
    
    cursor.execute("PRAGMA table_info(discovered_developers_enhanced)")
    columns = cursor.fetchall()
    print("\nDiscovered_developers_enhanced table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    print(f"\nTotal in 'discovered_developers_enhanced' table: {len(discovered)}")
    if discovered:
        print("\nDiscovered developers:")
        for dev in discovered:
            print(f"  - {dev}")
except sqlite3.OperationalError as e:
    print(f"Error accessing discovered_developers_enhanced table: {e}")

print("\n=== CHECKING ACTIVITY_RECORDS TABLE ===")
# Check activity records
cursor.execute("SELECT COUNT(*) FROM activity_records")
total_activities = cursor.fetchone()[0]
print(f"\nTotal activity records: {total_activities}")

# Check unique developers in activity_records
cursor.execute("""
    SELECT DISTINCT 
        developer_id,
        developer_name,
        COUNT(*) as activity_count
    FROM activity_records 
    WHERE developer_id IS NOT NULL OR developer_name IS NOT NULL
    GROUP BY developer_id, developer_name
""")
activity_developers = cursor.fetchall()
print(f"\nUnique developers in activity_records: {len(activity_developers)}")
if activity_developers:
    print("\nDevelopers with activities:")
    for dev in activity_developers:
        print(f"  - ID: {dev[0]}, Name: {dev[1]}, Activities: {dev[2]}")

conn.close()
