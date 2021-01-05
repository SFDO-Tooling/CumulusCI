# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

block_cipher = None

datas = [
    ('cumulusci/version.txt', 'cumulusci'),
    ('cumulusci/cumulusci.yml', 'cumulusci'),
] + copy_metadata("keyring")
a = Analysis(['cumulusci/__main__.py'],
             pathex=['/Users/davisagli/Work/CumulusCI'],
             binaries=[],
             datas=datas,
             hiddenimports=collect_submodules("keyring.backends"),
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='cci',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
