from PySide2.QtCore import QModelIndex
from MetadataManagerCore.service.WatchDogService import WatchDogService
from PySide2.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from viewers.service.WatchDogServiceViewer import WatchDogServiceViewer
from viewers.service.ServiceViewer import ServiceViewer
from MetadataManagerCore.service.Service import Service, ServiceStatus
from qt_extensions.DockWidget import DockWidget
import asset_manager
from PySide2 import QtWidgets, QtGui
from MetadataManagerCore.service.ServiceManager import ServiceManager
import re
from qt_extensions import qt_util
import logging
from MetadataManagerCore.service.ServiceInfo import ServiceInfo

logger = logging.getLogger(__name__)

class ServiceProcessHeader(object):
    info = [
        ('_id', 'ID'),
        ('name', 'Service Name'),
        ('status', 'Status'),
        ('hostname', 'Hostname'),
        ('pid', 'PID')
    ]

    @staticmethod
    def count() -> int:
        return len(ServiceProcessHeader.info)

    @staticmethod
    def keyAt(idx: int) -> str:
        return ServiceProcessHeader.info[idx][0]

    @staticmethod
    def headerLabels():
        return [v[1] for v in ServiceProcessHeader.info]
    
    @staticmethod
    def keys():
        return [v[0] for v in ServiceProcessHeader.info]

class ServiceManagerViewer(DockWidget):
    def __init__(self, parentWindow, serviceRegistry):
        super().__init__("Services", parentWindow, asset_manager.getUIFilePath("services.ui"))

        self.serviceManager: ServiceManager = serviceRegistry.serviceManager
        self.serviceRegistry = serviceRegistry
        # Maps service class to viewer
        self.serviceViewerClassMap : dict = dict()
        self.currentServiceViewer : ServiceViewer = None
        
        menuBar = QtWidgets.QMenuBar()
        fileMenu = QtWidgets.QMenu("File")
        menuBar.addMenu(fileMenu)

        self.newServiceAction = QtWidgets.QAction("New Service")
        self.newServiceAction.setShortcut(QtGui.QKeySequence.New)
        self.newServiceAction.triggered.connect(self.onCreateNewService)
        fileMenu.addAction(self.newServiceAction)
        
        self.widget.mainFrame.layout().insertWidget(0, menuBar)

        self.servicesTableWidget : QtWidgets.QTableWidget = self.widget.servicesTableWidget

        self.serviceFilterLineEdit : QtWidgets.QLineEdit = self.widget.serviceFilterLineEdit 
        self.serviceFilterLineEdit.returnPressed.connect(self.updateServiceList)

        self.registerServiceViewerClass(WatchDogService, WatchDogServiceViewer)
        
        self.updateServiceList()

        self.serviceManager.onServiceActiveStatusChanged.subscribe(lambda _: qt_util.runInMainThread(self.updateServiceList))
        self.serviceManager.onServiceAdded.subscribe(lambda _: qt_util.runInMainThread(self.updateServiceList))

        self.setupServicesTableWidgetContextMenu()

        self.setupServiceProcessTableWidget()
        self.updateServiceProcessTable()

        self.serviceManager.onServiceProcessChanged.subscribe(lambda _: self.updateServiceProcessTable())

    def setupServiceProcessTableWidget(self):
        self.serviceProcessesTableWidget : QtWidgets.QTableWidget = self.widget.serviceProcessesTableWidget

    def getAllServiceProcessInfos(self):
        serviceProcessInfos = []
        for serviceMonitor in self.serviceManager.serviceMonitors:
            for serviceProcessInfo in serviceMonitor.serviceProcessInfos:
                serviceProcessInfos.append(serviceProcessInfo)

        return serviceProcessInfos

    def updateServiceProcessTable(self):
        self.serviceProcessesTableWidget.clear()
        serviceProcessInfos = self.getAllServiceProcessInfos()
        self.serviceProcessesTableWidget.setRowCount(len(serviceProcessInfos))

        headerLabels = ServiceProcessHeader.headerLabels()
        self.serviceProcessesTableWidget.setColumnCount(len(headerLabels))
        self.serviceProcessesTableWidget.setHorizontalHeaderLabels(headerLabels)

        pattern = re.compile(self.serviceFilterLineEdit.text())

        for i in range(0, len(serviceProcessInfos)):
            serviceProcessInfo = serviceProcessInfos[i]
            serviceProcessId = serviceProcessInfo.id
            if serviceProcessId == None:
                logger.error(f'No service process id available.')
                continue

            if not re.search(pattern, serviceProcessId):
                continue
            
            for keyIdx in range(0, ServiceProcessHeader.count()):
                key = ServiceProcessHeader.keyAt(keyIdx)
                value = str(serviceProcessInfo.get(key))
                item = QtWidgets.QTableWidgetItem(value if value else 'None')
                self.serviceProcessesTableWidget.setItem(i, keyIdx, item)

    def setupServicesTableWidgetContextMenu(self):
        self.servicesTableWidgetContextMenu = QtWidgets.QMenu(self.widget)

        enableAction = QtWidgets.QAction('Enable', self.widget)
        disableAction = QtWidgets.QAction('Disable', self.widget)
        self.servicesTableWidgetContextMenu.addAction(enableAction)
        self.servicesTableWidgetContextMenu.addAction(disableAction)

        enableAction.triggered.connect(lambda: self.setSelectedServicesActive(True))
        disableAction.triggered.connect(lambda: self.setSelectedServicesActive(False))

        self.servicesTableWidget.customContextMenuRequested.connect(self.onServicesTableWidgetContextMenu)

    def setSelectedServicesActive(self, active: bool):
        for idx in self.servicesTableWidget.selectedIndexes():
            idx : int = idx.row()

            serviceName = self.servicesTableWidget.item(idx, 0).text()
            self.serviceManager.setServiceActive(serviceName, active)

    def onServicesTableWidgetContextMenu(self):
        self.servicesTableWidgetContextMenu.setEnabled(len(self.servicesTableWidget.selectedIndexes()) > 0)
        self.servicesTableWidgetContextMenu.exec_(QtGui.QCursor.pos())

    def registerServiceViewerClass(self, serviceClass, viewerClass):
        self.serviceViewerClassMap[serviceClass.__name__] = viewerClass

    def updateServiceList(self):
        self.servicesTableWidget.clear()
        self.servicesTableWidget.setRowCount(len(self.serviceManager.serviceMonitors))

        headerLabels = ['Name', 'Description', 'Status']
        self.servicesTableWidget.setColumnCount(len(headerLabels))
        self.servicesTableWidget.setHorizontalHeaderLabels(headerLabels)

        pattern = re.compile(self.serviceFilterLineEdit.text())

        for i in range(0, len(self.serviceManager.serviceMonitors)):
            serviceMonitor = self.serviceManager.serviceMonitors[i]
            serviceName = serviceMonitor.serviceName
            if serviceName == None:
                logger.error(f'No service name available in service monitor.')
                continue

            if not re.search(pattern, serviceName):
                continue

            nameItem = QtWidgets.QTableWidgetItem(serviceName)
            descItem = QtWidgets.QTableWidgetItem(serviceMonitor.serviceDescription)
            activeStatusItem = QtWidgets.QTableWidgetItem('Enabled' if serviceMonitor.serviceActive else 'Disabled')

            self.servicesTableWidget.setItem(i, 0, nameItem)
            self.servicesTableWidget.setItem(i, 1, descItem)
            self.servicesTableWidget.setItem(i, 2, activeStatusItem)

    def extendNewServiceView(self, newServiceWidget : QWidget, serviceClassName : str):
        qt_util.clearContainer(newServiceWidget.serviceExtensionFrame.layout())
        self.currentServiceViewer = None

        serviceViewerClass = self.serviceViewerClassMap.get(serviceClassName)
        if not serviceViewerClass:
            serviceViewerClass = ServiceViewer

        serviceViewer = serviceViewerClass(self.serviceRegistry)
        if serviceViewer.widget:
            newServiceWidget.serviceExtensionFrame.layout().addWidget(serviceViewer.widget)

        self.currentServiceViewer = serviceViewer

    def onCreateNewService(self):
        self.currentServiceViewer = None

        # Open new service dialog
        newServiceWidget = asset_manager.loadUIFile('newService.ui')
        dialog = QtWidgets.QDialog(self.widget)
        dialog.setWindowTitle('New Service')
        dialog.setLayout(QVBoxLayout())
        dialog.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        dialog.layout().addWidget(newServiceWidget)

        # Setup the service type combo box
        serviceTypeComboBox : QtWidgets.QComboBox = newServiceWidget.serviceTypeComboBox
        serviceTypeComboBox.clear()
        for serviceClass in self.serviceManager.serviceClasses:
            serviceTypeComboBox.addItem(serviceClass.__name__)

        newServiceWidget.createServiceButton.clicked.connect(lambda: dialog.accept())

        self.extendNewServiceView(newServiceWidget, serviceTypeComboBox.currentText())
        newServiceWidget.serviceTypeComboBox.currentTextChanged.connect(lambda serviceClassName: self.extendNewServiceView(newServiceWidget, serviceClassName))

        for status in [ServiceStatus.Running, ServiceStatus.Disabled]:
            newServiceWidget.initialStatusComboBox.addItem(status.value)

        if dialog.exec_():
            serviceClassName = newServiceWidget.serviceTypeComboBox.currentText()
            name = newServiceWidget.nameLineEdit.text()
            desc = newServiceWidget.descriptionLineEdit.text()
            initialStatus = ServiceStatus(newServiceWidget.initialStatusComboBox.currentText())

            if self.currentServiceViewer:
                serviceInfoDict = self.currentServiceViewer.getServiceInfoDict(serviceClassName, name, desc, initialStatus)
                self.serviceManager.addServiceFromDict(serviceInfoDict, newService=True)
            else:
               logger.warning(f'Could not find a viewer for service {serviceClassName}')
                
            self.updateServiceList()