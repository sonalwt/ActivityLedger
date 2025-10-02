# activity_categorizer.py
"""
Activity Categorizer - Categorizes activities based on window titles and applications
"""
import re
from typing import Dict, List, Optional, Tuple

class ActivityCategorizer:
    """Categorizes activities into Productive, Browser, and Server categories"""
    
    def __init__(self):
        # Define patterns for each category
        self.productive_patterns = [
            # IDEs and Code Editors
            r"visual studio", r"vscode", r"vs code", r"cursor", r"sublime", r"atom",
            r"intellij", r"pycharm", r"webstorm", r"phpstorm", r"rubymine",
            r"eclipse", r"netbeans", r"vim", r"emacs", r"notepad\+\+",
            
            # Development Tools
            r"git", r"github desktop", r"sourcetree", r"gitkraken",
            r"docker", r"kubernetes", r"postman", r"insomnia",
            r"datagrip", r"dbeaver", r"mysql workbench", r"pgadmin",
            r"mongodb compass", r"redis", r"terminal", r"cmd", r"powershell",
            r"wsl", r"ubuntu", r"bash", r"zsh",
            
            # File Management & Server Tools
            r"filezilla", r"winscp", r"cyberduck", r"putty", r"ssh",
            r"ftp", r"sftp", r"scp",
            
            # Control Panels
            r"cpanel", r"plesk", r"whm", r"directadmin", r"webmin",
            r"phpmyadmin", r"adminer",
            
            # Design & Documentation
            r"figma", r"sketch", r"adobe xd", r"photoshop", r"illustrator",
            r"notion", r"obsidian", r"confluence", r"jira", r"trello",
            r"asana", r"monday", r"clickup", r"linear",
            
            # Project Files
            r"\.js$", r"\.ts$", r"\.py$", r"\.php$", r"\.java$", r"\.cs$",
            r"\.cpp$", r"\.c$", r"\.rb$", r"\.go$", r"\.rs$", r"\.swift$",
            r"\.html$", r"\.css$", r"\.scss$", r"\.json$", r"\.xml$", r"\.yaml$",
            r"\.md$", r"\.txt$", r"\.sql$", r"\.sh$", r"\.bat$",
            
            # Common project folders
            r"timesheet", r"project", r"development", r"workspace",
            r"repos", r"repository", r"src", r"app", r"backend", r"frontend"
        ]
        
        self.browser_patterns = [
            # Browsers
            r"chrome", r"firefox", r"edge", r"safari", r"opera", r"brave",
            
            # AI/Chat Services
            r"claude", r"chatgpt", r"chat\.openai", r"bard", r"gemini",
            r"copilot", r"perplexity", r"phind", r"you\.com",
            
            # Development Resources
            r"stackoverflow", r"github\.com", r"gitlab", r"bitbucket",
            r"developer\.mozilla", r"w3schools", r"codecademy",
            r"freecodecamp", r"udemy", r"coursera", r"pluralsight",
            
            # Documentation Sites
            r"docs\.", r"documentation", r"api\.", r"reference",
            r"tutorial", r"guide", r"manual", r"wiki",
            
            # Social & Communication (if in browser)
            r"gmail", r"outlook", r"slack", r"discord", r"teams",
            r"twitter", r"linkedin", r"facebook", r"reddit",
            
            # Search Engines
            r"google\.com", r"bing\.com", r"duckduckgo", r"search"
        ]
        
        self.server_patterns = [
            # Cloud Providers
            r"aws", r"amazon web services", r"ec2", r"s3", r"lambda",
            r"cloudformation", r"elasticbeanstalk", r"rds", r"dynamodb",
            
            r"gcp", r"google cloud", r"compute engine", r"cloud storage",
            r"cloud functions", r"bigquery", r"firebase",
            
            r"azure", r"microsoft azure", r"azure portal", r"azure devops",
            
            r"digitalocean", r"linode", r"vultr", r"heroku", r"netlify",
            r"vercel", r"cloudflare", r"namecheap", r"godaddy",
            
            # Server Management
            r"ssh", r"rdp", r"remote desktop", r"vnc", r"teamviewer",
            r"anydesk", r"parsec",
            
            # Monitoring & Analytics
            r"datadog", r"new relic", r"grafana", r"prometheus",
            r"elastic", r"kibana", r"splunk", r"sentry",
            
            # CI/CD
            r"jenkins", r"travis", r"circle ?ci", r"gitlab ci", r"github actions",
            r"bitbucket pipelines", r"bamboo", r"teamcity",
            
            # Container & Orchestration
            r"kubernetes", r"k8s", r"docker", r"rancher", r"openshift",
            r"portainer", r"container", r"pod", r"cluster"
        ]
        
        # Non-work patterns to exclude
        self.non_work_patterns = [
            r"youtube", r"netflix", r"spotify", r"twitch", r"disney",
            r"hulu", r"prime video", r"music", r"video", r"movie",
            r"game", r"steam", r"epic games", r"origin", r"battle\.net",
            r"lock screen", r"locked", r"lockapp", r"screensaver",
            r"idle", r"afk", r"away"
        ]
    
    def categorize_activity(self, window_title: str, app_name: str = "") -> Tuple[str, float]:
        """
        Categorize an activity based on window title and application name
        Returns: (category, confidence_score)
        """
        # Combine title and app for analysis
        combined_text = f"{window_title} {app_name}".lower()
        
        # Check if it's non-work activity first
        if self._matches_patterns(combined_text, self.non_work_patterns):
            return "non-work", 0.9
        
        # Score each category
        scores = {
            "productive": self._calculate_score(combined_text, self.productive_patterns),
            "browser": self._calculate_score(combined_text, self.browser_patterns),
            "server": self._calculate_score(combined_text, self.server_patterns)
        }
        
        # Get the highest scoring category
        max_category = max(scores, key=scores.get)
        max_score = scores[max_category]
        
        # If no strong match, try to infer from context
        if max_score < 0.3:
            # Check for file extensions
            if re.search(r'\.(py|js|php|java|cs|cpp|html|css|json|xml|sql)', combined_text):
                return "productive", 0.7
            # Check if it's a browser window with development-related content
            elif any(browser in combined_text for browser in ["chrome", "firefox", "edge"]):
                if any(dev_term in combined_text for dev_term in ["localhost", "127.0.0.1", ":3000", ":8000", ":5000"]):
                    return "productive", 0.6
                else:
                    return "browser", 0.5
            else:
                return "uncategorized", 0.2
        
        return max_category, max_score
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the patterns"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _calculate_score(self, text: str, patterns: List[str]) -> float:
        """Calculate matching score for a category"""
        matches = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1
        
        # Normalize score (0 to 1)
        return min(matches / 5.0, 1.0)  # Cap at 5 matches for full score
    
    def get_detailed_category(self, window_title: str, app_name: str = "") -> Dict:
        """
        Get detailed categorization with subcategory
        """
        category, confidence = self.categorize_activity(window_title, app_name)
        
        # Determine subcategory
        combined_text = f"{window_title} {app_name}".lower()
        subcategory = "general"
        
        if category == "productive":
            if re.search(r"(cursor|vscode|visual studio|intellij|pycharm)", combined_text):
                subcategory = "coding"
            elif re.search(r"(filezilla|winscp|putty|ssh)", combined_text):
                subcategory = "server-management"
            elif re.search(r"(git|github desktop|sourcetree)", combined_text):
                subcategory = "version-control"
            elif re.search(r"(mysql|postgres|mongodb|redis)", combined_text):
                subcategory = "database"
            elif re.search(r"(figma|photoshop|sketch)", combined_text):
                subcategory = "design"
            elif re.search(r"(notion|confluence|jira)", combined_text):
                subcategory = "documentation"
                
        elif category == "browser":
            if re.search(r"(claude|chatgpt|bard)", combined_text):
                subcategory = "ai-assistance"
            elif re.search(r"(stackoverflow|github\.com)", combined_text):
                subcategory = "development-research"
            elif re.search(r"(docs\.|documentation|api\.)", combined_text):
                subcategory = "documentation"
            elif re.search(r"(gmail|outlook|slack)", combined_text):
                subcategory = "communication"
                
        elif category == "server":
            if re.search(r"(aws|ec2|s3)", combined_text):
                subcategory = "aws"
            elif re.search(r"(gcp|google cloud)", combined_text):
                subcategory = "gcp"
            elif re.search(r"(azure)", combined_text):
                subcategory = "azure"
            elif re.search(r"(kubernetes|docker)", combined_text):
                subcategory = "containers"
        
        return {
            "category": category,
            "subcategory": subcategory,
            "confidence": confidence,
            "window_title": window_title,
            "app_name": app_name
        }
    
    def categorize_batch(self, activities: List[Dict]) -> List[Dict]:
        """
        Categorize a batch of activities
        """
        categorized = []
        for activity in activities:
            window_title = activity.get('window_title', '')
            app_name = activity.get('application_name', '')
            
            category_info = self.get_detailed_category(window_title, app_name)
            
            # Add category info to activity
            activity['category'] = category_info['category']
            activity['subcategory'] = category_info['subcategory']
            activity['category_confidence'] = category_info['confidence']
            
            categorized.append(activity)
        
        return categorized


# Example usage
if __name__ == "__main__":
    categorizer = ActivityCategorizer()
    
    # Test cases
    test_cases = [
        ("timesheet_new - Cursor", "Cursor.exe"),
        ("Chrome - Claude", "chrome.exe"),
        ("AWS EC2 Dashboard", "chrome.exe"),
        ("localhost:3000 - React App", "chrome.exe"),
        ("Netflix - Watching Movie", "chrome.exe"),
        ("Termius - Node Server", "Termius.exe"),
        ("main.py - Visual Studio Code", "Code.exe"),
        ("GitHub - microsoft/vscode", "chrome.exe")
    ]
    
    for title, app in test_cases:
        result = categorizer.get_detailed_category(title, app)
        print(f"\nTitle: {title}")
        print(f"App: {app}")
        print(f"Category: {result['category']} ({result['subcategory']})")
        print(f"Confidence: {result['confidence']:.2f}")
