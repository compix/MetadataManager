from PySide2 import QtWidgets, QtCore, QtGui
import typing
from PySide2.QtGui import QStandardItemModel, QStandardItem
from MetadataManagerCore.Event import Event

class StandardListView(QtCore.QObject):
    def __init__(self, listView: QtWidgets.QListView) -> None:
        super().__init__()
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

        self.listView.installEventFilter(self)

        self.listView.setDragEnabled(True)
        self.listView.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)

        self.onAddedRowValue = Event()
        self.onDeletedRowValues = Event()

        self.curFilterText = ''
        self.curFilter = lambda value, filterText: filterText in value
        self.showDeleteConfirmationDialog = False

    def setFilter(self, filterFunction: typing.Callable[[str,str],bool]):
        self.curFilter = filterFunction
        self.applyFilter(self.curFilterText)

    def applyFilter(self, filterText: str):
        self.curFilterText = filterText

        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            self.listView.setRowHidden(i, not self.curFilter(item.text(), self.curFilterText))

    def setAllowFileDrop(self, allow: bool):
        self.listView.setDragEnabled(allow)

    def setEntriesUnique(self, unique: bool):
        self.entriesUnique = unique

    def eventFilter(self, object, event: QtCore.QEvent):
        if object is self.listView:
            if event.type() == QtCore.QEvent.DragEnter:
                mimeData: QtCore.QMimeData = event.mimeData()

                if mimeData.hasUrls():
                    event.accept()
                else:
                    event.ignore()

                return True
            if event.type() == QtCore.QEvent.Drop:
                mimeData: QtCore.QMimeData = event.mimeData()

                if mimeData.hasUrls():
                    for url in mimeData.urls():
                        self.addRow(url.toLocalFile())

                    event.accept()
                else:
                    event.ignore()

                return True

            return False

        return False

    @property
    def selectionModel(self) -> QtCore.QItemSelectionModel:
        return self.listView.selectionModel()

    def setCanClear(self, canClear: bool):
        if canClear:
            if not self.clearAllAction:
                self.clearAllAction = QtWidgets.QAction('Clear')
                self.clearAllAction.triggered.connect(self.onClearClick)
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

    def onClearClick(self):
        if self.showDeleteConfirmationDialog:
            ret = QtWidgets.QMessageBox.question(self.listView, 
                f"Delete Confirmation", f"Clear all entries?")
            if ret != QtWidgets.QMessageBox.Yes:
                return

        self.clear()

    def clear(self, triggerDeleteEvent=True):
        values = self.getAllRowValues()
        self.model.clear()
        self.currentEntries.clear()

        if triggerDeleteEvent and values and len(values) > 0:
            self.onDeletedRowValues(values)

    def deleteSelected(self):
        if self.showDeleteConfirmationDialog:
            ret = QtWidgets.QMessageBox.question(self.listView, 
                f"Delete Confirmation", f"Delete selected entries?")
            if ret != QtWidgets.QMessageBox.Yes:
                return

        selectedValues = []
        selectionModel = self.listView.selectionModel()
        
        selectedIndices = []

        for row in selectionModel.selectedRows():
            value = self.model.item(row.row()).text()
            selectedValues.append(value)
            self.currentEntries.remove(value)
            selectedIndices.append(row.row())
        
        for rowIdx in sorted(selectedIndices, reverse=True):
            self.model.removeRow(rowIdx)
        
        if len(selectedValues) > 0:
            self.onDeletedRowValues(selectedValues)

    def addRow(self, txt: str):
        if self.entriesUnique and txt in self.currentEntries:
            return

        self.model.appendRow(QStandardItem(txt))
        self.currentEntries.add(txt)
        self.onAddedRowValue(txt)

        self.listView.setRowHidden(self.model.rowCount()-1, not self.curFilter(txt, self.curFilterText))

    def addRows(self, rows: typing.List[str]):
        for row in rows:
            self.addRow(row)
            
    def setRows(self, rows: typing.List[str]):
        self.clear()
        self.addRows(rows)

    def yieldRowValuesFiltered(self) -> typing.Iterator[str]:
        for i in range(self.model.rowCount()):
            if not self.listView.isRowHidden(i):
                item = self.model.item(i)
                yield item.text()

    def getRowValuesFiltered(self) -> typing.List[str]:
        return [v for v in self.yieldRowValuesFiltered()]

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