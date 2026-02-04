from pathlib import Path
import shutil
from tempfile import mkdtemp

from django.http import FileResponse
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class DownloadFileViewTests(APITestCase):
    def setUp(self):
        self.temp_dir = mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        self.static_path = Path(self.temp_dir)
        self.settings_override = override_settings(STATIC_FILES_PATH=self.static_path)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.url = reverse("download_file")

    def _create_file(self, name: str, content: bytes) -> Path:
        file_path = self.static_path / name
        file_path.write_bytes(content)
        return file_path

    def test_returns_file_response_when_file_exists(self):
        file_name = "sample.txt"
        file_content = b"hello world"
        self._create_file(file_name, file_content)

        response = self.client.get(self.url, {"file_name": file_name})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response, FileResponse)
        downloaded = b"".join(response.streaming_content)
        self.assertEqual(downloaded, file_content)

    def test_returns_400_when_file_is_missing(self):
        file_name = "missing.txt"

        response = self.client.get(self.url, {"file_name": file_name})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
