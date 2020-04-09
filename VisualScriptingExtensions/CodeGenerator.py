from VisualScripting.node_exec import code_generator
from VisualScriptingExtensions.document_action_nodes import DocumentActionNode
from VisualScriptingExtensions.action_nodes import ActionNode
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from MetadataManagerCore.actions.Action import Action
import os
import sys
import importlib
from MetadataManagerCore.actions.ActionManager import ActionManager

class CodeGenerator(code_generator.CodeGenerator):
    def __init__(self, actionManager=None):
        super().__init__()
        
        self.actionManager : ActionManager = actionManager

    def setActionManager(self, actionManager):
        self.actionManager = actionManager

        allGraphSettings = self.graphManager.retrieveAvailableGraphSettings()

        for graphSettings in allGraphSettings:
            moduleName = self.graphManager.getModuleNameFromGraphName(graphSettings.name)
            pythonFile = self.graphManager.getPythonCodePath(graphSettings)
            pathonFileDir = os.path.dirname(pythonFile)

            if not pathonFileDir in sys.path:
                sys.path.append(pathonFileDir)

            try:
                execModule = importlib.import_module(moduleName)
                importlib.reload(execModule)
            except Exception as e:
                print(str(e))
            
            try:
                docAction = execModule.ActionVS()
                self.actionManager.registerAction(docAction)
            except:
                pass

    def writeCodeLine(self, srcFile, codeLine, indent, suffix="\n"):
        srcFile.write(code_generator.makeCodeLine(codeLine, indent) + suffix)

    def generatePythonCode(self, graph, graphName, startNode, moduleName, targetFolder):
        srcFilePath = super().generatePythonCode(graph, graphName, startNode, moduleName, targetFolder)

        if isinstance(startNode, DocumentActionNode) or isinstance(startNode, ActionNode):
            with open(srcFilePath,"a+") as srcFile:
                srcFile.write("\n")

                srcFile.write(f"import {DocumentAction.__module__}\n\n")

                if isinstance(startNode, DocumentActionNode):
                    actionClassName = f"{DocumentAction.__module__}.{DocumentAction.__name__}"
                elif isinstance(startNode, ActionNode):
                    actionClassName = f"{Action.__module__}.{Action.__name__}"

                vsActionClassName = "ActionVS"
                
                self.writeCodeLine(srcFile, f"class {vsActionClassName}({actionClassName}):", "")

                execArgs = ["document"] if isinstance(startNode, DocumentActionNode) else []
                self.writeCodeLine(srcFile, f"def execute({','.join(['self'] + execArgs)}):", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, f"execute({','.join(execArgs)})", code_generator.DEFAULT_INDENT*2,suffix="\n\n")

                self.writeCodeLine(srcFile, "@property", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "def id(self):", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "return {!r}".format(moduleName), code_generator.DEFAULT_INDENT*2)

                self.writeCodeLine(srcFile, "@property", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "def displayName(self):", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "return {!r}".format(graphName), code_generator.DEFAULT_INDENT*2)

                self.writeCodeLine(srcFile, "@property", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "def filterTags(self):", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, f"return {startNode.filterTags}", code_generator.DEFAULT_INDENT*2)

                self.writeCodeLine(srcFile, "@property", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "def category(self):", code_generator.DEFAULT_INDENT)
                category = startNode.category if startNode.category != None and startNode.category != "" and not startNode.category.isspace() else "Default"
                self.writeCodeLine(srcFile, f"return {category}", code_generator.DEFAULT_INDENT*2)

                self.writeCodeLine(srcFile, "@property", code_generator.DEFAULT_INDENT)
                self.writeCodeLine(srcFile, "def runsOnMainThread(self):", code_generator.DEFAULT_INDENT)
                runsOnMainThread = startNode.runsOnMainThread == True
                self.writeCodeLine(srcFile, f"return {'True' if runsOnMainThread else 'False'}", code_generator.DEFAULT_INDENT*2)

            pathonFileDir = os.path.dirname(srcFilePath)

            if not pathonFileDir in sys.path:
                sys.path.append(pathonFileDir)

            execModule = importlib.import_module(moduleName)
            importlib.reload(execModule)
            docAction = execModule.ActionVS()

            if self.actionManager.isActionIdRegistered(docAction.id):
                self.actionManager.unregisterActionId(docAction.id)

            self.actionManager.registerAction(docAction)

        return srcFilePath