# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
import zipfile

spec_root = os.path.abspath(SPECPATH)

a = Analysis(['metadata_viewer.py'],
             pathex=[spec_root, os.path.join(spec_root, 'VisualScripting')],
             binaries=[],
             datas=[('VisualScripting/assets', 'VisualScripting/assets'), ('assets', 'assets'), ('custom','custom'),
                    ('VisualScripting_SaveData', 'VisualScripting_SaveData'),
                    ('plugins', 'plugins'),
                    ('MetadataManagerCore/third_party_integrations/deadline/plugins', 'MetadataManagerCore/third_party_integrations/deadline/plugins')],
             hiddenimports=['PySide2.QtXml', 'VisualScripting.NodeGraphQt', 'openpyxl'],
             hookspath=[spec_root],
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
          [],
          exclude_binaries=True,
          name='metadata_manager',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='MetadataManager')

def zipDir(path: str, zipFilename: str):
    filenames = [os.path.join(root,fn) for root,_,filenames in os.walk(path) for fn in filenames]
    with zipfile.ZipFile(zipFilename, 'w', zipfile.ZIP_DEFLATED) as zipFile:
        for f in filenames:
            zipFile.write(f, os.path.relpath(f, path))

distPath = os.path.join(spec_root, 'dist')
zipTargetFolder = os.path.join(distPath, 'MetadataManager')
print('Zipping ' + zipTargetFolder)
zipDir(zipTargetFolder, os.path.join(distPath, 'MetadataManager.zip'))