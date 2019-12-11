from PySide2 import QtCore, QtWidgets

class Completer(QtWidgets.QCompleter):
    def splitPath(self, path):
        return path.split(' ')

    def pathFromIndex(self, index):
        result = []
        while index.isValid():
            result = [self.model().data(index, QtCore.Qt.DisplayRole)] + result
            index = index.parent()
        r = ' '.join(result)
        return r