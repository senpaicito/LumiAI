from src.core.plugin_system.plugin_base import BasePlugin

class ExamplePlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="Example Plugin",
            version="1.0.0",
            description="An example plugin template"
        )
        self.message_count = 0
    
    async def initialize(self) -> bool:
        self.logger.info("Example plugin initializing...")
        # Load any saved data
        self.message_count = self.load_plugin_data("message_count.json", 0)
        return True
    
    async def unload(self) -> bool:
        # Save plugin data
        self.save_plugin_data(self.message_count, "message_count.json")
        self.logger.info("Example plugin unloaded")
        return True
    
    async def on_message_received(self, message: str, message_type: str = "user"):
        self.message_count += 1
        self.logger.info(f"Example plugin processed message #{self.message_count}: {message[:50]}...")
        return None  # Return None to not modify the message
    
    async def on_dashboard_update(self):
        return {
            "message_count": self.message_count,
            "status": "active"
        }