import chromadb
import json
import logging
import numpy as np
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
from pathlib import Path
from config import settings

class VectorMemory:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.memory_path = settings.VECTOR_MEMORY_PATH
        
        # Emotion categories for tagging
        self.emotion_categories = {
            "joy": ["happy", "excited", "joyful", "delighted", "cheerful"],
            "sadness": ["sad", "melancholy", "unhappy", "disappointed", "gloomy"],
            "anger": ["angry", "frustrated", "annoyed", "irritated", "mad"],
            "surprise": ["surprised", "amazed", "astonished", "shocked"],
            "fear": ["scared", "afraid", "anxious", "nervous", "worried"],
            "disgust": ["disgusted", "repulsed", "grossed", "revulsed"],
            "trust": ["trusting", "confident", "secure", "reassured"],
            "anticipation": ["curious", "interested", "eager", "expectant"],
            "neutral": ["neutral", "calm", "balanced", "composed"]
        }
    
    async def initialize(self):
        """Initialize vector database and embedding model"""
        try:
            # Initialize ChromaDB
            self.client = chromadb.PersistentClient(path=str(self.memory_path.parent))
            
            # Create or get collection
            self.collection = self.client.get_or_create_collection(
                name="lumi_memory",
                metadata={"description": "Lumi AI Companion Memory"}
            )
            
            # Load embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            self.logger.info("Vector memory system initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize vector memory: {e}")
            return False
    
    async def store_memory(self, text, memory_type="conversation", metadata=None, emotion=None):
        """Store a memory with vector embeddings and emotion tagging"""
        if not self.embedding_model:
            return False
            
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(text).tolist()
            
            # Detect emotion if not provided
            if emotion is None:
                emotion = self._detect_emotion_from_text(text)
            
            # Prepare metadata - ChromaDB requires simple types (no nested dicts)
            memory_metadata = {
                "type": memory_type,
                "timestamp": datetime.now().isoformat(),
                "emotion": emotion,
                "emotion_category": self._categorize_emotion(emotion)
            }
            
            # Add simple metadata fields (no nested objects)
            if metadata:
                # Flatten any nested dictionaries
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        memory_metadata[key] = value
                    else:
                        # Convert complex objects to strings
                        memory_metadata[key] = str(value)
            
            # Generate unique ID
            memory_id = f"memory_{datetime.now().timestamp()}"
            
            # Store in vector database
            self.collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[memory_metadata],
                ids=[memory_id]
            )
            
            self.logger.info(f"Stored memory with emotion '{emotion}': {text[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing memory: {e}")
            return False
    
    def _detect_emotion_from_text(self, text):
        """Detect emotion from text content"""
        text_lower = text.lower()
        
        emotion_keywords = {
            "happy": ["happy", "joy", "excited", "great", "wonderful", "awesome", "good", "yay", "😊", "😂"],
            "sad": ["sad", "unhappy", "sorry", "bad", "terrible", "awful", "cry", "tear", "😢", "💔"],
            "angry": ["angry", "mad", "frustrated", "annoyed", "hate", "upset", "😠", "🤬"],
            "surprised": ["surprised", "wow", "amazing", "shocked", "unexpected", "😲", "🤯"],
            "curious": ["curious", "wonder", "question", "why", "how", "what if", "🤔", "❓"],
            "confused": ["confused", "unsure", "uncertain", "puzzled", "don't know", "😕", "🤷"],
            "excited": ["excited", "can't wait", "looking forward", "thrilled", "🎉", "✨"],
            "thoughtful": ["think", "ponder", "consider", "reflect", "maybe", "perhaps"],
            "neutral": ["okay", "fine", "alright", "sure", "yes", "no", "maybe"]
        }
        
        emotion_scores = {emotion: 0 for emotion in emotion_keywords.keys()}
        
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    emotion_scores[emotion] += 1
        
        # Return emotion with highest score, default to neutral
        detected_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        return detected_emotion[0] if detected_emotion[1] > 0 else "neutral"
    
    def _categorize_emotion(self, emotion):
        """Categorize specific emotion into broader categories"""
        for category, emotions in self.emotion_categories.items():
            if emotion in emotions:
                return category
        return "neutral"
    
    async def search_memories(self, query, n_results=5, memory_type=None, emotion=None, emotion_category=None):
        """Search for similar memories with emotion filtering"""
        if not self.embedding_model:
            return []
            
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Build filters
            where_filter = {}
            if memory_type:
                where_filter["type"] = memory_type
            if emotion:
                where_filter["emotion"] = emotion
            if emotion_category:
                where_filter["emotion_category"] = emotion_category
            
            # Search vector database
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter if where_filter else None
            )
            
            memories = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    memory = {
                        "text": doc,
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if results['distances'] else 0,
                        "emotion": results['metadatas'][0][i].get('emotion', 'neutral'),
                        "emotion_category": results['metadatas'][0][i].get('emotion_category', 'neutral')
                    }
                    memories.append(memory)
            
            return memories
            
        except Exception as e:
            self.logger.error(f"Error searching memories: {e}")
            return []
    
    async def get_memories_by_emotion(self, emotion, limit=10):
        """Get memories filtered by specific emotion"""
        return await self.search_memories(
            query="",  # Empty query to get all memories with this emotion
            n_results=limit,
            emotion=emotion
        )
    
    async def get_emotional_history(self, days_back=30):
        """Get emotional history over time"""
        try:
            all_memories = self.collection.get()
            
            if not all_memories['metadatas']:
                return {}
            
            # Filter by date and extract emotions
            emotional_data = {}
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for metadata in all_memories['metadatas']:
                timestamp_str = metadata.get('timestamp', '')
                if timestamp_str:
                    try:
                        memory_date = datetime.fromisoformat(timestamp_str)
                        if memory_date >= cutoff_date:
                            date_key = memory_date.strftime('%Y-%m-%d')
                            emotion = metadata.get('emotion', 'neutral')
                            
                            if date_key not in emotional_data:
                                emotional_data[date_key] = {}
                            
                            emotional_data[date_key][emotion] = emotional_data[date_key].get(emotion, 0) + 1
                    except:
                        continue
            
            return emotional_data
            
        except Exception as e:
            self.logger.error(f"Error getting emotional history: {e}")
            return {}
    
    async def get_emotion_stats(self):
        """Get statistics about emotions in memories"""
        try:
            all_memories = self.collection.get()
            
            if not all_memories['metadatas']:
                return {"total_memories": 0, "emotion_counts": {}}
            
            emotion_counts = {}
            for metadata in all_memories['metadatas']:
                emotion = metadata.get('emotion', 'neutral')
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            return {
                "total_memories": len(all_memories['metadatas']),
                "emotion_counts": emotion_counts,
                "most_common_emotion": max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "neutral"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting emotion stats: {e}")
            return {"total_memories": 0, "emotion_counts": {}}
    
    async def get_recent_memories(self, limit=10):
        """Get most recent memories with emotion data"""
        try:
            # Get all memories and sort by timestamp
            all_memories = self.collection.get()
            
            if not all_memories['metadatas']:
                return []
            
            # Combine data and sort by timestamp
            memories_with_times = []
            for i, metadata in enumerate(all_memories['metadatas']):
                memories_with_times.append({
                    "text": all_memories['documents'][i],
                    "metadata": metadata,
                    "timestamp": metadata.get('timestamp', ''),
                    "emotion": metadata.get('emotion', 'neutral'),
                    "emotion_category": metadata.get('emotion_category', 'neutral')
                })
            
            # Sort by timestamp (newest first)
            memories_with_times.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return memories_with_times[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting recent memories: {e}")
            return []