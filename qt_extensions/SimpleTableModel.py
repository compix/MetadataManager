from PySide2 import QtCore, QtWidgets
import operator
from typing import List

class SimpleTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent, header, entries = []):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.entries = entries
        self.header = header

    def rowCount(self, parent):
        return len(self.entries)

    def columnCount(self, parent):
        return len(self.header)

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        return self.entries[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.header[col]
        return None

    def sort(self, col, order):
        # Sort table by given column number col
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries = sorted(self.entries, key=operator.itemgetter(col))
        if order == QtCore.Qt.DescendingOrder:
            self.entries.reverse()
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def addEntry(self, entry : List[str]):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries.append(entry)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def addEntries(self, entries : List[List[str]]):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries.extend(entries)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def removeRowAtIndex(self, idx):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries.pop(idx)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def replaceEntryAtRow(self, rowIdx, newEntry : List[str]):
        if rowIdx < len(self.entries):
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.entries[rowIdx] = newEntry
            self.emit(QtCore.SIGNAL("layoutChanged()"))

    def clear(self):
        if len(self.entries) > 0:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.entries = []
            self.emit(QtCore.SIGNAL("layoutChanged()"))