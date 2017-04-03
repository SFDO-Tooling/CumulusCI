# -*- mode: python -*-

block_cipher = None
single_file = True

a = Analysis(
    ['cci.py'],
    binaries=[],
    datas=[
        ('cumulusci/cumulusci.yml', 'cumulusci'),
        ('cumulusci/files/admin_profile.xml', 'cumulusci/files'),
    ],
    hiddenimports=[
        'cumulusci.core.flows',
        'cumulusci.core.keychain',
        'cumulusci.tasks.github',
        'cumulusci.tasks.salesforce',
        'cumulusci.tasks.util',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

if single_file:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name='cci',
        debug=False,
        strip=False,
        upx=True,
        console=True,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name='cci',
        debug=False,
        strip=False,
        upx=True,
        console=True,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        name='cci',
    )
