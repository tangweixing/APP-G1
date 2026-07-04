#!/usr/bin/env python3
import numpy as np
import wave
import struct

def create_sine_wave(filename, duration=2, sample_rate=44100, frequency=440):
    # Generate sine wave data
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit PCM
    audio = (audio * 32767).astype(np.int16)
    
    # Write to WAV file
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

if __name__ == "__main__":
    # Create WAV file first
    wav_file = "/home/unitree/tang/WK/PythonProject/point_nav/audio/damen.wav"
    mp3_file = "/home/unitree/tang/WK/PythonProject/point_nav/audio/damen.mp3"
    
    create_sine_wave(wav_file)
    print(f"Created WAV file: {wav_file}")
    
    # Try to convert to MP3 using ffmpeg if available
    try:
        import subprocess
        subprocess.run(["ffmpeg", "-i", wav_file, "-y", mp3_file], check=True)
        print(f"Converted to MP3: {mp3_file}")
    except Exception as e:
        print(f"Could not convert to MP3: {e}")
        print("Using WAV file instead")
