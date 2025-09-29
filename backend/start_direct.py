# start_direct.py
import os
import sys

# Set up the environment
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

# Ensure we're in backend directory
if not os.path.exists('main.py'):
    os.chdir('backend')

print(f"Starting from: {os.getcwd()}")

# Import and run
try:
    # First fix the exec issue
    with open('main.py', 'r') as f:
        content = f.read()
    
    if "exec(open('real_data_endpoints.py').read())" in content and not "# exec" in content:
        print("Fixing exec() issue...")
        content = content.replace(
            "exec(open('real_data_endpoints.py').read())",
            "# exec(open('real_data_endpoints.py').read())"
        )
        with open('main.py', 'w') as f:
            f.write(content)
    
    # Now import
    import main
    import uvicorn
    
    print("\nStarting server at http://localhost:8000")
    print("API Docs at http://localhost:8000/docs\n")
    
    uvicorn.run(main.app, host="0.0.0.0", port=8000, reload=True)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
