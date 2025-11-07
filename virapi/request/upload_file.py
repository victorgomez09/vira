"""
UploadFile class for handling file uploads in virapi.
"""

import os
import shutil
from typing import IO


class UploadFile:
    """
    Container for uploaded file metadata with read-only file access.

    Use upload_file.open() to get a standard Python file handle for reading.
    Use upload_file.get_path() for advanced operations requiring write access.

    Attributes:
        filename: Original filename of the uploaded file
        size: Size of the file in bytes
        content_type: MIME type of the file
    """

    def __init__(
        self, filename: str, temp_path: str, size: int, content_type: str = ""
    ):
        self.filename = filename
        self.size = size
        self.content_type = content_type
        self._temp_path = temp_path

    def open(self, mode: str = "rb") -> IO[bytes]:
        """
        Open the uploaded file for reading.

        Args:
            mode: File mode. Only read modes allowed ('r', 'rb').
                 Defaults to 'rb' for binary reading.

        Returns:
            Standard Python file handle for reading

        Raises:
            ValueError: If write mode is attempted

        Example:
            with upload_file.open() as f:
                content = f.read()
                f.seek(0)
                header = f.read(100)
        """
        # Validate mode - only allow read modes
        if "w" in mode or "a" in mode or "+" in mode:
            raise ValueError(
                "Write operations not allowed on uploaded files. "
                "Use get_path() for advanced operations requiring write access."
            )

        return open(self._temp_path, mode)

    def get_path(self) -> str:
        """
        Get temporary file path for advanced operations.

        Warning: Direct path access allows write operations.
        Use open() method for safe read-only access.

        Returns:
            Absolute path to the temporary file

        Example:
            # Advanced usage - user is responsible for proper file handling
            temp_path = upload_file.get_path()
            with open(temp_path, 'r+b') as f:
                # Modify file if needed
                pass
        """
        return self._temp_path

    def save(self, path: str) -> None:
        """
        Save the uploaded file to a specific path.

        Args:
            path: Destination path where the file should be saved

        Example:
            upload_file.save('/path/to/documents/file.pdf')
        """
        shutil.copy2(self._temp_path, path)

    def cleanup(self) -> None:
        """
        Clean up temporary file.

        This is automatically called by the Request cleanup process.
        """
        if os.path.exists(self._temp_path):
            os.unlink(self._temp_path)

    def __repr__(self) -> str:
        return f"UploadFile(filename='{self.filename}', size={self.size}, content_type='{self.content_type}')"
