# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

spec_root = os.path.abspath(SPECPATH)

a = Analysis(['launcher.py'],
             pathex=[os.path.join(spec_root, '.env')],
             binaries=[],
             datas=[],
             hiddenimports=[],
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
          name='launcher',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

import shutil

privateFolder = os.path.join(spec_root, '..', 'assets', 'private')
launcherJsonFilename = os.path.join(privateFolder, 'launcher.json')
if not os.path.exists(launcherJsonFilename):
    launcherJsonFilename = os.path.join(spec_root, 'launcher.json')

shutil.copy(launcherJsonFilename, os.path.join(spec_root, '..', 'dist', 'launcher.json'))