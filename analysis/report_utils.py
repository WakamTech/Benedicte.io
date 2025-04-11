# analysis/report_utils.py

import io
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import logging

logger = logging.getLogger(__name__)

# --- PDF Generation ---

def generate_pdf_report(analysis_data, scenario_request):
    """Génère le rapport PDF en mémoire."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = f"Rapport d'Analyse - Demande #{scenario_request.id}"
    story.append(Paragraph(title, styles['h1']))
    story.append(Spacer(1, 0.5*cm))

    # Request Info
    story.append(Paragraph(f"Type d'analyse : {scenario_request.get_request_type_display()}", styles['Normal']))
    if scenario_request.user_description:
        story.append(Paragraph(f"Description : {scenario_request.user_description}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))

    if not analysis_data:
        story.append(Paragraph("Données d'analyse non disponibles.", styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    # Synthesis
    story.append(Paragraph("Synthèse", styles['h2']))
    story.append(Paragraph(analysis_data.get('synthese', 'N/A').replace('\n', '<br/>'), styles['Normal']))
    story.append(Spacer(1, 0.5*cm))

    # Forecasts Table
    story.append(Paragraph("Prévisions (3 ans)", styles['h2']))
    story.append(Paragraph(analysis_data.get('hypotheses_previsions', 'Hypothèses non spécifiées.'), styles['Italic']))
    story.append(Spacer(1, 0.2*cm))

    forecast_data = analysis_data.get('previsions_3_ans', [])
    if forecast_data:
        table_data = [['Année', 'CA Prévisionnel (€)', 'Charges Prév. (€)', 'Marge Brute Prév. (€)']]
        for row in forecast_data:
            table_data.append([
                row.get('annee', 'N/A'),
                f"{row.get('ca_prev', 0):,.2f}".replace(",", " "), # Format number
                f"{row.get('charges_prev', 0):,.2f}".replace(",", " "),
                f"{row.get('marge_brute_prev', 0):,.2f}".replace(",", " ")
            ])

        t = Table(table_data, colWidths=[2*cm, 4*cm, 4*cm, 4*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), # Align numbers right
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Données de prévisions non disponibles.", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))

    # Risks
    story.append(Paragraph("Risques Clés", styles['h2']))
    risks = analysis_data.get('risques_cles', [])
    if risks:
        risk_items = [ListItem(Paragraph(risk, styles['Normal'])) for risk in risks]
        story.append(ListFlowable(risk_items, bulletType='bullet', start='bulletchar'))
    else:
        story.append(Paragraph("Aucun risque clé identifié.", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))

    # Recommendations
    story.append(Paragraph("Recommandations", styles['h2']))
    recommendations = analysis_data.get('recommandations', [])
    if recommendations:
        reco_items = []
        for reco in recommendations:
            level = reco.get('niveau', '[INFO]')
            color = 'black'
            if '[VERT]' in level: color = 'green'
            elif '[ORANGE]' in level: color = 'orange'
            elif '[ROUGE]' in level: color = 'red'
            text = f"<font color='{color}'><b>{level}</b></font> {reco.get('recommendation', 'N/A')}"
            reco_items.append(ListItem(Paragraph(text, styles['Normal'])))
        story.append(ListFlowable(reco_items, bulletType='bullet', start='bulletchar'))
    else:
        story.append(Paragraph("Aucune recommandation fournie.", styles['Normal']))

    try:
        doc.build(story)
    except Exception as e:
         logger.error(f"Erreur lors de la construction du PDF pour demande {scenario_request.id}: {e}")
         # Peut-être retourner un buffer vide ou lever une exception spécifique
         return None

    buffer.seek(0)
    return buffer

# --- Excel Generation ---

def generate_excel_report(analysis_data, scenario_request):
    """Génère le rapport Excel en mémoire."""
    buffer = io.BytesIO()

    if not analysis_data:
         # Retourner un buffer vide si pas de données
         return buffer

    # Utiliser Pandas ExcelWriter
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Feuille 1: Synthèse & Infos
        info_data = {
            'Information': ['ID Demande', 'Type Analyse', 'Description', 'Synthèse Analyse', 'Hypothèses Prévisions'],
            'Valeur': [
                scenario_request.id,
                scenario_request.get_request_type_display(),
                scenario_request.user_description or 'N/A',
                analysis_data.get('synthese', 'N/A'),
                analysis_data.get('hypotheses_previsions', 'N/A')
            ]
        }
        df_info = pd.DataFrame(info_data)
        df_info.to_excel(writer, sheet_name='Synthèse', index=False)

        # Feuille 2: Prévisions
        forecast_data = analysis_data.get('previsions_3_ans', [])
        if forecast_data:
            df_forecast = pd.DataFrame(forecast_data)
            # Renommer colonnes pour clarté
            df_forecast = df_forecast.rename(columns={
                'annee': 'Année',
                'ca_prev': 'CA Prévisionnel (€)',
                'charges_prev': 'Charges Prévisionnelles (€)',
                'marge_brute_prev': 'Marge Brute Prévisionnelle (€)'
            })
            df_forecast.to_excel(writer, sheet_name='Prévisions_3_Ans', index=False)

        # Feuille 3: Risques
        risks = analysis_data.get('risques_cles', [])
        if risks:
            df_risks = pd.DataFrame({'Risques Clés Identifiés': risks})
            df_risks.to_excel(writer, sheet_name='Risques', index=False)

        # Feuille 4: Recommandations
        recommendations = analysis_data.get('recommandations', [])
        if recommendations:
            df_recos = pd.DataFrame(recommendations)
             # Renommer colonnes
            df_recos = df_recos.rename(columns={
                'recommendation': 'Recommandation',
                'niveau': 'Niveau'
            })
            df_recos.to_excel(writer, sheet_name='Recommandations', index=False)

    buffer.seek(0)
    return buffer