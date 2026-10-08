# file_parser.py
# This file extracts text from PDF and DOCX files
# When user uploads their CV we need to read the text inside it
# PDF files are read using PyMuPDF library
# DOCX files are read using python-docx library

import fitz  # PyMuPDF — used for reading PDF files
from docx import Document  # python-docx — used for reading DOCX files
import io

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF file
    
    file_bytes — the PDF file as bytes
    Returns all the text as a single string
    """

    # Open the PDF from bytes
    # fitz.open reads the PDF file
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")

    # This will store all the text we extract
    all_text = ""

    # Loop through every page in the PDF
    # Some CVs have multiple pages so we read all of them
    for page_number in range(len(pdf_document)):
        # Get the page
        page = pdf_document[page_number]

        # Extract text from this page
        page_text = page.get_text()

        # Add page text to our collection
        all_text += page_text + "\n"

    # Close the PDF document
    pdf_document.close()

    return all_text.strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract all text from a DOCX file
    
    file_bytes — the DOCX file as bytes
    Returns all the text as a single string
    """

    # Open the DOCX file from bytes
    docx_file = io.BytesIO(file_bytes)
    document = Document(docx_file)

    # This will store all the text we extract
    all_text = ""

    # Loop through every paragraph in the document
    # A paragraph can be a line of text, a heading, or a bullet point
    for paragraph in document.paragraphs:
        # Only add non empty paragraphs
        if paragraph.text.strip():
            all_text += paragraph.text + "\n"

    return all_text.strip()


def extract_text(file_bytes: bytes, file_type: str) -> str:
    """
    Main function — figures out if file is PDF or DOCX
    and calls the right extraction function
    
    file_bytes — the file as bytes
    file_type — either 'pdf' or 'docx'
    Returns the extracted text
    """

    # Convert file type to lowercase for comparison
    file_type = file_type.lower()

    if file_type == "pdf":
        return extract_text_from_pdf(file_bytes)

    elif file_type == "docx":
        return extract_text_from_docx(file_bytes)

    else:
        # If file type is not PDF or DOCX raise an error
        raise ValueError(f"Unsupported file type: {file_type}. Only PDF and DOCX are supported.")