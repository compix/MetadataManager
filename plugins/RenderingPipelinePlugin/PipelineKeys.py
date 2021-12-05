BaseFolder = 'rp_base_folder'
PipelineType = 'rp_pipeline_type'
PipelineClass = 'rp_pipeline_class'
RenderSceneCreationScript = 'rp_render_scene_creation_script'
InputSceneCreationScript = 'rp_input_scene_creation_script'
NukeScript = 'rp_nuke_script'
BlenderCompositingScript = 'rp_blender_compositing_script'
ProductTable = 'rp_product_table'
ProductTableSheetName = 'rp_product_table_sheet_name'
RenderSettings = 'rp_render_settings'
ReplaceGermanCharacters = 'rp_replace_german_characters'
PerspectiveCodes = 'rp_perspective_codes'
RenderingExtension = 'rp_rendering_extension'
PostOutputExtensions = 'rp_post_output_extensions'

BaseScenesFolder = 'rp_base_scenes_folder'
RenderScenesFolder = 'rp_render_scenes_folder'
InputScenesFolder = 'rp_input_scenes_folder'
CreatedInputScenesFolder = 'rp_created_input_scenes_folder'
EnvironmentScenesFolder = 'rp_environment_scenes_folder'
NukeScenesFolder = 'rp_nuke_scenes_folder'
BlenderCompositingScenesFolder = 'rp_blender_compositing_scenes_folder'
RenderingsFolder = 'rp_renderings_folder'
PostFolder = 'rp_post_folder'
DeliveryFolder = 'rp_delivery_folder'

SidNaming = 'rp_sid_naming'
BaseSceneNaming = 'rp_base_scene_naming'
RenderSceneNaming = 'rp_render_scene_naming'
InputSceneNaming = 'rp_input_scene_naming'
CreatedInputSceneNaming = 'rp_created_input_scene_naming'
EnvironmentSceneNaming = 'rp_environment_scene_naming'
NukeSceneNaming = 'rp_nuke_scene_naming'
BlenderCompositingSceneNaming = 'rp_blender_compositing_scene_naming'
RenderingNaming = 'rp_rendering_naming'
PostNaming = 'rp_post_naming'
DeliveryNaming = 'rp_delivery_naming'

Perspective = 'rp_perspective'
SceneExtension = 'rp_scene_extension'
Mapping = 'rp_mapping'

BaseSceneFilename = 'rp_base_scene_filename'
InputSceneFilename = 'rp_input_scene_filename'
CreatedInputSceneFilename = 'rp_created_input_scene_filename'
RenderSceneFilename = 'rp_render_scene_filename'
EnvironmentSceneFilename = 'rp_environment_scene_filename'
NukeSceneFilename = 'rp_nuke_scene_filename'
BlenderCompositingSceneFilename = 'rp_blender_compositing_scene_filename'
RenderingFilename = 'rp_rendering_filename'
PostFilename = 'rp_post_filename'
DeliveryFilename = 'rp_delivery_filename'

SaveRenderScene = 'rp_save_render_scene'
RenderInSceneCreationScript = 'rp_render_in_scene_creation_script'
ApplyCameraFraming = 'rp_apply_camera_framing'
Frames = 'rp_frames'

# Deadline
DeadlinePriority = 'rp_deadline_priority'
DeadlineInputScenePool = 'rp_deadline_input_scene_pool'
DeadlineRenderScenePool = 'rp_deadline_render_scene_pool'
DeadlineRenderingPool = 'rp_deadline_rendering_pool'
DeadlineNukePool = 'rp_deadline_nuke_pool'
DeadlineBlenderCompositingPool = 'rp_deadline_blender_compositing_pool'
DeadlineDeliveryPool = 'rp_deadline_delivery_pool'
DeadlineInputSceneTimeout = 'rp_deadline_input_scene_timeout'
DeadlineRenderSceneTimeout = 'rp_deadline_render_scene_timeout'
DeadlineRenderingTimeout = 'rp_deadline_rendering_timeout'
DeadlineNukeTimeout = 'rp_deadline_nuke_timeout'
DeadlineBlenderCompositingTimeout = 'rp_deadline_blender_compositing_timeout'
DeadlineDeliveryTimeout = 'rp_deadline_delivery_timeout'

# 3dsMax
Max3dsVersion = 'rp_3dsmax_version'

# Nuke
NukeVersion = 'rp_nuke_version'

# Blender
BlenderVersion = 'rp_blender_version'

# Unreal Engine
UnrealEngineVersion = 'rp_unreal_engine_version'

def getKeyWithPerspective(key: str, perspective: str):
    return f'{key}_{perspective}'