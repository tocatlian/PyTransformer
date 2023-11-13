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
txtconcat.py - A script to concatenate text files in a directory into a single file.

This script searches for all text (.txt) files within a specified directory and concatenates their contents into a single text file named after the directory itself. The resulting file is saved within the same directory.

No external library dependencies are required for this script.

Usage:
Run the script from the command line, providing the directory path as an argument:
python txtconcat.py /path/to/directory

The script will generate a file named <directory_name>.txt with the concatenated content of all text files found in the specified directory.
"""

import sys
import os

def concatenate_txt_files(directory_path):
    # Ensure the directory contains .txt files
    txt_files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]
    if not txt_files:
        print(f"No .txt files found in the directory {directory_path}.")
        return

    # Create a single file named after the directory with .txt extension
    output_filename = os.path.join(directory_path, os.path.basename(directory_path.strip('/')) + '.txt')

    with open(output_filename, 'w') as outfile:
        # Loop through all .txt files in the directory and concatenate them
        for filename in txt_files:
            # Avoid writing the output file into itself
            if filename != os.path.basename(output_filename):
                file_path = os.path.join(directory_path, filename)
                with open(file_path, 'r') as readfile:
                    outfile.write(readfile.read() + "\n") # Add a newline to separate content

    print(f"All text files have been concatenated into {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python txtconcat.py <directory_path>")
        sys.exit(1)

    directory_path = sys.argv[1]
    if not os.path.isdir(directory_path):
        print(f"The directory {directory_path} does not exist.")
        sys.exit(1)

    concatenate_txt_files(directory_path)

