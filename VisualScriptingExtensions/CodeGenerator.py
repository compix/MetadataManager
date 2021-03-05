from VisualScriptingExtensions.DocumentFilterNode import DocumentFilterNode
from VisualScripting.node_exec import code_generator
from VisualScriptingExtensions.document_action_nodes import DocumentActionNode
from VisualScriptingExtensions.action_nodes import ActionNode
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from MetadataManagerCore.actions.Action import Action
import os
import sys
import importlib
from MetadataManagerCore.actions.ActionManager import ActionManager
from MetadataManagerCore.filtering.DocumentFilterManager import DocumentFilterManager
from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter

class CodeGenerator(code_generator.CodeGenerator):
    def __init__(self, actionManager, documentFilterManager : DocumentFilterManager):
        super().__init__()
        
        self.actionManager : ActionManager = actionManager
        self.documentFilterManager = documentFilterManager

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

                extraArgs = []
                if not isinstance(startNode, DocumentActionNode):
                    extraArgs = ['self']

                self.writeCodeLine(srcFile, f"execute({','.join(extraArgs + execArgs)})", code_generator.DEFAULT_INDENT*2,suffix="\n\n")

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

            pythonFileDir = os.path.dirname(srcFilePath)

            if not pythonFileDir in sys.path:
                sys.path.append(pythonFileDir)

            execModule = importlib.import_module(moduleName)
            importlib.reload(execModule)
            docAction = execModule.ActionVS()

            if self.actionManager.isActionIdRegistered(docAction.id):
                self.actionManager.unregisterActionId(docAction.id)

            self.actionManager.registerAction(docAction)
        elif isinstance(startNode, DocumentFilterNode):
            with open(srcFilePath, "a+") as srcFile:
                srcFile.write("\n")

                srcFile.write(f"HAS_STRING_ARG = {startNode.hasStringArg}\n")
                srcFile.write(f"UNIQUE_LABEL_NAME = {startNode.uniqueLabelName}\n")

            pythonFileDir = os.path.dirname(srcFilePath)

            if not pythonFileDir in sys.path:
                sys.path.append(pythonFileDir)
                
            execModule = importlib.import_module(moduleName)
            importlib.reload(execModule)

            self.documentFilterManager.addFilter(DocumentFilter(execModule.execute, execModule.UNIQUE_LABEL_NAME, hasStringArg=execModule.HAS_STRING_ARG))

        return srcFilePath