import os
from faster_whisper import WhisperModel

class WhisperEngine:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.current_model_size = None

    def _load_model(self):
        model_size = self.config.get("model_size", "tiny.en")
        compute_type = self.config.get("compute_type", "default")
        
        if self.model is None or self.current_model_size != model_size:
            print(f"Loading Whisper model: {model_size}...")
            # We use CPU by default, or let faster_whisper auto-detect CUDA/ROCm
            self.model = WhisperModel(model_size, device="auto", compute_type=compute_type)
            self.current_model_size = model_size
            print("Model loaded successfully.")

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

        print("Transcribing...")
        segments, info = self.model.transcribe(
            audio_data, 
            beam_size=5, 
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            **kwargs
        )
        
        text = "".join(segment.text for segment in segments)
        return text.strip()
