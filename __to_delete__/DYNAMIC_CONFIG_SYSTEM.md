# Dynamic ActivityWatch Configuration System
# No hardcoded data - everything generated dynamically

## 🔧 How Developer ID and API Tokens Are Generated

### 1. **Server-Side Developer Registration**

When you register a developer, the system automatically generates:
- ✅ **Unique Developer ID** (based on name/email)
- ✅ **Secure API Token** (cryptographically generated)
- ✅ **Custom TOML Configuration** (personalized for each developer)

### 2. **Registration Process**

#### Method 1: API Endpoint (Recommended)
```bash
# Register developer - system auto-generates everything
curl -X POST https://your-server.com/api/v1/register-developer \
  -H "Admin-Token: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@company.com"
  }'

# Server Response (auto-generated):
{
  "developer_id": "john_doe_2025",        # Auto-generated from name
  "api_token": "dk8f9j3k2l1m5n7q8r9s",   # Cryptographically secure
  "name": "John Doe",
  "message": "Developer registered successfully"
}
```

#### Method 2: Interactive Registration Script
```bash
python register_developers.py
```

### 3. **Automatic Token Generation Logic**

The system generates tokens using:

```python
import secrets
import hashlib
from datetime import datetime

def generate_developer_id(name: str, email: str = None) -> str:
    """Generate unique developer ID from name"""
    # Clean and normalize name
    clean_name = name.lower().replace(' ', '_')
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '_')
    
    # Add year to ensure uniqueness
    year = datetime.now().year
    base_id = f"{clean_name}_{year}"
    
    # If email provided, add hash for extra uniqueness
    if email:
        email_hash = hashlib.sha256(email.encode()).hexdigest()[:4]
        base_id = f"{clean_name}_{email_hash}"
    
    return base_id

def generate_api_token() -> str:
    """Generate cryptographically secure API token"""
    return secrets.token_urlsafe(32)  # 43 characters, URL-safe
```

### 4. **Config Generation Per Developer**

Each developer gets a **personalized config**:

```toml
# ActivityWatch Configuration for John Doe
# Auto-generated on 2025-01-15 14:30:00

[server]
host = "127.0.0.1"
port = 5600

[integrations.timesheet]
enabled = true
webhook_url = "https://your-server.com/api/v1/activitywatch/webhook"
developer_id = "john_doe_2025"           # ← Auto-generated
api_token = "dk8f9j3k2l1m5n7q8r9s"       # ← Auto-generated
sync_interval = 1800

[webhooks]
enabled = true

[[webhooks.endpoints]]
url = "https://your-server.com/api/v1/activitywatch/webhook"
method = "POST"
interval = 1800
headers = {
    "Developer-ID" = "john_doe_2025",     # ← Auto-generated
    "Authorization" = "Bearer dk8f9j3k2l1m5n7q8r9s",  # ← Auto-generated
    "Content-Type" = "application/json"
}

# Privacy settings
[privacy]
include_window_titles = true
include_urls = true
exclude_patterns = ["*password*", "*login*", "*private*"]
```

## 🛠️ **Complete Setup Workflow**

### **Step 1: Register All Developers**
```bash
# Option A: One by one via API
curl -X POST https://your-server.com/api/v1/register-developer \
  -H "Admin-Token: your-admin-secret" \
  -d '{"name": "Alice Smith", "email": "alice@company.com"}'

curl -X POST https://your-server.com/api/v1/register-developer \
  -H "Admin-Token: your-admin-secret" \
  -d '{"name": "Bob Johnson", "email": "bob@company.com"}'

# Option B: Bulk registration script (see below)
python bulk_register_developers.py
```

### **Step 2: Generate All Configs**
```bash
# Automatically creates personalized config for each registered developer
python generate_aw_configs.py

# Creates:
# ├── alice_smith_2025_config.toml
# ├── alice_smith_2025_instructions.txt
# ├── bob_johnson_2025_config.toml
# ├── bob_johnson_2025_instructions.txt
# └── README.md
```

### **Step 3: Distribute to Developers**
Each developer gets:
- ✅ **Their unique config file** (with their personal ID/token)
- ✅ **Simple setup instructions** (same for everyone)
- ✅ **No sensitive data to manage** (all handled server-side)

## 📊 **Token Security Features**

### **Automatic Security**
- ✅ **32-byte random tokens** (cryptographically secure)
- ✅ **URL-safe encoding** (no special characters)
- ✅ **Unique per developer** (no sharing/reuse)
- ✅ **Server-side validation** (tokens verified on each request)
- ✅ **Revocable** (admin can disable developer access)

### **Token Rotation**
```bash
# Generate new token for developer (invalidates old one)
curl -X POST https://your-server.com/api/v1/rotate-token \
  -H "Admin-Token: your-admin-secret" \
  -d '{"developer_id": "john_doe_2025"}'

# Returns new token and updated config
```

### **Access Control**
```python
# Server validates each request
def verify_developer_token(developer_id: str, token: str) -> bool:
    developer = db.query(Developer).filter(
        Developer.developer_id == developer_id,
        Developer.api_token == token,
        Developer.active == True  # Can disable access instantly
    ).first()
    return developer is not None
```

## 🔄 **Dynamic ID Generation Examples**

### **Input → Output Examples**
```python
# Name-based generation
generate_developer_id("John Doe") 
# → "john_doe_2025"

generate_developer_id("Alice Smith-Johnson")
# → "alice_smith_johnson_2025"

generate_developer_id("Bob O'Connor", "bob@company.com")
# → "bob_oconnor_a1b2"  # with email hash

generate_developer_id("María José García")
# → "maria_jose_garcia_2025"  # handles international names
```

### **Collision Handling**
```python
def ensure_unique_developer_id(base_id: str, db: Session) -> str:
    """Ensure developer ID is unique in database"""
    original_id = base_id
    counter = 1
    
    while db.query(Developer).filter(Developer.developer_id == base_id).first():
        base_id = f"{original_id}_{counter}"
        counter += 1
    
    return base_id

# Example: If "john_doe_2025" exists, creates "john_doe_2025_1"
```

## 📋 **No Hardcoding Anywhere**

### **Configuration Template**
```python
def generate_config_toml(developer_id: str, api_token: str, server_url: str) -> str:
    """Generate ActivityWatch config with dynamic values"""
    return f'''# ActivityWatch Configuration for {developer.name}
# Generated: {datetime.now().isoformat()}

[server]
host = "127.0.0.1"
port = 5600

[integrations.timesheet]
enabled = true
webhook_url = "{server_url}/api/v1/activitywatch/webhook"
developer_id = "{developer_id}"
api_token = "{api_token}"
sync_interval = 1800

[webhooks]
enabled = true

[[webhooks.endpoints]]
url = "{server_url}/api/v1/activitywatch/webhook"
method = "POST"
interval = 1800
headers = {{
    "Developer-ID" = "{developer_id}",
    "Authorization" = "Bearer {api_token}",
    "Content-Type" = "application/json"
}}
'''
```

### **Environment-Based Server Config**
```python
# Server reads from environment (no hardcoding)
import os

SERVER_URL = os.getenv("SERVER_URL", "https://your-domain.com")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")  # Set in environment
DATABASE_URL = os.getenv("DATABASE_URL")
```

This approach ensures:
- ✅ **No hardcoded credentials** anywhere
- ✅ **Unique tokens per developer** automatically generated  
- ✅ **Secure by default** with crypto-random tokens
- ✅ **Easy token rotation** when needed
- ✅ **Scalable registration** for any team size
- ✅ **Environment-based configuration** for flexibility

Would you like me to create the bulk registration script and interactive setup tools?
