"""
Copyright (c) 2023 Paul Tocatlian

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
mp4file2txt.py - A script to transcribe audio from an MP4 file to a text file.

This script takes a single MP4 file as an input argument, extracts the audio, and uses the Google Web Speech API to 
transcribe the audio to text. The resulting text is saved to a new text file with the same name as the MP4 file.

Dependencies:
- moviepy: For audio extraction from video files.
- SpeechRecognition: For performing speech recognition.

To install dependencies, run:
pip install moviepy SpeechRecognition

Usage:
Run the script from the command line, providing the MP4 file path as an argument:
python mp4file2txt.py path_to_video.mp4

The script will output a text file with the transcribed audio in the same directory as the input MP4 file.
"""

import speech_recognition as sr
import sys
from moviepy.editor import AudioFileClip

def transcribe_audio(mp4_file_path):
    """
    Extracts audio from the provided MP4 file and transcribes it using Google's Speech Recognition API.

    :param mp4_file_path: The file path for the MP4 video file.
    :return: The transcribed text as a string.
    """
    # Convert MP4 audio to WAV format for compatibility with the SpeechRecognition library
    audio_clip = AudioFileClip(mp4_file_path)
    audio_clip.write_audiofile("temp.wav", codec='pcm_s16le')  # convert to wav for compatibility
    audio_clip.close()

    # Initialize the recognizer
    recognizer = sr.Recognizer()

    # Load the audio file data into an audio source
    with sr.AudioFile("temp.wav") as source:
        audio_data = recognizer.record(source)  # read the entire audio file

    # Recognize the speech using Google Web Speech API
    try:
        print("Transcribing audio...")
        text = recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        text = "Google Speech Recognition could not understand audio"
    except sr.RequestError as e:
        text = f"Could not request results from Google Speech Recognition service; {e}"

    return text

if __name__ == "__main__":
    # Check command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python mp4file2txt.py <mp4_file_path>")
        sys.exit(1)

    # Process the provided MP4 file and save the transcription
    mp4_file_path = sys.argv[1]
    transcript = transcribe_audio(mp4_file_path)

    # Write the transcript to a text file with the same base name as the MP4 file
    text_file_name = mp4_file_path.rsplit(".", 1)[0] + ".txt"
    with open(text_file_name, "w") as text_file:
        text_file.write(transcript)
    print(f"Transcription saved to {text_file_name}")

