from os import path
from datetime import datetime
from PySide2 import QtWidgets, QtCore, QtUiTools

BASE_PATH = path.join(path.dirname(path.realpath(__file__)), "assets")
BASE_UI_FILES_PATH = path.join(BASE_PATH, "ui_files")
BASE_DEFAULT_LAYOUT_FILES_PATH = path.join(BASE_PATH, "default_layouts")

def getUIFilePath(uiFileName):
    return path.join(BASE_UI_FILES_PATH, uiFileName)

def getDefaultLayoutFilePath(layoutName):
    return path.join(BASE_DEFAULT_LAYOUT_FILES_PATH, layoutName)

def getMainSettingsPath():
    return path.join(BASE_PATH, "settings.ini")

def getLogFilePath():
    curDateAndTime = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    logFilename = f"{curDateAndTime}.log"

    return path.abspath(path.join("log_output", logFilename))

def loadUIFile(uiFileName):
    fullPath = getUIFilePath(uiFileName)

    uiFile = QtCore.QFile(fullPath)
    uiFile.open(QtCore.QFile.ReadOnly)
    loader = QtUiTools.QUiLoader()
    return loader.load(uiFile)