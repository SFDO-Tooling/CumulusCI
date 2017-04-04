# -*- mode: python -*-

block_cipher = None
debug = False
single_file = True

a = Analysis(
    ['cci.py'],
    binaries=[],
    datas=[
        ('cumulusci/cumulusci.yml', 'cumulusci'),
        ('cumulusci/files/admin_profile.xml', 'cumulusci/files'),
        ('cumulusci/files/metadata_whitelist.txt', 'cumulusci/files'),
        (
            'cumulusci/tasks/metadata/metadata_map_manual.yml',
            'cumulusci/tasks/metadata',
        ),
        (
            'cumulusci/tasks/metadata/metadata_map.yml',
            'cumulusci/tasks/metadata',
        ),
    ],
    hiddenimports=[
        'cumulusci.core.flows',
        'cumulusci.core.keychain',
        'cumulusci.tasks.apextestsdb',
        'cumulusci.tasks.bulkdata',
        'cumulusci.tasks.command',
        'cumulusci.tasks.github',
        'cumulusci.tasks.metadata.package',
        'cumulusci.tasks.mrbelvedere',
        'cumulusci.tasks.push.tasks',
        'cumulusci.tasks.release_notes.task',
        'cumulusci.tasks.salesforce',
        'cumulusci.tasks.salesforcedx',
        'cumulusci.tasks.util',
    ],
    hookspath=[],
    runtime_hooks=['cci_rth.py'],
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
        debug=debug,
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
        debug=debug,
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
