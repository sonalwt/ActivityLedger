#!/usr/bin/env python3
"""
Simple Token Creator - Works with any database structure
"""

import secrets
import sys

def create_simple_token(developer_name):
    """Create a simple access token"""
    if not developer_name:
        print("❌ Developer name is required!")
        return None
    
    # Generate secure token
    token = f"AWToken_{secrets.token_urlsafe(32)}"
    
    print(f"\n🎉 Token Created!")
    print("=" * 50)
    print(f"Developer: {developer_name}")
    print(f"Token: {token}")
    print("=" * 50)
    print(f"\n📋 Instructions for {developer_name}:")
    print(f"1. Visit: http://localhost:8000/register-developer")
    print(f"2. Enter name: {developer_name}")
    print(f"3. Paste token: {token}")
    print(f"4. Click register!")
    
    return token

def main():
    print("🔑 Simple Token Generator")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        # Command line mode
        developer_name = " ".join(sys.argv[1:])
        create_simple_token(developer_name)
    else:
        # Interactive mode
        while True:
            developer_name = input("\nEnter developer name (or 'quit' to exit): ").strip()
            
            if developer_name.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if developer_name:
                create_simple_token(developer_name)
            else:
                print("❌ Please enter a valid developer name!")

if __name__ == "__main__":
    main()
