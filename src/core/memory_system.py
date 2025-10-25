import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from config import settings
from .vector_memory import VectorMemory

class MemorySystem:
    def __init__(self):
        self.vector_memory = VectorMemory()
        self.conversation_path = settings.CONVERSATION_HISTORY_PATH
        self.logger = logging.getLogger(__name__)
        
        # Ensure directories exist
        self.conversation_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize both vector and conversation memory"""
        return await self.vector_memory.initialize()
    
    async def store_interaction(self, user_input, ai_response, conversation_context=None, emotion=None):
        """Store a conversation interaction with vector memory and emotion tagging"""
        try:
            # Store in conversation history
            conversation = await self._load_conversation_history()
            
            interaction = {
                "user_input": user_input,
                "ai_response": ai_response,
                "timestamp": self._get_timestamp(),
                "context": conversation_context or {},
                "emotion": emotion or "neutral"
            }
            
            conversation.append(interaction)
            await self._save_conversation_history(conversation)
            
            # Store in vector memory for semantic search with emotion
            full_conversation = f"User: {user_input}\nLumi: {ai_response}"
            
            # Create simple metadata for ChromaDB
            metadata = {
                "user_input": user_input[:100],  # Limit length
                "ai_response": ai_response[:100],  # Limit length
                "context_summary": str(conversation_context)[:200] if conversation_context else "none"
            }
            
            await self.vector_memory.store_memory(
                text=full_conversation,
                memory_type="conversation",
                metadata=metadata,
                emotion=emotion
            )
            
            # Extract and store key information
            await self._extract_and_store_knowledge(user_input, ai_response, emotion)
            
            self.logger.debug(f"Stored interaction with emotion '{emotion}' in both memory systems")
            
        except Exception as e:
            self.logger.error(f"Error storing interaction: {e}")
    
    async def _extract_and_store_knowledge(self, user_input, ai_response, emotion=None):
        """Extract and store key information from conversation with emotion"""
        # Simple keyword-based extraction (can be enhanced with NLP)
        knowledge_keywords = [
            "name is", "i am", "i'm", "my name", "i live", "i work",
            "i study", "my hobby", "i like", "i love", "i hate", "my favorite",
            "i enjoy", "i dislike", "i prefer", "i wish", "i want", "i need"
        ]
        
        user_input_lower = user_input.lower()
        for keyword in knowledge_keywords:
            if keyword in user_input_lower:
                await self.vector_memory.store_memory(
                    text=user_input,
                    memory_type="user_fact",
                    metadata={
                        "fact_type": keyword,
                        "emotional_context": emotion or "neutral"
                    },
                    emotion=emotion
                )
                break
    
    async def get_conversation_context(self, current_input, max_memories=5):
        """Get relevant context for current conversation"""
        try:
            # Get relevant past memories
            relevant_memories = await self.vector_memory.search_memories(
                current_input, 
                n_results=max_memories
            )
            
            # Get recent conversation history
            recent_conversations = await self.get_recent_conversation(limit=3)
            
            # Get user preferences
            user_preferences = await self.vector_memory.get_user_preferences()
            
            # Get emotional context
            emotional_context = await self.get_emotional_context()
            
            context = {
                "relevant_memories": relevant_memories,
                "recent_conversations": recent_conversations,
                "user_preferences": user_preferences,
                "emotional_context": emotional_context,
                "summary": await self._generate_context_summary(
                    relevant_memories, 
                    recent_conversations, 
                    user_preferences,
                    emotional_context
                )
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return {}
    
    async def get_emotional_context(self, current_emotion="neutral"):
        """Get memories and context filtered by current emotion"""
        try:
            # Get memories with similar emotions
            similar_emotion_memories = await self.vector_memory.search_memories(
                query="",  # Get all memories with this emotion
                n_results=5,
                emotion=current_emotion
            )
            
            # Get emotion statistics
            emotion_stats = await self.vector_memory.get_emotion_stats()
            
            return {
                "current_emotion": current_emotion,
                "similar_emotion_memories": similar_emotion_memories,
                "emotion_stats": emotion_stats,
                "mood_patterns": await self._analyze_mood_patterns()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting emotional context: {e}")
            return {}
    
    async def _analyze_mood_patterns(self):
        """Analyze patterns in emotional history"""
        try:
            emotional_history = await self.vector_memory.get_emotional_history(days_back=7)
            
            patterns = {
                "recent_emotions": {},
                "dominant_mood": "neutral",
                "mood_consistency": "variable"
            }
            
            if emotional_history:
                # Analyze last 7 days
                all_emotions = []
                for day_emotions in emotional_history.values():
                    all_emotions.extend([emotion for emotion, count in day_emotions.items() for _ in range(count)])
                
                if all_emotions:
                    from collections import Counter
                    emotion_counter = Counter(all_emotions)
                    patterns["dominant_mood"] = emotion_counter.most_common(1)[0][0]
                    patterns["recent_emotions"] = dict(emotion_counter)
                    
                    # Calculate consistency (how often the dominant mood appears)
                    total_memories = sum(emotion_counter.values())
                    dominant_count = emotion_counter[patterns["dominant_mood"]]
                    consistency_ratio = dominant_count / total_memories
                    
                    if consistency_ratio > 0.6:
                        patterns["mood_consistency"] = "consistent"
                    elif consistency_ratio > 0.3:
                        patterns["mood_consistency"] = "moderate"
                    else:
                        patterns["mood_consistency"] = "variable"
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error analyzing mood patterns: {e}")
            return {}
    
    async def _generate_context_summary(self, memories, conversations, preferences, emotional_context):
        """Generate a natural language summary of the context"""
        summary_parts = []
        
        if memories:
            memory_texts = [mem['text'][:100] + "..." for mem in memories[:2]]
            summary_parts.append(f"Related past conversations: {'; '.join(memory_texts)}")
        
        if preferences.get('likes'):
            likes = preferences['likes'][:3]
            summary_parts.append(f"User likes: {', '.join(likes)}")
        
        if conversations:
            last_convo = conversations[-1]
            summary_parts.append(f"Last talked about: {last_convo['user_input'][:100]}...")
        
        if emotional_context.get('dominant_mood'):
            summary_parts.append(f"Recent mood pattern: {emotional_context['dominant_mood']}")
        
        return " | ".join(summary_parts) if summary_parts else "No significant context"
    
    async def get_recent_conversation(self, limit=10):
        """Get recent conversation history"""
        try:
            conversation = await self._load_conversation_history()
            return conversation[-limit:]
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def search_memories_by_emotion(self, emotion, limit=10):
        """Search for memories with specific emotion"""
        try:
            return await self.vector_memory.get_memories_by_emotion(emotion, limit)
        except Exception as e:
            self.logger.error(f"Error searching memories by emotion: {e}")
            return []
    
    async def get_memory_statistics(self):
        """Get comprehensive memory statistics"""
        try:
            emotion_stats = await self.vector_memory.get_emotion_stats()
            recent_memories = await self.vector_memory.get_recent_memories(limit=5)
            recent_conversations = await self.get_recent_conversation(limit=5)
            
            return {
                "total_memories": emotion_stats.get("total_memories", 0),
                "emotion_distribution": emotion_stats.get("emotion_counts", {}),
                "most_common_emotion": emotion_stats.get("most_common_emotion", "neutral"),
                "recent_memories_count": len(recent_memories),
                "recent_conversations_count": len(recent_conversations),
                "emotional_history": await self.vector_memory.get_emotional_history(days_back=30)
            }
        except Exception as e:
            self.logger.error(f"Error getting memory statistics: {e}")
            return {}
    
    async def clear_memories(self, memory_type=None):
        """Clear memories (use with caution)"""
        try:
            # This would require direct ChromaDB access to clear collections
            # For now, we'll just log the request
            self.logger.warning(f"Clear memories requested for type: {memory_type}")
            return False  # Implementation needed
        except Exception as e:
            self.logger.error(f"Error clearing memories: {e}")
            return False
    
    async def export_memories(self, file_path=None):
        """Export memories to JSON file"""
        try:
            if not file_path:
                file_path = Path(settings.DATA_DIR) / "memory_export.json"
            
            memories = await self.vector_memory.get_recent_memories(limit=1000)  # Get all memories
            conversations = await self._load_conversation_history()
            
            export_data = {
                "export_timestamp": self._get_timestamp(),
                "total_memories": len(memories),
                "total_conversations": len(conversations),
                "memories": memories,
                "conversations": conversations
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Memories exported to {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Error exporting memories: {e}")
            return None
    
    async def _load_conversation_history(self):
        """Load conversation history from file"""
        try:
            if self.conversation_path.exists():
                with open(self.conversation_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Error loading conversation history: {e}")
            return []
    
    async def _save_conversation_history(self, conversation):
        """Save conversation history to file"""
        try:
            with open(self.conversation_path, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving conversation history: {e}")
    
    def _get_timestamp(self):
        """Get current timestamp"""
        return datetime.now().isoformat()