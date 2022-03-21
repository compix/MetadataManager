import typing
from qt_extensions.FlowLayout import FlowLayout
from PySide2 import QtWidgets, QtCore
import asset_manager
from MetadataManagerCore.Event import Event

class FlowItemContainer(object):
    def __init__(self, item: str, frame: QtWidgets.QFrame, userData=None) -> None:
        self.item = item
        self.frame = frame
        self.userData = userData

class FlowItemsView(object):
    """
    Multiselection in a flow layout.
    """
    def __init__(self, knownItems: typing.List[str], items: typing.List[str] = None) -> None:
        self.itemContainers: typing.List[FlowItemContainer] = [] 
        self.layout = FlowLayout()

        self.itemComboBox = QtWidgets.QComboBox()
        self.itemComboBox.setEditable(True)
        self.itemComboBox.setMinimumWidth(200)
        self.comboBoxLayout = QtWidgets.QHBoxLayout()
        self.comboBoxLayout.addWidget(self.itemComboBox)
        itemAddButton = QtWidgets.QPushButton('')
        itemAddButton.setIcon(asset_manager.getPlusIcon())
        itemAddButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.comboBoxLayout.addWidget(itemAddButton)
        self.comboBoxFrame = QtWidgets.QFrame()
        self.comboBoxFrame.setLayout(self.comboBoxLayout)
        self.comboBoxFrame.layout().setMargin(0)

        self.layout.addWidget(self.comboBoxFrame)

        self.itemComboBox.addItems(knownItems)
        itemAddButton.clicked.connect(self.onAddItem)
        self.itemComboBox.lineEdit().returnPressed.connect(self.onAddItem)

        self.addItems(items)

        self.onUpdate = Event()

    def clear(self):
        for tc in self.itemContainers:
            tc.frame.setParent(None)
            tc.frame.deleteLater()

        self.itemContainers.clear()
        self.onUpdate()

    def setKnownItems(self, items: typing.Iterable[str], userData: typing.List[typing.Any]=None):
        self.itemComboBox.clear()
        if userData:
            for i, item in enumerate(items):
                self.itemComboBox.addItem(item, userData[i])
        else:
            self.itemComboBox.addItems(items)

        self.onUpdate()

    @property
    def items(self) -> typing.List[str]:
        return [c.item for c in self.itemContainers]

    @property
    def userData(self) -> typing.List[typing.Any]:
        return [c.userData for c in self.itemContainers]

    def addItems(self, items: typing.List[str], userData: typing.List[typing.Any] = None):
        if not items:
            return
            
        lastItem = self.layout.takeAt(len(self.layout.itemList)-1)

        for i, item in enumerate(items or []):
            label = QtWidgets.QLabel(item)
            delButton = QtWidgets.QPushButton()
            delButton.setIcon(asset_manager.getDeleteIcon())
            self.registerDeleteItem(delButton, item)
            layout = QtWidgets.QHBoxLayout()
            layout.addWidget(label)
            layout.addWidget(delButton)
            frame = QtWidgets.QFrame()
            frame.setLayout(layout)
            frame.layout().setMargin(0)

            ud = userData[i] if userData else None
            self.itemContainers.append(FlowItemContainer(item, frame, ud))
            self.layout.addWidget(frame)

        self.layout.addItem(lastItem)
        self.onUpdate()

    def registerDeleteItem(self, deleteButton: QtWidgets.QPushButton, item: str):
        deleteButton.clicked.connect(lambda: self.onDeleteItem(item))

    def onDeleteItem(self, item: str):
        idxToDelete = None
        for i in range(0, len(self.itemContainers)):
            if self.itemContainers[i].item == item:
                idxToDelete = i
                break

        if not idxToDelete is None:
            itemContainer = self.itemContainers.pop(idxToDelete)
            self.layout.removeWidget(itemContainer.frame)
            itemContainer.frame.deleteLater()
            self.onUpdate()

    def onAddItem(self):
        item = self.itemComboBox.currentText()
        if not item or item.strip() == '' or item in [c.item for c in self.itemContainers]:
            return
        
        self.addItems([item], [self.itemComboBox.currentData()])