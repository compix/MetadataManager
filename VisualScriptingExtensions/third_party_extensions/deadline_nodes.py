"""
AWS Thinkbox Software Deadline nodes
""" 

from VisualScripting.node_exec.base_nodes import defNode, defInlineNode
from MetadataManagerCore.third_party_integrations.deadline.deadline_service import DeadlineService, DeadlineServiceInfo
import os
import tempfile
import json
import uuid

DEADLINE_SERVICE : DeadlineService = None
DEADLINE_IDENTIFIER = "Deadline"

def removeFiles(filenames):
    for f in filenames:
        try:
            os.remove(f)
        except Exception as e:
            print(str(e))

@defNode("Submit Job Files", isExecutable=True, returnNames=["Job"], identifier=DEADLINE_IDENTIFIER)
def submitJobFiles(jobInfoFilename, pluginInfoFilename, auxiliaryFilenames=None, quiet=True, returnJobIdOnly=True, removeAuxiliaryFilesAfterSubmission=False):
    if DEADLINE_SERVICE == None:
        return None

    if auxiliaryFilenames == None:
        auxiliaryFilenames = []

    submissionResult = DEADLINE_SERVICE.submitJobFiles(jobInfoFilename, pluginInfoFilename, auxiliaryFilenames=auxiliaryFilenames, quiet=quiet, returnJobIdOnly=returnJobIdOnly)

    if removeAuxiliaryFilesAfterSubmission:
        removeFiles(auxiliaryFilenames)

    return submissionResult

@defNode("Submit Job", isExecutable=True, returnNames=["Job"], identifier=DEADLINE_IDENTIFIER)
def submitJob(jobInfoDict, pluginInfoDict, auxiliaryFilenames=None, quiet=True, returnJobIdOnly=True, jobDependencies=None, removeAuxiliaryFilesAfterSubmission=False):
    if DEADLINE_SERVICE == None:
        return None

    if auxiliaryFilenames == None:
        auxiliaryFilenames = []

    if jobDependencies != None and (isinstance(jobDependencies, str) or len(jobDependencies) > 0):
        jobInfoDict = jobInfoDict.copy()
        deps = jobInfoDict.get("JobDependencies")
        if deps == None or deps == '':
            deps = jobDependencies if isinstance(jobDependencies, str) else ",".join(jobDependencies)
        else:
            deps = deps + "," + (jobDependencies if isinstance(jobDependencies, str) else ",".join(jobDependencies))
        
        jobInfoDict["JobDependencies"] = deps

    auxiliaryFilenames = auxiliaryFilenames if isinstance(auxiliaryFilenames, list) else [auxiliaryFilenames]
    submissionResult = DEADLINE_SERVICE.submitJob(jobInfoDict, pluginInfoDict, auxiliaryFilenames=auxiliaryFilenames, quiet=quiet, returnJobIdOnly=returnJobIdOnly)

    if removeAuxiliaryFilesAfterSubmission:
        removeFiles(auxiliaryFilenames)

    return submissionResult

@defNode("Get Job Id", returnNames=["Job Id"], identifier=DEADLINE_IDENTIFIER)
def getJobId(jobDictionary):
    return jobDictionary.get("_id") if jobDictionary != None else ""

@defNode("Create Job Info Dictionary", isExecutable=True, returnNames=["Job Info Dict"], identifier=DEADLINE_IDENTIFIER)
def createJobInfoDictionary(pluginName, name="Test Job", batchName="", priority=50, department="", pool="", secondaryPool="", group="",jobDependencies=None):
    if jobDependencies == None:
        jobDependencies = []
        
    jobDict = {"Plugin":pluginName, "Name": name, "BatchName":batchName, "Priority":priority, "Department":department, "Pool":pool, "SecondaryPool":secondaryPool, "Group":group,
        "JobDependencies":(",".join(jobDependencies) if isinstance(jobDependencies, list) else jobDependencies)}
    return jobDict

@defNode("Submit 3ds Max Pipeline Job", isExecutable=True, returnNames=["Job"], identifier=DEADLINE_IDENTIFIER)
def submit_3dsMaxPipelineJob(pipelineMaxScriptFilename, pipelineInfoDict, jobInfoDict, versionOf3dsMax, auxiliaryFilenames=None, quiet=True, 
        returnJobIdOnly=True, jobDependencies=None, removeAuxiliaryFilesAfterSubmission=False):
    
    if auxiliaryFilenames == None:
        auxiliaryFilenames = []

    if jobDependencies == None:
        jobDependencies = []
        
    pipelineMaxScriptFilename = pipelineMaxScriptFilename.replace("\\", "/")
    
    # Generate auxiliary pipeline info file:
    pipelineInfoFileHandle, tempPipelineInfoFilename = tempfile.mkstemp(suffix=".json")
    auxiliaryFilenames.append(tempPipelineInfoFilename)
    with open(tempPipelineInfoFilename, "w+") as f:
        json.dump(pipelineInfoDict, f, sort_keys=True, indent=4)

    os.close(pipelineInfoFileHandle)

    # Generate auxiliary script file:
    maxScriptFileHandle, tempMaxScriptFilename = tempfile.mkstemp(suffix=".ms")
    auxiliaryFilenames.insert(0, tempMaxScriptFilename)
    
    with open(tempMaxScriptFilename, "w+") as f:
        f.write("global executePipelineRequest\n\n")
        f.write("python.Init()\n\n")
        f.write("try (\n")
        f.write(f"  fileIn \"{pipelineMaxScriptFilename}\"\n\n")
        f.write(f"  infoFile = (getFilenamePath (getSourceFileName())) + \"{os.path.basename(tempPipelineInfoFilename)}\"\n")
        f.write(f"  executePipelineRequest infoFile\n")
        f.write(") catch (\n")
        f.write(f"  (dotNetClass \"System.Console\").Error.WriteLine (\"ERROR: \" + (getCurrentException()))\n")
        f.write(")\n")
        f.write("\nquitMAX #noPrompt\n")

    os.close(maxScriptFileHandle)

    pluginInfoDict = {"3dsMaxVersion": versionOf3dsMax}
    job = submitJob(jobInfoDict, pluginInfoDict, auxiliaryFilenames, quiet, returnJobIdOnly, jobDependencies, removeAuxiliaryFilesAfterSubmission)

    if not removeAuxiliaryFilesAfterSubmission:
        removeFiles([tempPipelineInfoFilename, tempMaxScriptFilename])

    return job

@defNode("Submit Nuke Job", isExecutable=True, returnNames=["Job"], identifier=DEADLINE_IDENTIFIER)
def submitNukeJob(jobInfoDict: dict, pluginInfoDict: dict, scriptFilename: str, scriptInfoDict: dict, jobDependencies=None):
    # Create a python script file in the deadline repository:
    directory = os.path.join(DEADLINE_SERVICE.info.customJobInfoDirectory, 'nuke', uuid.uuid4().hex)
    os.makedirs(directory, exist_ok=True)

    bootstrapScriptFilename = os.path.join(directory,  f'{uuid.uuid4().hex}.py')
    infoFilename = os.path.join(directory, f'{uuid.uuid4().hex}.json')

    scriptDirectory = os.path.dirname(scriptFilename)
    scriptModule = os.path.splitext(os.path.basename(scriptFilename))[0]

    code = \
    f"""
    import sys, json

    sys.path.append("{scriptDirectory}")
    import {scriptModule}
    
    infoDict = json.load({infoFilename})
    {scriptModule}.process(infoDict)
    """.strip()

    with open(bootstrapScriptFilename, 'w+') as f:
        f.write(code)

    with open(infoFilename, 'w+') as f:
        json.dump(scriptInfoDict, f)

    jobInfoDict["Plugin"] = getNukePluginName()
    pluginInfoDict["ScriptFilename"] = bootstrapScriptFilename

    return submitJob(jobInfoDict, pluginInfoDict, jobDependencies=jobDependencies)

@defNode("Create Nuke Plugin Info Dictionary", isExecutable=True, returnNames=["Plugin Info Dict"], identifier=DEADLINE_IDENTIFIER)
def createNukePluginInfoDictionary(sceneFilename, scriptFilename=None, writeNode="", version="12.0", batchMode=True, 
        batchModeIsMove=False, continueOnError=False, enforceRenderOrder=False, nukeX=False, renderMode="Use Scene Settings", views="", useGPU=False, threads=0, gpuOverride=0):

    scriptJob = scriptFilename != None and os.path.exists(scriptFilename)
    pluginDict = {"BatchMode":batchMode, "BatchModeIsMovie":batchModeIsMove, "ContinueOnError":continueOnError, "EnforceRenderOrder":enforceRenderOrder,
        "GpuOverride":gpuOverride, "NukeX":nukeX, "PerformanceProfiler":False, "PerformanceProfilerDir":"", "RamUse":0, "RenderMode":renderMode, 
        "SceneFile":sceneFilename, "ScriptFilename":scriptFilename, "ScriptJob":scriptJob, "StackSize":0, "Threads":threads, "UseGpu":useGPU, "Version":version,
        "Views":views, "WriteNode":writeNode}

    return pluginDict

@defNode("Create 3ds Max Plugin Info Dictionary", isExecutable=True, returnNames=["Plugin Info Dict"], identifier=DEADLINE_IDENTIFIER)
def create3dsMaxPluginInfoDictionary(SceneFile, Version="2017", DisableMultipass=False,
        IgnoreMissingDLLs=False, IgnoreMissingExternalFiles=True, IgnoreMissingUVWs=True, IgnoreMissingXREFs=True, IsMaxDesign=False,
        GPUsPerTask=0, GammaCorrection=False, GammaInput=1.0, GammaOutput=1.0, Language="Default",
        LocalRendering=True, OneCpuPerTask=False, RemovePadding=False, RestartRendererMode=False, ShowFrameBuffer=True, UseSilentMode=False,UseSlaveMode=1):
    pluginDict = {"SceneFile":SceneFile, "Version":Version, "DisableMultipass":DisableMultipass, "IgnoreMissingDLLs": IgnoreMissingDLLs, 
                  "IgnoreMissingExternalFiles": IgnoreMissingExternalFiles, "IgnoreMissingUVWs":IgnoreMissingUVWs, "IgnoreMissingXREFs":IgnoreMissingXREFs,
                  "IsMaxDesign":IsMaxDesign, "GPUsPerTask":GPUsPerTask, "GammaCorrection": GammaCorrection,
                  "GammaInput":GammaInput, "GammaOutput":GammaOutput, "Language":Language, "LocalRendering":LocalRendering, "OneCpuPerTask":OneCpuPerTask,
                  "RemovePadding":RemovePadding, "RestartRendererMode":RestartRendererMode, "ShowFrameBuffer":ShowFrameBuffer, "UseSilentMode":UseSilentMode, 
                  "UseSlaveMode":UseSlaveMode}

    return pluginDict

@defNode("Create Python Plugin Info Dictionary", isExecutable=True, returnNames=["Plugin Info Dict"], identifier=DEADLINE_IDENTIFIER)
def createPythonPluginInfoDictionary(arguments="", version="3.7"):
    return {"Arguments":arguments, "Version":version, "SingleFramesOnly":False}

@defNode("Python Plugin Name", returnNames=["Plugin Name"], identifier=DEADLINE_IDENTIFIER)
def getPythonPluginName():
    return "Python"

@defNode("Nuke Plugin Name", returnNames=["Plugin Name"], identifier=DEADLINE_IDENTIFIER)
def getNukePluginName():
    return "Nuke"

@defNode("3ds Max Plugin Name", returnNames=["Plugin Name"], identifier=DEADLINE_IDENTIFIER)
def get3dsMaxPluginName():
    return "3dsmax"

@defNode("Maya Plugin Name", returnNames=["Plugin Name"], identifier=DEADLINE_IDENTIFIER)
def getMayaPluginName():
    return "Maya"

@defNode("3ds Max Pipeline Plugin Name", returnNames=["Plugin Name"], identifier=DEADLINE_IDENTIFIER)
def get3dsMaxPipelinePluginName():
    return "3dsMaxPipeline"

@defNode("Metadata Manager Plugin Name", returnNames=["Plugin Name"], identifier=DEADLINE_IDENTIFIER)
def getMetadataManagerPluginName():
    return "MetadataManager"

@defNode("Submit Metadata Manager Job", isExecutable=True, returnNames=["Job"], identifier=DEADLINE_IDENTIFIER)
def submitMetadataManagerJob(taskInfoDict, jobInfoDict, asPythonJob=False, quiet=True, returnJobIdOnly=True, jobDependencies=None):
    pluginInfoDict = {}
    auxiliaryFilenames = []

    taskFileHandle, taskFilename = tempfile.mkstemp(suffix=".json")
    auxiliaryFilenames.append(taskFilename)
    with open(taskFilename, "w+") as f:
        json.dump(taskInfoDict, f, sort_keys=True, indent=4)

    os.close(taskFileHandle)

    pluginInfoDict["as_python"] = str(asPythonJob)
    job = submitJob(jobInfoDict, pluginInfoDict, auxiliaryFilenames=auxiliaryFilenames, 
                    quiet=quiet, returnJobIdOnly=returnJobIdOnly, jobDependencies=jobDependencies, 
                    removeAuxiliaryFilesAfterSubmission=True)

    return job

@defNode("Create Metadata Manager Action Task Dictionary", isExecutable=True, returnNames=["Task Dictionary"], identifier=DEADLINE_IDENTIFIER)
def createMetadataManagerActionTaskDict(taskType="DocumentAction", actionId="", collections=None, documentFilter="{}", distinctionFilter="", customFilters=None):
    if collections == None:
        collections = []

    if not isinstance(collections, list):
        collections = [collections]

    return {"taskType":taskType, "actionId":actionId, "collections":collections, 
            "documentFilter":documentFilter, "distinctionFilter":distinctionFilter, 
            "customDocumentFilters": customFilters}

@defNode("Create Custom Filter Dict", isExecutable=False, returnNames=["Custom Filter"], identifier=DEADLINE_IDENTIFIER)
def createCustomFilterDict(filterLabel: str, args=None, active=True, negate=False, returnAsList=True):
    d = {
        'uniqueFilterLabel': filterLabel,
        'active': active,
        'args': args,
        'hasStringArg': args != None,
        'negate': negate
    }

    if returnAsList:
        return [d]

    return d

@defNode("Create Metadata Manager Action Task Dictionary for Document", isExecutable=True, returnNames=["Task Dictionary"], identifier=DEADLINE_IDENTIFIER)
def createMetadataManagerActionTaskDictForDocument(taskType="DocumentAction", actionId="", document=None, collections=None):
    if collections == None:
        collections = []

    if not isinstance(collections, list):
        collections = [collections]

    docFilter = f'"s_id": "{document.get("s_id")}"'

    return {"taskType":taskType, "actionId":actionId, "collections":collections, 
            "documentFilter":"{" + docFilter + "}", "distinctionFilter":""} 

@defNode("Get Deadline Job Names", isExecutable=True, returnNames=["Job Names"])
def getDeadlineJobNames(quiet=False):
    if DEADLINE_SERVICE == None:
        return None

    return DEADLINE_SERVICE.getJobNames(quiet=quiet)

@defNode("Get Deadline Pool Names", isExecutable=True, returnNames=["Pool Names"])
def getDeadlinePoolNames(quiet=False):
    if DEADLINE_SERVICE == None:
        return None

    return DEADLINE_SERVICE.getPoolNames(quiet=quiet)