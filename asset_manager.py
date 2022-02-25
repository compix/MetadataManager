from os import path
from datetime import datetime
from PySide2 import QtWidgets, QtCore, QtUiTools
from PySide2.QtWidgets import QDialog
from PySide2.QtCore import Qt

BASE_PLUGIN_PATH = path.join(path.dirname(path.realpath(__file__)), "plugins")
BASE_PATH = path.join(path.dirname(path.realpath(__file__)), "assets")
BASE_UI_FILES_PATH = path.join(BASE_PATH, "ui_files")
BASE_DEFAULT_LAYOUT_FILES_PATH = path.join(BASE_PATH, "default_layouts")

def getUIFilePath(uiFileName):
    return path.join(BASE_UI_FILES_PATH, uiFileName)

def getDefaultLayoutFilePath(layoutName):
    return path.join(BASE_DEFAULT_LAYOUT_FILES_PATH, layoutName)

def getPrivateFolder():
    return path.join(BASE_PATH, "private")

def getMainSettingsPath():
    privateSettingsFilename = path.join(getPrivateFolder(), "settings.ini")
    if path.exists(privateSettingsFilename):
        return privateSettingsFilename
        
    return path.join(BASE_PATH, "settings.ini")

def getLogFilePath():
    curDateAndTime = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    logFilename = f"{curDateAndTime}.log"

    return path.abspath(path.join("log_output", logFilename))

def getImagePath(imageBasename: str):
    return path.join(BASE_PATH, 'images', imageBasename)

def loadUIFileAbsolutePath(path: str):
    uiFile = QtCore.QFile(path)
    uiFile.open(QtCore.QFile.ReadOnly)
    loader = QtUiTools.QUiLoader()
    return loader.load(uiFile)

def loadDialogAbsolutePath(path: str, fixedSize=True) -> QDialog:
    dialog = loadUIFileAbsolutePath(path)
    dialog.setWindowFlags(Qt.Dialog | (Qt.MSWindowsFixedSizeDialogHint if fixedSize else 0))
    return dialog

def loadUIFile(relUIPath):
    return loadUIFileAbsolutePath(getUIFilePath(relUIPath))

def loadDialog(relUIPath, fixedSize=True) -> QDialog:
    return loadDialogAbsolutePath(getUIFilePath(relUIPath), fixedSize=fixedSize)

def getPluginUIFilePath(pluginName: str, uiFileName: str):
    return path.join(BASE_PLUGIN_PATH, pluginName, uiFileName)