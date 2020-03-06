from VisualScripting.node_exec import code_generator
from VisualScriptingExtensions.document_action_nodes import DocumentActionNode
from MetadataManagerCore.actions.DocumentAction import DocumentAction
import os
import sys
import importlib
from MetadataManagerCore.actions.DocumentActionManager import DocumentActionManager

class CodeGenerator(code_generator.CodeGenerator):
    def __init__(self, actionManager=None):
        super().__init__()
        
        self.actionManager : DocumentActionManager = actionManager

    def setActionManager(self, actionManager):
        self.actionManager = actionManager

        graphNames = self.graphManager.availableGraphNames

        for graphName in graphNames:
            moduleName = self.graphManager.getModuleNameFromGraphName(graphName)
            pythonFile = self.graphManager.getPythonCodePath(graphName)
            pathonFileDir = os.path.dirname(pythonFile)

            if not pathonFileDir in sys.path:
                sys.path.append(pathonFileDir)

            try:
                execModule = importlib.import_module(moduleName)
                importlib.reload(execModule)
            except Exception as e:
                print(str(e))
            
            try:
                docAction = execModule.DocumentActionVS()
                self.actionManager.registerAction(docAction)
            except:
                pass


    def writeCodeLine(self, srcFile, codeLine, indent, suffix="\n"):
        srcFile.write(code_generator.makeCodeLine(codeLine, indent) + suffix)

    def generatePythonCode(self, graph, startNode, moduleName, targetFolder):
        srcFilePath = super().generatePythonCode(graph, startNode, moduleName, targetFolder)

        if isinstance(startNode, DocumentActionNode):
            with open(srcFilePath,"a+") as srcFile:
                srcFile.write("\n")

                srcFile.write(f"import {DocumentAction.__module__}\n\n")

                
                documentActionClassName = f"{DocumentAction.__module__}.{DocumentAction.__name__}"
                vsDocumentActionClassName = "DocumentActionVS"
                
                self.writeCodeLine(srcFile, f"class {vsDocumentActionClassName}({documentActionClassName}):", "")
                self.writeCodeLine(srcFile, "def execute(self, document):", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "execute(document)", code_generator.DEFAULT_INDENT + code_generator.DEFAULT_INDENT,suffix="\n\n")

                self.writeCodeLine(srcFile, "@property", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "def id(self):", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "return {!r}".format(moduleName), code_generator.DEFAULT_INDENT + code_generator.DEFAULT_INDENT)

                self.writeCodeLine(srcFile, "@property", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "def filterTags(self):", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, f"return {startNode.filterTags}", code_generator.DEFAULT_INDENT + code_generator.DEFAULT_INDENT)

                self.writeCodeLine(srcFile, "@property", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "def category(self):", code_generator.DEFAULT_INDENT)
                category = startNode.category if startNode.category != None and startNode.category != "" and not startNode.category.isspace() else "Default"
                self.writeCodeLine(srcFile, f"return {category}", code_generator.DEFAULT_INDENT + code_generator.DEFAULT_INDENT)

            pathonFileDir = os.path.dirname(srcFilePath)

            if not pathonFileDir in sys.path:
                sys.path.append(pathonFileDir)

            execModule = importlib.import_module(moduleName)
            importlib.reload(execModule)
            docAction = execModule.DocumentActionVS()

            if self.actionManager.isActionIdRegistered(docAction.id):
                self.actionManager.unregisterActionId(docAction.id)

            self.actionManager.registerAction(docAction)

        return srcFilePath