"""
Web interface components for DateTime Plugin
"""

from typing import Dict, Any
import datetime

class DateTimeWebComponents:
    """Web interface components for the DateTime plugin"""
    
    @staticmethod
    def get_settings_form(current_config: Dict) -> Dict:
        """Generate settings form for web interface"""
        return {
            "type": "form",
            "title": "Date & Time Settings",
            "description": "Configure how date and time information is displayed",
            "sections": [
                {
                    "title": "Time Configuration",
                    "fields": [
                        {
                            "name": "timezone",
                            "label": "Timezone",
                            "type": "select",
                            "options": [
                                {"value": "", "label": "System Default"},
                                {"value": "UTC", "label": "UTC"},
                                {"value": "US/Eastern", "label": "Eastern Time"},
                                {"value": "US/Central", "label": "Central Time"},
                                {"value": "US/Mountain", "label": "Mountain Time"},
                                {"value": "US/Pacific", "label": "Pacific Time"},
                                {"value": "Europe/London", "label": "London"},
                                {"value": "Europe/Paris", "label": "Paris"},
                                {"value": "Asia/Tokyo", "label": "Tokyo"}
                            ],
                            "value": current_config.get('timezone', ''),
                            "help": "Leave empty for system timezone. Requires pytz for custom timezones."
                        },
                        {
                            "name": "time_format",
                            "label": "Time Format",
                            "type": "text",
                            "value": current_config.get('time_format', 'HH:mm:ss'),
                            "help": "Use HH for 24-hour, hh for 12-hour, mm for minutes, ss for seconds"
                        },
                        {
                            "name": "date_format",
                            "label": "Date Format",
                            "type": "text",
                            "value": current_config.get('date_format', 'YYYY-MM-DD'),
                            "help": "Use YYYY for year, MM for month, DD for day"
                        }
                    ]
                },
                {
                    "title": "Display Settings",
                    "fields": [
                        {
                            "name": "verbose_responses",
                            "label": "Verbose Responses",
                            "type": "checkbox",
                            "value": current_config.get('verbose_responses', True),
                            "help": "Use natural language responses instead of just numbers"
                        },
                        {
                            "name": "include_timezone",
                            "label": "Include Timezone",
                            "type": "checkbox",
                            "value": current_config.get('include_timezone', True),
                            "help": "Show timezone information in responses"
                        },
                        {
                            "name": "natural_language",
                            "label": "Natural Language",
                            "type": "checkbox",
                            "value": current_config.get('natural_language', True),
                            "help": "Use friendly language in responses"
                        }
                    ]
                }
            ]
        }
    
    @staticmethod
    def get_dashboard_widget(plugin_data: Dict) -> Dict:
        """Generate dashboard widget for current time display"""
        current_time = datetime.datetime.now()
        
        return {
            "type": "card",
            "title": "🕒 Current Time",
            "content": [
                {
                    "type": "text",
                    "content": f"**Time**: {current_time.strftime('%H:%M:%S')}",
                    "size": "large"
                },
                {
                    "type": "text", 
                    "content": f"**Date**: {current_time.strftime('%Y-%m-%d')}",
                    "size": "medium"
                },
                {
                    "type": "text",
                    "content": f"**Day**: {current_time.strftime('%A')}",
                    "size": "small"
                }
            ],
            "actions": [
                {
                    "label": "Refresh",
                    "action": "refresh_datetime",
                    "icon": "refresh"
                }
            ],
            "size": "small"
        }