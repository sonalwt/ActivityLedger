#!/usr/bin/env python3
"""
Stateless Developer Config Generator
No database required - generates configs dynamically based on developer input
"""

import secrets
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
import json

class StatelessConfigGenerator:
    def __init__(self, server_url: str, master_secret: str = None):
        self.server_url = server_url.rstrip('/')
        self.master_secret = master_secret or os.getenv("MASTER_SECRET", "your-master-secret-for-token-generation")
    
    def generate_developer_id(self, name: str, email: str = None) -> str:
        """Generate deterministic developer ID from name and email"""
        # Clean and normalize name
        clean_name = name.lower().strip()
        clean_name = ''.join(c if c.isalnum() or c.isspace() else '' for c in clean_name)
        clean_name = '_'.join(clean_name.split())
        
        if email:
            # Use email hash for uniqueness
            email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:6]
            return f"{clean_name}_{email_hash}"
        else:
            # Use current year
            year = datetime.now().year
            return f"{clean_name}_{year}"
    
    def generate_api_token(self, developer_id: str) -> str:
        """Generate deterministic but secure API token for developer"""
        # Create token from developer_id + master_secret (deterministic)
        token_input = f"{developer_id}:{self.master_secret}:{datetime.now().year}"
        token_hash = hashlib.sha256(token_input.encode()).hexdigest()
        
        # Convert to URL-safe format (similar to secrets.token_urlsafe)
        import base64
        token_bytes = bytes.fromhex(token_hash[:48])  # 24 bytes -> 32 chars when base64
        return base64.urlsafe_b64encode(token_bytes).decode().rstrip('=')
    
    def validate_token(self, developer_id: str, provided_token: str) -> bool:
        """Validate if provided token matches expected token for developer"""
        expected_token = self.generate_api_token(developer_id)
        return expected_token == provided_token
    
    def generate_config_toml(self, developer_id: str, developer_name: str) -> str:
        """Generate ActivityWatch TOML configuration"""
        api_token = self.generate_api_token(developer_id)
        
        config = f"""# ActivityWatch Configuration for {developer_name}
# Generated: {datetime.now().isoformat()}
# Developer ID: {developer_id}

[server]
host = "127.0.0.1"
port = 5600

# Team timesheet integration
[integrations.timesheet]
enabled = true
webhook_url = "{self.server_url}/api/v1/activitywatch/webhook"
developer_id = "{developer_id}"
api_token = "{api_token}"
sync_interval = 1800  # 30 minutes

# Webhook configuration  
[webhooks]
enabled = true

[[webhooks.endpoints]]
url = "{self.server_url}/api/v1/activitywatch/webhook"
method = "POST"
interval = 1800
headers = {{
    "Developer-ID" = "{developer_id}",
    "Authorization" = "Bearer {api_token}",
    "Content-Type" = "application/json"
}}

# Include these buckets in sync
include_buckets = [
    "aw-watcher-window",
    "aw-watcher-web-chrome",
    "aw-watcher-web-firefox", 
    "aw-watcher-afk"
]

# Privacy settings
[privacy]
include_window_titles = true
include_urls = true
exclude_patterns = [
    "*password*",
    "*login*",
    "*private*",
    "*confidential*"
]

# Logging
[logging]
level = "INFO"
"""
        return config
    
    def create_developer_package(self, name: str, email: str = None, output_dir: str = ".") -> dict:
        """Create complete package for a developer"""
        developer_id = self.generate_developer_id(name, email)
        api_token = self.generate_api_token(developer_id)
        config_toml = self.generate_config_toml(developer_id, name)
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save config file
        config_file = Path(output_dir) / f"{developer_id}_config.toml"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_toml)
        
        # Save instructions
        instructions_file = Path(output_dir) / f"{developer_id}_instructions.txt"
        instructions = f"""
Setup Instructions for {name}
{'=' * 40}

Your Details:
- Developer ID: {developer_id}
- Name: {name}
- Email: {email or 'Not provided'}

Setup Steps:
1. Find your ActivityWatch config directory:
   Windows: %APPDATA%\\activitywatch\\aw-server\\config.toml
   Linux:   ~/.config/activitywatch/aw-server/config.toml  
   macOS:   ~/Library/Application Support/activitywatch/aw-server/config.toml

2. Replace config.toml with contents from: {config_file.name}

3. Restart ActivityWatch:
   - Close ActivityWatch completely
   - Wait 10 seconds
   - Start ActivityWatch again

4. Verification:
   - Check ActivityWatch logs for webhook success messages
   - Your data will appear in team dashboard after 30+ minutes
   - Team Dashboard: {self.server_url}/team

Troubleshooting:
- Ensure ActivityWatch is completely restarted
- Check internet connection to {self.server_url}
- Look for webhook errors in ActivityWatch logs
- Contact your admin if issues persist

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions.strip())
        
        # Save developer info (for admin reference)
        info_file = Path(output_dir) / f"{developer_id}_info.json" 
        info = {
            "developer_id": developer_id,
            "name": name,
            "email": email,
            "api_token": api_token,
            "generated_at": datetime.now().isoformat(),
            "server_url": self.server_url
        }
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2)
        
        print(f"✅ Created package for {name}")
        print(f"   Developer ID: {developer_id}")
        print(f"   Files: {config_file.name}, {instructions_file.name}")
        
        return {
            "developer_id": developer_id,
            "name": name,
            "email": email,
            "api_token": api_token,
            "config_file": str(config_file),
            "instructions_file": str(instructions_file),
            "info_file": str(info_file)
        }

def interactive_mode():
    """Interactive config generation"""
    print("🔧 ActivityWatch Config Generator (Stateless)")
    print("=" * 50)
    
    server_url = input("Server URL (e.g., https://timesheet.company.com): ").strip()
    if not server_url:
        print("❌ Server URL is required")
        return
    
    master_secret = input("Master secret (leave empty for default): ").strip()
    output_dir = input("Output directory (default: ./configs): ").strip() or "./configs"
    
    generator = StatelessConfigGenerator(server_url, master_secret)
    
    developers_created = []
    
    print(f"\n👥 Enter developer details (empty name to finish):")
    print("-" * 40)
    
    while True:
        print()
        name = input("Developer name: ").strip()
        if not name:
            break
        
        email = input("Email (optional): ").strip() or None
        
        try:
            package = generator.create_developer_package(name, email, output_dir)
            developers_created.append(package)
        except Exception as e:
            print(f"❌ Error creating package for {name}: {e}")
    
    if developers_created:
        print(f"\n🎉 Created {len(developers_created)} developer packages")
        print(f"📁 Location: {Path(output_dir).absolute()}")
        
        # Create summary file
        summary_file = Path(output_dir) / "DISTRIBUTION_SUMMARY.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"""# Developer Configuration Distribution

## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
## Server: {server_url}
## Total Developers: {len(developers_created)}

## Distribution List

""")
            for dev in developers_created:
                f.write(f"""### {dev['name']} ({dev['developer_id']})
- **Email**: {dev['email'] or 'Not provided'}
- **Config File**: `{Path(dev['config_file']).name}`
- **Instructions**: `{Path(dev['instructions_file']).name}`

""")
            
            f.write("""
## Next Steps
1. Send each developer their specific config and instruction files
2. Developers replace ActivityWatch config.toml and restart
3. Check team dashboard for incoming data after 30+ minutes

## No Database Required
This system requires no developer database - tokens are generated deterministically from names and master secret.
""")
        
        print(f"📖 Created distribution summary: {summary_file}")

def csv_mode(csv_file: str, server_url: str, master_secret: str = None, output_dir: str = "./configs"):
    """Generate configs from CSV file"""
    import csv
    
    if not Path(csv_file).exists():
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    generator = StatelessConfigGenerator(server_url, master_secret)
    developers_created = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        print(f"📄 Processing CSV file: {csv_file}")
        
        for row_num, row in enumerate(reader, 2):
            name = row.get('name', '').strip()
            email = row.get('email', '').strip() or None
            
            if not name:
                print(f"⚠️  Skipping row {row_num}: No name")
                continue
            
            try:
                package = generator.create_developer_package(name, email, output_dir)
                developers_created.append(package)
            except Exception as e:
                print(f"❌ Error processing {name}: {e}")
    
    print(f"\n✅ Processed {len(developers_created)} developers from CSV")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Stateless ActivityWatch Config Generator')
    parser.add_argument('--server-url', required=True, help='Server URL')
    parser.add_argument('--master-secret', help='Master secret for token generation')
    parser.add_argument('--csv', help='CSV file with developer list')
    parser.add_argument('--output-dir', default='./configs', help='Output directory')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.csv:
        csv_mode(args.csv, args.server_url, args.master_secret, args.output_dir)
    else:
        print("Use --interactive or --csv mode")
        parser.print_help()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - run interactive mode
        interactive_mode()
    else:
        main()
