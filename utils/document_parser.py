import os
import pandas as pd
from docx import Document
from PyPDF2 import PdfReader
from typing import Any, List, Optional

def parse_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    except Exception as e:
        print(f"Error parsing PDF {file_path}: {e}")
    return text

def parse_docx(file_path: str) -> str:
    """Extract text from Word document"""
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error parsing DOCX {file_path}: {e}")
    return text

def parse_excel(file_path: str) -> str:
    """Extract text from Excel file"""
    text = ""
    try:
        # Load all sheets
        dict_df = pd.read_excel(file_path, sheet_name=None)
        for sheet_name, df in dict_df.items():
            text += f"Sheet: {sheet_name}\n"
            text += df.to_string() + "\n\n"
    except Exception as e:
        print(f"Error parsing Excel {file_path}: {e}")
    return text

def extract_text_from_file(file_path: str) -> str:
    """Determine file type and extract text"""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return parse_pdf(file_path)
    elif ext == '.docx':
        return parse_docx(file_path)
    elif ext in ['.xlsx', '.xls']:
        return parse_excel(file_path)
    else:
        # Try reading as plain text
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""
