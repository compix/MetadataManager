import os
import typing
import photoshop.api as ps
from photoshop.api._document import Document
from photoshop.api._artlayer import ArtLayer
from photoshop.api._layerSet import LayerSet
from photoshop.api._channel import Channel
from photoshop.api.enumerations import CopyrightedType, DialogModes, LayerCompressionType, MatteType, RasterizeType, SaveOptions, Urgency, TiffEncodingType, ElementPlacement
from VisualScripting.node_exec.base_nodes import ColorInput, SliderInput, VariableInputCountNode, defInlineNode, defNode
from enum import Enum, IntEnum
import re

PHOTOSHOP_IDENTIFIER = "Photoshop"

IMPORTS = [
    'from photoshop.api import NewDocumentMode, DocumentFill, BitsPerChannelType',
    'from photoshop.api.enumerations import CopyrightedType, DialogModes, LayerCompressionType, MatteType, RasterizeType, SaveOptions, Urgency, TiffEncodingType, ElementPlacement',
    'from VisualScriptingExtensions.third_party_extensions.photoshop_nodes import ExrColorDepth, ExrTilingType, ExrCompressionMethod, ToLayerPlacement'
]

class ToLayerPlacement(IntEnum):
    PlaceAfter = 4
    PlaceBefore = 3

class ExrColorDepth(Enum):
    FLOAT = """LOAT"""
    HALF = """ALF"""
    UINT = """INT"""

class ExrTilingType(Enum):
    Single = """ingle"""
    Mipmap = """ipmap"""
    Ripmap = """ipmap"""

class ExrCompressionMethod(Enum):
    none = """one"""
    PIZ = """IZ"""
    ZIP = """ip"""
    ZIPS = """IPS"""
    RLE = """LE"""
    PXR24 = """XR24"""
    B44 = """44"""    
    B44A = """44A"""
    DWAA = """WAA"""
    DWAB = """WAB"""

class ExrSaveOptions(object):
    def __init__(self, writeLumaChroma=False, writeTiles=False, ignoreHiddenLayers=True, renameSingleLayerToDefault=False, lumaChroma: int = 2,
                 tilesX=128, tilesY=128, dwaCompressionLevel: float = 45.0, colorDepth: ExrColorDepth = ExrColorDepth.FLOAT,
                 compressionMethod: ExrCompressionMethod = ExrCompressionMethod.ZIP, tilingType: ExrTilingType = ExrTilingType.Single) -> None:
        super().__init__()

        self.writeLumaChroma = writeLumaChroma
        self.writeTiles = writeTiles
        self.ignoreHiddenLayers = ignoreHiddenLayers
        self.renameSingleLayerToDefault = renameSingleLayerToDefault
        self.lumaChroma = lumaChroma
        self.tilesX = tilesX
        self.tilesY = tilesY
        self.dwaCompressionLevel = dwaCompressionLevel
        self.colorDepth = colorDepth
        self.compressionMethod = compressionMethod
        self.tilingType = tilingType

def getEnumValue(e: Enum):
    return e.value if isinstance(e, Enum) else e

class DocumentWrapper(object):
    def __init__(self, doc: Document, app: ps.Application) -> None:
        super().__init__()

        self.psDoc: Document = doc
        self.psApp: ps.Application = app

class ArtLayerWrapper(object):
    def __init__(self, layer: ArtLayer, doc: DocumentWrapper) -> None:
        super().__init__()

        self.psLayer = layer
        self.psDoc = doc.psDoc
        self.psApp = doc.psApp
        self.doc = doc

class LayerSetWrapper(object):
    def __init__(self, layerSet: LayerSet, doc: DocumentWrapper) -> None:
        super().__init__()

        self.psLayer = layerSet
        self.psDoc = doc.psDoc
        self.psApp = doc.psApp
        self.doc = doc

class ChannelWrapper(object):
    def __init__(self, channel: Channel, doc: DocumentWrapper) -> None:
        super().__init__()

        self.psChannel = channel
        self.psDoc = doc.psDoc
        self.psApp = doc.psApp
        self.doc = doc

class EvaluateJavascriptNode(VariableInputCountNode):
    __identifier__ = PHOTOSHOP_IDENTIFIER
    NODE_NAME = 'Photoshop Evaluate Javascript'

    def __init__(self):
        super(EvaluateJavascriptNode, self).__init__()

        self.add_exec_input('Execute')
        self.add_input("doc")
        self.add_input("script")
        
        self.add_exec_output('Execute')
        self.add_output("Document")
        self.add_output("return")

    @staticmethod
    def execute(doc: DocumentWrapper, script: str, *argv):
        ensureActiveDocument(doc)

        for i, arg in enumerate(argv):
            argName = f'in{i}'

            if isinstance(arg, str):
                arg = '{!r}'.format(arg)

            script = re.sub(r"\b%s\b" % argName, arg, script)

        return doc, doc.psDoc.eval_javascript(script)

def ensureActiveDocument(doc: DocumentWrapper):
    if doc.psApp.activeDocument != doc.psDoc:
        doc.psApp.activeDocument = doc.psDoc

@defNode('Create Photoshop App', isExecutable=True, returnNames=['app'], identifier=PHOTOSHOP_IDENTIFIER)
def createApp(version: str=None) -> ps.Application:
    return ps.Application(version=version)

@defNode('Photoshop Close All Documents', isExecutable=True, returnNames=['app'], identifier=PHOTOSHOP_IDENTIFIER)
def closeAllDocuments(app: ps.Application):
    for doc in [d for d in app.documents]:
        doc.close()

    return app

@defNode('Add Photoshop Document', isExecutable=True, returnNames=['Document'], identifier=PHOTOSHOP_IDENTIFIER, imports=IMPORTS)
def addDocument(app: ps.Application, 
        width: int = 960,
        height: int = 540,
        resolution: float = 72.0,
        name: str = None,
        mode: ps.NewDocumentMode = ps.NewDocumentMode.NewRGB,
        initialFill: ps.DocumentFill = ps.DocumentFill.Transparent,
        pixelAspectRatio: float = 1.0,
        bitsPerChannel: ps.BitsPerChannelType = ps.BitsPerChannelType.Document8Bits,
        colorProfileName: str = None) -> DocumentWrapper:
    
    doc = DocumentWrapper(app.documents.add(width, height, resolution, name, mode, initialFill, pixelAspectRatio, bitsPerChannel, colorProfileName), app)
    return doc

@defNode('Duplicate Photoshop Document', isExecutable=True, returnNames=['Old Document', 'New Document'], identifier=PHOTOSHOP_IDENTIFIER)
def duplicateDocument(doc: DocumentWrapper, name=None, mergeLayerOnly=False) -> typing.Tuple[DocumentWrapper, DocumentWrapper]:
    ensureActiveDocument(doc)
    newDoc = DocumentWrapper(doc.psDoc.duplicate(name, mergeLayerOnly), doc.psApp)
    
    return doc, newDoc

def setIfValid(targetObj, key, value):
    if not value is None:
        setattr(targetObj, key, value)

@defNode('Photoshop Set Metadata', isExecutable=True, returnNames=['Document'], identifier=PHOTOSHOP_IDENTIFIER)
def setMetadata(doc: DocumentWrapper, author: str = None, authorPosition: str = None, caption: str = None, 
                captionWriter: str = None, category: str = None, city: str = None,
                country: str = None, copyrightNotice: str = None, copyrighted: CopyrightedType = None, 
                credit: str = None, headline: str = None, instructions: str = None, jobName: str = None,
                keywords: typing.List[str]=None, provinceState: str=None, source: str=None, ownerUrl: str=None, 
                supplementalCategories: typing.List[str]=None, title: str=None, transmissionReference: str=None, urgency: Urgency=None) -> DocumentWrapper:
    ensureActiveDocument(doc)

    i = doc.psDoc.info
    
    setIfValid(i, 'author', author)
    setIfValid(i, 'authorPosition', authorPosition)
    setIfValid(i, 'caption', caption)
    setIfValid(i, 'captionWriter', captionWriter)
    setIfValid(i, 'category', category)
    setIfValid(i, 'city', city)
    setIfValid(i, 'country', country)
    setIfValid(i, 'copyrightNotice', copyrightNotice)
    setIfValid(i, 'copyrighted', copyrighted)
    #setIfValid(i, 'creationDate', creationDate)
    setIfValid(i, 'credit', credit)
    setIfValid(i, 'headline', headline)
    setIfValid(i, 'instructions', instructions)
    setIfValid(i, 'jobName', jobName)
    setIfValid(i, 'keywords', keywords)
    setIfValid(i, 'provinceState', provinceState)
    setIfValid(i, 'source', source)
    setIfValid(i, 'ownerUrl', ownerUrl)
    setIfValid(i, 'supplementalCategories', supplementalCategories)
    setIfValid(i, 'title', title)
    setIfValid(i, 'transmissionReference', transmissionReference)
    setIfValid(i, 'urgency', urgency)

    return doc

@defNode('Close Photoshop Document', isExecutable=True, identifier=PHOTOSHOP_IDENTIFIER)
def closePhotoshopDocument(doc: DocumentWrapper):
    ensureActiveDocument(doc)
    doc.psDoc.close()

@defNode('Photoshop RGB Color', returnNames=['RGB'], inputInfo={'colorArray': ColorInput()}, identifier=PHOTOSHOP_IDENTIFIER)
def createRGBColor(colorArray: typing.Tuple[int,int,int,int]=None) -> ps.SolidColor:
    c = ps.SolidColor()
    c.rgb.red = colorArray[0]
    c.rgb.green = colorArray[1]
    c.rgb.blue = colorArray[2]

    return c

@defNode('Photoshop Text Layer', isExecutable=True, returnNames=['Document', 'Text Layer'], identifier=PHOTOSHOP_IDENTIFIER)
def createTextLayer(doc: DocumentWrapper, text: str, size: int = 40, color: ps.SolidColor = None, posX: int = None, posY: int = None) -> typing.Tuple[DocumentWrapper, ArtLayerWrapper]:
    ensureActiveDocument(doc)

    textLayer = doc.psDoc.artLayers.add()
    textLayer.kind = ps.LayerKind.TextLayer
    textLayer.textItem.contents = text
    textLayer.textItem.size = size

    if color:
        textLayer.textItem.color = color

    if posX or posY:
        textLayer.textItem.position = [posX or 0, posY or 0]

    return doc, textLayer

@defNode('Photoshop JPEG Save Options', returnNames=['Options'], identifier=PHOTOSHOP_IDENTIFIER, inputInfo={'quality': SliderInput(0,12)})
def jpegSaveOptions(quality=5, embedColorProfile=True, matte: MatteType=MatteType.NoMatte) -> ps.JPEGSaveOptions:
    return ps.JPEGSaveOptions(quality, embedColorProfile, matte)

@defNode('Photoshop PNG Save Options', returnNames=['Options'], identifier=PHOTOSHOP_IDENTIFIER)
def pngSaveOptions(interlaced=False, compression=True) -> ps.PNGSaveOptions:
    options = ps.PNGSaveOptions()
    options.interlaced = interlaced
    options.compression = compression
    return options

@defNode('Photoshop TIFF Save Options', returnNames=['Options'], identifier=PHOTOSHOP_IDENTIFIER, inputInfo={'jpegQuality': SliderInput(0,12)})
def tiffSaveOptions(saveAlphaChannels=True, saveLayers=True, saveTransparency=True, saveAnnotations=True, 
                    embedColorProfile=True, imageCompression: TiffEncodingType = TiffEncodingType.NoTIFFCompression,
                    interleaveChannels=True, jpegQuality=10, layerCompression: LayerCompressionType = LayerCompressionType.ZIPLayerCompression,
                    saveImagePyramid=False, saveSpotColors=False) -> ps.TiffSaveOptions:
    options = ps.TiffSaveOptions()
    options.alphaChannels = saveAlphaChannels
    options.layers = saveLayers
    options.transparency = saveTransparency
    options.annotations = saveAnnotations
    options.embedColorProfile = embedColorProfile
    options.imageCompression = imageCompression
    options.interleaveChannels = interleaveChannels
    options.jpegQuality = jpegQuality
    options.layerCompression = layerCompression
    options.saveImagePyramid = saveImagePyramid
    options.spotColors = saveSpotColors
    return options

@defNode('Photoshop EXR Save Options', returnNames=['Options'], identifier=PHOTOSHOP_IDENTIFIER, inputInfo={'quality': SliderInput(0,12)})
def exrSaveOptions(writeLumaChroma=False, writeTiles=False, ignoreHiddenLayers=True, renameSingleLayerToDefault=False, lumaChroma: int = 2,
                   tilesX=128, tilesY=128, dwaCompressionLevel: float = 45.0, colorDepth: ExrColorDepth = ExrColorDepth.FLOAT,
                   compressionMethod: ExrCompressionMethod = ExrCompressionMethod.ZIP, tilingType: ExrTilingType = ExrTilingType.Single) -> ExrSaveOptions:
    return ExrSaveOptions(writeLumaChroma, writeTiles, ignoreHiddenLayers, renameSingleLayerToDefault, lumaChroma, tilesX, tilesY,
                          dwaCompressionLevel, colorDepth, compressionMethod, tilingType)

def saveAsExr(doc: DocumentWrapper, filename: str, options: ExrSaveOptions):
    idsave = doc.psApp.charIDToTypeID( "save" )
    desc25 = ps.ActionDescriptor()
    idAs = doc.psApp.charIDToTypeID( "As  " )
    desc26 = ps.ActionDescriptor()
    idiolc = doc.psApp.charIDToTypeID( "iolc" )
    desc26.putBoolean( idiolc, options.writeLumaChroma )
    idiowt = doc.psApp.charIDToTypeID( "iowt" )
    desc26.putBoolean( idiowt, options.writeTiles )
    idiohl = doc.psApp.charIDToTypeID( "iohl" )
    desc26.putBoolean( idiohl, options.ignoreHiddenLayers )
    idiosl = doc.psApp.charIDToTypeID( "iosl" )
    desc26.putBoolean( idiosl, options.renameSingleLayerToDefault )
    idiosw = doc.psApp.charIDToTypeID( "iosw" )
    desc26.putBoolean( idiosw, False )
    idiocs = doc.psApp.charIDToTypeID( "iocs" )
    desc26.putInteger( idiocs, options.lumaChroma )
    idiotw = doc.psApp.charIDToTypeID( "iotw" )
    desc26.putInteger( idiotw, options.tilesX )
    idioth = doc.psApp.charIDToTypeID( "ioth" )
    desc26.putInteger( idioth, options.tilesY )
    idiocl = doc.psApp.charIDToTypeID( "iocl" )
    desc26.putDouble( idiocl, options.dwaCompressionLevel )
    idiodt = doc.psApp.charIDToTypeID( "iodt" )
    desc26.putString( idiodt, getEnumValue(options.colorDepth) )
    idioct = doc.psApp.charIDToTypeID( "ioct" )
    desc26.putString( idioct, getEnumValue(options.compressionMethod) )
    idiotl = doc.psApp.charIDToTypeID( "iotl" )
    desc26.putString( idiotl, getEnumValue(options.tilingType) )
    idthreedioExrIO = doc.psApp.stringIDToTypeID( "3d-io Exr-IO" )
    desc25.putObject( idAs, idthreedioExrIO, desc26 )
    idIn = doc.psApp.charIDToTypeID( "In  " )
    desc25.putPath( idIn, filename )
    idDocI = doc.psApp.charIDToTypeID( "DocI" )
    desc25.putInteger( idDocI, 1817 )
    idsaveStage = doc.psApp.stringIDToTypeID( "saveStage" )
    idsaveStageType = doc.psApp.stringIDToTypeID( "saveStageType" )
    idsaveBegin = doc.psApp.stringIDToTypeID( "saveBegin" )
    desc25.putEnumerated( idsaveStage, idsaveStageType, idsaveBegin )
    doc.psApp.executeAction( idsave, desc25, DialogModes.DisplayNoDialogs )

def openExr(doc: DocumentWrapper, filename: str):
    idOpn = doc.psApp.charIDToTypeID( "Opn " )
    desc1 = ps.ActionDescriptor()
    idnull = doc.psApp.charIDToTypeID( "null" )
    desc1.putPath( idnull, filename )
    idAs = doc.psApp.charIDToTypeID( "As  " )
    desc2 = ps.ActionDescriptor()
    idioty = doc.psApp.charIDToTypeID( "ioty" )
    desc2.putBoolean( idioty, False )
    idiosa = doc.psApp.charIDToTypeID( "iosa" )
    desc2.putBoolean( idiosa, False )
    idioac = doc.psApp.charIDToTypeID( "ioac" )
    desc2.putBoolean( idioac, False )
    idioal = doc.psApp.charIDToTypeID( "ioal" )
    desc2.putBoolean( idioal, False )
    idiocm = doc.psApp.charIDToTypeID( "iocm" )
    desc2.putBoolean( idiocm, False )
    idioca = doc.psApp.charIDToTypeID( "ioca" )
    desc2.putBoolean( idioca, False )
    idiocd = doc.psApp.charIDToTypeID( "iocd" )
    desc2.putBoolean( idiocd, False )
    idioll = doc.psApp.charIDToTypeID( "ioll" )
    desc2.putBoolean( idioll, False )
    idioci = doc.psApp.charIDToTypeID( "ioci" )
    desc2.putBoolean( idioci, False )
    idiodw = doc.psApp.charIDToTypeID( "iodw" )
    desc2.putBoolean( idiodw, False )
    idiocg = doc.psApp.charIDToTypeID( "iocg" )
    desc2.putBoolean( idiocg, False )
    idiosr = doc.psApp.charIDToTypeID( "iosr" )
    desc2.putBoolean( idiosr, True )
    idiocw = doc.psApp.charIDToTypeID( "iocw" )
    desc2.putInteger( idiocw, 1000 )
    idthreedioExrIO = doc.psApp.stringIDToTypeID( "3d-io Exr-IO" )
    desc1.putObject( idAs, idthreedioExrIO, desc2 )
    doc.psApp.executeAction( idOpn, desc1, DialogModes.DisplayNoDialogs)

@defNode('Photoshop Save As', isExecutable=True, returnNames=['Document'], identifier=PHOTOSHOP_IDENTIFIER)
def saveAs(doc: DocumentWrapper, filename: str, options=None) -> DocumentWrapper:
    ensureActiveDocument(doc)

    if options == None:
        _,ext = os.path.splitext(filename)
        if ext and len(ext) > 0:
            ext = ext.lower()[1:]
            if ext in ['jpg', 'jpeg']:
                options = jpegSaveOptions()
            elif ext == 'png':
                options = pngSaveOptions()
            elif ext in ['tif', 'tiff']:
                options = tiffSaveOptions()
            elif ext == 'exr':
                options = exrSaveOptions()
            else:
                options = ps.PhotoshopSaveOptions()
    
    if isinstance(options, ExrSaveOptions):
        saveAsExr(doc, filename, options)
    else:
        doc.psDoc.saveAs(filename, options, asCopy=True)

    return doc

@defNode('Photoshop Place Image', isExecutable=True, returnNames=['Document', 'Art Layer'], identifier=PHOTOSHOP_IDENTIFIER)
def placeImage(doc: DocumentWrapper, filename: str, layerName: str = None, rasterize=False) -> typing.Tuple[DocumentWrapper, ArtLayerWrapper]:
    ensureActiveDocument(doc)

    idPlc = doc.psApp.charIDToTypeID("Plc ") 
    desc11 = ps.ActionDescriptor()
    idnull = doc.psApp.charIDToTypeID("null")
    
    desc11.putPath(idnull, filename)
    idFTcs = doc.psApp.charIDToTypeID("FTcs") 
    idQCSt = doc.psApp.charIDToTypeID("QCSt")   
    idQcsa = doc.psApp.charIDToTypeID("Qcsa") 
    desc11.putEnumerated( idFTcs, idQCSt, idQcsa)
    idOfst = doc.psApp.charIDToTypeID("Ofst")     
    desc12 = ps.ActionDescriptor()     
    idHrzn = doc.psApp.charIDToTypeID("Hrzn")    
    idPxl = doc.psApp.charIDToTypeID("#Pxl")      
    desc12.putUnitDouble(idHrzn, idPxl, 0.000000)     
    idVrtc = doc.psApp.charIDToTypeID("Vrtc")    
    idPxl = doc.psApp.charIDToTypeID("#Pxl")    
    desc12.putUnitDouble(idVrtc, idPxl, 0.000000)
    idOfst = doc.psApp.charIDToTypeID("Ofst")
    desc11.putObject(idOfst, idOfst, desc12)
    doc.psApp.executeAction(idPlc, desc11, ps.DialogModes.DisplayNoDialogs)

    layer: ArtLayer = doc.psDoc.activeLayer

    if layerName:
        layer.name = layerName
    
    if rasterize:
        layer.rasterize(RasterizeType.EntireLayer)

    return doc, ArtLayerWrapper(layer, doc)

@defNode('Photoshop Layer Rasterize', isExecutable=True, returnNames=['Document', 'Art Layer'], identifier=PHOTOSHOP_IDENTIFIER)
def rasterizeLayer(layer: ArtLayerWrapper, rasterizeType: RasterizeType = RasterizeType.EntireLayer) -> typing.Tuple[DocumentWrapper, ArtLayerWrapper]:
    ensureActiveDocument(layer.doc)

    layer.psLayer.rasterize(rasterizeType)

    return layer.doc, layer

@defNode('Photoshop Get Layer By Name', returnNames=['Document', 'Art Layer'], identifier=PHOTOSHOP_IDENTIFIER)
def getLayerByName(doc: DocumentWrapper, layerName: str):
    ensureActiveDocument(doc)
    
    layer = f'app.activeDocument.artLayers.getByName("{layerName}")'
    return doc, doc.psDoc.eval_javascript(layer)

@defNode('Photoshop Create Layer Set', isExecutable=True, returnNames=['Document', 'Layer Set'], identifier=PHOTOSHOP_IDENTIFIER)
def createLayerSet(doc: DocumentWrapper, name: str=None):
    layerSet = doc.psDoc.layerSets.add()
    if name:
        layerSet.name = name
        
    return doc, LayerSetWrapper(layerSet, doc)

@defNode('Photoshop Move To Layer Set', isExecutable=True, returnNames=['Document', 'Source', 'Target'], identifier=PHOTOSHOP_IDENTIFIER)
def moveToLayerSet(source, target: LayerSetWrapper, placementType: ElementPlacement = ElementPlacement.PlaceInside):
    ensureActiveDocument(source.doc)

    source.psLayer.move(target.psLayer, placementType)

    return source.doc, source, target

@defNode('Photoshop Move To Layer', isExecutable=True, returnNames=['Document', 'Source', 'Target'], identifier=PHOTOSHOP_IDENTIFIER)
def moveToLayer(source, target: ArtLayerWrapper, placementType: ToLayerPlacement = ToLayerPlacement.PlaceAfter):
    ensureActiveDocument(source.doc)
    
    source.psLayer.move(target.psLayer, placementType)

    return source.doc, source, target

@defNode("Photoshop Layer Add", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerAdd(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.add()

    return layer.doc, layer

@defNode("Photoshop Layer Adjust Brightness Contrast", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerAdjustBrightnessContrast(layer: ArtLayerWrapper, brightness, contrast):
    ensureActiveDocument(layer.doc)

    layer.psLayer.adjustBrightnessContrast(brightness, contrast)

    return layer.doc, layer

@defNode("Photoshop Layer Adjust Color Balance", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerAdjustColorBalance(layer: ArtLayerWrapper, shadows, midtones, highlights, preserveLuminosity):
    ensureActiveDocument(layer.doc)

    layer.psLayer.adjustColorBalance(shadows, midtones, highlights, preserveLuminosity)

    return layer.doc, layer

@defNode("Photoshop Layer Adjust Curves", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerAdjustCurves(layer: ArtLayerWrapper, curveShape):
    ensureActiveDocument(layer.doc)

    layer.psLayer.adjustCurves(curveShape)

    return layer.doc, layer

@defNode("Photoshop Layer Adjust Levels", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerAdjustLevels(layer: ArtLayerWrapper, inputRangeStart, inputRangeEnd, inputRangeGamma, outputRangeStart, outputRangeEnd):
    ensureActiveDocument(layer.doc)

    layer.psLayer.adjustLevels(inputRangeStart, inputRangeEnd, inputRangeGamma, outputRangeStart, outputRangeEnd)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Add Noise", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyAddNoise(layer: ArtLayerWrapper, amount, distribution, monochromatic):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyAddNoise(amount, distribution, monochromatic)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Average", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyAverage(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyAverage()

    return layer.doc, layer

@defNode("Photoshop Layer Apply Blur", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyBlur(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyBlur()

    return layer.doc, layer

@defNode("Photoshop Layer Apply Blur More", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyBlurMore(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyBlurMore()

    return layer.doc, layer

@defNode("Photoshop Layer Apply Clouds", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyClouds(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyClouds()

    return layer.doc, layer

@defNode("Photoshop Layer Apply Custom Filter", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyCustomFilter(layer: ArtLayerWrapper, characteristics, scale, offset):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyCustomFilter(characteristics, scale, offset)

    return layer.doc, layer

@defNode("Photoshop Layer Apply De Interlace", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyDeInterlace(layer: ArtLayerWrapper, eliminateFields, createFields):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyDeInterlace(eliminateFields, createFields)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Despeckle", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyDespeckle(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyDespeckle()

    return layer.doc, layer

@defNode("Photoshop Layer Apply Difference Clouds", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyDifferenceClouds(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyDifferenceClouds()

    return layer.doc, layer

@defNode("Photoshop Layer Apply Diffuse Glow", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyDiffuseGlow(layer: ArtLayerWrapper, graininess, amount, clear_amount):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyDiffuseGlow(graininess, amount, clear_amount)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Displace", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyDisplace(layer: ArtLayerWrapper, horizontalScale, verticalScale, displacementType, undefinedAreas, displacementMapFile):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyDisplace(horizontalScale, verticalScale, displacementType, undefinedAreas, displacementMapFile)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Dust And Scratches", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyDustAndScratches(layer: ArtLayerWrapper, radius, threshold):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyDustAndScratches(radius, threshold)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Gaussian Blur", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyGaussianBlur(layer: ArtLayerWrapper, radius):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyGaussianBlur(radius)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Glass Effect", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyGlassEffect(layer: ArtLayerWrapper, distortion, smoothness, scaling, invert, texture, textureFile):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyGlassEffect(distortion, smoothness, scaling, invert, texture, textureFile)

    return layer.doc, layer

@defNode("Photoshop Layer Apply High Pass", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyHighPass(layer: ArtLayerWrapper, radius):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyHighPass(radius)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Lens Blur", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyLensBlur(layer: ArtLayerWrapper, source, focalDistance, invertDepthMap, shape, radius, bladeCurvature, rotation, brightness, threshold, amount, distribution, monochromatic):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyLensBlur(source, focalDistance, invertDepthMap, shape, radius, bladeCurvature, rotation, brightness, threshold, amount, distribution, monochromatic)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Lens Flare", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyLensFlare(layer: ArtLayerWrapper, brightness, flareCenter, lensType):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyLensFlare(brightness, flareCenter, lensType)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Maximum", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyMaximum(layer: ArtLayerWrapper, radius):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyMaximum(radius)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Median Noise", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyMedianNoise(layer: ArtLayerWrapper, radius):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyMedianNoise(radius)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Minimum", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyMinimum(layer: ArtLayerWrapper, radius):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyMinimum(radius)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Motion Blur", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyMotionBlur(layer: ArtLayerWrapper, angle, radius):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyMotionBlur(angle, radius)

    return layer.doc, layer

@defNode("Photoshop Layer Apply NTSC", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyNTSC(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyNTSC()

    return layer.doc, layer

@defNode("Photoshop Layer Apply Ocean Ripple", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyOceanRipple(layer: ArtLayerWrapper, size, magnitude):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyOceanRipple(size, magnitude)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Offset", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyOffset(layer: ArtLayerWrapper, horizontal, vertical, undefinedAreas):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyOffset(horizontal, vertical, undefinedAreas)

    return layer.doc, layer

@defNode("Photoshop Layer Apply Pinch", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerApplyPinch(layer: ArtLayerWrapper, amount):
    ensureActiveDocument(layer.doc)

    layer.psLayer.applyPinch(amount)

    return layer.doc, layer

@defNode("Photoshop Layer Duplicate", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerDuplicate(layer: ArtLayerWrapper, relativeObject= None, insertionLocation= None):
    ensureActiveDocument(layer.doc)

    layer.psLayer.duplicate(relativeObject, insertionLocation)

    return layer.doc, layer

@defNode("Photoshop Layer Invert", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerInvert(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.invert()

    return layer.doc, layer

@defNode("Photoshop Layer Link", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerLink(layer: ArtLayerWrapper, with_layer):
    ensureActiveDocument(layer.doc)

    layer.psLayer.link(with_layer)

    return layer.doc, layer

@defNode("Photoshop Layer Merge", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerMerge(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.merge()

    return layer.doc, layer

@defNode("Photoshop Layer Move", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerMove(layer: ArtLayerWrapper, relativeObject, insertionLocation):
    ensureActiveDocument(layer.doc)

    layer.psLayer.move(relativeObject, insertionLocation)

    return layer.doc, layer

@defNode("Photoshop Layer Posterize", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerPosterize(layer: ArtLayerWrapper, levels):
    ensureActiveDocument(layer.doc)

    layer.psLayer.posterize(levels)

    return layer.doc, layer

@defNode("Photoshop Layer Remove", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerRemove(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.psLayer.remove()

    return layer.doc, layer

@defNode("Photoshop Layer Unlink", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def artLayerUnlink(layer: ArtLayerWrapper, with_layer):
    ensureActiveDocument(layer.doc)

    layer.psLayer.unlink(with_layer)

    return layer.doc, layer

@defNode("Photoshop Layer Opacity", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def setLayerOpacity(layer: ArtLayerWrapper, opacity: float = 0.0):
    ensureActiveDocument(layer.doc)

    layer.psLayer.app.opacity = opacity

    return layer.doc, layer

@defNode("Photoshop Layer Fill Opacity", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def setLayerFillOpaciy(layer: ArtLayerWrapper, opacity: float = 0.0):
    ensureActiveDocument(layer.doc)

    layer.psLayer.fillOpacity = opacity

    return layer.doc, layer

@defNode("Photoshop Layer Set Blend Mode", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def setLayerBlendMode(layer: ArtLayerWrapper, blendMode: ps.BlendMode = ps.BlendMode.NormalBlend):
    ensureActiveDocument(layer.doc)

    layer.psLayer.blendMode = blendMode

    return layer.doc, layer

@defNode("Photoshop Layer Set Name", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def setLayerName(layer: ArtLayerWrapper, name: str):
    ensureActiveDocument(layer.doc)

    layer.psLayer.name = name

    return layer.doc, layer

@defNode("Photoshop Layer Set Filter Mask Density", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def setLayerFilterMaskDensity(layer: ArtLayerWrapper, density: float):
    ensureActiveDocument(layer.doc)

    layer.psLayer.filterMaskDensity = density

    return layer.doc, layer

@defNode("Photoshop Layer Set As Background", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def setLayerAsBackground(layer: ArtLayerWrapper, asBackground: bool=True):
    ensureActiveDocument(layer.doc)

    layer.psLayer.isBackgroundLayer = asBackground

    return layer.doc, layer

@defNode("Photoshop Layer Set Kind", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def setLayerKind(layer: ArtLayerWrapper, kind: ps.LayerKind=ps.LayerKind.NormalLayer):
    ensureActiveDocument(layer.doc)

    layer.psLayer.kind = kind

    return layer.doc, layer

@defNode("Photoshop Layer Get Kind", isExecutable=True, returnNames=["Document", "Art Layer", "Kind"], identifier=PHOTOSHOP_IDENTIFIER)
def getLayerKind(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    return layer.doc, layer, layer.psLayer.kind

@defNode("Photoshop Layer Set Visible", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def setLayerVisible(layer: ArtLayerWrapper, visible: bool=True):
    ensureActiveDocument(layer.doc)

    layer.psLayer.visible = visible

    return layer.doc, layer

@defNode("Photoshop Layer Is Visible", isExecutable=True, returnNames=["Document", "Art Layer", "Visible"], identifier=PHOTOSHOP_IDENTIFIER)
def getLayerVisible(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    return layer.doc, layer, layer.psLayer.visible

@defNode("Photoshop Layer Lock", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def lockLayer(layer: ArtLayerWrapper, locked: bool=True):
    ensureActiveDocument(layer.doc)

    layer.psLayer.allLocked = locked

    return layer.doc, layer

@defNode("Photoshop Layer Is Locked", isExecutable=True, returnNames=["Document", "Art Layer", "Locked"], identifier=PHOTOSHOP_IDENTIFIER)
def isLayerLocked(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    return layer.doc, layer, layer.psLayer.allLocked

@defNode("Photoshop Layer Lock Position", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def lockLayerPosition(layer: ArtLayerWrapper, locked: bool=True):
    ensureActiveDocument(layer.doc)

    layer.psLayer.positionLocked = locked

    return layer.doc, layer

@defNode("Photoshop Layer Lock Pixels", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def lockLayerPixels(layer: ArtLayerWrapper, locked: bool=True):
    ensureActiveDocument(layer.doc)

    layer.psLayer.pixelsLocked = locked

    return layer.doc, layer

@defNode("Photoshop Layer Lock Transparent Pixels", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def lockLayerTransparentPixels(layer: ArtLayerWrapper, locked: bool=True):
    ensureActiveDocument(layer.doc)

    layer.psLayer.transparentPixelsLocked = locked

    return layer.doc, layer

@defNode("Photoshop Select Layer", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def selectLayer(layer: ArtLayerWrapper):
    ensureActiveDocument(layer.doc)

    layer.doc.psDoc.activeLayer = layer.psLayer

    return layer.doc, layer

@defNode("Photoshop Select Layer By Name", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)
def selectLayerByName(doc: DocumentWrapper, layerName: str):
    layer = getLayerByName(doc, layerName)
    layer.doc.psDoc.activeLayer = layer.psLayer

    return layer.doc, layer

@defNode("Photoshop Document Close", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentClose(doc: DocumentWrapper, saving: SaveOptions = SaveOptions.DoNotSaveChanges):
    ensureActiveDocument(doc)

    doc.psDoc.close(saving)

    return doc

@defNode("Photoshop Document Convert Profile", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentConvertProfile(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.convertProfile()

    return doc

@defNode("Photoshop Document Crop", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentCrop(doc: DocumentWrapper, bounds, angle= None, width= None, height= None):
    ensureActiveDocument(doc)

    doc.psDoc.crop(bounds, angle, width, height)

    return doc

@defNode("Photoshop Export Document", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentExportDocument(doc: DocumentWrapper, file_path, exportAs= None, options= None):
    ensureActiveDocument(doc)

    doc.psDoc.exportDocument(file_path, exportAs, options)

    return doc

@defNode("Photoshop Document Flatten", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentFlatten(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.flatten()

    return doc

@defNode("Photoshop Document Merge Visible Layers", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentMergeVisibleLayers(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.mergeVisibleLayers()

    return doc

@defNode("Photoshop Document Paste", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentPaste(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.paste()

    return doc

@defNode("Photoshop Document Print", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentPrint(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.print()

    return doc

@defNode("Photoshop Document Print One Copy", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentPrintOneCopy(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.printOneCopy()

    return doc

@defNode("Photoshop Document Rasterize All Layers", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentRasterizeAllLayers(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.rasterizeAllLayers()

    return doc

@defNode("Photoshop Document Record Measurements", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentRecordMeasurements(doc: DocumentWrapper, source, dataPoints):
    ensureActiveDocument(doc)

    doc.psDoc.recordMeasurements(source, dataPoints)

    return doc

@defNode("Photoshop Document Resize Image", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentResizeImage(doc: DocumentWrapper, width, height, resolution= 72, automatic= 8):
    ensureActiveDocument(doc)

    doc.psDoc.resizeImage(width, height, resolution, automatic)

    return doc

@defNode("Photoshop Save Document", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentSave(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.save()

    return doc

@defNode("Photoshop Document Split Channels", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentSplitChannels(doc: DocumentWrapper):
    ensureActiveDocument(doc)

    doc.psDoc.splitChannels()

    return doc

@defNode("Photoshop Document Suspend History", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentSuspendHistory(doc: DocumentWrapper, historyString, javaScriptString):
    ensureActiveDocument(doc)

    doc.psDoc.suspendHistory(historyString, javaScriptString)

    return doc

@defNode("Photoshop Document Trap", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentTrap(doc: DocumentWrapper, width):
    ensureActiveDocument(doc)

    doc.psDoc.trap(width)

    return doc

@defNode("Photoshop Document Trim", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def documentTrim(doc: DocumentWrapper, trim_type, top= True, left= True, bottom= True, right= True):
    ensureActiveDocument(doc)

    doc.psDoc.trim(trim_type, top, left, bottom, right)

    return doc

@defNode("Photoshop Get Channel By Name", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def getChannelByName(doc: DocumentWrapper, channelName: str):
    ensureActiveDocument(doc)

    channel = doc.psDoc.eval_javascript(f'app.activeDocument.channels.getByName("{channelName}")')

    return doc, ChannelWrapper(channel, doc)

@defNode("Photoshop Channel Add", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def addChannel(doc: DocumentWrapper, channelName: str):
    ensureActiveDocument(doc)

    channel = Channel(doc.psDoc.channels.app.add())
    channel.app.name = channelName

    return doc, ChannelWrapper(channel, doc)

@defNode("Photoshop Channel Remove", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)
def removeChannel(channel: ChannelWrapper):
    ensureActiveDocument(channel.doc)

    channel.psChannel.remove()

    return channel.doc

@defNode("Photoshop Channel Merge", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def mergeChannel(channel: ChannelWrapper):
    ensureActiveDocument(channel.doc)

    channel.psChannel.merge()

    return channel.doc, channel
    
@defNode("Photoshop Channel Duplicate", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def duplicateChannel(channel: ChannelWrapper, targetDocument: DocumentWrapper):
    ensureActiveDocument(channel.doc)

    channel.psChannel.duplicate(targetDocument.psDoc)

    return channel.doc, channel

@defNode("Photoshop Channel Set Opacity", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def setChannelOpacity(channel: ChannelWrapper, opacity: float = 0.0):
    ensureActiveDocument(channel.doc)

    channel.psChannel.opacity = opacity

    return channel.doc, channel

@defNode("Photoshop Channel Set Color", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def setChannelColor(channel: ChannelWrapper, color: ps.SolidColor):
    ensureActiveDocument(channel.doc)

    channel.psChannel.color = color

    return channel.doc, channel

@defNode("Photoshop Channel Set Visibility", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def setChannelVisibility(channel: ChannelWrapper, visible: bool=True):
    ensureActiveDocument(channel.doc)

    channel.psChannel.visible = visible

    return channel.doc, channel

@defNode("Photoshop Channel Set Name", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def setChannelName(channel: ChannelWrapper, name: str):
    ensureActiveDocument(channel.doc)

    channel.psChannel.app.name = name

    return channel.doc, channel

@defNode("Photoshop Channel Select", isExecutable=True, returnNames=["Document", "Channel"], identifier=PHOTOSHOP_IDENTIFIER)
def selectChannels(channel: ChannelWrapper, addToSelection=False):
    ensureActiveDocument(channel.doc)

    if channel.doc.psDoc.activeChannels is None or addToSelection:
        channel.doc.psDoc.activeChannels = [channel.psChannel]
    else:
        if not channel.psChannel in channel.doc.psDoc.activeChannels:
            channel.doc.psDoc.activeChannels += [channel.psChannel]

    return channel.doc, channel