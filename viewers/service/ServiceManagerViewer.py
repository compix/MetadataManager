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

logger = logging.getLogger(__name__)

class ServiceManagerViewer(DockWidget):
    def __init__(self, parentWindow, serviceRegistry):
        super().__init__("Services", parentWindow, asset_manager.getUIFilePath("services.ui"))

        self.serviceManager = serviceRegistry.serviceManager
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
        self.servicesTableWidget.setColumnCount(3)
        self.servicesTableWidget.setHorizontalHeaderLabels(['Name', 'Description', 'Status'])

        self.serviceFilterLineEdit : QtWidgets.QLineEdit = self.widget.serviceFilterLineEdit 
        self.serviceFilterLineEdit.returnPressed.connect(self.updateServiceList)

        self.registerServiceViewerClass(WatchDogService, WatchDogServiceViewer)
        
        self.updateServiceList()

        self.serviceManager.serviceStatusChangedEvent.subscribe(self.onServiceStatusChanged)

        self.setupServicesTableWidgetContextMenu()

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
            idx : QModelIndex = idx
            service = self.serviceManager.services[idx.row()]
            service.setActive(active)

    def onServicesTableWidgetContextMenu(self):
        self.servicesTableWidgetContextMenu.setEnabled(len(self.servicesTableWidget.selectedIndexes()) > 0)
        self.servicesTableWidgetContextMenu.exec_(QtGui.QCursor.pos())

    def onServiceStatusChanged(self, service: Service, status: ServiceStatus):
        self.updateServiceList()

    def registerServiceViewerClass(self, serviceClass, viewerClass):
        self.serviceViewerClassMap[serviceClass.__name__] = viewerClass

    def updateServiceList(self):
        self.servicesTableWidget.clear()
        self.servicesTableWidget.setRowCount(len(self.serviceManager.services))

        pattern = re.compile(self.serviceFilterLineEdit.text())

        for i in range(0, len(self.serviceManager.services)):
            service = self.serviceManager.services[i]
            if not re.search(pattern, service.name):
                continue

            nameItem = QtWidgets.QTableWidgetItem(service.name)
            descItem = QtWidgets.QTableWidgetItem(service.description)
            statusItem = QtWidgets.QTableWidgetItem(service.status.value)

            self.servicesTableWidget.setItem(i, 0, nameItem)
            self.servicesTableWidget.setItem(i, 1, descItem)
            self.servicesTableWidget.setItem(i, 2, statusItem)

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
                self.serviceManager.addServiceFromDict(serviceInfoDict)
            else:
               logger.warning(f'Could not find a viewer for service {serviceClassName}')
                
            self.updateServiceList()