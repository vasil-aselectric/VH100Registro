export const UI_CONFIG = {
  // Ruta del catálogo JSON en tu backend/servidor
  catalogUrl: "/JSON/base_and_variations.json",

  // Endpoint FastAPI para aplicar o resolver selección
 // submitUrl: "/api/v1/inverter/select",
  submitUrl: "/api/v1/inverter/apply",

  requestMethod: "POST"
};

export const LABELS = {
  use_type: {
    hibrido_pip: "Basic / Híbrido PID",
    clasico_pip: "Solo PID"
  },
  phase_type: {
    monofasico: "Monofásico",
    trifasico: "Trifásico"
  }
};
