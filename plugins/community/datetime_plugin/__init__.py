"""
DateTime Plugin for Lumi AI System
Provides current date and time information to users
"""

from .datetime_plugin import DateTimePlugin

# Plugin metadata
__version__ = "1.0.0"
__author__ = "Lumi AI Team"
__description__ = "Provides current date and time information to users"

# Export the main plugin class
__all__ = ['DateTimePlugin']

# Plugin factory function - this is what the plugin manager looks for
def create_plugin():
    """
    Factory function that creates and returns an instance of the DateTimePlugin.
    This is the standard entry point that the plugin manager uses to load plugins.
    """
    return DateTimePlugin()

# Optional: Plugin configuration schema for validation
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean", "default": True},
        "timezone": {"type": "string", "default": ""},
        "time_format": {"type": "string", "default": "HH:mm:ss"},
        "date_format": {"type": "string", "default": "YYYY-MM-DD"},
        "datetime_format": {"type": "string", "default": "YYYY-MM-DD HH:mm:ss"},
        "dashboard_time_format": {"type": "string", "default": "HH:mm:ss"},
        "dashboard_date_format": {"type": "string", "default": "YYYY-MM-DD"},
        "verbose_responses": {"type": "boolean", "default": True},
        "include_timezone": {"type": "boolean", "default": True},
        "natural_language": {"type": "boolean", "default": True}
    },
    "additionalProperties": False
}

# Optional: Default configuration
DEFAULT_CONFIG = {
    "enabled": True,
    "timezone": "",
    "time_format": "HH:mm:ss",
    "date_format": "YYYY-MM-DD",
    "datetime_format": "YYYY-MM-DD HH:mm:ss",
    "dashboard_time_format": "HH:mm:ss",
    "dashboard_date_format": "YYYY-MM-DD",
    "verbose_responses": True,
    "include_timezone": True,
    "natural_language": True
}