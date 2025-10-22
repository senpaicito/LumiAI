import logging
from typing import Any, Callable, Dict, List
from enum import Enum

class EventType(Enum):
    """Types of events that plugins can subscribe to"""
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent" 
    EMOTION_CHANGED = "emotion_changed"
    MEMORY_STORED = "memory_stored"
    VOICE_INPUT = "voice_input"
    VOICE_OUTPUT = "voice_output"
    DASHBOARD_UPDATE = "dashboard_update"
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"

class PluginEvents:
    """Event system for plugin communication"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.handlers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
    
    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe a handler to an event type"""
        if event_type in self.handlers:
            self.handlers[event_type].append(handler)
            self.logger.debug(f"Subscribed handler to {event_type.value}")
        else:
            self.logger.warning(f"Unknown event type: {event_type}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe a handler from an event type"""
        if event_type in self.handlers and handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)
            self.logger.debug(f"Unsubscribed handler from {event_type.value}")
    
    async def emit(self, event_type: EventType, *args, **kwargs) -> List[Any]:
        """Emit an event to all subscribed handlers and collect results"""
        results = []
        
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    result = await handler(*args, **kwargs)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_type.value}: {e}")
        
        return results
    
    def clear_handlers(self, event_type: EventType = None) -> None:
        """Clear all handlers for an event type (or all events)"""
        if event_type:
            if event_type in self.handlers:
                self.handlers[event_type].clear()
                self.logger.debug(f"Cleared handlers for {event_type.value}")
        else:
            for event_type in self.handlers:
                self.handlers[event_type].clear()
            self.logger.debug("Cleared all event handlers")