"""
PHASE 5: External Integrations
JIRA, Slack, GitHub, etc.
"""
import requests
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SlackNotifier:
    """Send crash notifications to Slack"""
    
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL
        self.enabled = settings.SLACK_NOTIFICATIONS_ENABLED
    
    def notify_crash(self, crash_data: Dict[str, Any], analysis: Dict[str, Any]):
        """Send crash notification to Slack"""
        if not self.enabled or not self.webhook_url:
            return
        
        try:
            severity = analysis.get("severity", "unknown")
            color = self._severity_to_color(severity)
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"Crash Detected: {crash_data.get('exception_code', 'Unknown')}",
                        "text": analysis.get("root_cause", "Analysis pending"),
                        "fields": [
                            {
                                "title": "Module",
                                "value": crash_data.get("faulting_module", "Unknown"),
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": severity.upper(),
                                "short": True
                            },
                            {
                                "title": "Confidence",
                                "value": f"{analysis.get('confidence_score', 0)}%",
                                "short": True
                            }
                        ],
                        "footer": "Crashbot AI Analysis"
                    }
                ]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info("Slack notification sent")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    def _severity_to_color(self, severity: str) -> str:
        """Map severity to Slack color"""
        colors = {
            "critical": "#FF0000",
            "high": "#FF6600",
            "medium": "#FFCC00",
            "low": "#00CC00",
            "unknown": "#999999"
        }
        return colors.get(severity.lower(), "#999999")


class JiraIntegration:
    """Create JIRA tickets for crashes"""
    
    def __init__(self, jira_url: str, api_token: str, project_key: str):
        self.jira_url = jira_url
        self.api_token = api_token
        self.project_key = project_key
    
    def create_issue(self, crash_data: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[str]:
        """
        Create JIRA issue for crash
        
        Returns:
            Issue key (e.g., 'PROJ-123') or None if failed
        """
        try:
            # Build issue description
            description = self._build_description(crash_data, analysis)
            
            # Build issue payload
            payload = {
                "fields": {
                    "project": {"key": self.project_key},
                    "summary": f"Crash: {crash_data.get('exception_code', 'Unknown')} in {crash_data.get('faulting_module', 'Unknown')}",
                    "description": description,
                    "issuetype": {"name": "Bug"},
                    "priority": {
                        "name": self._severity_to_priority(analysis.get("severity", "medium"))
                    },
                    "labels": ["crash", "automated", analysis.get("severity", "unknown")]
                }
            }
            
            # Create issue
            response = requests.post(
                f"{self.jira_url}/rest/api/2/issue",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            response.raise_for_status()
            
            issue_key = response.json().get("key")
            logger.info(f"Created JIRA issue: {issue_key}")
            
            return issue_key
            
        except Exception as e:
            logger.error(f"Failed to create JIRA issue: {e}")
            return None
    
    def _build_description(self, crash_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Build JIRA issue description"""
        description = f"""
h2. Crash Summary
*Exception Code:* {crash_data.get('exception_code', 'Unknown')}
*Faulting Module:* {crash_data.get('faulting_module', 'Unknown')}
*Platform:* {crash_data.get('platform', 'Unknown')}
*Architecture:* {crash_data.get('architecture', 'Unknown')}

h2. Root Cause
{analysis.get('root_cause', 'Analysis pending')}

h2. Explanation
{analysis.get('explanation', 'No detailed explanation available')}

h2. Recommended Solutions
"""
        
        solutions = analysis.get('solutions', [])
        for i, solution in enumerate(solutions, 1):
            description += f"\n{i}. *{solution.get('title', 'Solution')}*\n"
            description += f"   {solution.get('description', '')}\n"
        
        description += f"\n\n_Automated analysis by Crashbot AI (Confidence: {analysis.get('confidence_score', 0)}%)_"
        
        return description
    
    def _severity_to_priority(self, severity: str) -> str:
        """Map severity to JIRA priority"""
        mapping = {
            "critical": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "unknown": "Medium"
        }
        return mapping.get(severity.lower(), "Medium")


class GitHubIntegration:
    """GitHub issue and PR integration"""
    
    def __init__(self, repo: str, token: str):
        self.repo = repo  # format: "owner/repo"
        self.token = token
        self.api_url = "https://api.github.com"
    
    def create_issue(self, crash_data: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[int]:
        """Create GitHub issue for crash"""
        try:
            title = f"Crash: {crash_data.get('exception_code', 'Unknown')} in {crash_data.get('faulting_module', 'Unknown')}"
            
            body = f"""
## Crash Analysis

**Exception Code:** `{crash_data.get('exception_code', 'Unknown')}`  
**Faulting Module:** `{crash_data.get('faulting_module', 'Unknown')}`  
**Platform:** {crash_data.get('platform', 'Unknown')}  
**Severity:** {analysis.get('severity', 'unknown').upper()}  

### Root Cause
{analysis.get('root_cause', 'Analysis pending')}

### Explanation
{analysis.get('explanation', 'No detailed explanation available')}

### Recommended Solutions
"""
            
            solutions = analysis.get('solutions', [])
            for i, solution in enumerate(solutions, 1):
                body += f"\n{i}. **{solution.get('title', 'Solution')}**\n"
                body += f"   {solution.get('description', '')}\n"
            
            body += f"\n\n---\n_Automated analysis by Crashbot AI (Confidence: {analysis.get('confidence_score', 0)}%)_"
            
            payload = {
                "title": title,
                "body": body,
                "labels": ["crash", "automated", analysis.get("severity", "unknown")]
            }
            
            response = requests.post(
                f"{self.api_url}/repos/{self.repo}/issues",
                json=payload,
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=30
            )
            response.raise_for_status()
            
            issue_number = response.json().get("number")
            logger.info(f"Created GitHub issue: #{issue_number}")
            
            return issue_number
            
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return None
