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
        addCodeLine(edit, f'   global g_{key} = INFO_MAP["{value}"]')
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
        if not isinstance(value, str):
            continue
        
        addCodeLine(edit, f'@property', tabs=1)
        addCodeLine(edit, f'def {key}(self):', tabs=1)
        addCodeLine(edit, f'return self.infoDict.get("{value}")', tabs=2)
        addCodeLine(edit, '')
    
    addCodeLine(edit, 'def mergeScene(filename: str):')
    addCodeLine(edit, '    if os.path.exists(filename):')
    addCodeLine(edit, '        with bpy.data.libraries.load(filename) as (dataFrom, _):')
    addCodeLine(edit, '            files = []')
    addCodeLine(edit, '            for c in dataFrom.collections:')
    addCodeLine(edit, '                files.append({"name" : c})')
    addCodeLine(edit, '')
    addCodeLine(edit, '            bpy.ops.wm.append(directory=os.path.join(filename, "Collection"), files=files)')
    addCodeLine(edit, '')
    addCodeLine(edit, 'def resetScene():')
    addCodeLine(edit, '    for collection in [col for col in bpy.data.collections]:')
    addCodeLine(edit, '        for obj in [obj for obj in collection.objects if obj.users > 0]:')
    addCodeLine(edit, '            bpy.data.objects.remove(obj)')
    addCodeLine(edit, '')
    addCodeLine(edit, '        bpy.data.collections.remove(collection)')

    if sceneType == SourceCodeTemplateSceneType.RenderScene:
        addCodeLine(edit, '')
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
        addCodeLine(edit, 'def imageFileFormatToExtension(fileFormat: str):')
        addCodeLine(edit, '    fileFormatToExtMap = {')
        addCodeLine(edit, '        "BMP": "bmp", ')
        addCodeLine(edit, '        "IRIS": "rgb", ')
        addCodeLine(edit, '        "PNG": "png", ')
        addCodeLine(edit, '        "JPEG": "jpg", ')
        addCodeLine(edit, '        "JPEG2000": "jp2",') 
        addCodeLine(edit, '        "TARGA": "tga", ')
        addCodeLine(edit, '        "TARGA_RAW": "tga", ')
        addCodeLine(edit, '        "CINEON": "cin", ')
        addCodeLine(edit, '        "DPX": "dpx", ')
        addCodeLine(edit, '        "OPEN_EXR_MULTILAYER": "exr", ')
        addCodeLine(edit, '        "OPEN_EXR": "exr",')
        addCodeLine(edit, '        "HDR": "hdr", ')
        addCodeLine(edit, '        "TIFF": "tif"')
        addCodeLine(edit, '    }')
        addCodeLine(edit, '')
        addCodeLine(edit, '    return fileFormatToExtMap.get(fileFormat)')
        addCodeLine(edit, '')
        addCodeLine(edit, 'def setRenderingOutputFilenames(env: Environment):')
        addCodeLine(edit, '    bpy.context.scene.render.filepath = env.RenderingFilename')
        addCodeLine(edit, '    compositorTree = bpy.context.scene.node_tree')
        addCodeLine(edit, '')
        addCodeLine(edit, '    if bpy.context.scene.use_nodes:')
        addCodeLine(edit, '        for node in compositorTree.nodes:')
        addCodeLine(edit, '            if node.type == "OUTPUT_FILE":')
        addCodeLine(edit, '                nodeFormat = node.format')
        addCodeLine(edit, '                if nodeFormat.file_format == "OPEN_EXR_MULTILAYER":')
        addCodeLine(edit, '                    node.base_path = env.PostFilename + ".exr"')
        addCodeLine(edit, '                else:')
        addCodeLine(edit, '                    node.base_path = os.path.dirname(env.PostFilename)')
        addCodeLine(edit, '                    for fileSlot in node.file_slots:')
        addCodeLine(edit, '                        if fileSlot.use_node_format:')
        addCodeLine(edit, '                            format = nodeFormat')
        addCodeLine(edit, '                        else:')
        addCodeLine(edit, '                            format = fileSlot.format')
        addCodeLine(edit, '')
        addCodeLine(edit, '                        ext = imageFileFormatToExtension(format.file_format)')
        addCodeLine(edit, '                        fileSlot.path = os.path.basename(env.PostFilename) + "." + ext')
        addCodeLine(edit, '')
        addCodeLine(edit, 'def renameOutputFiles(env: Environment):')
        addCodeLine(edit, '    """Blender adds the frame number to the end of the file. This function renames the files."""')
        addCodeLine(edit, '    compositorTree = bpy.context.scene.node_tree')
        addCodeLine(edit, '')
        addCodeLine(edit, '    for node in compositorTree.nodes:')
        addCodeLine(edit, '        if node.type == "OUTPUT_FILE":')
        addCodeLine(edit, '            nodeFormat = node.format')
        addCodeLine(edit, '            renameRequests = []')
        addCodeLine(edit, '            if nodeFormat == "OPEN_EXR_MULTILAYER":')
        addCodeLine(edit, '                renameRequests.append((f"{env.PostFilename}0001.exr", f"{env.PostFilename}.exr"))')
        addCodeLine(edit, '            else:')
        addCodeLine(edit, '                for fileSlot in node.file_slots:')
        addCodeLine(edit, '                    format = nodeFormat if fileSlot.use_node_format else fileSlot.format')
        addCodeLine(edit, '')
        addCodeLine(edit, '                    ext = imageFileFormatToExtension(format.file_format)')
        addCodeLine(edit, '                    renameRequests.append((f"{env.PostFilename}.{ext}0001", f"{env.PostFilename}.{ext}"))')
        addCodeLine(edit, '')
        addCodeLine(edit, '            for src, dst in renameRequests:')
        addCodeLine(edit, '                print(f"Replacing {src} with {dst}")')
        addCodeLine(edit, '')
        addCodeLine(edit, '                if os.path.exists(src):')
        addCodeLine(edit, '                    os.replace(src, dst)')
        addCodeLine(edit, '')
        addCodeLine(edit, 'def getFrames(env: Environment):')
        addCodeLine(edit, '    if not env.Frames:')
        addCodeLine(edit, '        return []')
        addCodeLine(edit, '')
        addCodeLine(edit, '    frameStrings = [f.strip() for f in env.Frames.split(",")]')
        addCodeLine(edit, '    frames = []')
        addCodeLine(edit, '    for f in frameStrings:')
        addCodeLine(edit, '        frameRange = f.split("-")')
        addCodeLine(edit, '        if len(frameRange) > 0:')
        addCodeLine(edit, '            start = int(frameRange[0].strip())')
        addCodeLine(edit, '            end = int(frameRange[1].strip())')
        addCodeLine(edit, '            frames += [i for i in range(start,end+1)]')
        addCodeLine(edit, '        else:')
        addCodeLine(edit, '            frames.append(int(f))')
        addCodeLine(edit, '    return frames')

    addCodeLine(edit, '')
    addCodeLine(edit, 'def process(infoDict: dict):')
    addCodeLine(edit, '    """Entry point function for processing"""')
    addCodeLine(edit, '    env = Environment(infoDict)\n')

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
        addCodeLine(edit, '')
        addCodeLine(edit, '    print("Setting rendering output filenames...")')
        addCodeLine(edit, '    setRenderingOutputFilenames(env)')
        addCodeLine(edit, '')

    addCodeLine(edit, '    print("Applying variation logic...")')

    addCodeLine(edit, '')
    addCodeLine(edit, '    # TODO: Apply variation logic')
    addCodeLine(edit, '')

    if sceneType == SourceCodeTemplateSceneType.RenderScene:
        addCodeLine(edit, '    if env.ApplyCameraFraming:')
        addCodeLine(edit, '        print("Framing to all visible objects...")')
        addCodeLine(edit, '        cameraName = f"Camera_{env.Perspective}" if env.Perspective else "Camera"')
        addCodeLine(edit, '        frameCamera(cameraName)')
        addCodeLine(edit, '')
    
        addCodeLine(edit, '    if env.SaveRenderScene:')
        addCodeLine(edit, '        print(f"Saving scene to {env.RenderSceneFilename}")')
        addCodeLine(edit, '        bpy.ops.wm.save_mainfile(filepath=env.RenderSceneFilename, check_existing=False)')
        addCodeLine(edit, '')
        addCodeLine(edit, '    if env.RenderInSceneCreationScript:')
        addCodeLine(edit, '        print("Rendering...")')
        addCodeLine(edit, '        frames = getFrames(env)')
        addCodeLine(edit, '        if len(frames) > 0:')
        addCodeLine(edit, '            for frame in frames:')
        addCodeLine(edit, '                print(f"Rendering frame {frame}...")')
        addCodeLine(edit, '                bpy.context.scene.frame_set(frame)')
        addCodeLine(edit, '                bpy.ops.render.render(write_still=True)')
        addCodeLine(edit, '        else:')
        addCodeLine(edit, '            bpy.ops.render.render(write_still=True)')
        addCodeLine(edit, '')
        addCodeLine(edit, '        if not "#" in env.RenderingFilename:')
        addCodeLine(edit, '            print("Renaming output files...")')
        addCodeLine(edit, '            renameOutputFiles(env)')
    elif sceneType == SourceCodeTemplateSceneType.InputScene:
        addCodeLine(edit, '    print(f"Saving scene to {env.InputSceneFilename}")')
        addCodeLine(edit, '    bpy.ops.wm.save_mainfile(filepath=env.InputSceneFilename, check_existing=False)')