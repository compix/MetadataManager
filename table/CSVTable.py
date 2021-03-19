from table.Table import Table

class CSVTable(Table):
    def __init__(self, path, separator, encodingOverride=None):
        self.rows = []
        with open(path) as f:
            for row in f:
                self.rows.append(row.rstrip('\n').split(sep=separator))

    def getRowValues(self, rowIndex):
        return self.rows[rowIndex]

    def getColumnValues(self, colIndex):
        return [self.rows[i][colIndex] for i in range(0,self.nrows)]

    def getCellValue(self, rowIndex, colIndex):
        return self.rows[rowIndex][colIndex]

    @property
    def ncols(self):
        return len(self.rows[0]) if len(self.rows) > 0 else 0
    
    @property
    def nrows(self):
        return len(self.rows)

    def getRowsWithoutHeader(self, headerIdx=0):
        for rowIdx in range(headerIdx+1, self.nrows):
            yield self.getRowValues(rowIdx)

    def getRowAsDict(self, headerValues, rowValues):
        return dict(zip(headerValues, rowValues))