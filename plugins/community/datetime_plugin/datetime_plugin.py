from src.core.plugin_system.plugin_base import BasePlugin
import datetime
import re
from typing import Any, Dict, List, Optional

class DateTimePlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="datetime_plugin",
            version="1.0.0", 
            description="Provides current date and time information to users"
        )
        self.message_count = 0
        
    async def initialize(self) -> bool:
        self.logger.info("DateTime plugin initialized successfully!")
        return True
    
    async def unload(self) -> bool:
        self.logger.info("DateTime plugin unloaded")
        return True
    
    async def on_message_received(self, message: str, message_type: str = "user"):
        self.message_count += 1
        self.logger.info(f"=== DATETIME PLUGIN ===")
        self.logger.info(f"Processing message #{self.message_count}: '{message}'")
        self.logger.info(f"Message type: {message_type}")
        
        # Only process user messages
        if message_type != "user":
            self.logger.info("Not a user message, skipping")
            return None
            
        # Check if this is a time/date related question
        if self._is_time_related(message):
            response = self._get_time_response(message)
            self.logger.info(f"✅ DateTime plugin generating response: {response}")
            
            # Try multiple return strategies to stop propagation
            return_strategy = self.get_config_value('return_strategy', 'string')
            self.logger.info(f"Using return strategy: {return_strategy}")
            
            if return_strategy == 'dict_stop_propagation':
                # Strategy 1: Return dict with stop_propagation flag
                self.logger.info("🛑 Attempting to stop propagation with dict")
                return {
                    "response": response,
                    "stop_propagation": True,
                    "source": "datetime_plugin"
                }
            elif return_strategy == 'dict_final':
                # Strategy 2: Return dict with final flag
                self.logger.info("🛑 Attempting to stop propagation with final flag")
                return {
                    "response": response,
                    "final": True,
                    "processed_by": "datetime_plugin"
                }
            elif return_strategy == 'special_object':
                # Strategy 3: Return a special wrapper object
                self.logger.info("🛑 Attempting to stop propagation with special object")
                class PluginResponse:
                    def __init__(self, text, should_propagate=False):
                        self.text = text
                        self.should_propagate = should_propagate
                    def __str__(self):
                        return self.text
                
                return PluginResponse(response, should_propagate=False)
            else:
                # Strategy 4: Default - just return the string
                self.logger.info("📤 Returning plain string response")
                return response
        
        self.logger.info("❌ Not a time-related message, passing through to Ollama")
        return None
    
    def _is_time_related(self, message: str) -> bool:
        """Check if message is asking about time or date"""
        message_lower = message.lower().strip()
        
        time_phrases = [
            'time', 'date', 'day', 'clock', 'today', 'now',
            'what time', 'what date', 'what day', 
            'current time', 'current date', 'time now',
            'tell me the time', 'tell me the date',
            'what is the time', 'what is the date',
            'whats the time', 'whats the date',
            'do you know the time', 'do you know the date'
        ]
        
        self.logger.info(f"🔍 Checking for time phrases in: '{message_lower}'")
        
        # Simple keyword matching - more reliable than regex
        for phrase in time_phrases:
            if phrase in message_lower:
                self.logger.info(f"✅ Matched time phrase: '{phrase}'")
                return True
                
        self.logger.info("❌ No time phrases matched")
        return False
    
    def _get_time_response(self, message: str) -> str:
        """Generate appropriate time/date response"""
        message_lower = message.lower()
        now = datetime.datetime.now()
        
        self.logger.info(f"🎯 Generating response for: '{message_lower}'")
        
        if 'time' in message_lower and 'date' not in message_lower:
            # Time only request
            time_str = now.strftime("%H:%M:%S")
            response = f"🕒 The current time is {time_str}."
            self.logger.info(f"⏰ Time response: {response}")
            return response
        
        elif 'date' in message_lower and 'time' not in message_lower:
            # Date only request  
            date_str = now.strftime("%Y-%m-%d")
            day_str = now.strftime("%A")
            response = f"📅 Today is {day_str}, {date_str}."
            self.logger.info(f"📅 Date response: {response}")
            return response
        
        else:
            # Both date and time or ambiguous
            time_str = now.strftime("%H:%M:%S")
            date_str = now.strftime("%Y-%m-%d") 
            day_str = now.strftime("%A")
            response = f"🕒📅 It's currently {time_str} on {day_str}, {date_str}."
            self.logger.info(f"🕒📅 DateTime response: {response}")
            return response
    
    async def on_dashboard_update(self):
        return {
            "messages_processed": self.message_count,
            "status": "active",
            "last_checked": datetime.datetime.now().isoformat(),
            "plugin_name": "DateTime Plugin"
        }
