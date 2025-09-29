# test_main_imports.py
import sys
import os
import traceback

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

print("=== Testing main.py imports ===\n")
print(f"Current directory: {os.getcwd()}")
print(f"Backend path: {backend_path}")
print(f"Python path: {sys.path[:3]}...\n")

# Change to backend directory
os.chdir(backend_path)

try:
    print("1. Testing basic imports...")
    import fastapi
    print("✅ FastAPI imported successfully")
    
    import sqlalchemy
    print("✅ SQLAlchemy imported successfully")
    
    print("\n2. Testing local module imports...")
    
    # Test each module separately
    modules_to_test = [
        'config',
        'database', 
        'models',
        'schemas',
        'crud',
        'auth',
        'my_activitywatch_client',
        'productivity_calculator',
        'realistic_hours_calculator',
        'developer_discovery',
        'stateless_webhook',
        'simple_multi_dev_api',
        'fixed_dynamic_developer_api',
        'real_data_endpoints'
    ]
    
    for module in modules_to_test:
        try:
            exec(f'import {module}')
            print(f"✅ {module} imported successfully")
        except Exception as e:
            print(f"❌ {module} import failed: {str(e)[:100]}...")
            
    print("\n3. Testing main.py import...")
    import main
    print("✅ main.py imported successfully!")
    
    if hasattr(main, 'app'):
        print("✅ FastAPI app object found in main.py")
    else:
        print("❌ FastAPI app object NOT found in main.py")
        
except Exception as e:
    print(f"\n❌ Import failed with error:\n")
    traceback.print_exc()
    
print("\n=== Import test complete ===")
