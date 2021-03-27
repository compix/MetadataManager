from PySide2 import QtWidgets
from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.PipelineType import PipelineType

class SourceCodeTemplateSceneType:
    InputScene = 'InputScene'
    RenderScene = 'RenderScene'

def addCodeLine(edit: QtWidgets.QTextEdit, codeLine: str, tabs=0):
    edit.append(f'{" "*tabs*4}{codeLine}')

def generateNukeSourceCodeTemplate(edit: QtWidgets.QTextEdit, pipelineType: PipelineType):
    edit.clear()

    addCodeLine(edit, 'import nuke, os\n')

    addCodeLine(edit, 'class Environment:')
    addCodeLine(edit, '    def __init__(self, infoDict):')
    addCodeLine(edit, '        self.infoDict = infoDict\n')

    for key in [item for item in dir(PipelineKeys) if not item.startswith("__")]:
        value = getattr(PipelineKeys, key)

        addCodeLine(edit, f'    def {key}(self):')
        addCodeLine(edit, f'        return self.infoDict.get("{value}")')
        addCodeLine(edit, '')

    addCodeLine(edit, f'    def getRenderingFilename(self):')
    addCodeLine(edit, f'        return self.RenderingFilename().replace("\\\\", "/")\n')

    addCodeLine(edit, f'    def getPostOutputExtensions(self):')
    addCodeLine(edit, f'        return [ext.strip().lower() for ext in self.PostOutputExtensions().split(",")]\n')

    addCodeLine(edit, f'    def getPostFilename(self, ext):')
    addCodeLine(edit, f'        return self.PostFilename().replace("\\\\", "/") + "." + ext\n')

    addCodeLine(edit, '')
    addCodeLine(edit, 'def process(infoDict):')
    addCodeLine(edit, '    env = Environment(infoDict)\n')
    
    addCodeLine(edit,  '    # Set read node file:')
    addCodeLine(edit,  '    readNodeName = "Read"')
    addCodeLine(edit, f'    readNode = nuke.toNode(readNodeName)\n')
    addCodeLine(edit, f'    if not readNode:')
    addCodeLine(edit, f'        raise RuntimeError("Could not find " + readNodeName + " node.")\n')

    addCodeLine(edit, '    renderingFilename = env.getRenderingFilename()\n')

    if pipelineType == PipelineType.Blender:
        addCodeLine(edit, '    # Blender adds the frame number to the end of the file. Add it to the filename:')
        addCodeLine(edit, '    if not "#" in renderingFilename:')
        addCodeLine(edit, '        base, ext = os.path.splitext(renderingFilename)')
        addCodeLine(edit, '        renderingFilename = base + "0000" + ext')
        addCodeLine(edit, '')

    addCodeLine(edit, '    if not os.path.exists(renderingFilename):')
    addCodeLine(edit, '        raise RuntimeError("Could not find rendering " + renderingFilename)\n')

    addCodeLine(edit, f'    readNode["file"].setValue(renderingFilename)\n')

    # Setup write node:
    addCodeLine(edit, '    writeNodeName = "Write"')
    addCodeLine(edit, f'    writeNode = nuke.toNode(writeNodeName)\n')
    addCodeLine(edit, f'    if not writeNode:')
    addCodeLine(edit, f'        raise RuntimeError("Could not find " + writeNodeName + " node.")\n')

    addCodeLine(edit, '    # Set write node files:')
    addCodeLine(edit, f'    for ext in env.getPostOutputExtensions():')
    addCodeLine(edit, f'        filename = env.getPostFilename(ext)')
    addCodeLine(edit, f'        writeNode["file"].setValue(filename)\n')
    addCodeLine(edit, f'        nuke.execute(writeNode, 1, 1)')

def generateMaxSourceCodeTemplate(edit: QtWidgets.QTextEdit, sceneType: SourceCodeTemplateSceneType):
    edit.clear()
    
    addCodeLine(edit, 'global INFO_MAP = undefined')
    addCodeLine(edit, '')
    addCodeLine(edit, 'fn readInfoMap infoFile = (')
    addCodeLine(edit, '    py_main = Python.Import "__builtin__"')
    addCodeLine(edit, '    json = Python.Import "json"')
    addCodeLine(edit, '    ')
    addCodeLine(edit, '    f = py_main.open infoFile')
    addCodeLine(edit, '    infoMap = json.load f')
    addCodeLine(edit, '    f.close()')
    addCodeLine(edit, '    ')
    addCodeLine(edit, '    infoMap')
    addCodeLine(edit, ')')
    addCodeLine(edit, '')
    addCodeLine(edit, 'fn saveMaxFileChecked filename = (')
    addCodeLine(edit, '    if not (saveMaxFile filename) do throw ("Failed to save max file to " + filename as string)')
    addCodeLine(edit, ')')
    addCodeLine(edit, '')

    addCodeLine(edit, 'fn initInfoMapGlobals = (')
    for key in [item for item in dir(PipelineKeys) if not item.startswith("__")]:
        value = getattr(PipelineKeys, key)
        addCodeLine(edit, f'   global {key} = INFO_MAP["{value}"]')
    addCodeLine(edit, ')')
    
    addCodeLine(edit, '')
    addCodeLine(edit, 'fn executePipelineRequest infoFile = (')
    addCodeLine(edit, '    global INFO_MAP')
    addCodeLine(edit, '    ')
    addCodeLine(edit, '    INFO_MAP = readInfoMap infoFile')
    addCodeLine(edit, '    initInfoMapGlobals()')
    addCodeLine(edit, '    ')
    addCodeLine(edit, '    -- Prepare')
    addCodeLine(edit, '    loadedBaseSceneFile = loadMaxFile baseFile useFileUnits:true')
    addCodeLine(edit, '    if not loadedBaseSceneFile do throw ("Failed to load base scene file: " + BaseSceneFilename as string)')
    addCodeLine(edit, '    ')

    if sceneType == SourceCodeTemplateSceneType.RenderScene:
        addCodeLine(edit, '    -- Merge environment scene file if available')
        addCodeLine(edit, '    if EnvironmentSceneNaming != "" do (')
        addCodeLine(edit, '        mergedEnvSceneFile = mergeMAXFile EnvironmentSceneFilename #mergeDups #useMergedMtlDups #neverReparent')
        addCodeLine(edit, '        if not mergedEnvSceneFile do throw ("Failed to merge env scene file: " + EnvironmentSceneFilename as string)')
        addCodeLine(edit, '    )')
        addCodeLine(edit, '    ')

    if sceneType == SourceCodeTemplateSceneType.RenderScene:
        addCodeLine(edit, '    -- Merge input scene file')
        addCodeLine(edit, '    mergedInputSceneFile = mergeMAXFile InputSceneFilename #mergeDups #useMergedMtlDups #neverReparent')
        addCodeLine(edit, '    if not mergedInputSceneFile do throw ("Failed to merge input scene file: " + InputSceneFilename as string)')
        addCodeLine(edit, '    ')

    addCodeLine(edit, '    /*******************************************************')
    addCodeLine(edit, '    TODO: Apply variation logic')
    addCodeLine(edit, '    ********************************************************/')
    addCodeLine(edit, '    ')
    addCodeLine(edit, f'    saveMaxFileChecked {"InputSceneFilename" if sceneType == SourceCodeTemplateSceneType.InputScene else "RenderSceneFilename"}')
    addCodeLine(edit, ')')

def generateBlenderSourceCodeTemplate(edit: QtWidgets.QTextEdit, sceneType: SourceCodeTemplateSceneType):
    edit.clear()

    addCodeLine(edit, 'import bpy, os\n')

    addCodeLine(edit, 'class Environment:')
    addCodeLine(edit, 'def __init__(self, infoDict: dict):', tabs=1)
    addCodeLine(edit, 'self.infoDict = infoDict\n', tabs=2)

    for key in [item for item in dir(PipelineKeys) if not item.startswith("__")]:
        value = getattr(PipelineKeys, key)
        
        addCodeLine(edit, f'@property', tabs=1)
        addCodeLine(edit, f'def {key}(self):', tabs=1)
        addCodeLine(edit, f'return self.infoDict.get("{value}")', tabs=2)
        addCodeLine(edit, '')
    
    addCodeLine(edit, 'def mergeScene(filename: str):')
    addCodeLine(edit, '    with bpy.data.libraries.load(filename) as (dataFrom, _):')
    addCodeLine(edit, '        files = []')
    addCodeLine(edit, '        for c in dataFrom.collections:')
    addCodeLine(edit, '            files.append({"name" : c})')
    addCodeLine(edit, '')
    addCodeLine(edit, '        bpy.ops.wm.append(directory=os.path.join(filename, "Collection"), files=files)')
    addCodeLine(edit, '')
    addCodeLine(edit, 'def resetScene():')
    addCodeLine(edit, '    for collection in [col for col in bpy.data.collections]:')
    addCodeLine(edit, '        for obj in [obj for obj in collection.objects if obj.users > 0]:')
    addCodeLine(edit, '            bpy.data.objects.remove(obj)')
    addCodeLine(edit, '')
    addCodeLine(edit, '        bpy.data.collections.remove(collection)')
    addCodeLine(edit, '')

    if sceneType == SourceCodeTemplateSceneType.RenderScene:
        addCodeLine(edit, 'def frameCamera(cameraName: str):')
        addCodeLine(edit, '    camera = bpy.data.objects.get(cameraName)')
        addCodeLine(edit, '')
        addCodeLine(edit, '    if not camera:')
        addCodeLine(edit, '        raise RuntimeError(f"Could not find camera with name {cameraName}")')
        addCodeLine(edit, '')
        addCodeLine(edit, '    bpy.context.scene.camera = camera')
        addCodeLine(edit, '')
        addCodeLine(edit, '    # Select all visible objects:')
        addCodeLine(edit, '    for obj in bpy.data.objects:')
        addCodeLine(edit, '        if not obj.hide_render:')
        addCodeLine(edit, '            obj.select_set(True)')
        addCodeLine(edit, '')
        addCodeLine(edit, '    bpy.ops.view3d.camera_to_view_selected()')

    addCodeLine(edit, '')
    addCodeLine(edit, 'def process(infoDict: dict):')
    addCodeLine(edit, '"""Processing entry point function"""', tabs=1)
    addCodeLine(edit, 'env = Environment(infoDict)\n', tabs=1)

    # Always start with an empty scene if no base scene was provided:
    addCodeLine(edit, '    if not env.BaseSceneNaming:')
    addCodeLine(edit, '        print("Resetting scene...")\n')
    addCodeLine(edit, '        resetScene()\n')
    
    if sceneType == SourceCodeTemplateSceneType.RenderScene:
        addCodeLine(edit, '    # Merge environment scene file if available:')
        addCodeLine(edit, '    if env.EnvironmentSceneNaming:')
        addCodeLine(edit, '        print(f"Merging environment scene file: {env.EnvironmentSceneFilename}")')
        addCodeLine(edit, '        mergeScene(env.EnvironmentSceneFilename)\n')

        addCodeLine(edit, '    # Merge input scene file if available')
        addCodeLine(edit, '    if env.InputSceneNaming:')
        addCodeLine(edit, '        print(f"Merging input scene file: {env.InputSceneFilename}")')
        addCodeLine(edit, '        mergeScene(env.InputSceneFilename)\n')

    addCodeLine(edit, 'print("Applying variation logic...")\n', tabs=1)

    if sceneType == SourceCodeTemplateSceneType.RenderScene:
        addCodeLine(edit, '    print("Framing to all visible objects...")')
        addCodeLine(edit, '    cameraName = f"Camera_{env.Perspective}" if env.Perspective else "Camera"')
        addCodeLine(edit, '    frameCamera(cameraName)')
    
    addCodeLine(edit, '')
    addCodeLine(edit, '# TODO: Apply variation logic', tabs=1)
    addCodeLine(edit, '')

    if sceneType == SourceCodeTemplateSceneType.InputScene:
        addCodeLine(edit, 'print(f"Saving scene to {env.InputSceneFilename}")', tabs=1)
        addCodeLine(edit, 'bpy.ops.wm.save_mainfile(filepath=env.InputSceneFilename, check_existing=False)', tabs=1)
    elif sceneType == SourceCodeTemplateSceneType.RenderScene:
        addCodeLine(edit, 'print(f"Saving scene to {env.RenderSceneFilename}")', tabs=1)
        addCodeLine(edit, 'bpy.ops.wm.save_mainfile(filepath=env.RenderSceneFilename, check_existing=False)', tabs=1)