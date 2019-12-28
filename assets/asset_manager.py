from os import path

BASE_PATH = path.dirname(path.realpath(__file__))
BASE_UI_FILES_PATH = path.join(BASE_PATH, "ui_files")
BASE_DEFAULT_LAYOUT_FILES_PATH = path.join(BASE_PATH, "default_layouts")

def getUIFilePath(uiFileName):
    return path.join(BASE_UI_FILES_PATH, uiFileName)

def getDefaultLayoutFilePath(layoutName):
    return path.join(BASE_DEFAULT_LAYOUT_FILES_PATH, layoutName)

def getMainSettingsPath():
    return path.join(BASE_PATH, "settings.ini")