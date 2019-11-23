from PySide2 import QtCore
from PySide2.QtCore import QRunnable

# From https://stackoverflow.com/questions/10991991/pyside-easier-way-of-updating-gui-from-another-thread
# by chfoo: https://stackoverflow.com/users/1524507/chfoo
class InvokeEvent(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        QtCore.QEvent.__init__(self, InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class Invoker(QtCore.QObject):
    def event(self, event):
        event.fn(*event.args, **event.kwargs)

        return True

_invoker = Invoker()

def runInMainThread(fn, *args, **kwargs):
    QtCore.QCoreApplication.postEvent(_invoker, InvokeEvent(fn, *args, **kwargs))

############################################################################################################

class LambdaTask(QRunnable):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        QRunnable.__init__(self)

    def run(self):
        self.func(*self.args, **self.kwargs)