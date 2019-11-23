from PySide2 import QtCore, QtWidgets
import operator

class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent, entries, header, displayedKeys, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.entries = entries
        self.header = header
        self.displayedKeys = displayedKeys

    def getUID(self, rowIdx):
        return self.entries[rowIdx][0]

    def rowCount(self, parent):
        return len(self.entries)

    def columnCount(self, parent):
        return len(self.entries[0]) - 1 if len(self.entries) > 0 else 0 

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        return self.entries[index.row()][index.column() + 1]

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.header[col]
        return None

    def sort(self, col, order):
        # Sort table by given column number col
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries = sorted(self.entries, key=operator.itemgetter(col + 1))
        if order == QtCore.Qt.DescendingOrder:
            self.entries.reverse()
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def addEntry(self, entry):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries.append(entry)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def addEntries(self, entries):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries.extend(entries)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    """
    The heaeder won't be updated if the current header is equal to the new given header (order and value comparison).
    Note: Updating the header removes all entries.
    """
    def updateHeader(self, header, displayedKeys):
        if self.header != header:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.displayedKeys = displayedKeys
            self.entries = []
            self.header = header
            self.emit(QtCore.SIGNAL("layoutChanged()"))

    def clear(self):
        if len(self.entries) > 0:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.entries = []
            self.emit(QtCore.SIGNAL("layoutChanged()"))