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
pdfdir2txt.py - Batch convert PDF files in a directory to text files.

This script takes a directory as an input argument and generates a text file for each PDF file in that directory.
Each output text file has the same name as the corresponding PDF file, appended with a .txt extension.

Dependencies:
- PyPDF2: A library to read text from PDF files. Install it using pip:
    pip install PyPDF2

Usage:
To use this script, run it from the command line with the directory path as an argument:
python pdfdir2txt.py /path/to/directory

The script will create text files for each PDF in the provided directory.
"""

import PyPDF2
import sys
import os

def convert_pdf_to_text(pdf_file_path, text_file_path):
    """
    Converts a PDF file to a text file.

    :param pdf_file_path: Path to the source PDF file.
    :param text_file_path: Path to the output text file.
    """
    try:
        # Open the PDF file
        with open(pdf_file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            # Read each page and extract text
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        # Write the extracted text to a text file
        with open(text_file_path, 'w') as text_file:
            text_file.write(text)
        print(f"Created text file {text_file_path}")
    except Exception as e:
        print(f"Failed to convert {pdf_file_path} to text: {e}")

def process_directory(directory_path):
    """
    Processes all PDF files in the given directory to text files.

    :param directory_path: The directory containing PDF files to convert.
    """
    # List all PDF files in the directory
    for file_name in os.listdir(directory_path):
        if file_name.lower().endswith('.pdf'):
            pdf_file_path = os.path.join(directory_path, file_name)
            text_file_path = os.path.splitext(pdf_file_path)[0] + '.txt'
            convert_pdf_to_text(pdf_file_path, text_file_path)

if __name__ == "__main__":
    # Check for the correct number of command line arguments
    if len(sys.argv) != 2:
        print("Usage: python pdfdir2txt.py <directory_path>")
        sys.exit(1)
    
    # Directory path provided by the user
    directory_path = sys.argv[1]
    # Ensure the directory exists
    if not os.path.isdir(directory_path):
        print(f"The specified directory does not exist: {directory_path}")
        sys.exit(1)
    
    # Convert all PDFs in the specified directory
    process_directory(directory_path)

