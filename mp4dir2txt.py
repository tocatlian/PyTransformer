"""
mp4dir2txt.py - A script to transcribe audio from MP4 files within a directory to text files.

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

The script uses the moviepy library to extract audio from each MP4 file in a directory and utilizes the
SpeechRecognition library to convert spoken words into text, which is then saved as a .txt file named
after the original video file.

Dependencies:
- moviepy: For extracting audio from video files.
- SpeechRecognition: For converting audio speech into text.

To install dependencies, run:
pip install moviepy SpeechRecognition

Usage:
Run the script from the command line with the directory path as the argument:
python mp4dir2txt.py path_to_directory_with_mp4_files
"""

import speech_recognition as sr
import sys
import os
from moviepy.editor import VideoFileClip

def transcribe_audio_from_video(video_file_path, txt_file_path):
    # Extract audio from video file and transcribe it using Google Speech Recognition
    try:
        # Load the video file and extract the audio component
        video_clip = VideoFileClip(video_file_path)
        audio_clip = video_clip.audio
        # Save the audio as a wav file
        audio_file_path = os.path.splitext(video_file_path)[0] + '.wav'
        audio_clip.write_audiofile(audio_file_path, codec='pcm_s16le')
        audio_clip.close()
        video_clip.close()
    except Exception as e:
        print(f"An error occurred while extracting audio: {e}")
        return

    # Initialize the speech recognition recognizer
    recognizer = sr.Recognizer()

    # Transcribe the audio to text
    try:
        with sr.AudioFile(audio_file_path) as source:
            # Record the audio from the entire file
            audio_data = recognizer.record(source)
            # Perform speech recognition using the Google Web Speech API
            text = recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        text = "Google Speech Recognition could not understand audio."
    except sr.RequestError as e:
        text = f"Could not request results from Google Speech Recognition service; {e}"

    # Write the transcription to a text file
    with open(txt_file_path, "w") as txt_file:
        txt_file.write(text)

    # Remove the temporary audio file
    os.remove(audio_file_path)
    print(f"Transcription saved to {txt_file_path}")

def process_directory(directory_path):
    # Process all MP4 files in the specified directory and transcribe them
    mp4_files = [f for f in os.listdir(directory_path) if f.endswith('.mp4')]

    # Check for non-empty list of mp4 files
    if not mp4_files:
        print("No MP4 files found in the directory.")
        return

    for mp4_file in mp4_files:
        video_file_path = os.path.join(directory_path, mp4_file)
        txt_file_path = os.path.splitext(video_file_path)[0] + '.txt'
        print(f"Processing {video_file_path}")
        transcribe_audio_from_video(video_file_path, txt_file_path)

if __name__ == "__main__":
    # Command line argument validation
    if len(sys.argv) != 2:
        print("Usage: python mp4dir2txt.py <directory_path>")
        sys.exit(1)

    directory_path = sys.argv[1]
    # Check if the provided directory path is valid
    if not os.path.isdir(directory_path):
        print(f"The directory {directory_path} does not exist.")
        sys.exit(1)

    # Process the directory to transcribe all contained MP4 files
    process_directory(directory_path)

