import json
import logging
import re
from pathlib import Path
from config import settings

class AIEngine:
    def __init__(self, ollama_client, memory_system, tts_engine=None, stt_engine=None, vts_client=None):
        self.ollama_client = ollama_client
        self.memory_system = memory_system
        self.tts_engine = tts_engine
        self.stt_engine = stt_engine
        self.vts_client = vts_client
        self.character_data = None
        self.logger = logging.getLogger(__name__)
        self.current_emotion = "neutral"
        
        # Import and initialize advanced systems
        from .personality_engine import PersonalityEngine
        from .emotion_tracker import EmotionTracker
        from .relationship_tracker import RelationshipTracker
        from .conversation_analytics import ConversationAnalytics
        
        self.personality_engine = PersonalityEngine(memory_system)
        self.emotion_tracker = EmotionTracker()
        self.relationship_tracker = RelationshipTracker(memory_system)
        self.conversation_analytics = ConversationAnalytics(memory_system)
    
    async def load_character(self):
        """Load character data and initialize advanced systems"""
        try:
            character_path = Path(__file__).parent.parent.parent / "config" / "character_cards" / "lumi_character.json"
            with open(character_path, 'r', encoding='utf-8') as f:
                self.character_data = json.load(f)
            self.logger.info(f"Loaded character: {self.character_data['name']}")
            
            # Initialize all advanced systems
            await self.personality_engine.initialize()
            await self.emotion_tracker.initialize()
            await self.relationship_tracker.initialize()
            await self.conversation_analytics.initialize()
            
        except Exception as e:
            self.logger.error(f"Failed to load character data: {e}")
            raise
    
    async def generate_response(self, user_input, conversation_context=None):
        """Generate a response using Ollama with advanced context"""
        try:
            # Get all context systems
            memory_context = await self.memory_system.get_conversation_context(user_input)
            personality_context = await self.personality_engine.get_personality_context()
            emotional_state = await self.emotion_tracker.get_emotional_state()
            relationship_context = await self.relationship_tracker.get_relationship_context()
            
            # Predict emotional response to user input
            predicted_emotion, confidence = await self.emotion_tracker.predict_emotional_response(user_input)
            
            # Build enhanced system prompt
            system_prompt = await self._build_advanced_system_prompt(
                memory_context, 
                personality_context, 
                emotional_state,
                relationship_context,
                predicted_emotion
            )
            
            # Generate response
            response = await self.ollama_client.generate_response(
                user_input=user_input,
                system_prompt=system_prompt,
                context=conversation_context
            )
            
            # Extract emotion from response
            emotion = self._extract_emotion(response)
            await self._update_advanced_emotional_state(emotion, user_input)
            
            # Clean response
            clean_response = self._clean_response(response)
            
            # Analyze sentiment
            sentiment = self._analyze_sentiment(user_input + " " + clean_response)
            
            # Update all tracking systems
            await self._update_advanced_systems(user_input, clean_response, emotion, sentiment)
            
            # Speak response if TTS is available
            if self.tts_engine and self.tts_engine.is_initialized:
                await self.tts_engine.speak(clean_response)
            
            return clean_response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return "I'm having trouble thinking right now. Could you try again?"
    
    async def _build_advanced_system_prompt(self, memory_context, personality_context, emotional_state, relationship_context, predicted_emotion):
        """Build advanced system prompt with all context systems"""
        if not self.character_data:
            return "You are a helpful AI assistant."
        
        prompt_parts = [
            f"You are {self.character_data['name']}.",
            self.character_data['base_personality'],
            f"Speech style: {self.character_data['speech_style']}",
            "Traits: " + ", ".join(self.character_data['traits']),
            "Likes: " + ", ".join(self.character_data['likes']),
            "Behavior rules:",
            *[f"- {rule}" for rule in self.character_data['behavior_rules']],
        ]
        
        # Add memory context
        if memory_context.get('summary'):
            prompt_parts.extend([
                "",
                "Current conversation context:",
                memory_context['summary']
            ])
        
        # Add personality context
        if personality_context:
            prompt_parts.extend([
                "",
                "Your current state:",
                f"Mood: {personality_context['current_mood']}",
                f"Energy: {personality_context['energy_level']:.1f}",
                f"Conversation style: {personality_context['conversation_style']}",
            ])
            
            # Add learned preferences if available
            if personality_context['learned_preferences'].get('user_likes'):
                likes = personality_context['learned_preferences']['user_likes'][:3]
                prompt_parts.append(f"User likes: {', '.join(likes)}")
        
        # Add emotional context
        if emotional_state:
            prompt_parts.extend([
                "",
                "Emotional context:",
                f"Current emotion: {emotional_state['current_emotion']}",
                f"Mood stability: {emotional_state['mood_stability']}",
            ])
        
        # Add relationship context
        if relationship_context:
            prompt_parts.extend([
                "",
                "Relationship context:",
                f"Relationship stage: {relationship_context['relationship_stage']}",
                f"Trust level: {relationship_context['trust_level']:.1f}",
                f"Familiarity: {relationship_context['familiarity_level']:.1f}",
            ])
            
            # Add personalized prompt from relationship tracker
            personalized = await self.relationship_tracker.get_personalized_prompt_addition()
            if personalized:
                prompt_parts.extend(["", personalized])
        
        prompt_parts.extend([
            "",
            "Important: Be authentic and let your personality shine through.",
            "Reference past conversations naturally when relevant.",
            "Adapt your tone based on your current emotional state and relationship context.",
            "Use appropriate language for our relationship stage.",
        ])
        
        return "\n".join(prompt_parts)
    
    async def _update_advanced_emotional_state(self, emotion, user_input):
        """Update advanced emotional state with context"""
        # Update emotion tracker
        intensity = 1.0  # Can be calculated based on response content
        await self.emotion_tracker.update_emotion(emotion, intensity, f"response_to: {user_input[:50]}...")
        
        # Update current emotion for VTube Studio
        if emotion != self.current_emotion:
            self.current_emotion = emotion
            self.logger.info(f"Emotion changed to: {emotion}")
            
            # Trigger VTube Studio expression if connected
            if self.vts_client and self.vts_client.is_connected:
                await self.vts_client.send_emotional_state(emotion)
    
    async def _update_advanced_systems(self, user_input, ai_response, emotion, sentiment):
        """Update all advanced tracking systems"""
        # Store in memory systems
        await self.memory_system.store_interaction(user_input, ai_response, emotion=emotion)
        
        # Update personality engine
        await self.personality_engine.update_from_interaction(user_input, ai_response, sentiment)
        
        # Update relationship tracker
        interaction_data = {
            "user_input": user_input,
            "ai_response": ai_response,
            "emotion": emotion,
            "sentiment": sentiment
        }
        await self.relationship_tracker.update_relationship(interaction_data)
        
        # Update conversation analytics
        await self.conversation_analytics.analyze_conversation(user_input, ai_response, emotion, sentiment)
    
    def _analyze_sentiment(self, text):
        """Simple sentiment analysis (can be enhanced with proper NLP)"""
        text_lower = text.lower()
        
        positive_words = ["good", "great", "awesome", "wonderful", "happy", "love", "excellent", "amazing", "fantastic", "perfect"]
        negative_words = ["bad", "terrible", "awful", "hate", "sad", "angry", "disappointing", "horrible", "worst", "upset"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    def _extract_emotion(self, response):
        """Extract emotion from response text"""
        emotion_patterns = {
            "happy": r'\b(happy|joy|excited|great|wonderful|awesome|good|yay|😊|😂|🎉)\b',
            "sad": r'\b(sad|unhappy|sorry|bad|terrible|awful|cry|tear|😢|💔|😞)\b',
            "angry": r'\b(angry|mad|frustrated|annoyed|hate|upset|😠|🤬|💢)\b',
            "surprised": r'\b(surprised|wow|amazing|shocked|unexpected|😲|🤯|❗)\b',
            "curious": r'\b(curious|wonder|question|why|how|what if|🤔|❓|🧐)\b',
            "confused": r'\b(confused|unsure|uncertain|puzzled|don\'t know|😕|🤷|❔)\b',
            "excited": r'\b(excited|can\'t wait|looking forward|thrilled|🎉|✨|🌟)\b',
            "thoughtful": r'\b(think|ponder|consider|reflect|maybe|perhaps|hmm|🤔)\b',
            "neutral": r'\b(okay|fine|alright|sure|yes|no|maybe|understand)\b'
        }
        
        response_lower = response.lower()
        emotion_scores = {emotion: 0 for emotion in emotion_patterns.keys()}
        
        for emotion, pattern in emotion_patterns.items():
            if re.search(pattern, response_lower):
                emotion_scores[emotion] += 1
        
        # Return emotion with highest score, default to neutral
        detected_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        return detected_emotion[0] if detected_emotion[1] > 0 else "neutral"
    
    def _clean_response(self, response):
        """Clean response text by removing emotion tags and other metadata"""
        clean = re.sub(r'\[.*?\]', '', response)  # Remove anything in brackets
        clean = re.sub(r'\(.*?\)', '', clean)     # Remove anything in parentheses
        return clean.strip()
    
    async def get_memory_stats(self):
        """Get statistics about the memory system"""
        try:
            recent_memories = await self.memory_system.vector_memory.get_recent_memories(limit=1)
            recent_conversations = await self.memory_system.get_recent_conversation(limit=1)
            
            return {
                "total_memories": len(recent_memories) if recent_memories else 0,
                "total_conversations": len(recent_conversations) if recent_conversations else 0,
                "personality_state": await self.personality_engine.get_personality_context()
            }
        except Exception as e:
            self.logger.error(f"Error getting memory stats: {e}")
            return {}
    
    async def get_advanced_stats(self):
        """Get comprehensive advanced statistics"""
        try:
            memory_stats = await self.get_memory_stats()
            emotional_state = await self.emotion_tracker.get_emotional_state()
            relationship_context = await self.relationship_tracker.get_relationship_context()
            analytics_summary = await self.conversation_analytics.get_analytics_summary()
            
            return {
                "memory_system": memory_stats,
                "emotional_state": emotional_state,
                "relationship": relationship_context,
                "analytics": analytics_summary,
                "personality": await self.personality_engine.get_personality_context(),
                "character": {
                    "name": self.character_data['name'] if self.character_data else "Unknown",
                    "current_emotion": self.current_emotion
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting advanced stats: {e}")
            return {}
    
    async def process_voice_input(self):
        """Process voice input and generate response"""
        if not self.stt_engine or not self.stt_engine.is_initialized:
            return None, "Voice input not available"
        
        self.logger.info("Listening for voice input...")
        transcription = await self.stt_engine.process_voice_input()
        
        if transcription:
            response = await self.generate_response(transcription)
            return transcription, response
        else:
            return None, "I didn't catch that. Could you please repeat?"
    
    async def export_conversation_data(self):
        """Export comprehensive conversation data"""
        try:
            # Get memory export
            memory_export = await self.memory_system.export_memories()
            
            # Get advanced stats
            advanced_stats = await self.get_advanced_stats()
            
            export_data = {
                "export_timestamp": self._get_timestamp(),
                "character_info": self.character_data,
                "advanced_statistics": advanced_stats,
                "memory_export_path": memory_export
            }
            
            export_path = Path(settings.DATA_DIR) / "full_export.json"
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Full conversation data exported to {export_path}")
            return str(export_path)
            
        except Exception as e:
            self.logger.error(f"Error exporting conversation data: {e}")
            return None
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()