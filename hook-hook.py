from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['PySide2.QtXml', 'VisualScripting.NodeGraphQt'] + \
                collect_submodules('table') + \
                collect_submodules('VisualScripting') + \
                collect_submodules('qt_extensions') + \
                collect_submodules('plugins') + \
                collect_submodules('zipping') + \
                collect_submodules('animation')