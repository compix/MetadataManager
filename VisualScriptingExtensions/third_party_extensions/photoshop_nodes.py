import os
import typing
import photoshop.api as ps
from photoshop.api._document import Document
from photoshop.api._artlayer import ArtLayer
from photoshop.api.enumerations import CopyrightedType, DialogModes, LayerCompressionType, MatteType, RasterizeType, Urgency, TiffEncodingType
from VisualScripting.node_exec.base_nodes import SliderInput, defNode
from enum import Enum

PHOTOSHOP_IDENTIFIER = "Photoshop"

IMPORTS = [
    'from photoshop.api import NewDocumentMode, DocumentFill, BitsPerChannelType',
    'from photoshop.api.enumerations import CopyrightedType, LayerCompressionType, MatteType, RasterizeType, Urgency, TiffEncodingType',
    'from VisualScriptingExtensions.third_party_extensions.photoshop_nodes import ExrColorDepth, ExrTilingType, ExrCompressionMethod'
]

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

def ensureActiveDocument(doc: DocumentWrapper):
    if doc.psApp.activeDocument != doc.psDoc:
        doc.psApp.activeDocument = doc.psDoc

@defNode('Create Photoshop App', isExecutable=True, returnNames=['app'], identifier=PHOTOSHOP_IDENTIFIER)
def createApp() -> ps.Application:
    return ps.Application(version='CS6')

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

@defNode('Photoshop RGB Color', returnNames=['RGB'], identifier=PHOTOSHOP_IDENTIFIER)
def createRGBColor(red = 0, green = 0, blue = 0) -> ps.SolidColor:
    c = ps.SolidColor()
    c.rgb.red = red
    c.rgb.green = green
    c.rgb.blue = blue

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

@defNode('Photoshop Rasterize Layer', isExecutable=True, returnNames=['Document', 'Art Layer'], identifier=PHOTOSHOP_IDENTIFIER)
def rasterizeLayer(layer: ArtLayerWrapper, rasterizeType: RasterizeType = RasterizeType.EntireLayer) -> typing.Tuple[DocumentWrapper, ArtLayerWrapper]:
    ensureActiveDocument(layer.doc)

    layer.psLayer.rasterize(rasterizeType)

    return layer.doc, layer