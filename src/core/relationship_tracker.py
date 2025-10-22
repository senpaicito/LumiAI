import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from config import settings

class RelationshipTracker:
    def __init__(self, memory_system):
        self.memory_system = memory_system
        self.logger = logging.getLogger(__name__)
        self.relationship_state = {
            "familiarity": 0.0,
            "trust": 0.5,
            "comfort": 0.5,
            "shared_experiences": [],
            "inside_jokes": [],
            "user_preferences": {},
            "conversation_patterns": {}
        }
        self.state_file = Path(settings.DATA_DIR) / "relationship_state.json"
    
    async def initialize(self):
        """Load relationship state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.relationship_state = json.load(f)
                self.logger.info("Loaded relationship state")
            return True
        except Exception as e:
            self.logger.error(f"Error loading relationship state: {e}")
            return False
    
    async def update_relationship(self, interaction_data):
        """Update relationship based on interaction"""
        try:
            user_input = interaction_data.get("user_input", "")
            ai_response = interaction_data.get("ai_response", "")
            emotion = interaction_data.get("emotion", "neutral")
            sentiment = interaction_data.get("sentiment", 0.0)
            
            # Update familiarity (increases with each interaction)
            self.relationship_state["familiarity"] = min(1.0, 
                self.relationship_state["familiarity"] + 0.01)
            
            # Update trust based on sentiment and interaction quality
            trust_change = sentiment * 0.1
            self.relationship_state["trust"] = max(0.0, min(1.0,
                self.relationship_state["trust"] + trust_change))
            
            # Update comfort based on positive interactions
            if sentiment > 0:
                comfort_change = sentiment * 0.05
                self.relationship_state["comfort"] = max(0.0, min(1.0,
                    self.relationship_state["comfort"] + comfort_change))
            
            # Track shared experiences for meaningful conversations
            if await self._is_meaningful_interaction(user_input, ai_response):
                experience = {
                    "timestamp": datetime.now().isoformat(),
                    "topic": await self._extract_topic(user_input),
                    "emotion": emotion,
                    "user_input": user_input[:100] + "..." if len(user_input) > 100 else user_input
                }
                self.relationship_state["shared_experiences"].append(experience)
                # Keep only last 20 experiences
                self.relationship_state["shared_experiences"] = self.relationship_state["shared_experiences"][-20:]
            
            # Detect and track inside jokes
            joke_keywords = ["lol", "haha", "😂", "funny", "joke"]
            if any(keyword in user_input.lower() for keyword in joke_keywords):
                joke_context = user_input[:50] + "..."
                if joke_context not in self.relationship_state["inside_jokes"]:
                    self.relationship_state["inside_jokes"].append(joke_context)
                    # Keep only last 10 jokes
                    self.relationship_state["inside_jokes"] = self.relationship_state["inside_jokes"][-10:]
            
            # Update conversation patterns
            await self._update_conversation_patterns(user_input, ai_response)
            
            # Update user preferences
            await self._update_user_preferences(user_input)
            
            # Save state
            await self._save_state()
            
            self.logger.debug("Relationship state updated")
            
        except Exception as e:
            self.logger.error(f"Error updating relationship: {e}")
    
    async def _is_meaningful_interaction(self, user_input, ai_response):
        """Determine if interaction is meaningful for relationship building"""
        meaningful_indicators = [
            len(user_input.split()) > 10,  # Substantial input
            any(word in user_input.lower() for word in ["feel", "think", "believe", "experience"]),
            any(word in user_input.lower() for word in ["remember", "recall", "before"]),
            "?" in user_input  # Asking questions
        ]
        
        return any(meaningful_indicators)
    
    async def _extract_topic(self, text):
        """Extract main topic from text"""
        topics = {
            "personal": ["i", "my", "me", "mine"],
            "work": ["work", "job", "career", "office"],
            "hobbies": ["hobby", "game", "music", "movie", "sport"],
            "technology": ["computer", "phone", "ai", "tech", "programming"],
            "relationships": ["friend", "family", "partner", "relationship"]
        }
        
        text_lower = text.lower()
        for topic, keywords in topics.items():
            if any(keyword in text_lower for keyword in keywords):
                return topic
        
        return "general"
    
    async def _update_conversation_patterns(self, user_input, ai_response):
        """Update conversation patterns and styles"""
        # Analyze conversation length patterns
        user_word_count = len(user_input.split())
        ai_word_count = len(ai_response.split())
        
        pattern_key = "length_balance"
        if user_word_count > 50 and ai_word_count > 50:
            pattern = "detailed_discussions"
        elif user_word_count < 10 and ai_word_count < 20:
            pattern = "brief_exchanges"
        else:
            pattern = "balanced_conversations"
        
        self.relationship_state["conversation_patterns"][pattern_key] = pattern
        
        # Analyze question patterns
        if "?" in user_input:
            self.relationship_state["conversation_patterns"]["user_asks_questions"] = True
    
    async def _update_user_preferences(self, user_input):
        """Extract and update user preferences"""
        preference_phrases = {
            "communication_style": {
                "direct": ["be direct", "straightforward", "get to the point"],
                "detailed": ["explain", "details", "more information"],
                "casual": ["casual", "informal", "chill", "relaxed"]
            },
            "topics": {
                "technology": ["tech", "computer", "ai", "programming"],
                "gaming": ["game", "play", "minecraft", "steam"],
                "personal": ["life", "feelings", "thoughts", "experiences"]
            }
        }
        
        user_input_lower = user_input.lower()
        
        for category, styles in preference_phrases.items():
            for style, phrases in styles.items():
                if any(phrase in user_input_lower for phrase in phrases):
                    if category not in self.relationship_state["user_preferences"]:
                        self.relationship_state["user_preferences"][category] = {}
                    
                    self.relationship_state["user_preferences"][category][style] = \
                        self.relationship_state["user_preferences"][category].get(style, 0) + 1
    
    async def get_relationship_context(self):
        """Get relationship context for AI responses"""
        return {
            "familiarity_level": self.relationship_state["familiarity"],
            "trust_level": self.relationship_state["trust"],
            "comfort_level": self.relationship_state["comfort"],
            "shared_experiences_count": len(self.relationship_state["shared_experiences"]),
            "inside_jokes_count": len(self.relationship_state["inside_jokes"]),
            "user_preferences": self.relationship_state["user_preferences"],
            "relationship_stage": await self._determine_relationship_stage()
        }
    
    async def _determine_relationship_stage(self):
        """Determine the current stage of the relationship"""
        familiarity = self.relationship_state["familiarity"]
        
        if familiarity < 0.2:
            return "acquaintance"
        elif familiarity < 0.5:
            return "developing_friendship"
        elif familiarity < 0.8:
            return "close_friends"
        else:
            return "intimate_friends"
    
    async def get_personalized_prompt_addition(self):
        """Get personalized prompt addition based on relationship"""
        context = await self.get_relationship_context()
        
        prompt_parts = []
        
        # Add relationship stage context
        prompt_parts.append(f"Our relationship stage: {context['relationship_stage']}")
        
        # Add trust and comfort context
        if context['trust_level'] > 0.7:
            prompt_parts.append("We have built strong trust - you can be more open and personal")
        if context['comfort_level'] > 0.7:
            prompt_parts.append("We are very comfortable with each other - feel free to be casual")
        
        # Add shared experiences context
        if context['shared_experiences_count'] > 5:
            prompt_parts.append("We have many shared experiences - reference them naturally")
        
        # Add inside jokes context
        if context['inside_jokes_count'] > 0:
            prompt_parts.append("We have inside jokes - use humor appropriately")
        
        return " | ".join(prompt_parts)
    
    async def _save_state(self):
        """Save relationship state to file"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.relationship_state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving relationship state: {e}")