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
            # Convert to mono if stereo
            if self.channels > 1:
                mono_data = np.mean(indata, axis=1)
            else:
                mono_data = indata.flatten()
                
            self.audio_queue.put(mono_data.copy())
            # Calculate volume level for visualizer (RMS)
            rms = np.sqrt(np.mean(mono_data**2))
            # Normalize and smooth slightly
            self.volume_level = min(1.0, rms * 10)  # arbitrary scaling for visualization

    def start_recording(self):
        self.is_recording = True
        self.audio_queue = queue.Queue()
        self.volume_level = 0.0
        self.actual_sample_rate = self.sample_rate
        
        try:
            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    device=self.device_id,
                    channels=1,
                    callback=self._audio_callback,
                    dtype='float32'
                )
                self.channels = 1
            except Exception as e:
                import os
                try:
                    with open(os.path.join(os.environ.get("TEMP", "/tmp"), "protocol7_debug.log"), "a") as f:
                        f.write(f"[AUDIO] Initial 16k Mono stream failed: {e}\n")
                except: pass
                
                # Ultimate fallback: Let PortAudio/Windows auto-negotiate the exact required hardware format
                self.stream = sd.InputStream(
                    device=self.device_id,
                    callback=self._audio_callback,
                    dtype='float32'
                )
                self.actual_sample_rate = int(self.stream.samplerate)
                self.channels = self.stream.channels
            self.stream.start()
        except Exception as e:
            import os
            try:
                with open(os.path.join(os.environ.get("TEMP", "/tmp"), "protocol7_debug.log"), "a") as f:
                    f.write(f"[AUDIO] Error starting audio recording completely: {e}\n")
            except: pass
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
            audio = np.concatenate(audio_data, axis=0).flatten()
            # Resample if native hardware rate differs from Whisper's target rate
            if getattr(self, 'actual_sample_rate', self.sample_rate) != self.sample_rate:
                duration = len(audio) / self.actual_sample_rate
                time_old = np.linspace(0, duration, len(audio))
                time_new = np.linspace(0, duration, int(len(audio) * self.sample_rate / self.actual_sample_rate))
                audio = np.interp(time_new, time_old, audio).astype('float32')
            return audio
        return np.array([])
    
    def get_volume_level(self):
        return self.volume_level
