import os
import typing
import photoshop.api as ps
from photoshop.api._artlayer import ArtLayer
from photoshop.api._document import Document
import inspect

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

def splitAtUppercaseLetters(name: str) -> str:
    t_name = ''
    for i, c in enumerate(name):
        if i > 0 and c.isupper():
            t_name += ' '

        t_name += c

    return t_name

def generatePhotoshopNodes(filename: str, targetClass, addCodeFunc):
    methods = inspect.getmembers(targetClass, predicate=inspect.isroutine)
    codeLines = []
    for m in methods:
        funcName = m[0]

        if '_' in funcName:
            continue

        funcNameUpper = funcName[0].upper() + funcName[1:]

        try:
            signature = inspect.signature(m[1])
        except:
            continue

        argsArr = []
        sigArgsArr = []
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

        addCodeFunc(codeLines, sigArgs, args, funcName, funcNameUpper)

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

#generatePhotoshopNodes(os.path.join(CUR_DIR, 'art_layer_nodes.py'), ArtLayer, addArtLayerCode)
generatePhotoshopNodes(os.path.join(CUR_DIR, 'document_nodes.py'), Document, addDocumentCode)