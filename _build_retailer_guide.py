# -*- coding: utf-8 -*-
"""Builds the retailer-facing user guide DOCX for ApexPricing."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ACCENT = RGBColor(0x02, 0x84, 0xC7)   # deep blue
DARK = RGBColor(0x1F, 0x29, 0x37)
GRAY = RGBColor(0x6B, 0x72, 0x80)

doc = Document()

# Base style
normal = doc.styles['Normal']
normal.font.name = 'Calibri'
normal.font.size = Pt(10.5)
normal.font.color.rgb = DARK

for lvl, sz in (('Heading 1', 15), ('Heading 2', 12.5)):
    st = doc.styles[lvl]
    st.font.name = 'Calibri'
    st.font.size = Pt(sz)
    st.font.bold = True
    st.font.color.rgb = ACCENT

def p(text='', bold=False, italic=False, size=None, color=None, space_after=6):
    par = doc.add_paragraph()
    run = par.add_run(text)
    run.bold = bold
    run.italic = italic
    if size: run.font.size = Pt(size)
    if color: run.font.color.rgb = color
    par.paragraph_format.space_after = Pt(space_after)
    return par

def bullet(text, bold_prefix=None):
    par = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        r = par.add_run(bold_prefix)
        r.bold = True
        par.add_run(text)
    else:
        par.add_run(text)
    par.paragraph_format.space_after = Pt(3)
    return par

def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ''
        run = hdr[i].paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        # dark header shading via cell XML
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:fill'), '1F2937')
        hdr[i]._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
            for pr in cells[i].paragraphs:
                for run in pr.runs:
                    run.font.size = Pt(9.5)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    return t

# ---------- Title ----------
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run('APEXPRICING')
r.bold = True
r.font.size = Pt(26)
r.font.color.rgb = ACCENT
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("Retailer's User Guide — Turning AI Pricing into Store Profit")
r.font.size = Pt(13)
r.font.color.rgb = GRAY
meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = meta.add_run('AI Dynamic Pricing & Inventory Lifecycle Optimization  ·  Indian Consumer Electronics Retail  ·  Demo Edition')
r.italic = True
r.font.size = Pt(9)
r.font.color.rgb = GRAY
doc.add_paragraph()

# ---------- 1 ----------
doc.add_heading('1. What This Tool Does For You', level=1)
p('Every phone sitting on your shelf costs you money twice: working-capital interest and storage, plus the price collapse when the next model launches. This engine tells you, for every SKU in every store, the selling price that maximizes total profit across the product\u2019s remaining life — not just today\u2019s margin.')

# ---------- 2 ----------
doc.add_heading('2. The Core Idea: Lifecycle Profit, Not Today\u2019s Margin', level=1)
p('Traditional pricing asks "what margin do I make on this unit?" ApexPricing asks "how much total profit will this stock generate before the successor arrives?" It adds up:')
bullet('gross margin on expected sales,', bold_prefix='+  ')
bullet('holding and financing cost of stock sitting in stores,', bold_prefix='\u2212  ')
bullet('depreciation write-down on units left stranded after the successor launches.', bold_prefix='\u2212  ')
p('The flagship demo SKU shows why this matters:', space_after=4)
table(
    ['Price', 'Daily Demand', 'Stock Cleared (60 days)', 'Leftover Units', 'Expected Profit'],
    [
        ['\u20b979,999 (status quo)', '10.2 u/day', '611 units', '188 (\u2248\u20b938L write-down)', '\u20b918.2 Lakh'],
        ['\u20b979,000 (AI recommended)', '12.4 u/day', '745 units', '54 units', '\u20b956.5 Lakh'],
    ],
    widths=[2.0, 1.2, 1.5, 1.8, 1.3]
)
p('A tiny \u20b9999 price cut triples lifecycle profit because it avoids most of the end-of-life loss. That is the engine\u2019s whole philosophy: small, early, data-driven moves beat big, late, panic markdowns.', space_after=10)

# ---------- 3 ----------
doc.add_heading('3. Your Playbook, Screen by Screen', level=1)
table(
    ['Screen', 'It answers', 'Your action'],
    [
        ['Portfolio Summary', 'Which SKUs are burning money right now?', 'Work the top-3 opportunities table first; check the "Pre-Successor At Risk" KPI.'],
        ['SKU Matrix', 'What price should each SKU be at?', 'Filter by Price Increases to capture margin; filter by Clearance Markdown / High Risk to act today.'],
        ['Elasticity Simulator', 'What if I match Flipkart, or hold?', 'Drag the price slider and watch Horizon Net Profit and clearance time before committing.'],
        ['Market Intelligence', 'Am I premium or underpriced vs Amazon/Flipkart/Croma?', 'Defend justified premium pricing; fix accidental under-pricing.'],
        ['Store Balancing', 'Which store is stockout-bound while another sits on stock?', 'Approve profitable transfers (\u20b9250/unit logistics vs margin saved).'],
        ['Explain (per SKU)', 'Why does the model say this?', 'Read the contribution bars: competitor stockout, inventory pressure, successor proximity.'],
        ['Simulate Launch Signal', 'A successor just got announced — what now?', 'Trigger the event and execute the new markdown immediately, before market prices collapse.'],
    ],
    widths=[1.2, 2.2, 3.4]
)
doc.add_paragraph()

# ---------- 4 ----------
doc.add_heading('4. A Real Walkthrough: iPhone 17 256GB', level=1)
bullet('800 units in stock, cost \u20b968,000, selling at \u20b979,999, successor in 60 days. The engine detects the clearance shortfall (611 sold vs 800 in stock) and the \u20b938 Lakh depreciation risk.', bold_prefix='1. Open Portfolio Summary: ')
bullet('The demand curve shows \u20b978,999–79,000 as the sweet spot — the model predicts 12.4 units/day there.', bold_prefix='2. Check the Elasticity Simulator: ')
bullet('The SHAP bars show competitor pricing pressure is mild and inventory pressure dominates — a small cut, not a fire-sale, is optimal.', bold_prefix='3. Click Explain: ')
bullet('\u20b979,000 — a \u20b9999 reduction, 93% clearance, +\u20b938.3 Lakh vs status quo. Matching Flipkart at \u20b976,999 would LOSE money; a 15% blanket markdown would go below cost (forbidden).', bold_prefix='4. Execute the recommendation: ')
bullet('Monitor daily velocity for a week; if clearance lags, the simulator recalculates the next step.', bold_prefix='5. Track and iterate: ')

# ---------- 5 ----------
doc.add_heading('5. Your Weekly Routine', level=1)
table(
    ['When', 'Do'],
    [
        ['Daily', 'SKU Matrix → High-Risk rows; Sync Data; execute clearances and price increases.'],
        ['Monday', 'Portfolio Summary → top-3 opportunities; Store Balancing → approve transfer plan.'],
        ['After any competitor drop', 'Elasticity Simulator → test matching vs holding before reacting.'],
        ['After any launch announcement', 'Simulate Launch Signal → execute the re-optimized markdown the same day.'],
        ['Month end', 'Recalculate Engine → compare predicted vs actual; feed deviations back into the data.'],
    ],
    widths=[1.7, 5.1]
)
doc.add_paragraph()

# ---------- 6 ----------
doc.add_heading('6. Going Live With Your Own Data', level=1)
p('The demo runs on simulated data. To make real decisions, feed the engine your POS/ERP exports — six CSV files with these columns:', space_after=4)
table(
    ['File', 'What it holds'],
    [
        ['products.csv', 'Your catalog: SKU id, brand/model, MRP, successor model, launch & successor dates.'],
        ['stores.csv', 'Your branches: id, name, city, footfall index.'],
        ['costs.csv', 'Purchase cost, landed cost, holding/financing/depreciation rates per SKU.'],
        ['competitors.csv', 'Daily competitor prices & stock availability (Amazon, Flipkart, Croma...).'],
        ['sales.csv', 'Daily transactions: store, SKU, selling price, units, revenue.'],
        ['inventory.csv', 'Daily stock per store-SKU: opening, sold, received, closing.'],
    ],
    widths=[1.7, 5.1]
)
p('Steps: (1) fill the templates in data/import_templates, (2) copy them over data/synthetic or repoint src/config.py, (3) run python main.py --train, (4) open the dashboard and click Recalculate Engine.', space_after=4)
p('Tip: the model learns price sensitivity from price VARIATION — include your past markdowns, promos and price increases. A flat price history makes elasticity honestly "Not Identifiable".', italic=True)

# ---------- 7 ----------
doc.add_heading('7. Rules the Engine Never Breaks', level=1)
bullet('Selling price \u2264 MRP at all times (Legal Metrology Packaged Commodities Rules).', bold_prefix='Legal ceiling: ')
bullet('No recommendation below acquisition cost — loss tolerance is 0 by default.', bold_prefix='Margin floor: ')
bullet('If data cannot identify price sensitivity, the engine says so instead of inventing a number.', bold_prefix='Honesty: ')
bullet('Every recommendation comes with model-level explanation (SHAP contribution bars).', bold_prefix='Explainability: ')

# ---------- 8 ----------
doc.add_heading('8. What It Cannot Do Yet', level=1)
bullet('Live competitor scraping (currently you update competitors.csv manually).')
bullet('Your exact store/SKU specifics until real data is imported.')
bullet('Replacement for your judgment on promotions, festive pricing, and customer relationships — it is a decision aid, not autopilot.')

doc.save('docs/Retailer_User_Guide.docx')
print('DOCX saved: docs/Retailer_User_Guide.docx')
