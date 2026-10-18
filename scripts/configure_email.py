"""Grava configuração pública do Supabase; não altera credenciais ou dados."""
from pathlib import Path
import argparse,getpass,sqlite3,sys
from contextlib import closing
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from salva_ai_v2.security.email_config import SupabaseConfig,save_email_config
from salva_ai_v2.common.errors import BusinessError


def main(argv=None):
    parser=argparse.ArgumentParser(description='Configura somente URL e chave pública de recuperação por e-mail.')
    parser.add_argument('--data-dir',type=Path,default=Path.home()/'SalvaAiHeadshopV2')
    args=parser.parse_args(argv);issuer=None;database=(args.data_dir/'dados'/'salva_ai.sqlite3').resolve()
    try:
        if database.is_file():
            with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as conn:
                if conn.execute('PRAGMA application_id').fetchone()[0]!=0x53414932:raise BusinessError('A pasta selecionada contém banco de outro aplicativo.')
                columns={r[1] for r in conn.execute('PRAGMA table_info(establishment_account)')}
                if 'email_issuer' in columns:
                    row=conn.execute('SELECT email_issuer FROM establishment_account WHERE id=1').fetchone()
                    if row:issuer=row[0]
        print('Use apenas URL e chave pública. Não informe senha SMTP, service_role ou sb_secret.')
        config=SupabaseConfig(input('URL HTTPS do projeto: '),getpass.getpass('Chave publishable/anon pública (não será exibida): '))
        save_email_config(args.data_dir/'auth_service.json',config,bound_issuer=issuer)
        print('Configuração pública salva. Abra o programa e conclua o teste de recebimento real.')
        return 0
    except (BusinessError,sqlite3.Error,OSError,EOFError,KeyboardInterrupt) as error:
        print(str(error) if isinstance(error,BusinessError) else 'Configuração não concluída. Nenhum cadastro foi alterado.')
        return 1


if __name__=='__main__':raise SystemExit(main())
