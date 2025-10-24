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
        self.plugin_manager = None  # Plugin system integration
        
        # Import and initialize advanced systems
        try:
            from src.core.personality_engine import PersonalityEngine
            from src.core.emotion_tracker import EmotionTracker
            from src.core.relationship_tracker import RelationshipTracker
            from src.core.conversation_analytics import ConversationAnalytics
            
            self.personality_engine = PersonalityEngine(memory_system)
            self.emotion_tracker = EmotionTracker()
            self.relationship_tracker = RelationshipTracker(memory_system)
            self.conversation_analytics = ConversationAnalytics(memory_system)
        except ImportError as e:
            self.logger.warning(f"Advanced systems not available: {e}")
            # Create dummy systems
            self.personality_engine = DummyPersonalityEngine()
            self.emotion_tracker = DummyEmotionTracker()
            self.relationship_tracker = DummyRelationshipTracker()
            self.conversation_analytics = DummyConversationAnalytics()
    
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
            # Create minimal character data
            self.character_data = {
                'name': 'Lumi',
                'base_personality': 'A helpful and friendly AI assistant.',
                'speech_style': 'casual and conversational',
                'traits': ['friendly', 'helpful', 'curious'],
                'likes': ['learning', 'helping', 'conversation'],
                'behavior_rules': ['Be helpful and friendly', 'Adapt to user mood']
            }
    
    async def generate_response(self, user_input, conversation_context=None):
        """Generate a response using Ollama with advanced context and plugin support"""
        try:
            # Plugin hook: pre-process user input
            if self.plugin_manager:
                user_input = await self.plugin_manager.dispatch_message_received(user_input)
            
            # Get all context systems
            memory_context = await self.memory_system.get_conversation_context(user_input)
            
            # Get personality and emotional context with fallbacks
            try:
                personality_context = await self.personality_engine.get_personality_context()
                emotional_state = await self.emotion_tracker.get_emotional_state()
                relationship_context = await self.relationship_tracker.get_relationship_context()
                
                # Predict emotional response to user input
                predicted_emotion, confidence = await self.emotion_tracker.predict_emotional_response(user_input)
            except Exception as e:
                self.logger.warning(f"Advanced context systems not available: {e}")
                personality_context = {"current_mood": "neutral", "energy_level": 0.5, "conversation_style": "friendly"}
                emotional_state = {"current_emotion": "neutral", "mood_stability": 0.5}
                relationship_context = {"relationship_stage": "acquaintance", "trust_level": 0.5, "familiarity_level": 0.5}
                predicted_emotion = "neutral"
            
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
            
            # Plugin hook: post-process AI response
            if self.plugin_manager:
                await self.plugin_manager.dispatch_message_sent(clean_response)
            
            # Analyze sentiment
            sentiment = self._analyze_sentiment(user_input + " " + clean_response)
            
            # Update all tracking systems
            await self._update_advanced_systems(user_input, clean_response, emotion, sentiment)
            
            # Plugin hook: emotion change notification
            if self.plugin_manager:
                await self.plugin_manager.dispatch_emotion_changed(emotion, 1.0)
            
            # Speak response if TTS is available
            if self.tts_engine and hasattr(self.tts_engine, 'is_initialized') and self.tts_engine.is_initialized:
                # Plugin hook: pre-process voice output
                tts_text = clean_response
                if self.plugin_manager:
                    voice_results = await self.plugin_manager.dispatch_voice_output(tts_text)
                    if voice_results and len(voice_results) > 0:
                        # Use the last plugin's modification
                        tts_text = voice_results[-1]
                
                await self.tts_engine.speak(tts_text)
            
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
            if personality_context.get('learned_preferences', {}).get('user_likes'):
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
            try:
                personalized = await self.relationship_tracker.get_personalized_prompt_addition()
                if personalized:
                    prompt_parts.extend(["", personalized])
            except:
                pass
        
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
        try:
            await self.emotion_tracker.update_emotion(emotion, intensity, f"response_to: {user_input[:50]}...")
        except:
            pass  # Emotion tracker might not be available
        
        # Update current emotion for VTube Studio
        if emotion != self.current_emotion:
            self.current_emotion = emotion
            self.logger.info(f"Emotion changed to: {emotion}")
            
            # Trigger VTube Studio expression if connected
            if self.vts_client and hasattr(self.vts_client, 'is_connected') and self.vts_client.is_connected:
                try:
                    await self.vts_client.send_emotional_state(emotion)
                except Exception as e:
                    self.logger.error(f"Error sending emotion to VTS: {e}")
    
    async def _update_advanced_systems(self, user_input, ai_response, emotion, sentiment):
        """Update all advanced tracking systems"""
        # Store in memory systems
        await self.memory_system.store_interaction(user_input, ai_response, emotion=emotion)
        
        # Plugin hook: memory stored notification
        if self.plugin_manager:
            # Use the correct method name
            await self.plugin_manager.dispatch_memory_stored("conversation", f"User: {user_input}\nAI: {ai_response}")
        
        # Update personality engine
        try:
            await self.personality_engine.update_from_interaction(user_input, ai_response, sentiment)
        except:
            pass
        
        # Update relationship tracker
        try:
            interaction_data = {
                "user_input": user_input,
                "ai_response": ai_response,
                "emotion": emotion,
                "sentiment": sentiment
            }
            await self.relationship_tracker.update_relationship(interaction_data)
        except:
            pass
        
        # Update conversation analytics
        try:
            await self.conversation_analytics.analyze_conversation(user_input, ai_response, emotion, sentiment)
        except:
            pass
    
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
            
            # Get other stats with fallbacks
            try:
                emotional_state = await self.emotion_tracker.get_emotional_state()
                relationship_context = await self.relationship_tracker.get_relationship_context()
                analytics_summary = await self.conversation_analytics.get_analytics_summary()
                personality_context = await self.personality_engine.get_personality_context()
            except Exception as e:
                self.logger.warning(f"Some advanced stats not available: {e}")
                emotional_state = {"current_emotion": self.current_emotion}
                relationship_context = {"relationship_stage": "acquaintance", "trust_level": 0.5}
                analytics_summary = {}
                personality_context = {"current_mood": "neutral"}
            
            # Plugin hook: get plugin metrics for dashboard
            plugin_metrics = []
            if self.plugin_manager:
                plugin_metrics = await self.plugin_manager.dispatch_dashboard_update()
            
            return {
                "memory_system": memory_stats,
                "emotional_state": emotional_state,
                "relationship": relationship_context,
                "analytics": analytics_summary,
                "personality": personality_context,
                "character": {
                    "name": self.character_data['name'] if self.character_data else "Unknown",
                    "current_emotion": self.current_emotion
                },
                "plugins": plugin_metrics
            }
        except Exception as e:
            self.logger.error(f"Error getting advanced stats: {e}")
            return {}
    
    async def process_voice_input(self):
        """Process voice input and generate response with plugin support"""
        if not self.stt_engine or not hasattr(self.stt_engine, 'is_initialized') or not self.stt_engine.is_initialized:
            return None, "Voice input not available"
        
        self.logger.info("Listening for voice input...")
        transcription = await self.stt_engine.process_voice_input()
        
        # Plugin hook: process voice input
        if transcription and self.plugin_manager:
            processed_transcription = await self.plugin_manager.dispatch_voice_input(transcription)
            if processed_transcription and len(processed_transcription) > 0:
                # Use the last plugin's modification
                transcription = processed_transcription[-1]
        
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

# Dummy classes for fallback
class DummyPersonalityEngine:
    async def initialize(self): pass
    async def get_personality_context(self): 
        return {"current_mood": "neutral", "energy_level": 0.5, "conversation_style": "friendly"}
    async def update_from_interaction(self, *args, **kwargs): pass

class DummyEmotionTracker:
    async def initialize(self): pass
    async def get_emotional_state(self): 
        return {"current_emotion": "neutral", "mood_stability": 0.5}
    async def predict_emotional_response(self, text):
        return "neutral", 0.5
    async def update_emotion(self, *args, **kwargs): pass

class DummyRelationshipTracker:
    async def initialize(self): pass
    async def get_relationship_context(self): 
        return {"relationship_stage": "acquaintance", "trust_level": 0.5, "familiarity_level": 0.5}
    async def update_relationship(self, *args, **kwargs): pass
    async def get_personalized_prompt_addition(self): 
        return ""

class DummyConversationAnalytics:
    async def initialize(self): pass
    async def analyze_conversation(self, *args, **kwargs): pass
    async def get_analytics_summary(self): 
        return {}