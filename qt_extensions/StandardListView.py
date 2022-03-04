from PySide2 import QtWidgets, QtCore, QtGui
import typing
from PySide2.QtGui import QStandardItemModel, QStandardItem

class StandardListView(object):
    def __init__(self, listView: QtWidgets.QListView) -> None:
        self.listView = listView

        self.model = QStandardItemModel()
        self.listView.setModel(self.model)

        self.listView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listView.customContextMenuRequested.connect(self.contextMenuEvent)
        
        self.clearAllAction: QtWidgets.QAction = None
        self.deleteSelectedAction: QtWidgets.QAction = None
        self.contextMenu = QtWidgets.QMenu(self.listView)
        self.entriesUnique = False
        self.currentEntries: typing.Set[str] = set()

    def setEntriesUnique(self, unique: bool):
        self.entriesUnique = unique

    @property
    def selectionModel(self) -> QtCore.QItemSelectionModel:
        return self.listView.selectionModel()

    def setCanClear(self, canClear: bool):
        if canClear:
            if not self.clearAllAction:
                self.clearAllAction = QtWidgets.QAction('Clear')
                self.clearAllAction.triggered.connect(self.clear)
                self.contextMenu.addAction(self.clearAllAction)
        else:
            if self.clearAllAction:
                self.clearAllAction.setParent(None)
                self.clearAllAction.deleteLater()
                self.clearAllAction = None

    def setCanDeleteSelected(self, canDelete: bool):
        if canDelete:
            if not self.deleteSelectedAction:
                self.deleteSelectedAction = QtWidgets.QAction('Delete Selected')
                self.deleteSelectedAction.triggered.connect(self.deleteSelected)
                self.contextMenu.addAction(self.deleteSelectedAction)
        else:
            if self.deleteSelectedAction:
                self.deleteSelectedAction.setParent(None)
                self.deleteSelectedAction.deleteLater()
                self.deleteSelectedAction = None

    def contextMenuEvent(self):
        self.contextMenu.exec_(QtGui.QCursor.pos())

    def clear(self):
        self.model.clear()
        self.currentEntries.clear()

    def deleteSelected(self):
        selectionModel = self.listView.selectionModel()

        for rowIdx in selectionModel.selectedRows():
            self.currentEntries.remove(self.model.item(rowIdx.row()).text())
            self.model.removeRow(rowIdx.row())

    def addRow(self, txt: str):
        if self.entriesUnique and txt in self.currentEntries:
            return

        self.model.appendRow(QStandardItem(txt))
        self.currentEntries.add(txt)

    def addRows(self, rows: typing.List[str]):
        for row in rows:
            self.addRow(row)
            
    def setRows(self, rows: typing.List[str]):
        self.clear()
        self.addRows(rows)

    def yieldAllRowValues(self) -> typing.Iterator[str]:
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            yield item.text()

    def getAllRowValues(self) -> typing.List[str]:
        values = []
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            values.append(item.text())

        return values

    def yieldSelectedRowValues(self) -> typing.Iterator[str]:
        for rowIdx in self.selectionModel.selectedRows():
            yield self.model.item(rowIdx.row()).text()

    def getSelectedRowValues(self) -> typing.List[str]:
        return [v for v in self.yieldSelectedRowValues()]