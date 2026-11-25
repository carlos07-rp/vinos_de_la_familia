import io, json, pandas as pd
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import db

def excel(lote):
    b=io.BytesIO()
    with pd.ExcelWriter(b,engine='openpyxl') as w:
        pd.DataFrame([lote]).to_excel(w,sheet_name='Lote',index=False)
        for t in db.TABLES: pd.DataFrame(db.rows(t,lote['id'])).to_excel(w,sheet_name=t,index=False)
    return b.getvalue()
def pdf(lote):
    b=io.BytesIO(); styles=getSampleStyleSheet(); styles['Title'].textColor=colors.HexColor('#722F37'); story=[Paragraph('VINTALYTICS',styles['Title']),Paragraph('Expediente del lote',styles['Heading2'])]
    def p(s): return Paragraph(escape(str(s)),styles['BodyText'])
    for k,v in lote.items(): story.append(p(f'{k}: {v}'))
    for t in db.TABLES:
        story.append(Paragraph(t.capitalize(),styles['Heading2']))
        records=db.rows(t,lote['id'])
        if not records: story.append(p('Sin registros.'))
        for r in records:
            for k,v in r.items():
                if k not in ('id','lote_id'): story.append(p(f'{k}: {v}'))
            story.append(Spacer(1,8))
    SimpleDocTemplate(b,pagesize=A4,title='VINTALYTICS | Expediente').build(story); return b.getvalue()
