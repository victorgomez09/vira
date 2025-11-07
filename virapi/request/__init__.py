"""
Request package for virapi framework.

This package contains classes for handling HTTP requests, including:
- Request: Main request object with form and file handling
- UploadFile: Container for uploaded file metadata with standard Python file access
"""

from .request import Request
from .upload_file import UploadFile

__all__ = ["Request", "UploadFile"]
