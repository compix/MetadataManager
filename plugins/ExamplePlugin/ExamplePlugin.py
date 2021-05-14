from plugin.Plugin import Plugin
from ExamplePlugin.ExamplePluginLib import util

class ExamplePlugin(Plugin):
    def init(self):
        util.testPrint()

    @staticmethod
    def dependentPluginNames():
        return ["RenderingPipelinePlugin"]