import json
import logging
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
from config import settings

class DashboardManager:
    def __init__(self, ai_engine):
        self.ai_engine = ai_engine
        self.logger = logging.getLogger(__name__)
        self.dashboard_data = {
            "conversation_metrics": defaultdict(int),
            "emotion_timeline": deque(maxlen=100),
            "relationship_progress": {},
            "memory_stats": {},
            "user_engagement": defaultdict(int),
            "plugin_metrics": []  # NEW: Store plugin metrics
        }
        
    async def update_dashboard_data(self, interaction_data):
        """Update dashboard data with new interaction"""
        try:
            user_input = interaction_data.get("user_input", "")
            ai_response = interaction_data.get("ai_response", "")
            emotion = interaction_data.get("emotion", "neutral")
            timestamp = datetime.now()
            
            # Update conversation metrics
            self.dashboard_data["conversation_metrics"]["total_messages"] += 1
            self.dashboard_data["conversation_metrics"]["user_messages"] += 1
            
            # Update emotion timeline
            self.dashboard_data["emotion_timeline"].append({
                "timestamp": timestamp.isoformat(),
                "emotion": emotion,
                "intensity": interaction_data.get("sentiment", 0.5)
            })
            
            # Update user engagement
            word_count = len(user_input.split())
            self.dashboard_data["user_engagement"]["total_words"] += word_count
            self.dashboard_data["user_engagement"]["avg_words_per_message"] = (
                self.dashboard_data["user_engagement"]["total_words"] / 
                self.dashboard_data["conversation_metrics"]["user_messages"]
            )
            
            # Update relationship progress from AI engine
            stats = await self.ai_engine.get_advanced_stats()
            self.dashboard_data["relationship_progress"] = stats.get("relationship", {})
            self.dashboard_data["memory_stats"] = stats.get("memory_system", {})
            
            # Update plugin metrics if available
            if self.ai_engine.plugin_manager:
                plugin_metrics = await self.ai_engine.plugin_manager.dispatch_dashboard_update()
                self.dashboard_data["plugin_metrics"] = plugin_metrics
            
            self.logger.debug("Dashboard data updated")
            
        except Exception as e:
            self.logger.error(f"Error updating dashboard: {e}")
    
    async def get_dashboard_metrics(self):
        """Get comprehensive dashboard metrics"""
        try:
            # Get recent emotions for chart
            recent_emotions = list(self.dashboard_data["emotion_timeline"])[-20:]
            
            # Calculate emotion distribution
            emotion_counts = defaultdict(int)
            for entry in recent_emotions:
                emotion_counts[entry["emotion"]] += 1
            
            # Calculate conversation pace
            total_messages = self.dashboard_data["conversation_metrics"]["total_messages"]
            if total_messages > 0:
                messages_per_minute = await self._calculate_conversation_pace()
            else:
                messages_per_minute = 0
            
            # Get plugin information if available
            plugin_info = []
            if self.ai_engine.plugin_manager:
                plugin_info = self.ai_engine.plugin_manager.get_plugin_info()
            
            return {
                "conversation_metrics": dict(self.dashboard_data["conversation_metrics"]),
                "emotion_distribution": dict(emotion_counts),
                "emotion_timeline": recent_emotions,
                "user_engagement": dict(self.dashboard_data["user_engagement"]),
                "relationship_progress": self.dashboard_data["relationship_progress"],
                "memory_stats": self.dashboard_data["memory_stats"],
                "plugin_metrics": self.dashboard_data["plugin_metrics"],  # Include plugin metrics
                "plugin_info": plugin_info,  # Include plugin status info
                "conversation_pace": messages_per_minute,
                "interaction_quality": await self._calculate_interaction_quality()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard metrics: {e}")
            return {}
    
    async def _calculate_conversation_pace(self):
        """Calculate messages per minute"""
        try:
            if len(self.dashboard_data["emotion_timeline"]) < 2:
                return 0
            
            timeline = list(self.dashboard_data["emotion_timeline"])
            start_time = datetime.fromisoformat(timeline[0]["timestamp"])
            end_time = datetime.fromisoformat(timeline[-1]["timestamp"])
            
            time_diff = (end_time - start_time).total_seconds() / 60  # minutes
            if time_diff > 0:
                return len(timeline) / time_diff
            return 0
            
        except Exception as e:
            self.logger.error(f"Error calculating conversation pace: {e}")
            return 0
    
    async def _calculate_interaction_quality(self):
        """Calculate interaction quality score"""
        try:
            metrics = self.dashboard_data["conversation_metrics"]
            engagement = self.dashboard_data["user_engagement"]
            
            if metrics["total_messages"] == 0:
                return 0
            
            # Factors for quality calculation
            message_balance = min(1.0, metrics.get("user_messages", 0) / max(1, metrics["total_messages"]))
            word_density = min(1.0, engagement.get("avg_words_per_message", 0) / 20)  # Normalize
            emotion_diversity = len(set(e["emotion"] for e in self.dashboard_data["emotion_timeline"])) / 8
            
            # Plugin activity bonus (if plugins are active and contributing)
            plugin_bonus = 0.0
            if self.dashboard_data["plugin_metrics"]:
                active_plugins = len(self.dashboard_data["plugin_metrics"])
                plugin_bonus = min(0.2, active_plugins * 0.05)  # Max 20% bonus
            
            quality_score = (message_balance * 0.4 + word_density * 0.3 + emotion_diversity * 0.3) * 100
            quality_score += plugin_bonus * 100
            
            return min(100, round(quality_score, 1))
            
        except Exception as e:
            self.logger.error(f"Error calculating interaction quality: {e}")
            return 0
    
    async def get_visualization_data(self):
        """Get data formatted for charts and visualizations"""
        try:
            metrics = await self.get_dashboard_metrics()
            
            # Format for chart.js
            chart_data = {
                "emotion_pie": {
                    "labels": list(metrics["emotion_distribution"].keys()),
                    "data": list(metrics["emotion_distribution"].values()),
                    "colors": ["#4facfe", "#00f2fe", "#667eea", "#764ba2", "#f093fb", "#f5576c"]
                },
                "timeline_chart": {
                    "labels": [e["timestamp"][11:16] for e in metrics["emotion_timeline"]],  # HH:MM
                    "emotions": [e["emotion"] for e in metrics["emotion_timeline"]],
                    "intensities": [e["intensity"] for e in metrics["emotion_timeline"]]
                },
                "engagement_gauge": {
                    "value": metrics["interaction_quality"],
                    "max": 100,
                    "label": "Interaction Quality"
                },
                "plugin_activity": self._format_plugin_metrics(metrics.get("plugin_metrics", []))
            }
            
            return chart_data
            
        except Exception as e:
            self.logger.error(f"Error getting visualization data: {e}")
            return {}
    
    def _format_plugin_metrics(self, plugin_metrics):
        """Format plugin metrics for visualization"""
        if not plugin_metrics:
            return {}
        
        formatted = {
            "active_plugins": len(plugin_metrics),
            "plugin_data": []
        }
        
        for metric in plugin_metrics:
            plugin_name = metric.get('plugin', 'Unknown')
            formatted["plugin_data"].append({
                "name": plugin_name,
                "metrics": {k: v for k, v in metric.items() if k != 'plugin'}
            })
        
        return formatted