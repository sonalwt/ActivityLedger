#!/usr/bin/env python3
"""
Test script to verify the imports are working correctly
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    print("🔧 Testing imports...")
    
    try:
        print("1. Testing database import...")
        from database import engine, SessionLocal, Base
        print("   ✅ Database imports successful")
        
        print("2. Testing models import...")
        from models import User, ActivityRecord, Developer
        print("   ✅ Models import successful")
        
        print("3. Testing stateless_webhook import...")
        from stateless_webhook import router, validate_stateless_token
        print("   ✅ Stateless webhook import successful")
        
        print("4. Testing database connection...")
        conn = engine.connect()
        conn.close()
        print("   ✅ Database connection successful")
        
        print("\n🎉 All imports working correctly!")
        return True
        
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_imports()
