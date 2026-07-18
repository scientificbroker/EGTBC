import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# ──────────────────────────────────────────────────
# CONFIG DE PÁGINA
# ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Calculadora IGM — EGTBC 2026",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ──────────────────────────────────────────────────
# CSS PERSONALIZADO
# ──────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .header-banner {
    background: linear-gradient(90deg, #0F2A5C 0%, #1A4A8A 60%, #00B8A9 100%);
    padding: 18px 28px; border-radius: 12px; margin-bottom: 24px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .header-title { color: white; font-size: 1.6rem; font-weight: 700; margin: 0; }
  .header-sub   { color: #B2EBF2; font-size: 0.85rem; margin: 4px 0 0 0; }

  .card {
    background: white; border-radius: 10px; padding: 20px 24px;
    border: 1px solid #E0E0E0; margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  .card-header {
    font-weight: 700; font-size: 1rem; margin-bottom: 14px;
    padding-bottom: 10px; border-bottom: 2px solid;
  }

  .metric-box {
    border-radius: 10px; padding: 16px 20px; text-align: center;
    border: 1px solid #E0E0E0;
  }
  .metric-label { font-size: 0.78rem; font-weight: 600; letter-spacing: 0.05em; }
  .metric-value { font-size: 2rem; font-weight: 700; line-height: 1.1; }
  .metric-sub   { font-size: 0.72rem; color: #888; margin-top: 2px; }

  .semaforo-verde   { background:#D5F5E3; border:2px solid #1A7B4E; }
  .semaforo-amarillo{ background:#FFF3CD; border:2px solid #B45309; }
  .semaforo-rojo    { background:#FFEBEE; border:2px solid #C62828; }

  .igm-result {
    border-radius: 14px; padding: 22px 28px; text-align: center;
    margin-top: 10px; border: 3px solid;
  }
  .igm-value  { font-size: 3.5rem; font-weight: 800; line-height: 1; }
  .igm-label  { font-size: 1.1rem; font-weight: 600; margin-top: 6px; }
  .igm-action { font-size: 0.9rem; margin-top: 4px; }

  .pill {
    display: inline-block; border-radius: 20px; padding: 3px 14px;
    font-size: 0.78rem; font-weight: 600; margin: 2px;
  }

  .stSlider > div > div > div > div { background: #00B8A9 !important; }
  .stSlider [data-testid="stThumbValue"] { color: #0F2A5C !important; font-weight: 700; }

  div[data-testid="stSelectbox"] label { font-weight: 600; }
  div[data-testid="stTextInput"]  label { font-weight: 600; }

  .matching-row {
    background: white; border-radius: 10px; padding: 14px 18px;
    border-left: 5px solid; margin-bottom: 10px;
    display: flex; align-items: center; justify-content: space-between;
  }

  footer { visibility: hidden; }
  #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# CONSTANTES
# ──────────────────────────────────────────────────
RETOS = {
    "R1": "Sector Alimentario y Agroindustrial",
    "R2": "Ingeniería Civil y Construcción Subterránea",
    "R3": "Analítica de Datos e IA Industrial",
    "R4": "Sostenibilidad en Operaciones Mineras",
    "R5": "Geotécnica y Control de Vacíos",
    "R6": "Agricultura Sostenible y Bioprotección",
    "R7": "Alimentación Sostenible y Fitoquímica",
    "R8": "Manufactura Avanzada y Minería de Precisión",
}

PREGUNTAS = {
    "ICG": {
        "nombre": "Compatibilidad Global",
        "peso": 0.40,
        "color": "#1A5276",
        "bg": "#D6EAF8",
        "items": [
            ("P1.1", "TRL Alignment",
             "¿Qué tan cercana está la TRL actual a la que necesita la empresa?",
             "1 = Brecha enorme (TRL 2 vs TRL 9)  ·  3 = Brecha moderada  ·  5 = TRLs coinciden perfectamente"),
            ("P1.2", "Alineamiento de Sector",
             "¿La solución es exacta para el sector donde opera la empresa?",
             "1 = Otro sector, adaptación compleja  ·  3 = Aplicable con ajustes  ·  5 = Diseñada para este sector"),
            ("P1.3", "Brecha de Desempeño",
             "¿Cuánto de la especificación de la empresa cumple la tecnología?",
             "1 = Cumple <50%  ·  3 = Cumple 75–80%  ·  5 = Cumple 100% de la especificación"),
            ("P1.4", "Dependencia Externa",
             "¿Requiere tecnologías que no están disponibles en Perú?",
             "1 = Depende de 3+ tecnologías críticas importadas  ·  3 = 1 tecnología externa  ·  5 = Completamente autónoma"),
        ]
    },
    "IVC": {
        "nombre": "Viabilidad Comercial",
        "peso": 0.35,
        "color": "#1A7B4E",
        "bg": "#D5F5E3",
        "items": [
            ("P2.1", "Presupuesto I+D",
             "¿La empresa tiene presupuesto REAL para financiar la implementación?",
             "1 = Sin presupuesto  ·  3 = Presupuesto parcial (40–60%)  ·  5 = Presupuesto 100% propio"),
            ("P2.2", "Madurez Organizacional",
             "¿Ha trabajado antes con universidades en proyectos de transferencia tecnológica?",
             "1 = Nunca, desconoce procesos  ·  3 = 1 proyecto previo  ·  5 = Muy experimentada en TT"),
            ("P2.3", "Capacidad Técnica",
             "¿Tiene equipo competente para recibir e implementar la tecnología?",
             "1 = Sin personal especializado  ·  3 = Necesita entrenamiento  ·  5 = Especialistas listos"),
            ("P2.4", "Timeline Realista",
             "¿El plazo propuesto para implementación es factible?",
             "1 = Timeline imposible  ·  3 = Ambicioso con riesgo moderado  ·  5 = Conservador, 95%+ de éxito"),
            ("P2.5", "Apoyo de Directiva",
             "¿El liderazgo de la empresa respalda activamente este proyecto?",
             "1 = Solo 1 persona sin validación  ·  3 = Apoyo de directiva  ·  5 = Máxima prioridad ejecutiva"),
        ]
    },
    "IRR": {
        "nombre": "Retorno y Riesgo",
        "peso": 0.25,
        "color": "#7D3C98",
        "bg": "#E8DAEF",
        "items": [
            ("P3.1", "ROI Estimado",
             "¿Cuál es el retorno de inversión esperado para la empresa si la TT es exitosa?",
             "1 = ROI nulo o negativo  ·  3 = ROI 20–50% anual  ·  5 = ROI >100% anual, game-changer"),
            ("P3.2", "Retorno Sostenido",
             "¿El acuerdo genera ingresos CONTINUOS o es un pago único?",
             "1 = Pago único sin continuidad  ·  3 = Royalties sobre ventas  ·  5 = Múltiples streams de ingresos"),
            ("P3.3", "Riesgo IP",
             "¿Hay claridad sobre quién es dueño de la propiedad intelectual generada?",
             "1 = Conflicto potencial de IP  ·  3 = Acuerdo en IP base, gris en mejoras  ·  5 = IP 100% clarificada"),
            ("P3.4", "Riesgo Técnico",
             "¿Cuál es la probabilidad de que la tecnología NO funcione en campo real?",
             "1 = Riesgo >60% de fracaso  ·  3 = Riesgo 20–40%  ·  5 = Riesgo <10%, validada en campo similar"),
            ("P3.5", "Sostenibilidad de Alianza",
             "¿Ambas partes seguirán comprometidas más allá del contrato inicial?",
             "1 = Relación transaccional  ·  3 = Compromiso 1–2 años  ·  5 = Partnership 5+ años"),
        ]
    }
}

# ──────────────────────────────────────────────────
# CONEXIÓN A GOOGLE SHEETS & SANITIZACIÓN
# ──────────────────────────────────────────────────
@st.cache_resource(ttl=30)
def get_sheet(worksheet_name="matchings"):
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        client = gspread.authorize(creds)
        sh = client.open_by_key(st.secrets["spreadsheet_id"])
        try:
            ws = sh.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=worksheet_name, rows=500, cols=30)
            headers = ["id","timestamp","equipo","reto","tecnologia","empresa",
                       "P1.1","P1.2","P1.3","P1.4",
                       "P2.1","P2.2","P2.3","P2.4","P2.5",
                       "P3.1","P3.2","P3.3","P3.4","P3.5",
                       "ICG","IVC","IRR","IGM","semaforo","decision"]
            ws.append_row(headers)
        return ws
    except Exception as e:
        return None

def leer_matchings(worksheet_name="matchings"):
    ws = get_sheet(worksheet_name)
    if ws is None:
        return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            return df
        
        # ── MAPEO AUTOMÁTICO DE COLUMNAS GOOGLE FORMS (Preguntas largas → P1.1 a P3.5 y metadatos) ──
        # Si el DataFrame tiene títulos largos de Google Forms, los mapeamos automáticamente:
        mapeo_preguntas = {
            "madurez": "P1.1",
            "sector": "P1.2",
            "brecha": "P1.3",
            "other": "P1.4", "externa": "P1.4",
            "presupuesto": "P2.1",
            "trabajado antes": "P2.2", "capacidad de gestionar": "P2.2",
            "equipo técnico": "P2.3", "competente": "P2.3",
            "timeline": "P2.4", "realista": "P2.4",
            "leadership": "P2.5", "directiva": "P2.5",
            "retorno de inversión": "P3.1", "roi": "P3.1",
            "retorno sostenido": "P3.2",
            "dueño de la ip": "P3.3", "claridad en quién es dueño": "P3.3",
            "riesgo de que la tecnología no funcione": "P3.4", "riesgo": "P3.4",
            "mantener comprometidas": "P3.5", "compromiso": "P3.5"
        }
        
        for col in df.columns:
            col_lower = str(col).lower()
            # Mapeo por palabras clave si las columnas P1.1... no existen ya
            for clave, cod in mapeo_preguntas.items():
                if clave in col_lower and cod not in df.columns:
                    df[cod] = df[col]
                    break
            # Mapeo de metadatos si vienen de preguntas o columnas de forms
            if "reto" in col_lower and "reto" not in df.columns:
                df["reto"] = df[col]
            elif ("tecnolog" in col_lower or "proyecto" in col_lower) and "tecnologia" not in df.columns and "madurez" not in col_lower and "brecha" not in col_lower and "other" not in col_lower and "riesgo" not in col_lower:
                df["tecnologia"] = df[col]
            elif "empresa" in col_lower and "empresa" not in df.columns and not any(k in col_lower for k in ["madurez", "brecha", "presupuesto", "trabajado", "equipo", "timeline", "leadership", "roi", "retorno", "riesgo"]):
                df["empresa"] = df[col]
            elif ("correo" in col_lower or "email" in col_lower) and "equipo" not in df.columns:
                df["equipo"] = df[col]
        
        # Si por posición tenemos las 15 preguntas continuas y faltan códigos P1.x:
        if "Marca temporal" in df.columns and "P1.1" not in df.columns:
            preg_cols_pos = [f"P1.{i}" for i in range(1, 5)] + [f"P2.{i}" for i in range(1, 6)] + [f"P3.{i}" for i in range(1, 6)]
            # Si el form tiene Reto, Tecnología y Empresa en col 2, 3 y 4 (total >= 20 columnas) las preguntas inician en col 5
            start_idx = 5 if len(df.columns) >= 20 else 2
            for idx_offset, cod in enumerate(preg_cols_pos):
                target_col_idx = start_idx + idx_offset
                if target_col_idx < len(df.columns) and cod not in df.columns:
                    df[cod] = df.iloc[:, target_col_idx]

        # ── Sanitización y Cálculo al vuelo (Compatible con Google Forms y Streamlit) ──
        str_cols = ["id", "timestamp", "equipo", "reto", "tecnologia", "empresa", "semaforo", "decision"]
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            else:
                if col == "reto": df[col] = "Por definir"
                elif col == "tecnologia": df[col] = "Tecnología / Proyecto (Falta campo en Form)"
                elif col == "empresa": df[col] = "Empresa evaluada"
                elif col == "equipo": df[col] = "Evaluador"
                else: df[col] = "—"
                
        # Convertir preguntas P1.1 a P3.5 a numérico si existen
        preg_cols = [f"P1.{i}" for i in range(1, 5)] + [f"P2.{i}" for i in range(1, 6)] + [f"P3.{i}" for i in range(1, 6)]
        for col in preg_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        # Convertir o calcular columnas numéricas principales
        num_cols = ["ICG", "IVC", "IRR", "IGM"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        # Si vienen del Google Form sin calcular los índices de resumen, se calculan en vivo:
        if "IGM" not in df.columns or df["IGM"].sum() == 0:
            icg_cols = [f"P1.{i}" for i in range(1, 5) if f"P1.{i}" in df.columns]
            ivc_cols = [f"P2.{i}" for i in range(1, 6) if f"P2.{i}" in df.columns]
            irr_cols = [f"P3.{i}" for i in range(1, 6) if f"P3.{i}" in df.columns]
            if icg_cols and ivc_cols and irr_cols:
                df["ICG"] = round((df[icg_cols].sum(axis=1) / 4) * 2, 2)
                df["IVC"] = round((df[ivc_cols].sum(axis=1) / 5) * 2, 2)
                df["IRR"] = round((df[irr_cols].sum(axis=1) / 5) * 2, 2)
                df["IGM"] = round((df["ICG"] * 0.40) + (df["IVC"] * 0.35) + (df["IRR"] * 0.25), 2)
                
        # Asignar semáforo y decisión si faltan
        def asignar_sem(igm_val):
            sem, accion, _, _, _ = semaforo_info(igm_val)
            return sem, accion
        
        if "semaforo" not in df.columns or df["semaforo"].eq("").all() or df["semaforo"].eq("nan").all():
            res = df["IGM"].apply(asignar_sem)
            df["semaforo"] = [r[0] for r in res]
            df["decision"] = [r[1] for r in res]
            
        return df
    except Exception:
        return pd.DataFrame()

def guardar_matching(row_data: dict, worksheet_name="matchings"):
    ws = get_sheet(worksheet_name)
    if ws is None:
        st.error("No se pudo conectar con Google Sheets. Verifica las credenciales en Secrets.")
        return False
    try:
        headers = ws.row_values(1)
        if not headers:
            headers = ["id","timestamp","equipo","reto","tecnologia","empresa",
                       "P1.1","P1.2","P1.3","P1.4","P2.1","P2.2","P2.3","P2.4","P2.5",
                       "P3.1","P3.2","P3.3","P3.4","P3.5","ICG","IVC","IRR","IGM","semaforo","decision"]
        row = [row_data.get(h, "") for h in headers]
        ws.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# ──────────────────────────────────────────────────
# FUNCIONES DE CÁLCULO
# ──────────────────────────────────────────────────
def calcular_igm(scores: dict):
    icg_vals = [scores.get(f"P1.{i}", 0) for i in range(1, 5)]
    ivc_vals = [scores.get(f"P2.{i}", 0) for i in range(1, 6)]
    irr_vals = [scores.get(f"P3.{i}", 0) for i in range(1, 6)]

    icg = (sum(icg_vals) / 4) * 2
    ivc = (sum(ivc_vals) / 5) * 2
    irr = (sum(irr_vals) / 5) * 2
    igm = round((icg * 0.40) + (ivc * 0.35) + (irr * 0.25), 2)

    return round(icg, 2), round(ivc, 2), round(irr, 2), igm

def semaforo_info(igm: float):
    if igm >= 7.0:
        return ("🟢 VERDE", "Formar equipo INMEDIATAMENTE",
                "#D5F5E3", "#1A7B4E", "semaforo-verde")
    elif igm >= 5.0:
        return ("🟡 AMARILLO", "Segunda evaluación + condiciones",
                "#FFF3CD", "#B45309", "semaforo-amarillo")
    else:
        return ("🔴 ROJO", "No viable — documentar y redirigir",
                "#FFEBEE", "#C62828", "semaforo-rojo")

# ──────────────────────────────────────────────────
# COMPONENTES UI
# ──────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div class="header-banner">
      <div>
        <p class="header-title">🎯 Calculadora IGM — Matchmaking Tecnológico</p>
        <p class="header-sub">I Encuentro de Gestores Tecnológicos y Brokers Científicos 2026
           · Día 3 · OPEN PUCP San Miguel · Grupo Biogenia × CIDE-PUCP × BioActiva</p>
      </div>
      <div style="color:#B2EBF2; font-size:0.82rem; text-align:right;">
        IGM = (ICG×0.40) + (IVC×0.35) + (IRR×0.25)<br>
        Escala Likert 1–5 → convertida a 0–10
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_subindice(key_prefix: str, config: dict, expanded: bool = True):
    color  = config["color"]
    bg     = config["bg"]
    nombre = config["nombre"]
    peso   = int(config["peso"] * 100)
    items  = config["items"]

    with st.expander(
        f"**{key_prefix} — {nombre}** · Peso {peso}%",
        expanded=expanded
    ):
        scores = {}
        for pid, titulo, pregunta, escala in items:
            st.markdown(f"""
            <div style="background:{bg}; border-radius:8px; padding:10px 14px;
                        margin-bottom:6px; border-left:4px solid {color}">
              <span style="color:{color}; font-weight:700; font-size:0.82rem;">{pid}</span>
              <span style="font-weight:600; font-size:0.92rem; margin-left:8px;">{titulo}</span><br>
              <span style="font-size:0.83rem; color:#444;">{pregunta}</span><br>
              <span style="font-size:0.75rem; color:#777; font-style:italic;">{escala}</span>
            </div>
            """, unsafe_allow_html=True)
            scores[pid] = st.slider(
                label=f"{pid} — {titulo}",
                min_value=1, max_value=5, value=3,
                key=f"slider_{key_prefix}_{pid}",
                label_visibility="collapsed"
            )
        return scores

def render_igm_card(icg, ivc, irr, igm):
    sem, accion, bg, fg, css_class = semaforo_info(igm)
    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        (c1, "ICG", icg, "#1A5276", "#D6EAF8", "Compat. Global ×0.40"),
        (c2, "IVC", ivc, "#1A7B4E", "#D5F5E3", "Viabilidad Comercial ×0.35"),
        (c3, "IRR", irr, "#7D3C98", "#E8DAEF", "Retorno y Riesgo ×0.25"),
        (c4, "IGM", igm, fg,         bg,         "Índice de Matchmaking Global"),
    ]
    for col, lbl, val, fc, bc, sub in metrics:
        with col:
            brd = "3px solid" if lbl == "IGM" else "1px solid"
            st.markdown(f"""
            <div class="metric-box"
                 style="background:{bc}; border:{brd} {fc};">
              <div class="metric-label" style="color:{fc};">{lbl}</div>
              <div class="metric-value" style="color:{fc};">
                  {'<b>' if lbl=='IGM' else ''}{val:.1f}{'</b>' if lbl=='IGM' else ''}
              </div>
              <div class="metric-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="igm-result" style="background:{bg}; border-color:{fg};">
      <div class="igm-value" style="color:{fg};">{igm:.2f} / 10</div>
      <div class="igm-label" style="color:{fg};">{sem}</div>
      <div class="igm-action" style="color:{fg};">{accion}</div>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# SIDEBAR — NAVEGACIÓN & FUENTE DE DATOS
# ──────────────────────────────────────────────────
render_header()

with st.sidebar:
    st.markdown("### 🧭 Navegación")
    pagina = st.radio(
        "Selecciona una vista:",
        ["📝 Formulario de Evaluación",
         "📊 Dashboard en Tiempo Real",
         "ℹ️ Instrucciones IGM"],
        index=0,
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("### 📋 Fuente de Datos (Google Sheets)")
    pestaña_activa = st.text_input(
        "Pestaña vinculada:",
        value="matchings",
        help="Escribe 'matchings' (para este form) o el nombre de tu pestaña de Google Forms (ej: 'Respuestas de formulario 1')."
    )
    st.markdown("---")
    st.markdown("""
    **Leyenda IGM**  
    🟢 ≥ 7.0 → Equipo inmediato  
    🟡 5.0–6.9 → Con condiciones  
    🔴 < 5.0 → No viable  
    """)
    st.markdown("---")
    st.caption("Grupo Biogenia · I EGTBC 2026  \n`conecta@biogeniainnova.com`")

# ══════════════════════════════════════════════════
# PÁGINA 1: FORMULARIO
# ══════════════════════════════════════════════════
if pagina == "📝 Formulario de Evaluación":
    st.subheader("📝 Formulario de Evaluación IGM")
    st.caption("Completa todos los campos. Los puntajes se calculan en tiempo real y se guardan al presionar **Guardar matching**.")

    # ── Identificación ──────────────────────────
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🏷️ Identificación del Matching")
        c1, c2, c3, c4 = st.columns([1.2, 2, 2, 2])
        with c1:
            reto_key = st.selectbox("Reto", list(RETOS.keys()), key="reto_sel")
        with c2:
            reto_nombre = st.text_input("Nombre del reto", value=RETOS[reto_key], disabled=True)
        with c3:
            tecnologia = st.text_input("Tecnología / equipo académico", placeholder="Ej: Bioplaguicida Bacillus PUCP")
        with c4:
            empresa = st.text_input("Empresa / institución receptora", placeholder="Ej: Exportadora Agrícola S.A.")
        equipo = st.text_input("Nombre del equipo / gestor evaluador", placeholder="Ej: GT-06 María Quispe + Dr. Juan Díaz")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Preguntas por subíndice ──────────────────
    all_scores = {}
    for key, config in PREGUNTAS.items():
        scores = render_subindice(key, config, expanded=True)
        all_scores.update(scores)

    # ── Cálculo en vivo ──────────────────────────
    st.markdown("---")
    st.subheader("📐 Resultado IGM en Tiempo Real")

    icg, ivc, irr, igm = calcular_igm(all_scores)
    render_igm_card(icg, ivc, irr, igm)

    # ── Guardar ──────────────────────────────────
    st.markdown("")
    col_btn, col_warn = st.columns([1, 3])
    with col_btn:
        guardar = st.button("💾 Guardar matching", type="primary", use_container_width=True)
    with col_warn:
        if not tecnologia or not empresa or not equipo:
            st.warning("⚠️ Completa Tecnología, Empresa y Equipo antes de guardar.")

    if guardar:
        if not tecnologia or not empresa or not equipo:
            st.error("Faltan campos obligatorios.")
        else:
            sem, accion, _, _, _ = semaforo_info(igm)
            row = {
                "id": f"{reto_key}_{int(time.time())}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "equipo": equipo, "reto": reto_key,
                "tecnologia": tecnologia, "empresa": empresa,
                **{k: v for k, v in all_scores.items()},
                "ICG": icg, "IVC": ivc, "IRR": irr, "IGM": igm,
                "semaforo": sem, "decision": accion,
            }
            with st.spinner(f"Guardando en pestaña '{pestaña_activa}' de Google Sheets…"):
                ok = guardar_matching(row, worksheet_name=pestaña_activa)
            if ok:
                st.success(f"✅ Matching guardado exitosamente. IGM = **{igm:.2f}** — {sem}")
                st.balloons()
            get_sheet.clear()  # Invalidar caché para que el dashboard recargue

# ══════════════════════════════════════════════════
# PÁGINA 2: DASHBOARD EN TIEMPO REAL
# ══════════════════════════════════════════════════
elif pagina == "📊 Dashboard en Tiempo Real":
    st.subheader(f"📊 Dashboard en Tiempo Real — I EGTBC 2026 (Pestaña: `{pestaña_activa}`)")

    # Auto-refresh cada 8 segundos
    try:
        from streamlit_autorefresh import st_autorefresh
        count = st_autorefresh(interval=8000, limit=None, key="dashboard_refresh")
        st.caption(f"🔄 Actualización automática cada 8 seg · ciclo #{count}")
    except ImportError:
        col_ref, _ = st.columns([1, 4])
        with col_ref:
            if st.button("🔄 Actualizar ahora", use_container_width=True):
                get_sheet.clear()
                st.rerun()

    # Cargar datos sanitizados
    with st.spinner("Cargando y procesando matchings…"):
        df = leer_matchings(worksheet_name=pestaña_activa)

    if df.empty:
        st.info(f"📭 Aún no hay matchings en la pestaña '{pestaña_activa}'. Verifica la barra lateral si tus respuestas de Google Forms están en otra pestaña (ej. 'Respuestas de formulario 1').")
        st.stop()

    # ── Filtros Interactivos ──────────────────────
    st.markdown("---")
    fc1, fc2, fc3 = st.columns([2, 2, 3])
    with fc1:
        retos_opts = ["Todos"] + list(RETOS.keys())
        f_reto = st.selectbox("🎯 Filtrar por Reto BioActiva:", retos_opts, index=0)
    with fc2:
        f_sem = st.selectbox("🚦 Filtrar por Semáforo:", ["Todos", "🟢 VERDE", "🟡 AMARILLO", "🔴 ROJO"], index=0)
    with fc3:
        st.markdown(f"<div style='margin-top:28px; font-size:0.85rem; color:#666;'>Mostrando registros en vivo de <b>{len(df)}</b> evaluaciones totales.</div>", unsafe_allow_html=True)

    df_show = df.copy()
    if f_reto != "Todos":
        df_show = df_show[df_show["reto"] == f_reto]
    if f_sem != "Todos":
        df_show = df_show[df_show["semaforo"].astype(str).str.contains(f_sem[:2], na=False)]

    if df_show.empty:
        st.warning("⚠️ No hay evaluaciones que coincidan con los filtros seleccionados.")
        st.stop()

    # ── Métricas resumen globales (KPI Cards) ─────
    n = len(df_show)
    verde_cnt    = len(df_show[df_show["IGM"] >= 7])
    amarillo_cnt = len(df_show[(df_show["IGM"] >= 5) & (df_show["IGM"] < 7)])
    rojo_cnt     = len(df_show[df_show["IGM"] < 5])

    pct_v = (verde_cnt / n * 100) if n > 0 else 0
    pct_a = (amarillo_cnt / n * 100) if n > 0 else 0
    pct_r = (rojo_cnt / n * 100) if n > 0 else 0

    mean_igm = df_show["IGM"].mean()
    mean_icg = df_show["ICG"].mean()
    mean_ivc = df_show["IVC"].mean()
    mean_irr = df_show["IRR"].mean()

    m1, m2, m3, m4, m5 = st.columns([1.1, 1.1, 1.1, 1.1, 1.5])
    with m1:
        st.markdown(f"""<div class="metric-box" style="background:#D6E8F7;border:2px solid #0F2A5C;">
        <div class="metric-label" style="color:#0F2A5C;">TOTAL FILTRADO</div>
        <div class="metric-value" style="color:#0F2A5C;">{n}</div>
        <div class="metric-sub">Pares evaluados</div></div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="metric-box" style="background:#D5F5E3;border:2px solid #1A7B4E;">
        <div class="metric-label" style="color:#1A7B4E;">🟢 VERDE ({pct_v:.0f}%)</div>
        <div class="metric-value" style="color:#1A7B4E;">{verde_cnt}</div>
        <div class="metric-sub">Equipo inmediato</div></div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="metric-box" style="background:#FFF3CD;border:2px solid #B45309;">
        <div class="metric-label" style="color:#B45309;">🟡 AMARILLO ({pct_a:.0f}%)</div>
        <div class="metric-value" style="color:#B45309;">{amarillo_cnt}</div>
        <div class="metric-sub">Con condiciones</div></div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""<div class="metric-box" style="background:#FFEBEE;border:2px solid #C62828;">
        <div class="metric-label" style="color:#C62828;">🔴 ROJO ({pct_r:.0f}%)</div>
        <div class="metric-value" style="color:#C62828;">{rojo_cnt}</div>
        <div class="metric-sub">No viable</div></div>""", unsafe_allow_html=True)
    with m5:
        st.markdown(f"""<div class="metric-box" style="background:#F4F6F9;border:3px solid #00B8A9;">
        <div class="metric-label" style="color:#0F2A5C;">📐 IGM PROMEDIO ECOSISTEMA</div>
        <div class="metric-value" style="color:#00B8A9;">{mean_igm:.2f}</div>
        <div class="metric-sub">ICG {mean_icg:.1f} · IVC {mean_ivc:.1f} · IRR {mean_irr:.1f}</div></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Pestañas de Navegación del Dashboard ──────
    tab_rank, tab_charts, tab_data = st.tabs(["🏆 Ranking & Tabla Semáforo", "📈 Gráficos del Ecosistema (Retos & Brechas)", "📥 Registro Completo & Exportar"])

    with tab_rank:
        st.markdown("#### 🏆 Ranking por IGM (De mayor a menor viabilidad)")
        df_sorted = df_show.sort_values("IGM", ascending=False).reset_index(drop=True)

        for _, row in df_sorted.iterrows():
            igm_val = float(row.get("IGM", 0))
            sem, accion, bg, fg, _ = semaforo_info(igm_val)
            reto_code = row.get("reto", "—")
            reto_desc = RETOS.get(reto_code, reto_code)
            tec = row.get("tecnologia", "—")
            emp = row.get("empresa", "—")
            ts  = row.get("timestamp", "")

            st.markdown(f"""
            <div class="matching-row" style="border-left-color:{fg}; background:{bg}20;">
              <div>
                <span style="font-weight:700; font-size:1rem; color:{fg};">{sem}</span>
                <span style="margin-left:12px; font-weight:700; font-size:0.9rem;">{reto_code}</span>
                <span style="color:#555; font-size:0.85rem;"> — {str(reto_desc)[:45]}</span><br>
                <span style="font-size:0.8rem; color:#444;">
                  🔬 <b>{str(tec)[:50]}</b>  ·  🏢 <b>{str(emp)[:45]}</b>
                </span><br>
                <span style="font-size:0.72rem; color:#888;">{ts}</span>
              </div>
              <div style="text-align:right; min-width:140px;">
                <div style="font-size:2.2rem; font-weight:800; color:{fg};">{igm_val:.2f}</div>
                <div style="font-size:0.72rem; font-weight:600; color:{fg};">ICG {float(row.get('ICG',0)):.1f}
                  · IVC {float(row.get('IVC',0)):.1f}
                  · IRR {float(row.get('IRR',0)):.1f}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    with tab_charts:
        st.markdown("#### 📈 Análisis Estratégico del Ecosistema CTI")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("##### 🎯 Demanda de Tecnologías por Reto BioActiva")
            df_reto_cnt = df_show["reto"].value_counts().reset_index()
            df_reto_cnt.columns = ["Reto", "Evaluaciones"]
            df_reto_cnt["Reto_Nombre"] = df_reto_cnt["Reto"].astype(str).map(lambda x: f"{x} · {RETOS.get(x, x)[:28]}")
            st.bar_chart(df_reto_cnt.set_index("Reto_Nombre")["Evaluaciones"], color="#00B8A9")

        with col_c2:
            st.markdown("##### 🔬 Comparativa Desglosada por Proyecto (IGM vs ICG, IVC, IRR)")
            df_chart = df_show[["reto","tecnologia","IGM","ICG","IVC","IRR"]].copy()
            df_chart["label"] = df_chart["reto"].astype(str) + " · " + df_chart["tecnologia"].astype(str).str[:22]
            df_chart = df_chart.sort_values("IGM", ascending=True)
            st.bar_chart(df_chart.set_index("label")[["IGM","ICG","IVC","IRR"]])

    with tab_data:
        st.markdown("#### 📋 Registro Detallado de Evaluaciones")
        st.caption("Puedes buscar, ordenar y explorar todas las variables y respuestas de los gestores.")
        st.dataframe(df_show, hide_index=True, use_container_width=True)

        csv_data = df_show.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar Reporte Completo en CSV (Listo para Excel / MOU)",
            data=csv_data,
            file_name=f"reporte_igm_egtbc2026_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

# ══════════════════════════════════════════════════
# PÁGINA 3: INSTRUCCIONES
# ══════════════════════════════════════════════════
elif pagina == "ℹ️ Instrucciones IGM":
    st.subheader("ℹ️ Instrucciones — Modelo IGM")

    st.markdown("""
    ### ¿Qué es el IGM?

    El **Índice de Matchmaking Global (IGM)** mide la probabilidad de éxito de un acuerdo
    de transferencia tecnológica entre un equipo académico y una empresa receptora.
    Se calcula con la fórmula:
    """)
    st.latex(r"IGM = (ICG \times 0.40) + (IVC \times 0.35) + (IRR \times 0.25)")

    col1, col2, col3 = st.columns(3)
    bloques = [
        (col1, "ICG · Compatibilidad Global", "40 %", "#D6EAF8", "#1A5276",
         "Mide si la tecnología académica REALMENTE resuelve el problema técnico "
         "de la empresa: alineamiento TRL, sector, brecha de desempeño y "
         "dependencia de tecnologías externas."),
        (col2, "IVC · Viabilidad Comercial", "35 %", "#D5F5E3", "#1A7B4E",
         "Mide si la empresa tiene capacidad de absorber e implementar la tecnología: "
         "presupuesto, madurez organizacional, equipo técnico, timeline y apoyo de directiva."),
        (col3, "IRR · Retorno y Riesgo", "25 %", "#E8DAEF", "#7D3C98",
         "Mide si ambas partes ganan algo sostenible y los riesgos son asumibles: "
         "ROI esperado, retorno sostenido, claridad en IP, riesgo técnico y "
         "sostenibilidad de la alianza."),
    ]
    for col, titulo, peso, bg, fg, desc in bloques:
        with col:
            st.markdown(f"""
            <div style="background:{bg}; border-radius:10px; padding:18px;
                        border-top:4px solid {fg}; height:200px;">
              <div style="font-weight:700; color:{fg}; font-size:0.9rem;">{titulo}</div>
              <div style="font-size:1.6rem; font-weight:800; color:{fg}; margin:6px 0;">{peso}</div>
              <div style="font-size:0.8rem; color:#444;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🚦 Semáforo de resultados")
    for sem_txt, rng, accion, bg, fg in [
        ("🟢 VERDE", "IGM ≥ 7.0",
         "Alta compatibilidad técnica, comercial y de riesgo. Proceder con carta de intención HOY.",
         "#D5F5E3", "#1A7B4E"),
        ("🟡 AMARILLO", "IGM 5.0 – 6.9",
         "Hay potencial pero existen brechas que deben resolverse antes de firmar. Segunda evaluación en 30 días.",
         "#FFF3CD", "#B45309"),
        ("🔴 ROJO", "IGM < 5.0",
         "Brecha insalvable en al menos un subíndice. No procede en este ciclo. Documentar para próxima convocatoria.",
         "#FFEBEE", "#C62828"),
    ]:
        st.markdown(f"""
        <div style="background:{bg}; border-radius:8px; padding:14px 18px; margin-bottom:8px;
                    border-left:5px solid {fg}; display:flex; gap:20px; align-items:center;">
          <div style="font-size:1.3rem; font-weight:800; color:{fg}; min-width:130px;">{sem_txt}</div>
          <div>
            <div style="font-weight:700; color:{fg};">{rng}</div>
            <div style="font-size:0.85rem; color:#444;">{accion}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📐 Escala Likert (1–5 → convertida a 0–10)")
    escala_data = {
        "Puntaje": [1, 2, 3, 4, 5],
        "Significado general": [
            "Muy bajo / No aplica / Brecha crítica",
            "Bajo / Insuficiente / Alto riesgo",
            "Moderado / Aplicable con esfuerzo",
            "Bueno / Casi cumple / Riesgo bajo",
            "Excelente / Cumple perfectamente / Muy bajo riesgo",
        ],
        "Valor convertido (×2)": [2, 4, 6, 8, 10],
    }
    st.dataframe(pd.DataFrame(escala_data), hide_index=True, use_container_width=True)
