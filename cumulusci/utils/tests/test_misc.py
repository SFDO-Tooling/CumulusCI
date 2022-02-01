import urllib.request
from pathlib import Path
from unittest import mock

from cumulusci.utils import view_file


class TestMisc:
    def test_view_file_str_path(self):
        """Verify view_file works when given a path as a string"""
        with mock.patch("webbrowser.open") as webbrowser_open:
            path = "robot/results/index.html"
            view_file(path)
            url = f"file://{urllib.request.pathname2url(str(Path(path).resolve()))}"
            webbrowser_open.assert_called_once_with(url)

    def test_view_file_Path(self):
        """Verify view_file works when given a path as a Path object"""
        with mock.patch("webbrowser.open") as webbrowser_open:
            path = Path("robot/results/index.html")
            view_file(path)
            url = f"file://{urllib.request.pathname2url(str(path.resolve()))}"
            webbrowser_open.assert_called_once_with(url)
