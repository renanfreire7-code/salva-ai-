"""Fixtures usam login real; nenhum bypass faz parte do aplicativo."""
from salva_ai_v2.bootstrap import build_application


def build_test_application(data_dir):
    app=build_application(data_dir)
    try:
        if not app.accounts.configured:
            proof=app.security.authorize('681','access.configure') if app.security.configured else None
            app.accounts.create('bar','Senha fictícia 42','681',proof)
        app.unlock(app.accounts.login('bar','Senha fictícia 42'))
        return app
    except BaseException:
        app.close();raise
