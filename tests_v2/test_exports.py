from pathlib import Path
from datetime import date
import tempfile
import unittest
import zipfile


class ExportsTest(unittest.TestCase):
    def test_xlsx_text_is_not_formula_and_period_is_recorded(self):
        from salva_ai_v2.reporting.models import ReportBundle
        from salva_ai_v2.reporting.xlsx import export_xlsx
        with tempfile.TemporaryDirectory() as directory:
            bundle = ReportBundle(date(2025,1,1), date(2025,1,31), {'categoria':'Teste'}, {'Teste':[['Descrição'], ['=1+1']]}, [])
            path = export_xlsx(Path(directory)/'teste.xlsx', bundle)
            with zipfile.ZipFile(path) as z:
                content = z.read('xl/worksheets/sheet1.xml').decode()
                strings = z.read('xl/sharedStrings.xml').decode()
            self.assertNotIn('<f>', content)
            self.assertIn('=1+1', strings)
            self.assertIn('2025-01-01', strings)

    def test_html_escapes_reason(self):
        from salva_ai_v2.reporting.models import CashReport
        from salva_ai_v2.reporting.html import cash_html
        with tempfile.TemporaryDirectory() as directory:
            report = CashReport(1, 10000, 10000, 9900, -100, '<script>alert(1)</script>', {}, [])
            content = cash_html(Path(directory)/'caixa.html', report).read_text()
            self.assertNotIn('<script>', content)
            self.assertIn('&lt;script&gt;', content)
