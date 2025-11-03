"""
Multipart parser - non-streaming implementation for educational purposes.
"""

import tempfile
import os
from typing import Dict, List, Tuple, Optional
from ..upload_file import UploadFile


class MultipartParser:
    """
    Simple multipart parser that parses the entire request body in memory.
    It is not suitable for large file uploads due to memory constraints.

    This parser is designed for educational purposes and handles
    basic multipart/form-data parsing without streaming complexity.
    """

    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize the multipart parser.

        Args:
            temp_dir: Directory for temporary files. If None, uses system default.
        """

        self.temp_dir = temp_dir

    def parse(
        self, body: bytes, boundary: str
    ) -> Tuple[Dict[str, str], List[UploadFile]]:
        """
        Parse multipart data from request body.

        Args:
            body: Complete request body as bytes
            boundary: Boundary string from Content-Type header

        Returns:
            Tuple of (form_data_dict, uploaded_files_list)
        """

        if not body or not boundary:
            return {}, []

        # Split body into parts using boundary
        boundary_bytes = f"--{boundary}".encode()
        parts = body.split(boundary_bytes)

        form_data = {}
        files = []

        # Process each part (skip first empty part and last closing part)
        for part in parts[1:-1]:
            # If the part is empty or just the closing boundary, skip it.
            # If the body is well-formed, this won't happen, but to be safe.
            if not part or part == b"--":
                continue

            # Split headers from content BEFORE stripping to preserve empty content
            if b"\r\n\r\n" not in part:
                continue

            headers_section, content = part.split(b"\r\n\r\n", 1)
            # Strip only the headers section, not the content
            headers_section = headers_section.strip()

            content_disposition = self._get_part_content_disposition(headers_section)
            field_name = self._extract_field_name(content_disposition)
            filename = self._extract_filename(content_disposition)

            if not field_name:
                continue

            if filename:
                # This is a file upload - write to temp file
                content_type = self._get_part_content_type(headers_section)

                # Strip only the final CRLF from content as it's part of multipart formatting
                # not actual file content.
                file_content = content.removesuffix(b"\r\n")

                temp_path = self._write_to_temp_file(file_content)

                upload_file = UploadFile(
                    filename=filename,
                    temp_path=temp_path,
                    size=len(file_content),
                    content_type=content_type,
                )
                files.append(upload_file)
            else:
                # This is a regular form field
                # Strip only the final CRLF from content as it's part of multipart formatting
                field_content = content.removesuffix(b"\r\n")

                try:
                    form_data[field_name] = field_content.decode("utf-8")
                except UnicodeDecodeError:
                    # Handle binary form data as empty string
                    form_data[field_name] = ""

        return form_data, files

    def _write_to_temp_file(self, content: bytes) -> str:
        """
        Write content to a temporary file and return the path.

        Args:
            content: File content as bytes

        Returns:
            Path to the temporary file
        """

        # Create a temporary file
        temp_fd, temp_path = tempfile.mkstemp(dir=self.temp_dir)

        try:
            # Write content to the temporary file
            with os.fdopen(temp_fd, "wb") as temp_file:
                temp_file.write(content)
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e

        return temp_path

    def _get_part_content_disposition(self, headers_section: bytes) -> str:
        """
        Extract Content-Disposition header value from multipart section.

        Args:
            headers_section: Raw headers as bytes

        Returns:
            Content-Disposition header value or empty string
        """
        for line in headers_section.split(b"\r\n"):
            line = line.strip()
            if not line:
                continue

            if b":" in line:
                name, value = line.split(b":", 1)
                name = name.decode().strip().lower()

                if name == "content-disposition":
                    return value.decode().strip()

        return ""

    def _get_part_content_type(self, headers_section: bytes) -> str:
        """
        Extract Content-Type header value from multipart section.

        Args:
            headers_section: Raw headers as bytes

        Returns:
            Content-Type header value or default 'application/octet-stream'
        """
        for line in headers_section.split(b"\r\n"):
            line = line.strip()
            if not line:
                continue

            if b":" in line:
                name, value = line.split(b":", 1)
                name = name.decode().strip().lower()

                if name == "content-type":
                    return value.decode().strip()

        return "application/octet-stream"

    def _extract_field_name(self, content_disposition: str) -> Optional[str]:
        """
        Extract field name from Content-Disposition header.

        Example: 'form-data; name="username"' -> 'username'
        """
        if not content_disposition:
            return None

        # Split by semicolon and find the name part
        parts = content_disposition.split(";")

        for part in parts:
            part = part.strip()
            if part.startswith("name="):
                value = part[5:]  # Remove 'name='

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]

                return value

        return None

    def _extract_filename(self, content_disposition: str) -> Optional[str]:
        """
        Extract filename from Content-Disposition header.

        Example: 'form-data; name="file"; filename="test.txt"' -> 'test.txt'
        """
        if not content_disposition:
            return None

        # Split by semicolon and find the filename part
        parts = content_disposition.split(";")

        for part in parts:
            part = part.strip()
            if part.startswith("filename="):
                value = part[9:]  # Remove 'filename='

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]

                return value

        return None

    @staticmethod
    def extract_boundary(content_type: str) -> Optional[str]:
        """
        Extract boundary from Content-Type header.

        Example: 'multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW'
        """
        if not content_type or "multipart/" not in content_type:
            return None

        # Find 'boundary=' in the content type
        boundary_start = content_type.find("boundary=")
        if boundary_start == -1:
            return None

        # Move past 'boundary='
        value_start = boundary_start + 9
        if value_start >= len(content_type):
            return None

        # Find the end of the boundary value (semicolon, space, or end of string)
        value_end = value_start
        while value_end < len(content_type):
            char = content_type[value_end]
            if char in [";", " ", "\t"]:
                break
            value_end += 1

        boundary = content_type[value_start:value_end]

        # Remove quotes if present
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]

        return boundary
