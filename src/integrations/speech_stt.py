import os
import threading
import queue
import logging
import tempfile
from pathlib import Path
import pyaudio
import wave
import numpy as np
from config import settings

try:
    import whisper
except ImportError:
    whisper = None

class STTEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.is_initialized = False
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.audio_input_dir = Path(settings.DATA_DIR) / "audio" / "input"
        self.audio_input_dir.mkdir(parents=True, exist_ok=True)
        
        # Audio recording settings
        self.chunk_size = 1024
        self.sample_rate = 16000
        self.record_seconds = 5
        self.silence_threshold = 500
        self.silence_duration = 2
        
    async def initialize(self):
        """Initialize STT engine"""
        if whisper is None:
            self.logger.warning("Whisper not available. Install with: pip install openai-whisper")
            return False
            
        try:
            # Load the base model (smallest for performance)
            self.model = whisper.load_model("base")
            self.is_initialized = True
            self.logger.info("STT engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize STT: {e}")
            return False
    
    async def transcribe_audio(self, audio_file_path):
        """Transcribe audio file to text"""
        if not self.is_initialized or not self.model:
            self.logger.warning("STT not initialized")
            return None
            
        try:
            result = self.model.transcribe(str(audio_file_path))
            transcription = result["text"].strip()
            
            if transcription:
                self.logger.info(f"STT transcription: {transcription}")
                return transcription
            else:
                self.logger.info("No speech detected in audio")
                return None
                
        except Exception as e:
            self.logger.error(f"STT transcription error: {e}")
            return None
    
    def start_listening(self, callback=None):
        """Start listening for voice input"""
        if not self.is_initialized:
            self.logger.warning("STT not initialized")
            return False
            
        self.is_listening = True
        
        def record_audio():
            try:
                audio = pyaudio.PyAudio()
                
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size
                )
                
                self.logger.info("Started listening for voice input...")
                frames = []
                silent_chunks = 0
                max_silent_chunks = int(self.silence_duration * self.sample_rate / self.chunk_size)
                
                while self.is_listening:
                    data = stream.read(self.chunk_size)
                    frames.append(data)
                    
                    # Convert to numpy array to check volume
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    volume = np.sqrt(np.mean(audio_data**2))
                    
                    if volume < self.silence_threshold:
                        silent_chunks += 1
                        if silent_chunks > max_silent_chunks and len(frames) > self.sample_rate:  # At least 1 second
                            break
                    else:
                        silent_chunks = 0
                        
                    # Limit recording to 10 seconds max
                    if len(frames) > (10 * self.sample_rate / self.chunk_size):
                        break
                
                stream.stop_stream()
                stream.close()
                audio.terminate()
                
                if frames and callback:
                    # Save recorded audio to temporary file
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                        with wave.open(temp_file.name, 'wb') as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
                            wf.setframerate(self.sample_rate)
                            wf.writeframes(b''.join(frames))
                        
                        # Callback with the file path
                        callback(temp_file.name)
                        
                self.logger.info("Stopped listening")
                
            except Exception as e:
                self.logger.error(f"Audio recording error: {e}")
        
        thread = threading.Thread(target=record_audio)
        thread.daemon = True
        thread.start()
        return True
    
    def stop_listening(self):
        """Stop listening for voice input"""
        self.is_listening = False
    
    async def process_voice_input(self):
        """Process voice input and return transcription"""
        if not self.is_initialized:
            return None
            
        def recording_callback(audio_file_path):
            self.audio_queue.put(audio_file_path)
        
        self.start_listening(recording_callback)
        
        try:
            audio_file_path = self.audio_queue.get(timeout=30)  # Wait up to 30 seconds
            transcription = await self.transcribe_audio(audio_file_path)
            
            # Clean up temporary file
            try:
                os.unlink(audio_file_path)
            except:
                pass
                
            return transcription
            
        except queue.Empty:
            self.logger.info("No voice input detected")
            return None