from PySide2 import QtWidgets
import os
from RenderingPipelinePlugin import PipelineKeys
from MetadataManagerCore.environment.Environment import Environment
from RenderingPipelinePlugin.PipelineType import PipelineType
import re

from dist.MetadataManager.plugins.RenderingPipelinePlugin.NamingConvention import extractNameFromNamingConvention

def connectRelativeProjectFolderSelection(dialog, lineEdit: QtWidgets.QLineEdit, button: QtWidgets.QPushButton, initialDir=""):
    def onSelect():
        dirName = QtWidgets.QFileDialog.getExistingDirectory(dialog, "Open", initialDir)
        if dirName != None and dirName != "":
            baseProjectFolder = dialog.baseProjectFolderEdit.text()
            if os.path.normpath(dirName).startswith(os.path.normpath(baseProjectFolder)):
                dirName = os.path.relpath(dirName, baseProjectFolder)

            lineEdit.setText(dirName)
    
    button.clicked.connect(onSelect)

def connectRelativeProjectFileSelection(dialog, lineEdit: QtWidgets.QLineEdit, button: QtWidgets.QPushButton, filter=""):
    def onSelect():
        filename,_ = QtWidgets.QFileDialog.getOpenFileName(dialog, "Open", "", filter=filter)
        if filename:
            baseProjectFolder = dialog.baseProjectFolderEdit.text()
            if os.path.normpath(filename).startswith(os.path.normpath(baseProjectFolder)):
                filename = os.path.relpath(filename, baseProjectFolder)

            lineEdit.setText(filename)
    
    button.clicked.connect(onSelect)

def stripBaseFolder(v: str):
    base = '${' + PipelineKeys.BaseFolder + '}'
    if v.startswith(base):
        return v.lstrip(base).lstrip('/').lstrip('\\')

    return v

class EnvironmentEntry(object):
    def __init__(self, envKey: str, widget: QtWidgets.QWidget, pipelineType: PipelineType = None, pipelineComboBox: QtWidgets.QComboBox = None) -> None:
        super().__init__()

        self.envKey = envKey
        self.widget = widget
        self.pipelineType = pipelineType
        self.pipelineComboBox = pipelineComboBox

    def saveValue(self, environment: Environment):
        pass

    def loadValue(self, environment: Environment):
        pass

    def isApplicable(self):
        if self.pipelineType and self.pipelineComboBox:
            return self.pipelineType == PipelineType(self.pipelineComboBox.currentText())

        return True

    def verify(self):
        pass

class LineEditEnvironmentEntry(EnvironmentEntry):
    def __init__(self, envKey: str, widget: QtWidgets.QWidget, pipelineType: PipelineType = None, 
                 pipelineComboBox: QtWidgets.QComboBox = None, regexPattern = None, valueType=str, fallbackValue=None) -> None:
        super().__init__(envKey, widget, pipelineType=pipelineType, pipelineComboBox=pipelineComboBox)

        self.regexPattern = regexPattern
        self.valueType = valueType
        self.fallbackValue = fallbackValue

    def saveValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        try:
            environment.settings[self.envKey] = self.valueType(edit.text())
        except:
            environment.settings[self.envKey] = self.fallbackValue

    def loadValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        try:
            value = self.valueType(environment.settings.get(self.envKey))
        except:
            value = self.fallbackValue

        edit.setText('' if value is None else str(value))

    def verify(self):
        if self.regexPattern:
            valid = re.search(self.regexPattern, self.widget.text()) != None

            if not valid:
                raise RuntimeError(f'The text of {self.envKey} is not valid. The supported format is: {self.regexPattern}')

class DeadlineTimeoutEnvironmentEntry(LineEditEnvironmentEntry):
    def __init__(self, envKey: str, widget: QtWidgets.QWidget, pipelineType: PipelineType = None, 
                 pipelineComboBox: QtWidgets.QComboBox = None, regexPattern=None, valueType=str, fallbackValue=None) -> None:
        super().__init__(envKey, widget, pipelineType=pipelineType, pipelineComboBox=pipelineComboBox, 
                         regexPattern=regexPattern, valueType=valueType, fallbackValue=fallbackValue)

        widget.setToolTip('Timeout in minutes. There is no timeout if left empty.')

class CheckBoxEnvironmentEntry(EnvironmentEntry):
    def saveValue(self, environment: Environment):
        checkbox: QtWidgets.QCheckBox = self.widget
        environment.settings[self.envKey] = checkbox.isChecked()

    def loadValue(self, environment: Environment):
        checkbox: QtWidgets.QCheckBox = self.widget
        checkbox.setChecked(environment.settings.get(self.envKey, False))

class ComboBoxEnvironmentEntry(EnvironmentEntry):
    def saveValue(self, environment: Environment):
        cb: QtWidgets.QComboBox = self.widget
        environment.settings[self.envKey] = cb.currentText()

    def loadValue(self, environment: Environment):
        cb: QtWidgets.QComboBox = self.widget
        cb.setCurrentText(environment.settings.get(self.envKey))

class DeadlinePoolComboBoxEnvironmentEntry(ComboBoxEnvironmentEntry):
    def loadValue(self, environment: Environment):
        value = environment.settings.get(self.envKey)
        cb: QtWidgets.QComboBox = self.widget
        hasValue = False
        for i in range(cb.count()):
            if cb.itemText(i) == value:
                hasValue = True
                break
        
        if not hasValue and value:
            cb.addItem(value)
        
        if value:
            cb.setCurrentText(value)
        else:
            cb.setCurrentIndex(0)

class NamingEnvironmentEntry(LineEditEnvironmentEntry):
    def saveValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        environment.settings[self.envKey] = edit.text()

    def loadValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        edit.setText(environment.settings.get(self.envKey))

    def verify(self):
        namingRegexPattern = '^([\w\d# /\-]*(\[[\w\d# /\-]*\])*)*$'
        namingConvention = self.widget.text()
        valid = re.search(namingRegexPattern, namingConvention) != None

        if not valid:
            raise RuntimeError(f'The naming convetion for {self.envKey} is not valid.')

class ProjectSubFolderEnvironmentEntry(LineEditEnvironmentEntry):
    def __init__(self, envKey: str, lineEdit: QtWidgets.QLineEdit, renderingPipelineViewer, 
                 folderSelectButton: QtWidgets.QPushButton, pipelineType: PipelineType = None, pipelineComboBox: QtWidgets.QComboBox = None) -> None:
        super().__init__(envKey, lineEdit, pipelineType=pipelineType, pipelineComboBox=pipelineComboBox)

        connectRelativeProjectFolderSelection(renderingPipelineViewer.dialog, lineEdit, folderSelectButton)

        self.renderingPipelineViewer = renderingPipelineViewer

    def saveValue(self, environment: Environment):
        baseProjectFolder = self.renderingPipelineViewer.dialog.baseProjectFolderEdit.text()
        folder = self.widget.text()
        fullpath = folder
        if os.path.isabs(fullpath):
            environment.settings[self.envKey] = fullpath.replace('\\', '/')
        else:
            fullpath = os.path.join(baseProjectFolder, folder)
            base = '${' + PipelineKeys.BaseFolder + '}'
            environment.settings[self.envKey] = os.path.normpath(fullpath).replace(os.path.normpath(baseProjectFolder), base).replace('\\', '/')

        try:
            os.makedirs(fullpath, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f'Failed to create subfolder for key {self.envKey}: {str(e)}')

    def loadValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        edit.setText(stripBaseFolder(environment.settings.get(self.envKey, '')))

class ProjectFileEnvironmentEntry(LineEditEnvironmentEntry):
    def __init__(self, envKey: str, lineEdit: QtWidgets.QLineEdit, renderingPipelineViewer, 
                 fileSelectButton: QtWidgets.QPushButton, pipelineType: PipelineType = None, pipelineComboBox: QtWidgets.QComboBox = None, fileFilter="") -> None:
        super().__init__(envKey, lineEdit, pipelineType=pipelineType, pipelineComboBox=pipelineComboBox)

        connectRelativeProjectFileSelection(renderingPipelineViewer.dialog, lineEdit, fileSelectButton, filter=fileFilter)

        self.renderingPipelineViewer = renderingPipelineViewer

    def saveValue(self, environment: Environment):
        baseProjectFolder = self.renderingPipelineViewer.dialog.baseProjectFolderEdit.text()
        filename = self.widget.text()
        fullpath = filename
        if os.path.isabs(fullpath):
            environment.settings[self.envKey] = fullpath.replace('\\', '/')
        else:
            fullpath = os.path.join(baseProjectFolder, filename)
            base = '${' + PipelineKeys.BaseFolder + '}'
            environment.settings[self.envKey] = os.path.normpath(fullpath).replace(os.path.normpath(baseProjectFolder), base).replace('\\', '/')

        try:
            os.makedirs(os.path.dirname(fullpath), exist_ok=True)
        except Exception as e:
            raise RuntimeError(f'Failed to create subfolder for key {self.envKey}: {str(e)}')

    def loadValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        edit.setText(stripBaseFolder(environment.settings.get(self.envKey, '')))

    def getAbsoluteFilename(self):
        baseProjectFolder = self.renderingPipelineViewer.dialog.baseProjectFolderEdit.text()
        filename = self.widget.text()
        if os.path.isabs(filename):
            return filename.replace('\\', '/')
        else:
            return os.path.join(baseProjectFolder, filename).replace('\\', '/')