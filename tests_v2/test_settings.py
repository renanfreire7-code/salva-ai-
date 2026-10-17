from tests_v2.support import DatabaseCase


class SettingsTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.finance.settings import FinancialSettings
        self.security=SecurityService(self.db)
        self.security.setup('681942')
        self.settings=FinancialSettings(self.db,self.security)

    def grant(self):
        return self.security.authorize('681942','settings.finance')

    def test_combined_configuration_does_not_save_half(self):
        from salva_ai_v2.common.errors import BusinessError
        self.settings.set_das(10000,self.grant(),'Configuração inicial','das1')
        rates={'MONEY':0,'PIX':0,'DEBIT':150,'CREDIT':350}
        with self.assertRaises(BusinessError):
            self.settings.configure(rates,-1,self.grant(),'DAS inválido','bad1')
        self.assertIsNone(self.settings.rates()['DEBIT'])
        self.assertEqual(self.settings.das(),10000)
        self.settings.configure(rates,10000,self.grant(),'Configuração completa','config1')
        self.assertEqual(self.settings.rates()['DEBIT'],150)
        self.assertEqual(self.settings.das(),10000)
