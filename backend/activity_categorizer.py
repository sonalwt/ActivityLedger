# activity_categorizer.py
"""
Four Categories:
1) PRODUCTIVE  → IDEs, Office, dev tools, terminals, database tools, AI tools, project folders
2) BROWSER     → YouTube, Gmail, social, entertainment, shopping, ALL MAIL
3) SERVER      → AWS, GCP, Azure, SSH, Docker, monitoring, hosting, Firebase
4) NON-WORK    → Lock screen, idle, AFK, personal media, system utilities
"""

import re
from typing import Dict, List, Tuple


class ActivityCategorizer:
    def __init__(self):

        # Known projects/clients - ALWAYS productive
        self.known_projects = [
            "radiant_clone", "radiant clone", "radiant-mail", "timesheet",
            "waaree", "firsteconomy", "first economy",
            "hdfc", "mahindra", "manulife", "indosolar",
            "jaypeeinfratechcoin", "scalpe", "nodeserver"
        ]

        # 🟦 SERVER keywords (word-boundary safe)
        self.server_keywords = [
            # AWS (use longer forms to avoid substring issues)
            "aws console", "aws.", "ec2", "s3 bucket", "lambda function",
            "iam ", "cloudwatch", "cloudfront", "route 53", "elasticache",
            "amazon web services",
            # Azure
            "azure", "microsoft azure",
            # GCP / Firebase
            "gcp", "google cloud", "firebase", "firestore",
            # Hosting / DNS
            "digitalocean", "droplet", "linode", "vultr",
            "vercel", "netlify", "cloudflare", "godaddy", "namecheap",
            "heroku", "render.com", "railway.app",
            # CI/CD
            "jenkins", "github actions", "gitlab ci", "circleci", "travis ci",
            # Containers
            "docker", "kubernetes", "k8s",
            # Monitoring
            "grafana", "prometheus", "datadog", "new relic", "sentry",
            "statuscake", "status cake",
            # Remote access
            "ssh ", "rdp ", " vnc", "teamviewer", "anydesk", "openvpn",
            "termius", "putty", "securecrt", "xshell", "mobaxterm",
            "winscp",
            # cPanel / hosting panels
            "cpanel", "whm", "plesk", "directadmin"
        ]

        # 🟩 PRODUCTIVE apps/tools (checked by app_name or specific indicators)
        self.productive_apps = [
            # IDEs
            "vscode", "code.exe", "cursor", "pycharm", "intellij",
            "webstorm", "phpstorm", "sublime", "atom", "vim", "nvim",
            "emacs", "notepad++", "visual studio", "claude code",
            "android studio", "xcode", "rider", "goland", "rubymine",
            "clion", "datagrip",
            # Terminals
            "windowsterminal", "windows terminal", "powershell",
            "cmd.exe", "pwsh.exe", "git bash", "mintty", "conemu",
            "cmder", "hyper", "warp", "alacritty", "wezterm",
            # Microsoft Office
            "winword", "excel", "powerpnt", "onenote", "msword",
            "microsoft word", "microsoft excel", "microsoft powerpoint",
            "microsoft teams",
            # Database tools
            "dbeaver", "pgadmin", "mysql workbench", "mongodb compass",
            "redis", "sqlitestudio", "navicat", "heidisql",
            "phpmyadmin", "adminer",
            # Git tools
            "github desktop", "gitkraken", "sourcetree", "tortoisegit",
            "lazygit",
            # API tools
            "postman", "insomnia", "hoppscotch",
            # Design
            "figma", "adobe xd", "photoshop", "illustrator", "canva",
            "sketch",
            # AI tools
            "chatgpt", "claude", "perplexity", "phind", "copilot",
            # Communication (work)
            "slack", "zoom", "microsoft teams", "google meet",
            # File transfer
            "filezilla",
            # Note-taking
            "notion", "obsidian",
            # Windows tools
            "notepad.exe", "calculator"
        ]

        # 🟩 PRODUCTIVE browser URLs/sites
        self.productive_sites = [
            # Code hosting
            "github.com", "gitlab.com", "bitbucket",
            # Dev communities
            "stackoverflow", "stack overflow", "stackexchange",
            "dev.to", "hashnode",
            # Package registries
            "npmjs.com", "pypi.org", "crates.io", "nuget.org",
            "packagist.org", "rubygems.org",
            # Documentation
            "developer.mozilla.org", "mdn web docs",
            "docs.python.org", "docs.oracle.com",
            "reactjs.org", "vuejs.org", "angular.io", "nextjs.org",
            "tailwindcss.com", "getbootstrap.com",
            "swagger", "readthedocs", "gitbook",
            # Dev tools
            "localhost", "127.0.0.1",
            ":3000", ":8000", ":5000", ":4200", ":8080", ":5173",
            # PM tools
            "jira", "trello", "asana", "confluence", "clickup",
            "linear.app", "basecamp",
            # AI tools
            "chat.openai.com", "claude.ai", "perplexity.ai",
            # CMS
            "wordpress", "wp-admin"
        ]

        # Code file extensions
        self.code_extensions = [
            ".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".java",
            ".cpp", ".c", ".h", ".cs", ".rb", ".go", ".rs", ".vue",
            ".html", ".css", ".scss", ".sass", ".json", ".xml", ".sql",
            ".swift", ".kt", ".dart", ".sh", ".yaml", ".yml",
            ".env", ".gitignore", ".dockerfile", ".toml", ".ini"
        ]

        # Pre-compile regex patterns for code extensions (avoid recompiling per row)
        self._code_ext_patterns = [
            re.compile(re.escape(ext) + r'(?:\s|$|["\s\-,;])')
            for ext in self.code_extensions
        ]

        # 🟧 BROWSER (non-productive) keywords
        self.browser_keywords = [
            # Shopping
            "amazon.in", "amazon.com", "flipkart", "myntra", "ajio",
            "snapdeal", "meesho", "add to cart", "buy online",
            # Entertainment
            "youtube", "youtu.be", "netflix", "amazon prime",
            "primevideo", "hotstar", "spotify", "twitch", "voot",
            "zee5", "sonyliv", "jiocinema",
            # Social
            "facebook", "instagram", "snapchat", "tiktok",
            "pinterest", "reddit", "twitter", "x.com",
            "whatsapp web", "telegram web", "linkedin feed",
            # Search
            "google.com/search", "bing.com/search",
            "duckduckgo", "- google search",
            # Google services (non-work)
            "google photos", "google maps", "google calendar",
            # News / non-work
            "news", "cricket", "sports", "movies", "songs",
            # Extensions
            "awesome screenshot"
        ]

        # 🟥 NON-WORK keywords
        self.non_work_keywords = [
            "untitled", "new tab", "blank", "empty",
            "lockapp.exe", "lockapp", "lock screen", "sessionlock",
            "windows default lock screen",
            "idle", "idle-time", "afk", "away",
            "not active", "userinactive", "no active window",
            "screensaver", "screen saver", "new incognito tab",
            # Windows system
            "program manager", "task manager",
            "ms-settings", "windows settings", "control panel",
            # Personal media apps
            "photos.exe", "microsoft.photos",
            "movies & tv", "groove music", "windows media player",
            "vlc media player"
        ]

        # Personal folders (for File Explorer)
        self.personal_folders = [
            "downloads", "documents", "desktop", "pictures",
            "music", "videos", "recycle bin", "this pc",
            "onedrive", "dropbox", "appdata"
        ]

    def categorize_activity(self, window_title: str, app_name: str = "", project_name: str = "") -> Tuple[str, float]:
        text = f"{window_title} {app_name} {project_name}".lower()
        window_lower = window_title.lower().strip()
        app_lower = app_name.lower().strip() if app_name else ""

        # ── Termius -> SERVER (check by app name before project match) ──
        if "termius" in app_lower:
            return ("server", 1.0)

        # ── 0a. ALL browser apps -> BROWSER (before project match) ──
        browser_apps = ["chrome.exe", "google chrome", "firefox", "msedge",
                        "brave", "opera", "safari", "vivaldi", "arc"]
        is_browser_app = any(b in app_lower for b in browser_apps)
        if is_browser_app:
            # Check server keywords first (AWS, StatusCake, etc. in browser = server)
            for word in self.server_keywords:
                if word in text:
                    return ("server", 0.95)
            return ("browser", 1.0)

        # ── 0b. Known projects -> ALWAYS PRODUCTIVE (check first!) ──
        if project_name and any(project in project_name.lower() for project in self.known_projects):
            return ("productive", 1.0)

        # ── 1. SKIP: Empty/meaningless/idle ──
        idle_titles = ["untitled", "new tab", "blank", "",
                       "open folder", "welcome", "walkthrough",
                       "getting started", "release notes",
                       "visual studio code"]
        if window_lower in idle_titles:
            # If it's an IDE title but has a project name, it's still productive work
            if window_lower == "visual studio code" and project_name:
                return ("productive", 1.0)
            return ("non-work", 1.0)

        # ── 2. EMAIL: Always browser ──
        email_indicators = ["inbox", "@gmail", "@yahoo", "@outlook", "@hotmail",
                           "@firsteconomy", "first economy mail", "webmail"]
        if any(ind in text for ind in email_indicators):
            # But NOT if it's a code file with "mail" in the path
            if not any(ext in text for ext in [".py", ".js", ".jsx", ".ts", ".php", ".html"]):
                return ("browser", 1.0)

        # ── 3. uKnowva/HR portal -> BROWSER ──
        if "uknowva" in text or "uknowa" in text:
            return ("browser", 1.0)

        # ── 4. System utilities -> NON-WORK ──
        system_apps = ["notification center", "shellexperiencehost", "searchhost",
                       "searchapp", "searchui", "windows shell experience host",
                       "snipping tool", "snippingtool", "cortana"]
        if any(app in text for app in system_apps):
            return ("non-work", 1.0)

        # ── 5. Known projects -> ALWAYS PRODUCTIVE ──
        if any(project in text for project in self.known_projects):
            return ("productive", 1.0)

        # ── 6. IDEs & Terminals -> PRODUCTIVE ──
        ide_indicators = [
            "vscode", "code.exe", "cursor", "pycharm", "intellij",
            "webstorm", "phpstorm", "sublime", "atom", " vim ",
            "emacs", "notepad++", "visual studio", "claude code",
            "android studio", "xcode", "rider", "goland", "rubymine",
            "clion", "datagrip"
        ]
        if any(ide in text for ide in ide_indicators):
            return ("productive", 1.0)

        terminal_indicators = [
            "windowsterminal", "windows terminal", "powershell",
            "cmd.exe", "pwsh.exe", "git bash", "mintty",
            "conemu", "cmder", "command prompt"
        ]
        if any(t in text for t in terminal_indicators):
            return ("productive", 1.0)

        # ── 7. Microsoft Office -> PRODUCTIVE ──
        office_tools = ["winword", "excel", "powerpnt", "onenote", "msword",
                        "microsoft word", "microsoft excel", "microsoft powerpoint",
                        "libreoffice", "openoffice"]
        if any(tool in text for tool in office_tools):
            return ("productive", 1.0)

        # ── 8. Code file extensions -> PRODUCTIVE ──
        for i, ext in enumerate(self.code_extensions):
            if window_lower.endswith(ext) or f"{ext} " in text or self._code_ext_patterns[i].search(text):
                return ("productive", 1.0)

        # ── 9. Database tools -> PRODUCTIVE ──
        db_tools = ["dbeaver", "pgadmin", "mysql workbench", "mongodb compass",
                     "sqlitestudio", "navicat", "heidisql", "phpmyadmin",
                     "adminer", "redis desktop"]
        if any(db in text for db in db_tools):
            return ("productive", 1.0)

        # ── 10. Design / API / PM tools -> PRODUCTIVE ──
        work_tools = ["postman", "insomnia", "figma", "adobe xd", "photoshop",
                      "illustrator", "canva", "sketch", "filezilla",
                      "jira", "notion", "trello", "asana", "confluence",
                      "clickup", "obsidian", "slack", "microsoft teams",
                      "github desktop", "gitkraken", "sourcetree"]
        if any(tool in text for tool in work_tools):
            return ("productive", 1.0)

        # ── 11. AI tools -> PRODUCTIVE ──
        ai_tools = ["chatgpt", "claude.ai", "perplexity", "phind",
                     "copilot", "chat.openai"]
        if any(ai in text for ai in ai_tools):
            return ("productive", 1.0)

        # ── 12. SERVER keywords ──
        for word in self.server_keywords:
            if word in text:
                return ("server", 0.95)

        # ── 13. File Explorer -> smart check ──
        if "file explorer" in text:
            if any(f in text for f in self.personal_folders):
                return ("non-work", 1.0)
            return ("productive", 0.85)

        # ── 14. NON-WORK keywords ──
        for word in self.non_work_keywords:
            if word in text:
                return ("non-work", 1.0)

        # ── 15. Browser: productive sites first ──
        is_browser = any(b in app_lower for b in
                        ["chrome", "firefox", "msedge", "brave", "opera", "browser"])

        if is_browser:
            # Check productive sites FIRST
            for site in self.productive_sites:
                if site in text:
                    return ("productive", 0.95)

            # Shopping
            shopping = ["amazon.in", "amazon.com", "flipkart", "myntra",
                       "ajio", "meesho", "snapdeal"]
            if any(s in text for s in shopping):
                return ("browser", 1.0)

            # Entertainment
            entertainment = ["youtube", "netflix", "primevideo", "hotstar",
                           "spotify", "twitch", "voot", "zee5", "sonyliv"]
            if any(e in text for e in entertainment):
                return ("browser", 1.0)

            # Social media
            social = ["facebook", "instagram", "snapchat", "tiktok",
                     "pinterest", "reddit", "twitter", "x.com"]
            if any(s in text for s in social):
                return ("browser", 1.0)

            # Email in browser
            if "mail" in text or "inbox" in text or "compose" in text:
                return ("browser", 1.0)

            # Search
            if "google.com/search" in text or "- google search" in text:
                return ("browser", 0.95)

            # Google non-work services
            google_nonwork = ["google photos", "google maps", "google calendar"]
            if any(g in text for g in google_nonwork):
                return ("browser", 0.90)

            # News/entertainment keywords
            nonwork_browsing = ["news", "cricket", "sports", "movies",
                               "songs", "shopping", "buy online"]
            if any(n in text for n in nonwork_browsing):
                return ("browser", 0.90)

            # Generic browser content not caught above
            return ("browser", 0.85)

        # ── 16. Generic titles -> BROWSER ──
        generic_titles = ["welcome", "home", "start", "open", "loading",
                         "page", "open folder"]
        if window_lower in generic_titles:
            return ("browser", 1.0)

        # ── 17. Communication apps (Zoom, Meet) -> PRODUCTIVE ──
        comm_apps = ["zoom", "google meet", "teams"]
        if any(c in text for c in comm_apps):
            return ("productive", 0.90)

        # ── 18. Default -> PRODUCTIVE ──
        # Developer is active on something not caught above
        return ("productive", 0.90)

    def get_detailed_category(self, window_title: str, app_name: str = "", project_name: str = "") -> Dict:
        category, confidence = self.categorize_activity(window_title, app_name, project_name)
        text = f"{window_title} {app_name}".lower()

        if category == "non-work":
            if "lock" in text:
                sub = "system-lock"
            elif "idle" in text or "afk" in text:
                sub = "idle"
            elif "file explorer" in text:
                sub = "file-browsing"
            elif "task manager" in text:
                sub = "system"
            else:
                sub = "non-work"
        elif category == "browser":
            if "@" in text or "inbox" in text or "mail" in text:
                sub = "email"
            elif "youtube" in text or "netflix" in text or "spotify" in text:
                sub = "entertainment"
            elif "amazon" in text or "flipkart" in text or "myntra" in text:
                sub = "shopping"
            elif "facebook" in text or "instagram" in text or "twitter" in text:
                sub = "social-media"
            elif "google.com/search" in text or "google search" in text:
                sub = "search"
            elif "uknowva" in text:
                sub = "hr-portal"
            else:
                sub = "general-browsing"
        elif category == "server":
            if "aws" in text or "ec2" in text or "s3" in text:
                sub = "aws"
            elif "azure" in text:
                sub = "azure"
            elif "gcp" in text or "firebase" in text or "google cloud" in text:
                sub = "gcp"
            elif "docker" in text or "kubernetes" in text:
                sub = "containers"
            elif "ssh" in text or "putty" in text or "termius" in text:
                sub = "remote-access"
            elif "vercel" in text or "netlify" in text or "cloudflare" in text:
                sub = "hosting"
            elif "cpanel" in text:
                sub = "hosting"
            else:
                sub = "server-tools"
        else:  # PRODUCTIVE
            if any(ide in text for ide in ["vscode", "code.exe", "cursor",
                                           "visual studio", "pycharm", "intellij"]):
                sub = "coding"
            elif any(t in text for t in ["terminal", "powershell", "cmd.exe", "git bash"]):
                sub = "terminal"
            elif any(o in text for o in ["winword", "excel", "powerpnt"]):
                sub = "office"
            elif "localhost" in text or ":3000" in text or ":8080" in text:
                sub = "dev-server"
            elif "postman" in text or "insomnia" in text:
                sub = "api-testing"
            elif "figma" in text or "photoshop" in text or "illustrator" in text:
                sub = "design"
            elif any(db in text for db in ["dbeaver", "pgadmin", "mysql", "mongodb"]):
                sub = "database"
            elif "github" in text or "gitlab" in text or "bitbucket" in text:
                sub = "version-control"
            elif "stackoverflow" in text or "stack overflow" in text:
                sub = "research"
            elif any(ai in text for ai in ["chatgpt", "claude", "perplexity", "copilot"]):
                sub = "ai-tools"
            elif "slack" in text or "teams" in text or "zoom" in text:
                sub = "communication"
            elif "file explorer" in text:
                sub = "file-browsing"
            elif "jira" in text or "trello" in text or "notion" in text:
                sub = "project-management"
            else:
                sub = "productive-general"

        return {
            "category": category,
            "subcategory": sub,
            "confidence": confidence,
            "window_title": window_title,
            "app_name": app_name
        }

    def categorize_batch(self, activities: List[Dict]) -> List[Dict]:
        categorized = []
        for activity in activities:
            info = self.get_detailed_category(
                activity.get("window_title", ""),
                activity.get("application_name", "")
            )
            activity.update(info)
            categorized.append(activity)
        return categorized


# Module-level singleton — avoids re-creating keyword lists on every request
_categorizer_instance = None

def get_categorizer() -> ActivityCategorizer:
    global _categorizer_instance
    if _categorizer_instance is None:
        _categorizer_instance = ActivityCategorizer()
    return _categorizer_instance


if __name__ == "__main__":
    categorizer = get_categorizer()

    test_cases = [
        ("Document1 - Microsoft Word", "WINWORD.EXE"),
        ("Snipping Tool Overlay", "SnippingTool.exe"),
        ("Online Shopping - Amazon.in", "chrome.exe"),
        ("Luxury Dealz - ankita@firsteconomy.com - First Economy Mail", "chrome.exe"),
        ("[Claude Code] radiant_clone\\src\\Mail.jsx", "Code.exe"),
        ("Welcome", "chrome.exe"),
        ("YouTube - Google Chrome", "chrome.exe"),
        ("index.js - myproject - Visual Studio Code", "Code.exe"),
        ("Radiant-mail - Usage and billing - Firebase console", "chrome.exe"),
        ("Downloads - File Explorer", "explorer.exe"),
        ("scalpe - File Explorer", "explorer.exe"),
        ("Search", "SearchHost.exe"),
        ("PS D:\\projects> npm start", "WindowsTerminal.exe"),
        ("pgAdmin 4", "pgAdmin4.exe"),
        ("npmjs.com - express", "chrome.exe"),
        ("developer.mozilla.org - Array.map()", "chrome.exe"),
        ("Slack - #general", "Slack.exe"),
    ]

    print("Testing categorization:")
    print("-" * 70)
    for title, app in test_cases:
        info = categorizer.get_detailed_category(title, app)
        print(f"  {title}")
        print(f"  {app} -> {info['category'].upper()} ({info['subcategory']})")
        print("-" * 70)
