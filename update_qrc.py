import subprocess
import os

curDir = os.path.dirname(os.path.abspath(__file__))
outputQrcPath = os.path.join(curDir, 'resources_qrc.py')
rccFilename = os.path.join(curDir, 'assets', 'resource_files', 'resources.qrc')

subprocess.call(f'pyside2-rcc "{rccFilename}" -o "{os.path.normpath(outputQrcPath)}"', shell=False)