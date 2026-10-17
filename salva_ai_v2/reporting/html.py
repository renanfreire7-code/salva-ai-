from html import escape
from pathlib import Path
from ..common.money import money


def cash_html(path,report):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    rows="".join("<tr><td>"+escape(str(r.get("occurred_at","")))+"</td><td>"+escape(str(r.get("kind","")))+"</td><td>"+escape(money(r.get("delta_cents",0)))+"</td><td>"+escape(str(r.get("reason") or ""))+"</td></tr>" for r in report.entries)
    content=f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Fechamento do caixa {report.session_id}</title>
<style>body{{font:16px sans-serif;max-width:1000px;margin:30px auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border-bottom:1px solid #aaa;text-align:left}}@media print{{body{{margin:0}}}}</style>
<h1>Fechamento do caixa #{report.session_id}</h1>
<p>Troco inicial: {escape(money(report.opening_cents))}</p><p>Esperado: {escape(money(report.expected_cents))}</p>
<p>Contado: {escape(money(report.counted_cents))}</p><p>Diferença: {escape(money(report.variance_cents))}</p>
<p>Justificativa: {escape(report.reason or "Sem diferença")}</p>
<table><tr><th>Data</th><th>Movimento</th><th>Valor</th><th>Motivo</th></tr>{rows}</table></html>"""
    path.write_text(content,encoding="utf-8")
    return path
