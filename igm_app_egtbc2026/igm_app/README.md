# 🎯 Calculadora IGM — I EGTBC 2026

**Calculadora de Matchmaking en Tiempo Real**  
Grupo Biogenia × CIDE-PUCP × BioActiva

## ¿Qué hace?

Permite a equipos de gestores tecnológicos evaluar matchings entre tecnologías académicas y retos empresariales usando el modelo **IGM** (Índice de Matchmaking Global):

```
IGM = (ICG × 0.40) + (IVC × 0.35) + (IRR × 0.25)
```

- **ICG** — Índice de Compatibilidad Global (40 %)
- **IVC** — Índice de Viabilidad Comercial (35 %)
- **IRR** — Índice de Retorno y Riesgo (25 %)

## Stack

- Frontend/app: **Streamlit**
- Base de datos en tiempo real: **Google Sheets** (vía gspread)
- Despliegue: **Streamlit Cloud** (gratis)

## Estructura

```
igm_app/
├── app.py                     # App principal
├── requirements.txt           # Dependencias Python
├── .streamlit/
│   ├── config.toml            # Configuración de tema
│   ├── secrets.toml           # Credenciales (NO subir a Git)
│   └── secrets.toml.template  # Plantilla de credenciales
├── .gitignore
└── README.md
```

## Despliegue

Ver guía completa de despliegue en la documentación del evento.  
`conecta@biogeniainnova.com`
