import os
import zipfile

def zipDir(path: str, zipFilename: str):
    filenames = [os.path.join(root,fn) for root,_,filenames in os.walk(path) for fn in filenames]
    with zipfile.ZipFile(zipFilename, 'w', zipfile.ZIP_DEFLATED) as zipFile:
        for f in filenames:
            zipFile.write(f, os.path.relpath(f, path))