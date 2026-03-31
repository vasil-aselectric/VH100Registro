# Selector web HV100 PIP

## Estructura
- `index.html`
- `assets/css/styles.css`
- `assets/js/config.js`
- `assets/js/catalog.js`
- `assets/js/api.js`
- `assets/js/app.js`

## Qué hace
- Carga el catálogo JSON desde `UI_CONFIG.catalogUrl`
- Muestra 3 dropdowns:
  - tipo de uso
  - tipo de alimentación
  - referencia / potencia
- Genera `variant_code`
- Envía el payload al backend FastAPI

## Payload esperado
```json
{
  "use_type": "hibrido_pip",
  "phase_type": "monofasico",
  "power_code": "202MH",
  "variant_code": "HIBRIDO_MONO_202MH"
}
```

## Ajustes que debes revisar
En `assets/js/config.js`:
- `catalogUrl`
- `submitUrl`

## Nota
El frontend está hecho con HTML + CSS + JS clásico, sin frameworks, para que sea ligero y fácil de integrar con el navegador del HMI.
