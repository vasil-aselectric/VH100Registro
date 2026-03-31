export const UI_CONFIG = {
  // Ruta del catálogo JSON en tu backend/servidor
  catalogUrl: "/JSON/base_and_variations.json",

  // Endpoint FastAPI para aplicar o resolver selección
  submitUrl: "/api/v1/inverter/select",

  requestMethod: "POST"
};

export const LABELS = {
  use_type: {
    hibrido_pip: "Híbrido PIP",
    clasico_pip: "Clásico PIP"
  },
  phase_type: {
    monofasico: "Monofásico",
    trifasico: "Trifásico"
  }
};
