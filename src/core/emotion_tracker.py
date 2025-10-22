import json
import logging
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
from config import settings

class EmotionTracker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.emotion_history = deque(maxlen=100)  # Last 100 emotions
        self.emotion_intensities = {}
        self.state_file = Path(settings.DATA_DIR) / "emotion_state.json"
        self.current_emotion = "neutral"
        self.emotion_duration = 0
        
        # Emotion decay rates (how quickly emotions fade)
        self.decay_rates = {
            "happy": 0.1,
            "sad": 0.05,
            "angry": 0.15,
            "surprised": 0.2,
            "curious": 0.08,
            "confused": 0.1,
            "excited": 0.12,
            "thoughtful": 0.06,
            "neutral": 0.03
        }
    
    async def initialize(self):
        """Load emotion state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.emotion_history = deque(data.get('emotion_history', []), maxlen=100)
                    self.emotion_intensities = data.get('emotion_intensities', {})
                    self.current_emotion = data.get('current_emotion', 'neutral')
                    self.emotion_duration = data.get('emotion_duration', 0)
                self.logger.info("Loaded emotion state")
            return True
        except Exception as e:
            self.logger.error(f"Error loading emotion state: {e}")
            return False
    
    async def update_emotion(self, new_emotion, intensity=1.0, trigger=None):
        """Update current emotion with intensity and context"""
        try:
            # Record emotion change
            emotion_record = {
                "emotion": new_emotion,
                "intensity": intensity,
                "timestamp": datetime.now().isoformat(),
                "trigger": trigger,
                "previous_emotion": self.current_emotion
            }
            
            self.emotion_history.append(emotion_record)
            
            # Update current emotion
            self.current_emotion = new_emotion
            self.emotion_intensities[new_emotion] = intensity
            self.emotion_duration = 0  # Reset duration for new emotion
            
            # Apply emotion persistence logic
            await self._apply_emotion_persistence()
            
            # Save state
            await self._save_state()
            
            self.logger.info(f"Emotion updated to: {new_emotion} (intensity: {intensity})")
            
        except Exception as e:
            self.logger.error(f"Error updating emotion: {e}")
    
    async def _apply_emotion_persistence(self):
        """Apply emotion persistence and decay over time"""
        # Update emotion durations
        self.emotion_duration += 1
        
        # Apply decay to all emotions
        for emotion in list(self.emotion_intensities.keys()):
            decay_rate = self.decay_rates.get(emotion, 0.1)
            self.emotion_intensities[emotion] *= (1 - decay_rate)
            
            # Remove very weak emotions
            if self.emotion_intensities[emotion] < 0.05:
                del self.emotion_intensities[emotion]
    
    async def get_emotional_state(self):
        """Get comprehensive emotional state"""
        return {
            "current_emotion": self.current_emotion,
            "emotion_duration": self.emotion_duration,
            "emotion_intensities": self.emotion_intensities,
            "recent_emotions": list(self.emotion_history)[-10:],  # Last 10 emotions
            "mood_stability": await self._calculate_mood_stability(),
            "emotional_tendencies": await self._analyze_emotional_tendencies()
        }
    
    async def _calculate_mood_stability(self):
        """Calculate how stable the mood has been"""
        if len(self.emotion_history) < 2:
            return "unknown"
        
        recent_emotions = [record["emotion"] for record in list(self.emotion_history)[-10:]]
        unique_emotions = len(set(recent_emotions))
        
        if unique_emotions <= 2:
            return "very_stable"
        elif unique_emotions <= 4:
            return "stable"
        elif unique_emotions <= 6:
            return "variable"
        else:
            return "unstable"
    
    async def _analyze_emotional_tendencies(self):
        """Analyze emotional patterns and tendencies"""
        if not self.emotion_history:
            return {}
        
        emotion_counts = {}
        triggers = {}
        
        for record in self.emotion_history:
            emotion = record["emotion"]
            trigger = record.get("trigger")
            
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            if trigger:
                triggers[trigger] = triggers.get(trigger, 0) + 1
        
        # Calculate percentages
        total = len(self.emotion_history)
        emotion_percentages = {emotion: count/total for emotion, count in emotion_counts.items()}
        
        return {
            "dominant_emotion": max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "neutral",
            "emotion_distribution": emotion_percentages,
            "common_triggers": dict(sorted(triggers.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    async def predict_emotional_response(self, input_text):
        """Predict emotional response to input (simple version)"""
        # Simple keyword-based prediction
        emotional_triggers = {
            "happy": ["good", "great", "awesome", "wonderful", "congratulations"],
            "sad": ["sad", "sorry", "bad", "unfortunate", "disappointing"],
            "angry": ["angry", "mad", "frustrating", "annoying", "hate"],
            "curious": ["why", "how", "what if", "explain", "tell me about"],
            "excited": ["exciting", "can't wait", "looking forward", "amazing"]
        }
        
        input_lower = input_text.lower()
        emotion_scores = {}
        
        for emotion, triggers in emotional_triggers.items():
            score = sum(1 for trigger in triggers if trigger in input_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        if emotion_scores:
            predicted_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
            confidence = emotion_scores[predicted_emotion] / len(emotional_triggers[predicted_emotion])
            return predicted_emotion, confidence
        
        return "neutral", 0.3
    
    async def _save_state(self):
        """Save emotion state to file"""
        try:
            state_data = {
                "emotion_history": list(self.emotion_history),
                "emotion_intensities": self.emotion_intensities,
                "current_emotion": self.current_emotion,
                "emotion_duration": self.emotion_duration,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error saving emotion state: {e}")