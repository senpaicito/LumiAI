import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from config import settings

class PersonalityEngine:
    def __init__(self, memory_system):
        self.memory_system = memory_system
        self.logger = logging.getLogger(__name__)
        self.personality_state = {
            "mood": "neutral",
            "energy": 0.5,
            "familiarity": 0.0,
            "conversation_style": "friendly",
            "learned_preferences": {}
        }
        self.state_file = Path(settings.DATA_DIR) / "personality_state.json"
        
    async def initialize(self):
        """Load personality state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.personality_state = json.load(f)
                self.logger.info("Loaded personality state")
            return True
        except Exception as e:
            self.logger.error(f"Error loading personality state: {e}")
            return False
    
    async def update_from_interaction(self, user_input, ai_response, sentiment=0.0):
        """Update personality based on interaction"""
        try:
            # Update mood based on sentiment and recent activity
            await self._update_mood(sentiment)
            
            # Update familiarity based on conversation frequency
            await self._update_familiarity()
            
            # Learn from user preferences
            await self._learn_user_preferences(user_input)
            
            # Adjust conversation style based on interaction patterns
            await self._adjust_conversation_style(user_input, ai_response)
            
            # Save updated state
            await self._save_state()
            
        except Exception as e:
            self.logger.error(f"Error updating personality: {e}")
    
    async def _update_mood(self, sentiment):
        """Update mood based on sentiment and other factors"""
        # Simple mood system - can be enhanced
        mood_weights = {
            "positive": 0.6,
            "recent_activity": 0.3,
            "random_variation": 0.1
        }
        
        # Base mood from sentiment
        mood_score = sentiment * mood_weights["positive"]
        
        # Adjust based on recent activity
        recent_convos = await self.memory_system.get_recent_conversation(limit=5)
        activity_bonus = min(len(recent_convos) * 0.1, 0.3)
        mood_score += activity_bonus * mood_weights["recent_activity"]
        
        # Small random variation
        mood_score += (random.random() - 0.5) * mood_weights["random_variation"]
        
        # Convert to mood categories
        if mood_score > 0.3:
            self.personality_state["mood"] = "happy"
        elif mood_score < -0.3:
            self.personality_state["mood"] = "thoughtful"
        else:
            self.personality_state["mood"] = "neutral"
        
        self.personality_state["energy"] = max(0.1, min(1.0, 0.5 + mood_score))
    
    async def _update_familiarity(self):
        """Update familiarity based on interaction history"""
        try:
            conversations = await self.memory_system.get_recent_conversation(limit=50)
            total_interactions = len(conversations)
            
            # Familiarity increases with interactions but has diminishing returns
            familiarity = min(1.0, total_interactions / 100)
            self.personality_state["familiarity"] = familiarity
            
        except Exception as e:
            self.logger.error(f"Error updating familiarity: {e}")
    
    async def _learn_user_preferences(self, user_input):
        """Learn user preferences from conversations"""
        try:
            preferences = await self.memory_system.vector_memory.get_user_preferences()
            
            # Store learned preferences
            self.personality_state["learned_preferences"] = {
                "user_likes": preferences.get("likes", [])[:10],  # Top 10
                "user_dislikes": preferences.get("dislikes", [])[:10],
                "conversation_topics": await self._extract_topics()
            }
            
        except Exception as e:
            self.logger.error(f"Error learning preferences: {e}")
    
    async def _extract_topics(self):
        """Extract common conversation topics"""
        try:
            memories = await self.memory_system.vector_memory.get_recent_memories(limit=20)
            
            # Simple topic extraction (can be enhanced with NLP)
            topic_keywords = {
                "technology": ["computer", "phone", "internet", "ai", "programming"],
                "gaming": ["game", "play", "minecraft", "steam", "console"],
                "personal": ["family", "friend", "work", "school", "home"],
                "hobbies": ["music", "art", "sports", "read", "movie"]
            }
            
            topics = {}
            for memory in memories:
                text = memory['text'].lower()
                for topic, keywords in topic_keywords.items():
                    for keyword in keywords:
                        if keyword in text:
                            topics[topic] = topics.get(topic, 0) + 1
            
            # Return top 3 topics
            return sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]
            
        except Exception as e:
            self.logger.error(f"Error extracting topics: {e}")
            return []
    
    async def _adjust_conversation_style(self, user_input, ai_response):
        """Adjust conversation style based on interaction patterns"""
        # Analyze user input style and adapt
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["please", "thank you", "appreciate"]):
            self.personality_state["conversation_style"] = "polite"
        elif any(word in input_lower for word in ["lol", "haha", "funny", "😂"]):
            self.personality_state["conversation_style"] = "playful"
        elif len(user_input.split()) > 20:  # Long message
            self.personality_state["conversation_style"] = "detailed"
        else:
            self.personality_state["conversation_style"] = "friendly"
    
    async def get_personality_context(self):
        """Get personality context for AI response generation"""
        return {
            "current_mood": self.personality_state["mood"],
            "energy_level": self.personality_state["energy"],
            "familiarity_level": self.personality_state["familiarity"],
            "conversation_style": self.personality_state["conversation_style"],
            "learned_preferences": self.personality_state["learned_preferences"]
        }
    
    async def _save_state(self):
        """Save personality state to file"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.personality_state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving personality state: {e}")