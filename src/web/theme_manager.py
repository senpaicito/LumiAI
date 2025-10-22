import json
import logging
from pathlib import Path
from config import settings

class ThemeManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.themes_path = Path(settings.CONFIG_DIR) / "themes.json"
        self.current_theme = "default"
        self.available_themes = {}
        
        self.load_themes()
    
    def load_themes(self):
        """Load available themes from configuration"""
        try:
            if self.themes_path.exists():
                with open(self.themes_path, 'r', encoding='utf-8') as f:
                    self.available_themes = json.load(f)
            else:
                self._create_default_themes()
            
            self.logger.info(f"Loaded {len(self.available_themes)} themes")
            
        except Exception as e:
            self.logger.error(f"Error loading themes: {e}")
            self._create_default_themes()
    
    def _create_default_themes(self):
        """Create default themes if none exist"""
        self.available_themes = {
            "default": {
                "name": "Ocean Blue",
                "colors": {
                    "primary": "#4facfe",
                    "secondary": "#00f2fe",
                    "accent": "#667eea",
                    "background": "#f8f9fa",
                    "surface": "#ffffff",
                    "text": "#333333",
                    "text_secondary": "#666666"
                },
                "gradients": {
                    "header": "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
                    "card": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    "accent": "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)"
                }
            },
            "dark": {
                "name": "Midnight Dark",
                "colors": {
                    "primary": "#6366f1",
                    "secondary": "#8b5cf6",
                    "accent": "#ec4899",
                    "background": "#1a1a1a",
                    "surface": "#2d2d2d",
                    "text": "#ffffff",
                    "text_secondary": "#a0a0a0"
                },
                "gradients": {
                    "header": "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                    "card": "linear-gradient(135deg, #1e293b 0%, #334155 100%)",
                    "accent": "linear-gradient(135deg, #ec4899 0%, #f59e0b 100%)"
                }
            },
            "nature": {
                "name": "Forest Nature",
                "colors": {
                    "primary": "#10b981",
                    "secondary": "#059669",
                    "accent": "#f59e0b",
                    "background": "#f0fdf4",
                    "surface": "#ffffff",
                    "text": "#1c1917",
                    "text_secondary": "#57534e"
                },
                "gradients": {
                    "header": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                    "card": "linear-gradient(135deg, #86efac 0%, #4ade80 100%)",
                    "accent": "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
                }
            },
            "sunset": {
                "name": "Sunset Orange",
                "colors": {
                    "primary": "#f97316",
                    "secondary": "#ea580c",
                    "accent": "#dc2626",
                    "background": "#fff7ed",
                    "surface": "#ffffff",
                    "text": "#431407",
                    "text_secondary": "#78350f"
                },
                "gradients": {
                    "header": "linear-gradient(135deg, #f97316 0%, #ea580c 100%)",
                    "card": "linear-gradient(135deg, #fdba74 0%, #fb923c 100%)",
                    "accent": "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)"
                }
            }
        }
        
        self.save_themes()
    
    def save_themes(self):
        """Save themes to file"""
        try:
            with open(self.themes_path, 'w', encoding='utf-8') as f:
                json.dump(self.available_themes, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving themes: {e}")
    
    def get_theme_css(self, theme_name=None):
        """Generate CSS variables for a theme"""
        theme = self.available_themes.get(theme_name or self.current_theme, 
                                         self.available_themes["default"])
        
        colors = theme["colors"]
        gradients = theme["gradients"]
        
        css = f"""
        :root {{
            --primary-color: {colors['primary']};
            --secondary-color: {colors['secondary']};
            --accent-color: {colors['accent']};
            --background-color: {colors['background']};
            --surface-color: {colors['surface']};
            --text-color: {colors['text']};
            --text-secondary: {colors['text_secondary']};
            --header-gradient: {gradients['header']};
            --card-gradient: {gradients['card']};
            --accent-gradient: {gradients['accent']};
        }}
        """
        return css
    
    def set_theme(self, theme_name):
        """Set the current theme"""
        if theme_name in self.available_themes:
            self.current_theme = theme_name
            self.logger.info(f"Theme changed to: {theme_name}")
            return True
        return False
    
    def get_available_themes(self):
        """Get list of available themes"""
        return {name: theme["name"] for name, theme in self.available_themes.items()}