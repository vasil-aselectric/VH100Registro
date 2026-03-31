import { UI_CONFIG, LABELS } from "./config.js";

export async function fetchCatalog() {
  const response = await fetch(UI_CONFIG.catalogUrl, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`No se pudo cargar el catálogo (${response.status})`);
  }
  return response.json();
}

export function getUseTypes(catalog) {
  return Object.keys(catalog.variations?.use_type ?? {});
}

export function getPhaseTypes(catalog) {
  return Object.keys(catalog.variations?.phase_type ?? {});
}

export function getPowerCodes(catalog) {
  return Object.keys(catalog.variations?.power_kw ?? {});
}

export function buildVariantCode({ useType, phaseType, powerCode }) {
  const usePrefix = useType === "hibrido_pip" ? "HIBRIDO" : "CLASICO";
  const phasePrefix = phaseType === "monofasico" ? "MONO" : "TRI";
  return `${usePrefix}_${phasePrefix}_${powerCode}`;
}

export function makePayload({ useType, phaseType, powerCode }) {
  return {
    use_type: useType,
    phase_type: phaseType,
    power_code: powerCode,
    variant_code: buildVariantCode({ useType, phaseType, powerCode })
  };
}

export function getLabel(type, value) {
  return LABELS[type]?.[value] ?? value ?? "—";
}
