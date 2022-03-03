import typing
from qt_extensions.FlowLayout import FlowLayout
from PySide2 import QtWidgets
import asset_manager

class TagContainer(object):
    def __init__(self, tag: str, frame: QtWidgets.QFrame) -> None:
        self.tag = tag
        self.frame = frame

class TagsView(object):
    def __init__(self, knownTags: typing.List[str], currentTags: typing.List[str] = None) -> None:
        self.tagContainers: typing.List[TagContainer] = [] 
        self.layout = FlowLayout()

        self.tagComboBox = QtWidgets.QComboBox()
        self.tagComboBox.setEditable(True)
        self.tagComboBox.setMinimumWidth(200)
        self.comboBoxLayout = QtWidgets.QHBoxLayout()
        self.comboBoxLayout.addWidget(self.tagComboBox)
        tagAddButton = QtWidgets.QPushButton('')
        tagAddButton.setIcon(asset_manager.getPlusIcon())
        self.comboBoxLayout.addWidget(tagAddButton)
        self.comboBoxFrame = QtWidgets.QFrame()
        self.comboBoxFrame.setLayout(self.comboBoxLayout)

        self.layout.addWidget(self.comboBoxFrame)

        self.tagComboBox.addItems(knownTags)
        tagAddButton.clicked.connect(self.onAddTag)
        self.tagComboBox.lineEdit().returnPressed.connect(self.onAddTag)

        self.addTags(currentTags)

    @property
    def tags(self) -> typing.List[str]:
        return [c.tag for c in self.tagContainers]

    def addTags(self, tags: typing.List[str]):
        item = self.layout.takeAt(len(self.layout.itemList)-1)

        for tag in tags or []:
            label = QtWidgets.QLabel(tag)
            delButton = QtWidgets.QPushButton()
            delButton.setIcon(asset_manager.getDeleteIcon())
            self.registerDeleteTag(delButton, tag)
            layout = QtWidgets.QHBoxLayout()
            layout.addWidget(label)
            layout.addWidget(delButton)
            frame = QtWidgets.QFrame()
            frame.setLayout(layout)

            self.tagContainers.append(TagContainer(tag, frame))
            self.layout.addWidget(frame)

        self.layout.addItem(item)

    def registerDeleteTag(self, deleteButton: QtWidgets.QPushButton, tag: str):
        deleteButton.clicked.connect(lambda: self.onDeleteTag(tag))

    def onDeleteTag(self, tag: str):
        idxToDelete = None
        for i in range(0, len(self.tagContainers)):
            if self.tagContainers[i].tag == tag:
                idxToDelete = i
                break

        if not idxToDelete is None:
            tagContainer = self.tagContainers.pop(idxToDelete)
            self.layout.removeWidget(tagContainer.frame)
            tagContainer.frame.deleteLater()

    def onAddTag(self):
        tag = self.tagComboBox.currentText()
        if not tag or tag in [c.tag for c in self.tagContainers]:
            return
        
        self.addTags([tag])