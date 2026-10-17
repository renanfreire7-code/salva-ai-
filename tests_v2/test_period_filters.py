from datetime import date,datetime
import tkinter as tk
import unittest
from tests_v2.support import FakeClock


class PeriodFilterTest(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.addCleanup(self.root.destroy)
        self.clock=FakeClock();self.clock.value=self.clock.value.replace(month=3,day=1)

    def test_presets_and_invalid_date_keep_last_applied(self):
        from salva_ai_v2.ui.period import PeriodFilter
        calls=[];period=PeriodFilter(self.root,self.clock,'TODAY',calls.append)
        period.preset.set('Últimos 7 dias');period.choose_preset();self.assertTrue(period.apply())
        self.assertEqual((period.applied.start,period.applied.end),(date(2026,2,23),date(2026,3,1)))
        previous=period.applied
        period.start.set('31/02/2026');self.assertFalse(period.apply())
        self.assertEqual(period.applied,previous);self.assertEqual(len(calls),1)
        self.assertTrue(period.error.get())
        period.clear();self.assertEqual(period.applied.start,self.clock.today())

    def test_typing_does_not_apply_and_default_month_is_calendar_month(self):
        from salva_ai_v2.ui.period import PeriodFilter
        calls=[];period=PeriodFilter(self.root,self.clock,'THIS_MONTH',calls.append)
        self.assertEqual((period.applied.start,period.applied.end),(date(2026,3,1),date(2026,3,31)))
        period.start.set('01/02/2026');self.root.update()
        self.assertEqual(period.applied.start,date(2026,3,1));self.assertEqual(calls,[])

    def test_month_selector_does_not_apply_invalid_month(self):
        from salva_ai_v2.ui.period import MonthSelector
        calls=[];selector=MonthSelector(self.root,self.clock,calls.append)
        selector.value.set('2026-02');self.assertTrue(selector.apply())
        selector.value.set('2026-99');self.assertFalse(selector.apply())
        self.assertEqual(selector.applied,'2026-02');self.assertEqual(calls,['2026-02'])
