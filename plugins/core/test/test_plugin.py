from src.core.plugin_system.plugin_base import BasePlugin

class TestPlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="Test Plugin",
            version="1.0.0",
            description="A simple test plugin to verify the system works"
        )
        self.message_count = 0
    
    async def initialize(self) -> bool:
        self.logger.info("Test plugin initialized successfully!")
        return True
    
    async def unload(self) -> bool:
        self.logger.info("Test plugin unloaded")
        return True
    
    async def on_message_received(self, message: str, message_type: str = "user"):
        self.message_count += 1
        self.logger.info(f"Test plugin processed message #{self.message_count}: {message[:30]}...")
        return None
    
    async def on_dashboard_update(self):
        return {
            "messages_processed": self.message_count,
            "status": "active"
        }