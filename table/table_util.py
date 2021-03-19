from table.Table import Table
from table.ExcelTable import ExcelTable
from table.CSVTable import CSVTable

def readTable(tablePath: str, csvSeparator=';', excelSheetName=None, encodingOverride=None) -> Table:
    if tablePath.lower().endswith('.csv'):
        return CSVTable(tablePath, csvSeparator, encodingOverride=encodingOverride)
    elif tablePath.lower().endswith('.xlsx'):
        return ExcelTable.read(tablePath, excelSheetName, encodingOverride=encodingOverride)

    return None