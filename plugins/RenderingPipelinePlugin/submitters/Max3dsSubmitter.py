from RenderingPipelinePlugin.submitters.RenderingPipelineSubmitter import RenderingPipelineSubmitter
from RenderingPipelinePlugin.submitters.Submitter import Submitter, SubmitterPipelineKeyRequirementsResponse
from RenderingPipelinePlugin import PipelineKeys
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from typing import List
import os
import json

class Max3dsInputSceneCreationSubmitter(RenderingPipelineSubmitter):
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None) -> str:
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.InputSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.get3dsMaxPipelinePluginName()
        jobName = self.pipeline.namingConvention.getCreatedInputSceneName(documentWithSettings)
        batchName = 'Input Scene'
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio + 4,
                                                   documentWithSettings.get(PipelineKeys.DeadlineInputScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getCreatedInputSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneCreationInfo)

        return deadline_nodes.submit_3dsMaxPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, documentWithSettings.get(PipelineKeys.Max3dsVersion))

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.InputSceneCreationScript, 
                                                        messages=['An input scene creation script is not specified.'], isFile=True)

class Max3dsRenderSceneCreationSubmitter(RenderingPipelineSubmitter):
    defaultActive = True

    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.RenderSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.get3dsMaxPipelinePluginName()
        jobName = self.pipeline.namingConvention.getRenderSceneName(documentWithSettings)
        batchName = 'Render Scene'
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio + 3, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineRenderScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        concurrentTasks = documentWithSettings.get(PipelineKeys.DeadlineConcurrentTasks) or 1
        jobInfoDict['ConcurrentTasks'] = concurrentTasks

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneCreationInfo)

        return deadline_nodes.submit_3dsMaxPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, documentWithSettings.get(PipelineKeys.Max3dsVersion))

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.RenderSceneCreationScript, 
                                                        messages=['A render scene creation script is not specified.'], isFile=True)

class Max3dsRenderingSubmitter(RenderingPipelineSubmitter):
    defaultActive = True

    def prepareScript(self, documentWithSettings: dict, scriptPipelineKey: str, scriptPluginKey: str, pluginInfoDict: dict):
        scriptFilename = documentWithSettings.get(scriptPipelineKey)
        if scriptFilename and os.path.exists(scriptFilename) and os.path.isfile(scriptFilename):
            scriptFilename = scriptFilename.replace('\\', '/')
            bootstrapScriptFilename = deadline_nodes.getDeadlineFilename('3dsMax', 'ms')
            pipelineInfoFilename = deadline_nodes.getDeadlineFilename('3dsMax', 'json')
            
            with open(pipelineInfoFilename, "w+", encoding='utf-8') as f:
                json.dump(documentWithSettings, f, sort_keys=True, indent=4, ensure_ascii=False)

            with open(bootstrapScriptFilename, "w+") as f:
                f.write("(\n")
                f.write("   global executePipelineRequest\n\n")
                f.write("   python.Init()\n\n")
                f.write("   processResult = true\n\n")
                f.write("   try (\n")
                f.write(f"      fileIn \"{scriptFilename}\"\n\n")
                f.write(f"      infoFile = \"" + pipelineInfoFilename.replace('\\', '/') + "\"\n")
                f.write(f"      executePipelineRequest infoFile\n")
                f.write("   ) catch (\n")
                f.write(f"      (dotNetClass \"System.Console\").Error.WriteLine (\"ERROR: \" + (getCurrentException()))\n")
                f.write(f"      processResult = false\n")
                f.write("   )\n")
                f.write("\n")
                f.write("   processResult\n")
                f.write(")")

            pluginInfoDict[scriptPluginKey] = bootstrapScriptFilename

    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        pluginName = deadline_nodes.get3dsMaxPluginName()
        jobName = self.pipeline.namingConvention.getRenderingName(documentWithSettings)
        batchName = 'Rendering'
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio + 2, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineRenderingPool), dependentJobIds=dependentJobIds)

        frames = documentWithSettings.get(PipelineKeys.Frames)    
        if not frames:
            frames = documentWithSettings.get(PipelineKeys.getKeyWithPerspective(PipelineKeys.Frames, documentWithSettings.get(PipelineKeys.Perspective, '')), '')                                                   
            
        if frames:
            jobInfoDict['Frames'] = frames

        filename = self.pipeline.namingConvention.getRenderingFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)
        
        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderingTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderingInfo)

        sceneFilename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        pluginInfoDict = deadline_nodes.create3dsMaxPluginInfoDictionary(sceneFilename, Version=documentWithSettings.get(PipelineKeys.Max3dsVersion))
        removePadding = documentWithSettings.get(PipelineKeys.DeadlineRemovePadding)
        pluginInfoDict['RemovePadding'] = 'True' if removePadding else 'False'

        #stateSet = documentWithSettings.get(PipelineKeys.DeadlineStateSet)
        #if stateSet:
        #    pluginInfoDict['RenderStateSet'] = '1'
        #    pluginInfoDict['StateSetToRender'] = stateSet

        """
        jobInfoDict['Frames'] = '1'
        pluginInfoDict['Camera'] = 'CAM_VANITY_UNIT_sloped'
        pluginInfoDict['Camera0'] = 'CAM_VANITY_UNIT_sloped'
        pluginInfoDict['Camera1'] = 'CAM_VANITY_UNIT_sloped'
        """
        
        self.prepareScript(documentWithSettings, PipelineKeys.RenderPostLoadScript, 'PostLoadScript', pluginInfoDict)
        self.prepareScript(documentWithSettings, PipelineKeys.PreFrameScript, 'PreFrameScript', pluginInfoDict)

        return deadline_nodes.submitJob(jobInfoDict, pluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.RenderingNaming, 
                perspectiveDependent=True, messages=['Rendering naming convention not specified.'])