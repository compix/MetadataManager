from viewers.PluginManagerViewer import PluginManagerViewer
from VisualScripting.VisualScriptingViewer import VisualScriptingViewer
from viewers.DocumentSearchFilterViewer import DocumentSearchFilterViewer
from viewers.ActionsViewer import ActionsViewer
from viewers.SettingsViewer import SettingsViewer
from viewers.PreviewViewer import PreviewViewer
from viewers.Inspector import Inspector
from viewers.HostProcessViewer import HostProcessViewer
from viewers.EnvironmentManagerViewer import EnvironmentManagerViewer
from viewers.DeadlineServiceViewer import DeadlineServiceViewer
from viewers.CollectionViewer import CollectionViewer
from viewers.ActionManagerViewer import ActionManagerViewer

import typing

if typing.TYPE_CHECKING:
    from MainWindowManager import MainWindowManager

class ViewerRegistry(object):
    def __init__(self) -> None:
        super().__init__()

        self.mainWindowManager: 'MainWindowManager' = None
        self.settingsViewer: SettingsViewer = None
        self.previewViewer: PreviewViewer = None
        self.inspector: Inspector = None
        self.hostProcessViewer: HostProcessViewer = None
        self.environmentManagerViewer: EnvironmentManagerViewer = None
        self.documentSearchFilterViewer: DocumentSearchFilterViewer = None
        self.deadlineServiceViewer: DeadlineServiceViewer = None
        self.collectionViewer: CollectionViewer = None
        self.actionsViewer: ActionsViewer = None
        self.actionManagerViewer: ActionManagerViewer = None
        self.pluginManagerViewer: PluginManagerViewer = None

        self.visualScriptingViewer: VisualScriptingViewer = None