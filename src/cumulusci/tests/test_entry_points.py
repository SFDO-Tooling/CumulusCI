from subprocess import PIPE, Popen

import pytest


class TestEntryPoints:
    def _popen(self, cmd):
        process = Popen([cmd], stdout=PIPE, stderr=PIPE)
        process.communicate()
        return process.stdout or process.stderr

    def test_cci_entry_point(self):
        assert self._popen("cci")

    def test_snowfakery_entry_point(self):
        assert self._popen("snowfakery")

    def test_bad_entry_point(self):
        with pytest.raises(FileNotFoundError):
            assert not self._popen("zomboxyzzy")
