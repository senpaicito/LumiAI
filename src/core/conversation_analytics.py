import json
import logging
import re
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path
from config import settings

class ConversationAnalytics:
    def __init__(self, memory_system):
        self.memory_system = memory_system
        self.logger = logging.getLogger(__name__)
        self.analytics_file = Path(settings.DATA_DIR) / "conversation_analytics.json"
        self.analytics_data = {
            "conversation_stats": {},
            "topic_analysis": {},
            "interaction_patterns": {},
            "engagement_metrics": {}
        }
    
    async def initialize(self):
        """Load analytics data from file"""
        try:
            if self.analytics_file.exists():
                with open(self.analytics_file, 'r', encoding='utf-8') as f:
                    self.analytics_data = json.load(f)
                self.logger.info("Loaded conversation analytics")
            return True
        except Exception as e:
            self.logger.error(f"Error loading analytics: {e}")
            return False
    
    async def analyze_conversation(self, user_input, ai_response, emotion, sentiment):
        """Analyze conversation and update analytics"""
        try:
            # Update basic statistics
            await self._update_basic_stats(user_input, ai_response)
            
            # Analyze topics
            await self._analyze_topics(user_input)
            
            # Analyze interaction patterns
            await self._analyze_interaction_patterns(user_input, ai_response)
            
            # Calculate engagement metrics
            await self._calculate_engagement(user_input, ai_response, sentiment)
            
            # Save analytics
            await self._save_analytics()
            
        except Exception as e:
            self.logger.error(f"Error analyzing conversation: {e}")
    
    async def _update_basic_stats(self, user_input, ai_response):
        """Update basic conversation statistics"""
        stats = self.analytics_data["conversation_stats"]
        
        # Conversation count
        stats["total_conversations"] = stats.get("total_conversations", 0) + 1
        
        # Word counts
        user_words = len(user_input.split())
        ai_words = len(ai_response.split())
        
        stats["total_user_words"] = stats.get("total_user_words", 0) + user_words
        stats["total_ai_words"] = stats.get("total_ai_words", 0) + ai_words
        stats["average_user_words"] = stats["total_user_words"] / stats["total_conversations"]
        stats["average_ai_words"] = stats["total_ai_words"] / stats["total_conversations"]
        
        # Update daily stats
        today = datetime.now().strftime('%Y-%m-%d')
        if "daily_stats" not in stats:
            stats["daily_stats"] = {}
        
        if today not in stats["daily_stats"]:
            stats["daily_stats"][today] = {"conversations": 0, "words": 0}
        
        stats["daily_stats"][today]["conversations"] += 1
        stats["daily_stats"][today]["words"] += user_words + ai_words
    
    async def _analyze_topics(self, user_input):
        """Analyze conversation topics"""
        topics = self.analytics_data["topic_analysis"]
        
        # Topic keywords
        topic_keywords = {
            "technology": ["computer", "ai", "tech", "programming", "code", "software"],
            "gaming": ["game", "play", "minecraft", "steam", "console", "gaming"],
            "personal": ["i feel", "my life", "experience", "think", "believe"],
            "hobbies": ["music", "art", "sports", "read", "movie", "hobby"],
            "work": ["work", "job", "career", "office", "boss", "colleague"],
            "relationships": ["friend", "family", "partner", "relationship", "love"]
        }
        
        user_input_lower = user_input.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                if topic not in topics:
                    topics[topic] = {"count": 0, "recent_mentions": []}
                
                topics[topic]["count"] += 1
                topics[topic]["recent_mentions"].append({
                    "timestamp": datetime.now().isoformat(),
                    "excerpt": user_input[:100] + "..." if len(user_input) > 100 else user_input
                })
                
                # Keep only last 10 mentions
                topics[topic]["recent_mentions"] = topics[topic]["recent_mentions"][-10:]
    
    async def _analyze_interaction_patterns(self, user_input, ai_response):
        """Analyze interaction patterns"""
        patterns = self.analytics_data["interaction_patterns"]
        
        # Question patterns
        if "?" in user_input:
            patterns["user_questions"] = patterns.get("user_questions", 0) + 1
        
        # Response length patterns
        user_len = len(user_input)
        ai_len = len(ai_response)
        
        if user_len > 100 and ai_len > 100:
            pattern = "detailed_discussions"
        elif user_len < 50 and ai_len < 50:
            pattern = "brief_exchanges"
        else:
            pattern = "balanced_conversations"
        
        patterns[pattern] = patterns.get(pattern, 0) + 1
        
        # Time-based patterns (you would need to track conversation timing)
        current_hour = datetime.now().hour
        time_slot = "morning" if current_hour < 12 else "afternoon" if current_hour < 18 else "evening"
        patterns[f"conversations_{time_slot}"] = patterns.get(f"conversations_{time_slot}", 0) + 1
    
    async def _calculate_engagement(self, user_input, ai_response, sentiment):
        """Calculate engagement metrics"""
        engagement = self.analytics_data["engagement_metrics"]
        
        # Sentiment-based engagement
        if sentiment > 0.3:
            engagement["positive_engagements"] = engagement.get("positive_engagements", 0) + 1
        elif sentiment < -0.3:
            engagement["negative_engagements"] = engagement.get("negative_engagements", 0) + 1
        else:
            engagement["neutral_engagements"] = engagement.get("neutral_engagements", 0) + 1
        
        # Length-based engagement (longer responses might indicate higher engagement)
        total_length = len(user_input) + len(ai_response)
        if total_length > 500:
            engagement_level = "high"
        elif total_length > 200:
            engagement_level = "medium"
        else:
            engagement_level = "low"
        
        engagement[f"{engagement_level}_engagement"] = engagement.get(f"{engagement_level}_engagement", 0) + 1
    
    async def get_analytics_summary(self):
        """Get comprehensive analytics summary"""
        return {
            "conversation_stats": self.analytics_data["conversation_stats"],
            "popular_topics": await self._get_popular_topics(),
            "interaction_patterns": self.analytics_data["interaction_patterns"],
            "engagement_analysis": await self._analyze_engagement_trends(),
            "conversation_quality": await self._assess_conversation_quality()
        }
    
    async def _get_popular_topics(self):
        """Get most popular conversation topics"""
        topics = self.analytics_data["topic_analysis"]
        if not topics:
            return []
        
        popular = sorted(topics.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
        return [{"topic": topic, "count": data["count"]} for topic, data in popular]
    
    async def _analyze_engagement_trends(self):
        """Analyze engagement trends over time"""
        engagement = self.analytics_data["engagement_metrics"]
        total_engagements = sum(engagement.values())
        
        if total_engagements == 0:
            return {"trend": "unknown", "engagement_rate": 0}
        
        positive_rate = engagement.get("positive_engagements", 0) / total_engagements
        high_engagement_rate = engagement.get("high_engagement", 0) / total_engagements
        
        if positive_rate > 0.7 and high_engagement_rate > 0.5:
            trend = "excellent"
        elif positive_rate > 0.5:
            trend = "good"
        elif positive_rate > 0.3:
            trend = "average"
        else:
            trend = "needs_improvement"
        
        return {
            "trend": trend,
            "engagement_rate": positive_rate,
            "high_engagement_rate": high_engagement_rate
        }
    
    async def _assess_conversation_quality(self):
        """Assess overall conversation quality"""
        stats = self.analytics_data["conversation_stats"]
        
        if stats.get("total_conversations", 0) < 5:
            return {"quality": "insufficient_data", "score": 0}
        
        # Simple quality score based on various factors
        score = 0
        
        # Factor 1: Conversation balance
        user_avg = stats.get("average_user_words", 0)
        ai_avg = stats.get("average_ai_words", 0)
        if user_avg > 10 and ai_avg > 20:  # Both parties contributing
            score += 0.3
        
        # Factor 2: Topic diversity
        topics_count = len(self.analytics_data["topic_analysis"])
        if topics_count > 3:
            score += 0.3
        
        # Factor 3: Engagement (simplified)
        engagement = self.analytics_data["engagement_metrics"]
        positive_engagements = engagement.get("positive_engagements", 0)
        total_engagements = sum(engagement.values())
        if total_engagements > 0:
            positive_rate = positive_engagements / total_engagements
            score += positive_rate * 0.4
        
        # Quality categories
        if score >= 0.8:
            quality = "excellent"
        elif score >= 0.6:
            quality = "good"
        elif score >= 0.4:
            quality = "average"
        else:
            quality = "needs_improvement"
        
        return {"quality": quality, "score": round(score, 2)}
    
    async def _save_analytics(self):
        """Save analytics data to file"""
        try:
            with open(self.analytics_file, 'w', encoding='utf-8') as f:
                json.dump(self.analytics_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving analytics: {e}")