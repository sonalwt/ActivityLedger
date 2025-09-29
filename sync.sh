#!/bin/bash
# ActivityWatch Sync Script - Dynamic Version with Fixed Bucket Extraction

# Get developer details from:
# 1. Command line arguments: ./sync.sh "name" "token"
# 2. Environment variables: AW_DEVELOPER_NAME and AW_API_TOKEN
# 3. Config file: ~/.aw-sync-config
# 4. Interactive prompt

if [ -n "$1" ] && [ -n "$2" ]; then
    # From command line arguments
    DEVELOPER_NAME="$1"
    API_TOKEN="$2"
elif [ -n "$AW_DEVELOPER_NAME" ] && [ -n "$AW_API_TOKEN" ]; then
    # From environment variables
    DEVELOPER_NAME="$AW_DEVELOPER_NAME"
    API_TOKEN="$AW_API_TOKEN"
elif [ -f "$HOME/.aw-sync-config" ]; then
    # From config file
    source "$HOME/.aw-sync-config"
else
    # Interactive prompt
    echo "ActivityWatch Sync Setup"
    echo "========================"
    read -p "Enter your developer name: " DEVELOPER_NAME
    read -s -p "Enter your API token: " API_TOKEN
    echo ""
    
    # Offer to save for next time
    read -p "Save credentials for future use? (y/n): " save_config
    if [ "$save_config" = "y" ] || [ "$save_config" = "Y" ]; then
        echo "DEVELOPER_NAME=\"$DEVELOPER_NAME\"" > "$HOME/.aw-sync-config"
        echo "API_TOKEN=\"$API_TOKEN\"" >> "$HOME/.aw-sync-config"
        chmod 600 "$HOME/.aw-sync-config"
        echo "Credentials saved to ~/.aw-sync-config"
    fi
fi

# Validate inputs
if [ -z "$DEVELOPER_NAME" ] || [ -z "$API_TOKEN" ]; then
    echo "Error: Developer name and API token are required!"
    echo ""
    echo "Usage options:"
    echo "  1. ./sync.sh \"developer_name\" \"api_token\""
    echo "  2. Export environment variables:"
    echo "     export AW_DEVELOPER_NAME=\"your_name\""
    echo "     export AW_API_TOKEN=\"your_token\""
    echo "  3. Create config file ~/.aw-sync-config with:"
    echo "     DEVELOPER_NAME=\"your_name\""
    echo "     API_TOKEN=\"your_token\""
    exit 1
fi

# Server configuration
SERVER_URL="https://api-timesheet.firsteconomy.com/api/sync"
LOCAL_AW="http://localhost:5600/api/0"

send_data() {
    echo "Checking ActivityWatch at $(date '+%H:%M:%S')"
    
    if ! command -v curl &> /dev/null; then
        echo "Error: curl is required but not installed"
        return 1
    fi
    
    # Get buckets from ActivityWatch
    buckets_response=$(curl -s --max-time 10 "$LOCAL_AW/buckets/" 2>/dev/null)
    if [ $? -ne 0 ] || [ -z "$buckets_response" ]; then
        echo "ActivityWatch not responding"
        return 1
    fi
    
    # Extract bucket names using Python for reliability
    bucket_names=""
    if command -v python3 &> /dev/null; then
        bucket_names=$(echo "$buckets_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for key in data.keys():
        print(key)
except:
    pass
" 2>/dev/null)
    fi
    
    # Fallback: Extract bucket names that start with 'aw-'
    if [ -z "$bucket_names" ]; then
        # Look for patterns like "aw-watcher-window_hostname"
        bucket_names=$(echo "$buckets_response" | sed -n 's/.*"\(aw-[^"]*\)".*/\1/p' | sort -u)
    fi
    
    if [ -z "$bucket_names" ]; then
        echo "No ActivityWatch buckets found"
        echo "Debug: Check buckets at http://localhost:5600/#/buckets/"
        return 1
    fi
    
    bucket_count=$(echo "$bucket_names" | wc -l)
    echo "Found $bucket_count ActivityWatch buckets"
    
    # Calculate time range
    if [[ "$OSTYPE" == "darwin"* ]]; then
        start_time=$(date -u -v-6M '+%Y-%m-%dT%H:%M:%S.000Z')
        end_time=$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')
    else
        start_time=$(date -u -d '6 minutes ago' '+%Y-%m-%dT%H:%M:%S.000Z')
        end_time=$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')
    fi
    
    # Collect events from first bucket with data
    all_events=""
    
    for bucket in $bucket_names; do
        if [ -n "$bucket" ]; then
            # Make sure bucket doesn't contain 'http://' or slashes
            if [[ "$bucket" == *"http"* ]] || [[ "$bucket" == *"/"* ]]; then
                continue
            fi
            
            events_url="$LOCAL_AW/buckets/$bucket/events?start=$start_time&end=$end_time"
            echo "Checking bucket: $bucket"
            
            # Get events and save to temp file to preserve JSON
            curl -s --max-time 15 "$events_url" -o /tmp/aw_events_$$.json 2>/dev/null
            
            if [ $? -eq 0 ] && [ -s /tmp/aw_events_$$.json ]; then
                # Check if file contains actual events (not just [])
                if ! grep -q '^\[\]$' /tmp/aw_events_$$.json; then
                    # Use the events directly without modification
                    all_events=$(cat /tmp/aw_events_$$.json)
                    rm -f /tmp/aw_events_$$.json
                    echo "Using events from bucket: $bucket"
                    break
                fi
            fi
            rm -f /tmp/aw_events_$$.json
        fi
    done
    
    # If no events found, use empty array
    if [ -z "$all_events" ]; then
        all_events="[]"
    fi
    
    if [ "$all_events" = "[]" ]; then
        echo "No new data to sync"
        return 0
    fi
    
    # Create payload
    payload="{\"name\":\"$DEVELOPER_NAME\",\"token\":\"$API_TOKEN\",\"data\":$all_events,\"timestamp\":\"$end_time\"}"
    
    # Send to server
    response=$(curl -s --max-time 20 -X POST -H "Content-Type: application/json" -d "$payload" "$SERVER_URL" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        if echo "$response" | grep -q '"success":true'; then
            event_count=$(echo "$all_events" | grep -o '{' | wc -l)
            echo "✓ Synced $event_count events successfully"
        else
            echo "✗ Server error: $response"
            # Debug: save response for inspection
            echo "$response" > /tmp/sync_error_$$.json
            echo "   (Debug info saved to /tmp/sync_error_$$.json)"
        fi
    else
        echo "✗ Failed to connect to server"
    fi
}

echo "=================================================="
echo "ActivityWatch Sync for $DEVELOPER_NAME"
echo "=================================================="
echo "Press Ctrl+C to stop"
echo ""

# Initial check for ActivityWatch
echo "Testing ActivityWatch connection..."
if curl -s --max-time 5 "$LOCAL_AW/info" > /dev/null 2>&1; then
    echo "✓ ActivityWatch is running"
else
    echo "✗ ActivityWatch is not running or not accessible"
    echo "  Please start ActivityWatch first"
    exit 1
fi

while true; do
    send_data
    if [[ "$OSTYPE" == "darwin"* ]]; then
        next_sync=$(date -v+5M '+%H:%M:%S')
    else
        next_sync=$(date -d '+5 minutes' '+%H:%M:%S')
    fi
    echo "Waiting 5 minutes... (next sync at $next_sync)"
    sleep 300
done