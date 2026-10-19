"""Fixtures de operação direta; fluxo antigo exercitado isoladamente para compatibilidade."""
from salva_ai_v2.bootstrap import build_application,CredentialApplication


def build_test_application(data_dir):
    app=build_application(data_dir)
    try:
        if not app.security.configured:app.security.setup('681')
        return app
    except BaseException:
        app.close();raise


def build_credential_application(data_dir):
    # Somente testes históricos: o entrypoint público sempre usa a abertura direta.
    return CredentialApplication(data_dir)
