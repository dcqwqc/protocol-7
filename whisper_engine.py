import os
from faster_whisper import WhisperModel

class WhisperEngine:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.current_model_size = None

    def _load_model(self):
        model_size = self.config.get("model_size", "tiny.en")
        
        # If running on CPU, int8 is significantly faster and uses less memory
        compute_type = self.config.get("compute_type", "int8")
        
        if self.model is None or self.current_model_size != model_size:
            print(f"Loading Whisper model: {model_size} (compute_type: {compute_type})...")
            import time
            start_load = time.time()
            self.model = WhisperModel(model_size, device="auto", compute_type=compute_type)
            self.current_model_size = model_size
            print(f"Model loaded successfully in {time.time() - start_load:.2f}s.")

    def transcribe(self, audio_data):
        if len(audio_data) == 0:
            return ""

        self._load_model()
        
        # Determine language and task
        language = self.config.get("language", "en")
        auto_detect = self.config.get("auto_detect_language", True)
        translate = self.config.get("translate", False)
        
        task = "translate" if translate else "transcribe"
        
        kwargs = {
            "task": task,
            "condition_on_previous_text": False,
            "initial_prompt": "Hello. This is a clean, perfectly punctuated transcript."
        }
        
        if not auto_detect and language:
            kwargs["language"] = language

        print("Transcribing with Whisper (beam_size=1)...")
        import time
        t0 = time.time()
        
        # Use beam_size=1 (greedy) for massive speedup. Beam size 5 is overkill for dictation and slow on CPU.
        # We also disable VAD or make it very lenient so it doesn't aggressively cut off quiet speech or natural pauses.
        segments, info = self.model.transcribe(
            audio_data, 
            beam_size=1, 
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=2000,  # Increased from 500ms to 2s to allow natural breathing pauses
                speech_pad_ms=400              # Pad speech segments so ends of words aren't cut off
            ),
            **kwargs
        )
        
        text = "".join(segment.text for segment in segments)
        print(f"[Whisper] Internal Transcription took {time.time() - t0:.2f}s")
        return text.strip()
