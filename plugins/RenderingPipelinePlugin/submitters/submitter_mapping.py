from RenderingPipelinePlugin.submitters.BlenderCompositingSubmitter import BlenderCompositingSubmitter
from RenderingPipelinePlugin.submitters.DeliveryCopySubmitter import DeliveryCopySubmitter
from RenderingPipelinePlugin.submitters.Max3dsSubmitter import Max3dsInputSceneCreationSubmitter, Max3dsRenderSceneCreationSubmitter, Max3dsRenderingSubmitter
from RenderingPipelinePlugin.submitters.MetadataManagerTaskSubmitter import MetadataManagerTaskSubmitter
from RenderingPipelinePlugin.submitters.UnrealEngineSubmitter import UnrealEngineInputSceneCreationSubmitter, UnrealEngineRenderSceneCreationSubmitter, UnrealEngineRenderingSubmitter
from RenderingPipelinePlugin.submitters.BlenderSubmitter import BlenderInputSceneCreationSubmitter, BlenderRenderSceneCreationSubmitter, BlenderRenderingSubmitter
from RenderingPipelinePlugin.submitters.NukeSubmitter import NukeSubmitter

ClassNameToClassMap = {
    'Max3dsInputSceneCreationSubmitter': Max3dsInputSceneCreationSubmitter,
    'Max3dsRenderSceneCreationSubmitter': Max3dsRenderSceneCreationSubmitter,
    'Max3dsRenderingSubmitter': Max3dsRenderingSubmitter,
    'UnrealEngineInputSceneCreationSubmitter': UnrealEngineInputSceneCreationSubmitter,
    'UnrealEngineRenderSceneCreationSubmitter': UnrealEngineRenderSceneCreationSubmitter,
    'UnrealEngineRenderingSubmitter': UnrealEngineRenderingSubmitter,
    'BlenderInputSceneCreationSubmitter': BlenderInputSceneCreationSubmitter,
    'BlenderRenderSceneCreationSubmitter': BlenderRenderSceneCreationSubmitter,
    'BlenderRenderingSubmitter': BlenderRenderingSubmitter,
    'NukeSubmitter': NukeSubmitter,
    'BlenderCompositingSubmitter': BlenderCompositingSubmitter,
    'DeliveryCopySubmitter': DeliveryCopySubmitter,
    'MetadataManagerTaskSubmitter': MetadataManagerTaskSubmitter
}