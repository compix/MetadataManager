from abc import ABC, abstractclassmethod

class Table(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractclassmethod
    def getRowValues(self, rowIndex):
        ...

    @abstractclassmethod
    def getColumnValues(self, colIndex):
        ...

    @abstractclassmethod
    def getCellValue(self, rowIndex, colIndex):
        ...

    @property
    @abstractclassmethod
    def ncols(self):
        ...

    @property
    @abstractclassmethod
    def nrows(self):
        ...

    def getColumnsWithoutHeader(self, headerIdx=0):
        return [self.getColumnValues(i)[headerIdx+1:] for i in range(0, self.ncols)]

    def getHeader(self,rowIndex=0):
        return self.getRowValues(rowIndex)

    def getRowsWithoutHeader(self, headerIdx=0):
        for rowIdx in range(headerIdx+1, self.nrows):
            yield self.getRowValues(rowIdx)

    def getRowAsDict(self, headerValues, rowValues):
        return dict(zip(headerValues, rowValues))