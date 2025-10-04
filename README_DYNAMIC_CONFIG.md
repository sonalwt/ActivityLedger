# Dynamic Configuration for Timesheet Sync

This project now supports dynamic configuration for developer name and API token instead of hardcoding them. Here are the available methods:

## Configuration Methods

### 1. **Secure Credential Storage (Recommended)**
Uses Windows built-in encryption to store credentials securely.

**Setup:**
1. Run `manage_credentials.bat`
2. Choose option 1 to set credentials
3. Enter your developer name and API token

**Usage:**
```batch
start_sync_secure.bat
```

**Advantages:**
- Most secure - API token is encrypted
- Credentials persist across sessions
- No need to enter credentials each time

### 2. **Interactive Mode**
Prompts for credentials when the script starts.

**Usage:**
```batch
start_sync_interactive.bat
```

**Advantages:**
- No credentials stored on disk
- Good for shared computers

### 3. **Configuration File**
Uses a JSON file to store credentials.

**Setup:**
1. Copy `sync_config.json.example` to `sync_config.json`
2. Edit the file with your credentials

**Usage:**
```batch
start_sync_interactive.bat
```
(The script will detect and use the config file)

**Example sync_config.json:**
```json
{
    "DeveloperName": "your-name",
    "ApiToken": "your-api-token"
}
```

### 4. **Environment Variables**
Set credentials as environment variables.

**Setup Option A - Edit the batch file:**
Edit `start_sync_env.bat` and set your credentials:
```batch
set TIMESHEET_DEVELOPER_NAME=your-name
set TIMESHEET_API_TOKEN=your-api-token
```

**Setup Option B - System-wide:**
1. Open System Properties → Environment Variables
2. Add:
   - Variable: `TIMESHEET_DEVELOPER_NAME` Value: `your-name`
   - Variable: `TIMESHEET_API_TOKEN` Value: `your-api-token`

**Usage:**
```batch
start_sync_env.bat
```

### 5. **Command Line Parameters**
Pass credentials directly as parameters.

**Usage:**
```batch
start_sync_params.bat "your-name" "your-api-token"
```

**Advantages:**
- Good for automation/scripting
- Can create shortcuts with different credentials

## Priority Order

If multiple configuration methods are present, they are used in this order:
1. Command line parameters
2. Environment variables
3. Configuration file (sync_config.json)
4. Interactive prompt

## Security Notes

1. **Most Secure:** Use the secure credential storage method (`start_sync_secure.bat`)
2. **Avoid:** Hardcoding credentials in scripts
3. **Be Careful:** With config files - don't commit them to version control
4. **Add to .gitignore:** `sync_config.json` and any files with credentials

## Troubleshooting

### "No credentials found"
- Run `manage_credentials.bat` to set up secure credentials
- Or use one of the other methods listed above

### "Cannot decrypt API token"
- The secure credentials were created by a different Windows user
- Run `manage_credentials.bat` option 4 to remove, then option 1 to reset

### DNS Resolution Issues
- Run `diagnose_connection.bat` to check connectivity
- Ensure you're connected to company VPN if required
- Contact IT for the correct server address

## Quick Start

For first-time setup:
1. Run `manage_credentials.bat`
2. Choose option 1 and enter your credentials
3. Run `start_sync_secure.bat` to start syncing

That's it! Your credentials are now securely stored and the sync will use them automatically.
