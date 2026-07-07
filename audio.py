import sounddevice as sd
import numpy as np
import threading
import queue

class AudioRecorder:
    def __init__(self, device_id=None, sample_rate=16000):
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.channels = 1
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.volume_level = 0.0

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        if self.is_recording:
            self.audio_queue.put(indata.copy())
            # Calculate volume level for visualizer (RMS)
            rms = np.sqrt(np.mean(indata**2))
            # Normalize and smooth slightly
            self.volume_level = min(1.0, rms * 10)  # arbitrary scaling for visualization

    def start_recording(self):
        self.is_recording = True
        self.audio_queue = queue.Queue()
        self.volume_level = 0.0
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                device=self.device_id,
                channels=self.channels,
                callback=self._audio_callback,
                dtype='float32'
            )
            self.stream.start()
        except Exception as e:
            print(f"Error starting audio recording: {e}")
            self.is_recording = False

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        # Collect all audio data from queue
        audio_data = []
        while not self.audio_queue.empty():
            audio_data.append(self.audio_queue.get())
        
        if audio_data:
            return np.concatenate(audio_data, axis=0).flatten()
        return np.array([])
    
    def get_volume_level(self):
        return self.volume_level
