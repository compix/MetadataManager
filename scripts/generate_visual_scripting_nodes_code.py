import os
import photoshop.api as ps
from photoshop.api._artlayer import ArtLayer
import inspect

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

def splitAtUppercaseLetters(name: str) -> str:
    t_name = ''
    for i, c in enumerate(name):
        if i > 0 and c.isupper():
            t_name += ' '

        t_name += c

    return t_name

def generatePhotoshopNodes(filename: str):
    methods = inspect.getmembers(ArtLayer, predicate=inspect.isroutine)
    code = ''
    for m in methods:
        funcName = m[0]

        if '_' in funcName:
            continue

        funcName_ = funcName[0].upper() + funcName[1:]

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

        code += f'@defNode("Photoshop Layer {splitAtUppercaseLetters(funcName_)}", isExecutable=True, returnNames=["Document", "Art Layer"], identifier=PHOTOSHOP_IDENTIFIER)\n'
        code += f'def artLayer{funcName_}(layer: ArtLayerWrapper{sigArgs}):\n'
        code += '    ensureActiveDocument(layer.doc)\n'
        code += '\n'
        code += f'    layer.psLayer.{funcName}({args})\n'
        code += '\n'
        code += '    return layer.doc, layer\n'
        code += '\n'

    with open(filename, mode='w+') as f:
        f.write(code)

generatePhotoshopNodes(os.path.join(CUR_DIR, 'art_layer_nodes.py'))