"""Generate the two one-page assessment PDFs (requires reportlab)."""

from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit

HERE = Path(__file__).resolve().parent
W, H = A4
INK = HexColor('#173b34')
MUTED = HexColor('#5d7168')
GREEN = HexColor('#eaf3e7')
LINE = HexColor('#dce7dd')


def heading(c, label, subtitle):
    c.setFillColor(INK); c.setFont('Helvetica-Bold', 18); c.drawString(34, H-43, label)
    c.setFillColor(MUTED); c.setFont('Helvetica', 8.4); c.drawString(34, H-59, subtitle)
    c.setStrokeColor(LINE); c.line(34, H-69, W-34, H-69)


def text(c, x, y, content, width, size=9, leading=12, bold=False):
    font = 'Helvetica-Bold' if bold else 'Helvetica'
    c.setFont(font, size); c.setFillColor(INK)
    for line in simpleSplit(content, font, size, width):
        c.drawString(x, y, line); y -= leading
    return y


def box(c, x, y, w, h, title, lines):
    c.setFillColor(white); c.setStrokeColor(LINE); c.roundRect(x, y, w, h, 7, fill=1, stroke=1)
    text(c, x+10, y+h-17, title, w-20, 9.5, 11, True)
    pos = y+h-32
    for line in lines:
        pos = text(c, x+10, pos, line, w-20, 8, 10)


def arrow(c, x1, y1, x2, y2):
    c.setStrokeColor(HexColor('#78a281')); c.setLineWidth(1.1); c.line(x1,y1,x2,y2)
    p=c.beginPath(); p.moveTo(x2,y2); p.lineTo(x2-4,y2+3); p.lineTo(x2-4,y2-3); p.close()
    c.setFillColor(HexColor('#78a281')); c.drawPath(p, fill=1, stroke=0)


def architecture():
    c=canvas.Canvas(str(HERE/'architecture.pdf'), pagesize=A4)
    heading(c,'System architecture','Credit Risk Portfolio Analytics  |  Synthetic-data demonstration')
    gap=10; x=34; width=(W-68-3*gap)/4; y=H-184
    stages=[('01  RAW DATA',['Five synthetic CSV tables','Customers, loans, bureau,','repayments, collections']),
            ('02  INGESTION',['Python + pandas','Validate keys; clean labels;','aggregate at account grain']),
            ('03  ANALYTICS',['pandas / FastAPI','Portfolio counts, rates,','dimensions and filters']),
            ('04  DASHBOARD',['React + Vite on Vercel','Account explorer, charts,','assistant and review queue'])]
    for i,(title,lines) in enumerate(stages): box(c,x+i*(width+gap),y,width,88,title,lines)
    for i in range(3): arrow(c,x+(i+1)*width+i*gap,y+44,x+(i+1)*(width+gap),y+44)
    text(c,34,H-215,'MODEL AND AI SERVICES',W-68,10,12,True)
    box(c,34,H-332,250,97,'DEFAULT MODEL  |  scikit-learn',[
        'Grouped customer holdout; logistic regression and random forest.',
        'Account score, log-odds drivers, AUC / KS / Gini.',
        'Exploratory only: input and default timing uncertain.'])
    box(c,311,H-332,250,97,'ANOMALY DETECTION  |  scikit-learn',[
        'Isolation Forest per loan type; repayment and bureau patterns.',
        'Review queue with peer percentiles and confirm / dismiss.',
        'PostgreSQL (Supabase) stores decisions; SQLite locally.'])
    box(c,34,H-470,527,113,'ASK THE PORTFOLIO  |  Gemini + FastAPI',[
        'Question enters the React dashboard and is sent to the FastAPI backend on Render.',
        'The backend sends Gemini the user question and a whitelist of metrics, dimensions and categories;',
        'it does not send raw account rows. Gemini returns a structured interpretation.',
        'Backend validates the plan, computes values from the prepared dataset and returns figures + source.',
        'Unsupported questions are declined; the analyst verifies the interpretation.'])
    text(c,34,H-504,'DATA AND CONTROL FLOW',W-68,10,12,True)
    y2=H-523
    for line in [
        'CSV inputs -> account-level features -> portfolio statistics and default-model scores -> FastAPI -> React.',
        'Full-history aggregates -> per-loan-type anomaly flags -> analyst decision -> Supabase PostgreSQL.',
        'Browser question -> FastAPI -> Gemini (question + allowed schema) -> validated plan -> local calculation.',
        'Credentials remain in backend environment variables; the frontend receives only API responses.'
    ]: y2=text(c,34,y2,line,W-68,8.5,16)
    c.setFillColor(MUTED); c.setFont('Helvetica',7.5)
    c.drawString(34,35,'Synthetic data only  |  Review actions currently unauthenticated  |  Source: repository code and supplied CSVs')
    c.showPage(); c.save()


def overview():
    c=canvas.Canvas(str(HERE/'solution_overview.pdf'), pagesize=A4)
    heading(c,'Solution overview','Credit Risk Portfolio Analytics  |  One-page assessment summary')
    y=H-91
    sections=[
      ('WORKFLOW', 'Portfolio: filter by region, loan type and employment; compare observed default rates and original lending amounts. Account explorer: look up a loan, its recorded outcome, exploratory logistic score and top log-odds contributions. Review model metrics and the anomaly queue in the same dashboard.'),
      ('TWO AI FEATURES AND HUMAN REVIEW', 'Ask the Portfolio: a submitted question triggers Gemini to select a supported calculation; the backend validates it and computes the figures. False positive: a question is misinterpreted; false negative: a valid question is declined. The analyst checks the metric, filters and source. Anomaly review: Isolation Forest flags about 5% within each loan type. False positive: a benign unusual account; false negative: a concerning account is missed. An analyst investigates and confirms or dismisses; peer percentiles provide context, not a causal explanation.'),
      ('DEFAULT MODEL AND MONITORING', 'Customer-grouped 80/20 holdout: logistic regression AUC 0.662, KS 0.249, Gini 0.323; random forest AUC 0.634, KS 0.204, Gini 0.267. Inputs include first-three-month repayments and bureau lines opened by the cutoff. Displayed logistic scores use training and held-out accounts (labeled). Monitor missingness, drift, calibration and discrimination on matured outcomes.'),
      ('THREE PORTFOLIO INSIGHTS', '1. Mortgages: 353/1,432 defaults (24.65%) vs 16.10% overall; prioritize a deeper mortgage review. 2. Unemployed borrowers: 251/718 (34.96%) vs salaried 1,130/7,546 (14.97%); investigate differences before action. 3. East + unemployed: 57/135 (42.22%); investigate this cross-dimensional segment and its sample size. These are associations, not causes.'),
      ('ASSUMPTIONS AND PRODUCTION NEEDS', 'Exposure means original loan amount, not current balance. Default dates, bureau reporting dates and historic customer snapshots are unavailable, so post-default leakage cannot be excluded; results are exploratory, not credit decisions. Bank teams must provide dated snapshots and outcomes, secure access, validation and governance, authentication and an audit trail. Current public review actions are unauthenticated.')
    ]
    for title, body in sections:
        y=text(c,34,y,title,W-68,9.2,11,True)-2
        y=text(c,34,y,body,W-68,8.15,10.6)-13
    if y < 43: raise ValueError(f'Overview content exceeds one page: {y}')
    c.setFillColor(MUTED); c.setFont('Helvetica',7.5); c.drawString(34,28,'Synthetic portfolio  |  Source: supplied CSVs and customer-grouped holdout results')
    c.showPage(); c.save()


if __name__ == '__main__':
    architecture(); overview()
