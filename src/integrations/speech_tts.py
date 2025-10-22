import os
import wave
import threading
import logging
from pathlib import Path
import numpy as np
from config import settings

try:
    from piper.voice import PiperVoice
except ImportError:
    PiperVoice = None

class TTSEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.voice = None
        self.is_initialized = False
        self.audio_output_dir = Path(settings.DATA_DIR) / "audio" / "output"
        self.audio_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default voice model path (you can download more voices)
        self.voice_model = self.audio_output_dir / "en_US-lessac-medium.onnx"
        
    async def initialize(self):
        """Initialize TTS engine"""
        if PiperVoice is None:
            self.logger.warning("Piper TTS not available. Install with: pip install piper-tts")
            return False
            
        try:
            # Check if voice model exists, if not download a small one
            if not self.voice_model.exists():
                self.logger.warning(f"Voice model not found at {self.voice_model}")
                self.logger.info("TTS will be disabled until a voice model is downloaded")
                return False
                
            self.voice = PiperVoice.load(self.voice_model)
            self.is_initialized = True
            self.logger.info("TTS engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {e}")
            return False
    
    async def speak(self, text, output_file=None):
        """Convert text to speech"""
        if not self.is_initialized or not self.voice:
            self.logger.warning("TTS not initialized")
            return None
            
        try:
            if not output_file:
                output_file = self.audio_output_dir / f"tts_{hash(text) & 0xFFFFFFFF}.wav"
            
            # Generate audio
            audio_data = []
            for audio_bytes in self.voice.synthesize(text):
                audio_data.append(audio_bytes)
            
            if audio_data:
                # Combine audio chunks and save to file
                combined_audio = b''.join(audio_data)
                
                with wave.open(str(output_file), 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(22050)  # Sample rate
                    wav_file.writeframes(combined_audio)
                
                self.logger.info(f"TTS generated: {output_file}")
                return str(output_file)
                
        except Exception as e:
            self.logger.error(f"TTS generation error: {e}")
            
        return None
    
    def speak_async(self, text, callback=None):
        """Speak text asynchronously"""
        def run_tts():
            async def async_tts():
                result = await self.speak(text)
                if callback and result:
                    callback(result)
            
            import asyncio
            asyncio.run(async_tts())
        
        thread = threading.Thread(target=run_tts)
        thread.daemon = True
        thread.start()