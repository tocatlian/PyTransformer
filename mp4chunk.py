"""
mp4chunk.py - A script to split MP4 files into fixed-length chunks.

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

This script splits an MP4 file into chunks of a specified length (default is 30 seconds) and saves these chunks into a new directory named after the original file with '_chunks' appended.

Dependencies:
- moviepy: A library for video editing that can be used to split MP4 files. This can be installed using pip:
    pip install moviepy

Usage:
The script is run from the command line, taking a path to an MP4 file as its argument. It creates a subdirectory alongside the original file and outputs the chunks there.

Example:
    python mp4chunk.py /path/to/your/video.mp4
"""

from moviepy.editor import VideoFileClip
import sys
import os

def split_video_into_chunks(filename, chunk_length=30):
    """
    Splits the video file located at 'filename' into chunks of 'chunk_length' seconds.

    :param filename: The path to the input MP4 file to be split.
    :param chunk_length: The length in seconds of each chunk.
    """
    # Load the video file
    clip = VideoFileClip(filename)
    duration = clip.duration  # Duration of the whole video in seconds

    # Calculate number of chunks to be created
    num_chunks = int(duration // chunk_length) + (duration % chunk_length > 0)

    # Create directory for chunks
    base_filename = os.path.splitext(filename)[0]
    chunks_dir = f"{base_filename}_chunks"
    os.makedirs(chunks_dir, exist_ok=True)

    # Split video into chunks
    for i in range(num_chunks):
        # Calculate start and end time for each chunk
        start_time = i * chunk_length
        end_time = min((i + 1) * chunk_length, duration)
        # Create a subclip for the current chunk
        current_clip = clip.subclip(start_time, end_time)
        # Generate chunk filename
        chunk_filename = f"{chunks_dir}/{base_filename}_chunk{i+1}.mp4"
        # Write the subclip to a file
        current_clip.write_videofile(chunk_filename, codec='libx264', audio_codec='aac')

        print(f"Chunk {i+1}/{num_chunks} saved to {chunk_filename}")

    # Release resources to prevent memory leaks
    clip.close()

if __name__ == "__main__":
    # Command line argument handling
    if len(sys.argv) != 2:
        print("Usage: python mp4chunk.py <mp4_file_path>")
        sys.exit(1)

    # Validate that the file exists
    video_file_path = sys.argv[1]
    if not os.path.isfile(video_file_path):
        print(f"The file {video_file_path} does not exist.")
        sys.exit(1)

    # Split the file into chunks
    split_video_into_chunks(video_file_path)
