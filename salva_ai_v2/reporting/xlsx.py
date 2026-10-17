from pathlib import Path
from decimal import Decimal


def export_xlsx(path,report):
    from ..vendor.xlsxwriter import Workbook
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with Workbook(str(path),{"strings_to_formulas":False,"strings_to_urls":False}) as book:
        head=book.add_format({"bold":True,"bg_color":"#e5edf3"})
        currency=book.add_format({"num_format": 'R$ #,##0.00'})
        meta=book.add_worksheet("Período")
        for row,values in enumerate([["Início",report.start.isoformat()],["Fim",report.end.isoformat()]]+
                [[str(k),str(v)] for k,v in report.filters.items()]+[["Atenção",w] for w in report.warnings]):
            meta.write_string(row,0,values[0]);meta.write_string(row,1,values[1])
        meta.set_column(0,1,45)
        for name,rows in report.sheets.items():
            sheet=book.add_worksheet(name[:31])
            sheet.freeze_panes(1,0);sheet.set_column(0,20,22)
            for r,values in enumerate(rows):
                for c,value in enumerate(values):
                    if isinstance(value,(int,Decimal)) and not isinstance(value,bool):
                        sheet.write_number(r,c,value,head if r==0 else currency if isinstance(value,Decimal) else None)
                    else:
                        sheet.write_string(r,c,str(value) if value is not None else "",head if r==0 else None)
            if rows:
                sheet.autofilter(0,0,len(rows)-1,len(rows[0])-1)
    return path
