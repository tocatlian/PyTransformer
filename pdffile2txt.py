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
pdffile2txt.py - Script to convert PDF file contents to a text file.

This script takes a single PDF file as an input argument and extracts the text contained within,
saving it to a text file with the same name as the PDF file but with a .txt extension.

Dependencies:
- PyPDF2: A library to read text from PDF files. Install it using pip:
    pip install PyPDF2

Usage:
To use this script, run it from the command line providing the PDF file path as an argument:
python pdffile2txt.py path_to_pdf_file.pdf

The script outputs a text file in the same directory as the input PDF.
"""

import PyPDF2
import sys
import os

def extract_text_from_pdf(pdf_file_path):
    # Extracts text from a PDF file and returns it as a string.
    try:
        with open(pdf_file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            # Iterate over each page in the PDF and extract text
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        raise Exception(f"An error occurred while reading {pdf_file_path}: {e}")
    
    return text

if __name__ == "__main__":
    # Command line argument validation
    if len(sys.argv) != 2:
        print("Usage: python pdffile2txt.py <pdf_file_path>")
        sys.exit(1)

    # The path to the PDF file
    pdf_file_path = sys.argv[1]
    # Ensure the file exists before proceeding
    if not os.path.isfile(pdf_file_path):
        print(f"File not found: {pdf_file_path}")
        sys.exit(1)

    # Define the output text file name
    output_file_path = os.path.splitext(pdf_file_path)[0] + ".txt"

    # Extract and write the text to the output file
    extracted_text = extract_text_from_pdf(pdf_file_path)
    with open(output_file_path, 'w') as text_file:
        text_file.write(extracted_text)

    print(f"Text successfully written to {output_file_path}")

