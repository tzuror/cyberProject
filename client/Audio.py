import pyaudio
import base64

# Audio configuration
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 2  # Stereo
RATE = 44100  # Sample rate (44.1 kHz)
CHUNK = 1024  # Buffer size

class AudioCapture:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_capturing = False

    def start_capture(self):
        """Start capturing audio from the system."""
        self.is_capturing = True
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self.callback
        )
        self.stream.start_stream()

    def stop_capture(self):
        """Stop capturing audio."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.is_capturing = False

    def callback(self, in_data, frame_count, time_info, status):
        """Callback function for audio capture."""
        if self.is_capturing:
            # Send the audio data over the network
            self.send_audio(in_data)
        return (in_data, pyaudio.paContinue)

    def get_audio(self, audio_data):
        """Send audio data over the network."""
        if hasattr(self, 'client'):
            # Encode the audio data as Base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            # Send the audio data to the server
            return audio_base64

class AudioPlayback:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None

    def start_playback(self):
        """Start playing audio."""
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK
        )

    def play_audio(self, audio_data):
        """Play received audio data."""
        if self.stream:
            self.stream.write(audio_data)

    def stop_playback(self):
        """Stop playing audio."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()