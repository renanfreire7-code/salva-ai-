"""Gera somente documentação PDF; ReportLab/Pillow são dependências de autoria, não do PDV."""
from pathlib import Path
from xml.sax.saxutils import escape
from collections import OrderedDict
import json,re
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,PageBreak,NextPageTemplate,Image,Table,TableStyle,Flowable,KeepTogether
from reportlab.platypus.tableofcontents import TableOfContents

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs'/'manuais';IMAGES=SOURCE/'imagens';OUT=ROOT/'dist'
VERSION='0.4.2-dev';EDITION='19 de outubro de 2026'
ZIP='https://raw.githubusercontent.com/renanfreire7-code/salva-ai-/refs/heads/feat/salva-ai-v2/dist/Bar_Simples_0.4.2-dev_sem_login.zip'
REPO='https://github.com/renanfreire7-code/salva-ai-'
CODE=REPO+'/tree/397acca183f7ecd8283c3fdad60d2d35548b141d'
GREEN=colors.HexColor('#164C3B');ORANGE=colors.HexColor('#B7472C');INK=colors.HexColor('#233D3D');MUTED=colors.HexColor('#52645D');CREAM=colors.HexColor('#FAF7EF');PALE=colors.HexColor('#EDF4EF');LINE=colors.HexColor('#D7E3DA')
W,H=A4;LEFT=44;WIDTH=W-88;FRAME_H=H-105
FONTDIR=Path('/usr/share/fonts/truetype/noto')
if not (FONTDIR/'NotoSans-Regular.ttf').is_file():raise SystemExit('Instale a fonte de autoria Noto Sans para gerar os manuais.')
for name,file in [('Manual','NotoSans-Regular.ttf'),('ManualBold','NotoSans-Bold.ttf'),('ManualItalic','NotoSans-Italic.ttf')]:pdfmetrics.registerFont(TTFont(name,str(FONTDIR/file)))
pdfmetrics.registerFontFamily('Manual',normal='Manual',bold='ManualBold',italic='ManualItalic',boldItalic='ManualBold')
S={
 'kicker':ParagraphStyle('Kicker',fontName='ManualBold',fontSize=9,leading=12,textColor=GREEN,spaceAfter=6),
 'h1':ParagraphStyle('H1',fontName='ManualBold',fontSize=21,leading=26,textColor=GREEN,spaceAfter=10),
 'intro':ParagraphStyle('Intro',fontName='Manual',fontSize=10.5,leading=14.8,textColor=INK,spaceAfter=10),
 'body':ParagraphStyle('Body',fontName='Manual',fontSize=10.2,leading=14.2,textColor=INK),
 'small':ParagraphStyle('Small',fontName='Manual',fontSize=9.2,leading=12.5,textColor=INK,spaceAfter=4),
 'caption':ParagraphStyle('Caption',fontName='ManualItalic',fontSize=8,leading=10.5,textColor=MUTED,spaceAfter=10),
 'subhead':ParagraphStyle('Subhead',fontName='ManualBold',fontSize=10,leading=14,textColor=GREEN,spaceBefore=4,spaceAfter=5),
 'number':ParagraphStyle('Number',fontName='ManualBold',fontSize=11,leading=14.2,textColor=GREEN),
 'toc_title':ParagraphStyle('TOCTitle',fontName='ManualBold',fontSize=25,leading=32,textColor=GREEN,spaceAfter=16),
}
LOGO=ROOT/'salva_ai_v2/assets/bar_simples_logo.png';ICON=ROOT/'salva_ai_v2/assets/bar_simples_icon.png'

def clean(value):
 value=str(value)
 for a,b in [('Python3.','Python 3.'),('versão0.','versão 0.'),('referência0.','referência 0.'),('versões0.','versões 0.'),('Windows11','Windows 11'),('de64bits','de 64 bits'),('meses12','meses 12')]:value=value.replace(a,b)
 return value

def text(value):return escape(clean(value)).replace('\n','<br/>')
def para(value,style='body'):return Paragraph(text(value),S[style])
def link(label,url):return Paragraph(f'<link href="{escape(url)}" color="#164C3B"><u>{text(label)}</u></link>',S['body'])

def draw_par(c,t,x,y,width,font=10,bold=False,color=INK):
 p=Paragraph(text(t),ParagraphStyle('Diagram',fontName='ManualBold' if bold else 'Manual',fontSize=font,leading=font*1.35,textColor=color))
 _,height=p.wrap(width,300);p.drawOn(c,x,y-height);return height

class Diagram(Flowable):
 def __init__(self,kind):super().__init__();self.kind=kind;self.width=WIDTH;self.height=174
 def draw(self):
  c=self.canv;c.saveState();c.setFillColor(PALE);c.roundRect(0,0,self.width,self.height,8,fill=1,stroke=0)
  if self.kind=='folders_diagram':
   for x,title,body,foot in [(12,'ARQUIVOS DO PROGRAMA','Documentos\\Bar Simples\nCRIAR_ATALHO.vbs\nABRIR_BAR_SIMPLES.vbs\nBar_Simples.pyw e pastas','Estes arquivos vêm no ZIP.'),(WIDTH/2+5,'DADOS DO BAR','Pasta do usuário\\SalvaAiHeadshopV2\ndados → produtos e movimentos\nbackups → cópias\nrelatorios → fechamentos','Não leve os testes para o dono.')]:
    draw_par(c,title,x,158,WIDTH/2-28,9,True,GREEN);draw_par(c,body,x,132,WIDTH/2-28,9.3);draw_par(c,foot,x,34,WIDTH/2-28,8.4,True,ORANGE)
   c.setStrokeColor(LINE);c.line(WIDTH/2,12,WIDTH/2,162)
  elif self.kind=='python_diagram':
   draw_par(c,'ESCOLHAS PARA A INSTALAÇÃO DO PYTHON',15,157,WIDTH-30,10,True,GREEN)
   labels=[('1','Site oficial','python.org'),('2','Versão estável','3.12 ou superior'),('3','Interface gráfica','Manter Tcl/Tk'),('4','Finalizar','Depois, criar atalho')]
   size=(WIDTH-42)/4
   for i,(n,title,body) in enumerate(labels):
    x=10+i*(size+6);c.setFillColor(colors.white);c.roundRect(x,35,size,92,5,fill=1,stroke=0)
    draw_par(c,n,x+9,116,size-18,16,True,ORANGE);draw_par(c,title,x+9,91,size-18,9,True);draw_par(c,body,x+9,61,size-18,8.5)
  elif self.kind=='extract_diagram':
   draw_par(c,'DO DOWNLOAD À PASTA NORMAL',15,158,WIDTH-30,10,True,GREEN)
   boxes=[(12,'Arquivo ZIP','O pacote baixado\nAinda compactado'),(WIDTH/3+7,'Extrair Tudo','Opção do Windows\nEscolha a pasta fixa'),(2*WIDTH/3+2,'Pasta extraída','Arquivos e pastas\nCRIAR_ATALHO.vbs')]
   size=WIDTH/3-18
   for x,title,body in boxes:
    c.setFillColor(colors.white);c.roundRect(x,34,size,90,5,fill=1,stroke=0);draw_par(c,title,x+9,110,size-18,11,True,GREEN);draw_par(c,body,x+9,82,size-18,9)
  else:
   c.drawImage(ImageReader(ICON),28,39,width=104,height=104,mask='auto',preserveAspectRatio=True)
   draw_par(c,'Bar Simples',24,30,140,11,True,GREEN)
   draw_par(c,'ATALHO NA ÁREA DE TRABALHO',170,153,WIDTH-185,10,True,GREEN)
   draw_par(c,'1. Criar uma vez: CRIAR_ATALHO.vbs\n2. Depois, abrir pelo ícone Bar Simples\n3. Manter a pasta extraída no mesmo lugar',170,123,WIDTH-185,10)
   draw_par(c,'Esquema ilustrativo; não é uma captura do Windows.',170,31,WIDTH-185,8.2,False,MUTED)
  c.restoreState()

class ManualDoc(BaseDocTemplate):
 def __init__(self,path,kind):
  self.kind=kind;self.manual='Manual de instalação' if kind=='installation' else 'Manual de uso'
  super().__init__(str(path),pagesize=A4,leftMargin=LEFT,rightMargin=LEFT,topMargin=60,bottomMargin=45,title='Bar Simples — '+self.manual+' — 0.4.2',author='Documentação do projeto Bar Simples',subject='Guia didático com imagens da versão 0.4.2-dev',pageCompression=1,allowSplitting=1)
  frame=Frame(LEFT,45,WIDTH,FRAME_H,id='content',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
  self.addPageTemplates([PageTemplate(id='cover',frames=[frame],onPage=self.cover),PageTemplate(id='normal',frames=[frame],onPage=self.normal)])
 def cover(self,c,doc):
  c.saveState();c.setFillColor(CREAM);c.rect(0,0,W,H,fill=1,stroke=0)
  c.setFillColor(GREEN);c.rect(0,H-15,W,15,fill=1,stroke=0)
  c.drawImage(ImageReader(LOGO),W/2-142,425,width=284,height=284,mask='auto',preserveAspectRatio=True)
  c.setFillColor(GREEN);c.setFont('ManualBold',28);c.drawCentredString(W/2,390,self.manual)
  subtitle='Do download ao ícone na Área de Trabalho' if self.kind=='installation' else 'Todas as funções, explicadas passo a passo'
  p=Paragraph(text(subtitle),ParagraphStyle('CoverSub',fontName='Manual',fontSize=15,leading=21,textColor=INK,alignment=1));_,h=p.wrap(W-110,80);p.drawOn(c,55,350-h)
  c.setFillColor(GREEN);c.roundRect(W/2-115,260,230,34,7,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('ManualBold',11);c.drawCentredString(W/2,272,'VERSÃO 0.4.2-DEV · '+('GUIA 1 DE 2' if self.kind=='installation' else 'GUIA 2 DE 2'))
  for y,line in [(218,'Abertura direta · Sem login · PIN administrativo'),(196,'Com imagens reais e exemplos fictícios'),(124,'Edição: '+EDITION)]:
   c.setFillColor(INK if y>130 else MUTED);c.setFont('Manual',10.4 if y>130 else 9);c.drawCentredString(W/2,y,line)
  c.setStrokeColor(LINE);c.line(50,95,W-50,95)
  p=Paragraph('Prepare o notebook com o guia de instalação.<br/>Aprenda o atendimento e a gestão com o guia de uso.',ParagraphStyle('CoverFooter',fontName='Manual',fontSize=9,leading=14,textColor=MUTED,alignment=1));p.wrap(W-100,60);p.drawOn(c,50,48)
  c.restoreState()
 def normal(self,c,doc):
  c.saveState();c.setStrokeColor(LINE);c.line(LEFT,H-43,W-LEFT,H-43)
  c.setFont('ManualBold',8.5);c.setFillColor(GREEN);c.drawString(LEFT,H-29,'BAR SIMPLES')
  c.setFont('Manual',8.5);c.setFillColor(MUTED);c.drawRightString(W-LEFT,H-29,self.manual+' · 0.4.2-dev')
  c.line(LEFT,34,W-LEFT,34);c.setFont('Manual',8);c.drawString(LEFT,21,'Exemplos fictícios · Consulte o sumário para localizar uma função.')
  c.drawRightString(W-LEFT,21,str(doc.page));c.restoreState()
 def afterFlowable(self,flowable):
  if hasattr(flowable,'toc_key'):
   key=flowable.toc_key;self.canv.bookmarkPage(key);level=flowable.toc_level
   label=flowable.getPlainText();self.canv.addOutlineEntry(label,key,level=level,closed=level==0)
   self.notify('TOCEntry',(level,label,self.page,key))

CAPTIONS={
 'sales':'Venda de balcão: busca, pedido atual e recebimento.', 'tabs':'Comandas por cliente: seleção à esquerda e itens à direita.',
 'products':'Produtos e estoque: cadastro, entradas e saldos.', 'delivery':'Delivery: filtros, situações e ações disponíveis.',
 'cash':'Caixa: dinheiro esperado, recebimentos e movimentos.', 'finance':'Contas e despesas: filtros, situações e ações.',
 'history':'Histórico: lista à esquerda e discriminação à direita.', 'monthly':'Resultado do mês: indicadores gerenciais.',
 'results':'Lucro por produto: resultados e exportação.', 'backup':'Centro de backups e recuperação do PIN.',
 'settlement':'Acerto com entregador: seleção de pedidos e conferência.', 'settlement_history':'Acertos anteriores: valores e vínculos registrados.',
 'delivery_editor':'Novo pedido: endereço, pagamento, troco e produtos.', 'delivery_receive':'Recebimento do delivery: modalidade real e responsável.',
 'delivery_refund':'Formulário de reembolso: registre o valor realmente devolvido.', 'delivery_return':'Conferência de unidades que voltaram em condição de revenda.',
 'delivery_retry':'Resumo real antes de criar outra tentativa.', 'purchase_form':'Entrada de mercadoria: quantidade, unidade e custo total.',
 'promotion_form':'Promoção por quantidade para o produto selecionado.', 'cash_close':'Fechamento: informe o dinheiro efetivamente contado.',
 'replenishment':'Sugestão de compras, sem efetuar uma compra.', 'supplier_credit':'Créditos do fornecedor: saldo a receber ou abater.',
 'sale_correction':'Correção da venda: mercadoria, reembolso e comanda são separados.', 'sale_refund':'Concluir o registro de reembolso após devolução real do valor.',
 'expense_pay':'Quitar uma conta: data, modalidade e origem do dinheiro.', 'cash_open':'Abrir caixa: informe o dinheiro inicial para troco.',
}
MAIN={'sales','tabs','products','purchases','cash','finance','monthly','results','replenishment','history','supplier_credit','delivery'}
FORM={'product_form','purchase_form','promotion_form','shortcut_form','stock_adjust','expense_form','rates','expense_pay','sale_correction','sale_refund','product_edit'}

def figure(image,max_height=170):
 if image.endswith('_diagram'):return Diagram(image), 'Esquema ilustrativo para orientar o procedimento; não é captura do Windows.'
 path=IMAGES/(image+'.png')
 if not path.is_file():raise ValueError('Imagem ausente: '+str(path))
 with PILImage.open(path) as im:
  # Recortes mecânicos destacam o conteúdo; os originais permanecem no repositório.
  w,h=im.size
  if image in MAIN:box=(210,84,w-4,min(h-28,520))
  elif image in FORM and h>340:box=(0,0,w,min(h,290))
  else:box=(0,0,w,h)
  clip=im.crop(box).convert('RGB')
  cache=Path('/tmp/bar-simples-manual-images');cache.mkdir(exist_ok=True)
  target=cache/(image+'.png');clip.save(target)
  pw,ph=clip.size
 ratio=min(WIDTH/pw,max_height/ph)
 fig=Image(str(target),width=pw*ratio,height=ph*ratio,hAlign='CENTER')
 return fig,(CAPTIONS.get(image,'Formulário real do programa.')+' Dados fictícios; imagem pode estar recortada. Amplie no leitor de PDF para conferir os detalhes.')

def steps(items):
 out=[]
 for n,item in enumerate(items,1):
  table=Table([[para(str(n),'number'),para(item)]],colWidths=[24,WIDTH-24],hAlign='LEFT')
  table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
  out.append(table)
 return out

def box(label,value):
 p=Paragraph('<b>'+text(label)+'</b> '+text(value),S['small']);t=Table([[p]],colWidths=[WIDTH])
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.4,LINE),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
 return t

def reference_pages(kind,pages):
 heading=para('Referências e versão','kicker');heading.toc_key=kind+'-references';heading.toc_level=0
 title=para('Fontes e links úteis','h1');title.toc_key=kind+'-links';title.toc_level=1
 flows=[PageBreak(),heading,title,para('Os links abaixo ajudam a conferir a versão, baixar o programa e consultar as instruções oficiais. As explicações de funções foram conferidas no código da versão entregue.','intro')]
 refs=[('Baixar Bar Simples 0.4.2-dev com atalho',ZIP),('Repositório do projeto e documentos',REPO),('Código-base do programa 0.4.2-dev (commit 397acca)',CODE),('Python: downloads oficiais para Windows','https://www.python.org/downloads/windows/'),('Python: uso e instalação no Windows (documentação oficial)','https://docs.python.org/pt-br/3/using/windows.html'),('Microsoft: comando wscript e Windows Script Host','https://learn.microsoft.com/pt-br/windows-server/administration/windows-commands/wscript')]
 for label,url in refs:flows.extend([link(label,url),Spacer(1,9)])
 flows.extend([Spacer(1,10),box('Sobre as imagens.','As telas do Bar Simples foram capturadas diretamente em Linux/Xvfb, em dados de demonstração isolados. No Windows, fontes e bordas podem variar. Diagramas de pastas, ZIP, Python e atalho são esquemas explicativos, não telas oficiais do Windows.'),Spacer(1,10),box('Sobre esta edição.','Programa 0.4.2-dev, edição 19/10/2026. A criação real do atalho e a ausência de console precisam ser confirmadas no notebook Windows. O programa continua dependente do Python instalado. Estes PDFs não instalam nem alteram seus dados.')])
 if kind=='usage':
  provenance=para('Como este guia foi conferido','h1');provenance.toc_key=kind+'-provenance';provenance.toc_level=1
  flows.extend([PageBreak(),para('Referências e versão','kicker'),provenance,para('Cada grupo foi comparado às telas, aos formulários e às regras do programa. A tabela indica as fontes primárias para manutenção e conferência; você não precisa ler código para usar o sistema.','intro')])
  sources=[('Atendimento e comandas','ui/sales.py · ui/tabs.py · ui/payment.py'),('Delivery e entregador','ui/delivery.py · ui/delivery_editor.py · ui/settlement.py · delivery/cancellation.py'),('Produtos e compras','ui/products.py · ui/purchases.py · inventory/service.py'),('Caixa e fechamento','ui/cash.py · cash/closing.py'),('Despesas e recorrências','ui/finance.py · ui/recurrence.py · finance/service.py'),('Histórico e backups','ui/history.py · ui/audit.py · maintenance/restore.py · security/service.py'),('Resultados e reposição','ui/monthly.py · ui/results.py · reporting/queries.py'),('Abertura e atalho','bootstrap.py · desktop.py · CRIAR_ATALHO.vbs')]
  for title,source in sources:flows.extend([para(title,'subhead'),para(source,'small'),Spacer(1,6)])
  flows.extend([Spacer(1,8),box('Limite conhecido de restauração.','Nesta edição, a mensagem final pode falhar depois da substituição dos dados, porque a interface é reconstruída. Por isso o guia manda preservar uma cópia antes e reabrir/conferir antes de voltar a atender. Falta de mensagem não comprova que nada foi restaurado.'),Spacer(1,8),para('Logo e identidade visual: arquivos da identidade Bar Simples presentes no projeto. Dados nas figuras: exclusivamente fictícios. O resultado financeiro é estimativa gerencial, não apuração fiscal.','small')])
 return flows


def build(kind):
 filename='instalacao.json' if kind=='installation' else 'uso.json'
 pages=json.loads((SOURCE/filename).read_text());OUT.mkdir(exist_ok=True)
 target=OUT/('Manual_Instalacao_Bar_Simples_0.4.2.pdf' if kind=='installation' else 'Manual_Uso_Bar_Simples_0.4.2.pdf')
 doc=ManualDoc(target,kind)
 toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC0',fontName='ManualBold',fontSize=10.2,leading=14,leftIndent=0,firstLineIndent=0,spaceBefore=9,textColor=GREEN),ParagraphStyle('TOC1',fontName='Manual',fontSize=9.1,leading=12.4,leftIndent=12,firstLineIndent=0,spaceBefore=2,textColor=INK)]
 story=[Spacer(1,650),NextPageTemplate('normal'),PageBreak(),para('Sumário','toc_title'),para('Clique em um título para ir à página. Também é possível abrir os marcadores do seu leitor de PDF.','intro'),toc]
 last=None
 for idx,p in enumerate(pages):
  story.append(PageBreak())
  section=p['section'];kicker=para(section,'kicker')
  if section!=last:kicker.toc_key=kind+'-section-'+str(idx);kicker.toc_level=0
  story.append(kicker)
  title=para(p['title'],'h1');title.toc_key=kind+'-'+p['id'];title.toc_level=1;story.append(title)
  story.append(para(p['intro'],'intro'))
  if p.get('image'):
   fig,caption=figure(p['image']);story.extend([fig,Spacer(1,5),para(caption,'caption')])
  story.append(para('Passo a passo','subhead'));story.extend(steps(p['steps']))
  if p.get('example'):story.extend([Spacer(1,5),box('Exemplo.',p['example']),Spacer(1,7)])
  if p.get('notes'):
   story.append(para('Para conferir','subhead'))
   for note in p['notes']:story.append(Paragraph('• '+text(note),S['small']))
  last=section
 story.extend(reference_pages(kind,pages))
 doc.multiBuild(story,maxPasses=5)
 return target

if __name__=='__main__':
 for kind in ('installation','usage'):print(build(kind))
