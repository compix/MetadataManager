import os
import typing
import photoshop.api as ps
from photoshop.api._artlayer import ArtLayer
from photoshop.api._document import Document
from photoshop.api._layerSet import LayerSet
from photoshop.api._selection import Selection
import inspect

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

def splitAtUppercaseLetters(name: str) -> str:
    t_name = ''
    for i, c in enumerate(name):
        if i > 0 and c.isupper():
            t_name += ' '

        t_name += c

    return t_name

def isRoutineOrProperty(o):
    return inspect.isroutine(o) or isinstance(o, property)

def generatePhotoshopNodes(filename: str, targetClass, addCodeFunc):
    methodsAndProperties = inspect.getmembers(targetClass, predicate=isRoutineOrProperty)
    codeLines = []
    for m in methodsAndProperties:
        funcName = m[0]

        if '_' in funcName:
            continue

        funcNameUpper = funcName[0].upper() + funcName[1:]

        try:
            signature = inspect.signature(m[1])
        except:
            pass

        isProperty = isinstance(m[1], property)

        argsArr = []
        sigArgsArr = []
        if not isProperty:
            for k, v in signature.parameters.items():
                if k == 'self':
                    continue

                arg = k
                argsArr.append(arg)

                if v.annotation != inspect.Parameter.empty:
                    arg += ': ' + str(v.annotation.__name__)
                
                if v.default != inspect.Parameter.empty:
                    arg += '= ' + str(v.default)

                sigArgsArr.append(arg)
        
        args = ', '.join(argsArr) if len(argsArr) > 0 else ''
        sigArgs = (', ' + ', '.join(sigArgsArr)) if len(sigArgsArr) > 0 else ''

        addCodeFunc(codeLines, sigArgs, args, funcName, funcNameUpper, isProperty)

    code = ''
    for l in codeLines:
        code += l + '\n'

    with open(filename, mode='w+') as f:
        f.write(code)

def addArtLayerCode(codeLines: typing.List[str], sigArgs: str, args: str, funcName: str, funcNameUpper: str):
    codeLines.append(f'@defNode("Photoshop Layer {splitAtUppercaseLetters(funcNameUpper)}", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)')
    codeLines.append(f'def artLayer{funcNameUpper}(layer: ArtLayerWrapper{sigArgs}):')
    codeLines.append('    ensureActiveDocument(layer.doc)')
    codeLines.append('')
    codeLines.append(f'    layer.psLayer.{funcName}({args})')
    codeLines.append('')
    codeLines.append('    return layer.doc, layer')
    codeLines.append('')

def addDocumentCode(codeLines: typing.List[str], sigArgs: str, args: str, funcName: str, funcNameUpper: str):
    codeLines.append(f'@defNode("Photoshop Document {splitAtUppercaseLetters(funcNameUpper)}", isExecutable=True, returnNames=["Document"], identifier=PHOTOSHOP_IDENTIFIER)')
    codeLines.append(f'def document{funcNameUpper}(doc: DocumentWrapper{sigArgs}):')
    codeLines.append('    ensureActiveDocument(doc)')
    codeLines.append('')
    codeLines.append(f'    doc.psDoc.{funcName}({args})')
    codeLines.append('')
    codeLines.append('    return doc')
    codeLines.append('')

def addLayerSetCode(codeLines: typing.List[str], sigArgs: str, args: str, funcName: str, funcNameUpper: str, isProperty: bool):
    if isProperty:
        codeLines.append(f'@defNode("Photoshop Layer Set Set {splitAtUppercaseLetters(funcNameUpper)}", isExecutable=True, returnNames=["Document", "Layer Set"], identifier=PHOTOSHOP_IDENTIFIER)')
        codeLines.append(f'def layerSetSet{funcNameUpper}(layerSet: LayerSetWrapper, {funcName}):')
        codeLines.append('    ensureActiveDocument(layerSet.doc)')
        codeLines.append(f'    layerSet.psLayer.{funcName} = {funcName}')
        codeLines.append('')
        codeLines.append(f'    return layerSet.doc, layerSet')
        codeLines.append('')
        codeLines.append(f'@defNode("Photoshop Layer Set Get {splitAtUppercaseLetters(funcNameUpper)}", isExecutable=True, returnNames=["Document", "Layer Set", "{funcNameUpper}"], identifier=PHOTOSHOP_IDENTIFIER)')
        codeLines.append(f'def layerSetGet{funcNameUpper}(layerSet: LayerSetWrapper):')
        codeLines.append('    ensureActiveDocument(layerSet.doc)')
        codeLines.append('')
        codeLines.append(f'    return layerSet.doc, layerSet, layerSet.psLayer.{funcName}')
        codeLines.append('')
    else:
        codeLines.append(f'@defNode("Photoshop Layer Set {splitAtUppercaseLetters(funcNameUpper)}", isExecutable=True, returnNames=["Document", "Layer Set"], identifier=PHOTOSHOP_IDENTIFIER)')
        codeLines.append(f'def layerSet{funcNameUpper}(layerSet: LayerSetWrapper{sigArgs}):')
        codeLines.append('    ensureActiveDocument(layerSet.doc)')
        codeLines.append('')
        codeLines.append(f'    layerSet.psLayer.{funcName}({args})')
        codeLines.append('')
        codeLines.append('    return layerSet.doc, layerSet')
        codeLines.append('')

def addSelectionCode(codeLines: typing.List[str], sigArgs: str, args: str, funcName: str, funcNameUpper: str, isProperty: bool):
    if isProperty:
        codeLines.append(f'@defNode("Photoshop Selection Set {splitAtUppercaseLetters(funcNameUpper)}", isExecutable=True, returnNames=["Document", "Selection"], identifier=PHOTOSHOP_IDENTIFIER)')
        codeLines.append(f'def selectionSet{funcNameUpper}(selection: SelectionWrapper, {funcName}):')
        codeLines.append('    ensureActiveDocument(selection.doc)')
        codeLines.append(f'    selection.psSelection.{funcName} = {funcName}')
        codeLines.append('')
        codeLines.append(f'    return selection.doc, selection')
        codeLines.append('')
        codeLines.append(f'@defNode("Photoshop Selection Get {splitAtUppercaseLetters(funcNameUpper)}", isExecutable=True, returnNames=["Document", "Selection", "{funcNameUpper}"], identifier=PHOTOSHOP_IDENTIFIER)')
        codeLines.append(f'def selectionGet{funcNameUpper}(selection: SelectionWrapper):')
        codeLines.append('    ensureActiveDocument(selection.doc)')
        codeLines.append('')
        codeLines.append(f'    return selection.doc, selection, selection.psSelection.{funcName}')
        codeLines.append('')
    else:
        codeLines.append(f'@defNode("Photoshop Selection {splitAtUppercaseLetters(funcNameUpper)}", isExecutable=True, returnNames=["Document", "Selection"], identifier=PHOTOSHOP_IDENTIFIER)')
        codeLines.append(f'def selection{funcNameUpper}(selection: SelectionWrapper{sigArgs}):')
        codeLines.append('    ensureActiveDocument(selection.doc)')
        codeLines.append('')
        codeLines.append(f'    selection.psSelection.{funcName}({args})')
        codeLines.append('')
        codeLines.append('    return selection.doc, selection')
        codeLines.append('')

#generatePhotoshopNodes(os.path.join(CUR_DIR, 'art_layer_nodes.py'), ArtLayer, addArtLayerCode)
#generatePhotoshopNodes(os.path.join(CUR_DIR, 'document_nodes.py'), Document, addDocumentCode)
#generatePhotoshopNodes(os.path.join(CUR_DIR, 'layer_set_nodes.py'), LayerSet, addLayerSetCode)
generatePhotoshopNodes(os.path.join(CUR_DIR, 'selection_nodes.py'), Selection, addSelectionCode)