from table.Table import Table


imported = False
try:
    import xlrd
    imported = True
except:
    print("Note: Excel table is not available because the xlrd module is missing: pip install xlrd")

class ExcelTable(Table):
    def __init__(self, sheet):
        super.__init__()

        self.sheet = sheet

    def getRowValues(self, rowIndex):
        return self.sheet.row_values(rowIndex) if self.sheet != None else []

    def getColumnValues(self, colIndex):
        return self.sheet.col_values(colIndex) if self.sheet != None else []

    def getCellValue(self, rowIndex, colIndex):
        return self.sheet.cell_value(rowIndex, colIndex) if self.sheet != None else None

    @property
    def ncols(self):
        return self.sheet.ncols if self.sheet != None else 0

    @property
    def nrows(self):
        return self.sheet.nrows if self.sheet != None else 0

    @staticmethod
    def read(workbookPath: str, sheetName: str, encodingOverride=None):
        return ExcelTable(xlrd.open_workbook(filename=workbookPath,encoding_override=encodingOverride).sheet_by_name(sheetName))