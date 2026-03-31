import { fetchCatalog, getUseTypes, getPhaseTypes, getPowerCodesByPhase, makePayload, getLabel } from "./catalog.js";
import { submitSelection } from "./api.js";

const elements = {
  form: document.getElementById("selectorForm"),
  useType: document.getElementById("useType"),
  phaseType: document.getElementById("phaseType"),
  powerCode: document.getElementById("powerCode"),
  submitBtn: document.getElementById("submitBtn"),
  resetBtn: document.getElementById("resetBtn"),
  copyPayloadBtn: document.getElementById("copyPayloadBtn"),
  payloadPreview: document.getElementById("payloadPreview"),
  responsePreview: document.getElementById("responsePreview"),
  catalogStatus: document.getElementById("catalogStatus"),
  requestStatus: document.getElementById("requestStatus"),
  summaryUse: document.getElementById("summaryUse"),
  summaryPhase: document.getElementById("summaryPhase"),
  summaryPower: document.getElementById("summaryPower"),
  summaryVariant: document.getElementById("summaryVariant")
};

let catalog = null;

function resetSelect(select, placeholder) {
  select.innerHTML = "";
  const option = document.createElement("option");
  option.value = "";
  option.textContent = placeholder;
  select.appendChild(option);
  select.value = "";
}

function fillSelect(select, items, labelType = null) {
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = labelType ? getLabel(labelType, item) : item;
    select.appendChild(option);
  });
}

function updatePayloadPreview() {
  const useType = elements.useType.value;
  const phaseType = elements.phaseType.value;
  const powerCode = elements.powerCode.value;

  if (!useType || !phaseType || !powerCode) {
    elements.payloadPreview.textContent = "{}";
    elements.summaryUse.textContent = "—";
    elements.summaryPhase.textContent = "—";
    elements.summaryPower.textContent = "—";
    elements.summaryVariant.textContent = "—";
    elements.submitBtn.disabled = true;
    return;
  }

  const payload = makePayload({ useType, phaseType, powerCode });

  elements.payloadPreview.textContent = JSON.stringify(payload, null, 2);
  elements.summaryUse.textContent = getLabel("use_type", useType);
  elements.summaryPhase.textContent = getLabel("phase_type", phaseType);
  elements.summaryPower.textContent = powerCode;
  elements.summaryVariant.textContent = payload.variant_code;
  elements.submitBtn.disabled = false;
}

function initializeUseType() {
  resetSelect(elements.useType, "Selecciona una opción");
  fillSelect(elements.useType, getUseTypes(catalog), "use_type");
  elements.useType.disabled = false;
}

function handleUseTypeChange() {
  resetSelect(elements.phaseType, "Selecciona una opción");
  resetSelect(elements.powerCode, "Selecciona una opción");
  elements.phaseType.disabled = true;
  elements.powerCode.disabled = true;
  elements.submitBtn.disabled = true;
  updatePayloadPreview();

  if (!elements.useType.value) return;

  fillSelect(elements.phaseType, getPhaseTypes(catalog), "phase_type");
  elements.phaseType.disabled = false;
}

function handlePhaseTypeChange() {
  resetSelect(elements.powerCode, "Selecciona una opción");
  elements.powerCode.disabled = true;
  elements.submitBtn.disabled = true;
  updatePayloadPreview();

  if (!elements.phaseType.value) return;

  fillSelect(elements.powerCode, getPowerCodesByPhase(elements.phaseType.value));
  elements.powerCode.disabled = false;
}

async function initialize() {
  try {
    catalog = await fetchCatalog();
    initializeUseType();
    elements.catalogStatus.textContent = "Catálogo listo";
    elements.catalogStatus.className = "status-pill status-pill--ready";
  } catch (error) {
    elements.catalogStatus.textContent = "Error catálogo";
    elements.catalogStatus.className = "status-pill status-pill--error";
    elements.responsePreview.textContent = String(error.message ?? error);
  }
}

elements.useType.addEventListener("change", handleUseTypeChange);
elements.phaseType.addEventListener("change", handlePhaseTypeChange);
elements.powerCode.addEventListener("change", updatePayloadPreview);

elements.resetBtn.addEventListener("click", () => {
  resetSelect(elements.useType, "Selecciona una opción");
  resetSelect(elements.phaseType, "Selecciona una opción");
  resetSelect(elements.powerCode, "Selecciona una opción");

  elements.phaseType.disabled = true;
  elements.powerCode.disabled = true;
  elements.submitBtn.disabled = true;
  elements.responsePreview.textContent = "—";
  elements.requestStatus.textContent = "Sin enviar";

  if (catalog) {
    fillSelect(elements.useType, getUseTypes(catalog), "use_type");
    elements.useType.disabled = false;
  }

  updatePayloadPreview();
});

elements.copyPayloadBtn.addEventListener("click", async () => {
  const text = elements.payloadPreview.textContent;
  if (!text || text === "{}") return;

  try {
    await navigator.clipboard.writeText(text);
    elements.requestStatus.textContent = "Payload copiado";
  } catch {
    elements.requestStatus.textContent = "No se pudo copiar";
  }
});

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const useType = elements.useType.value;
  const phaseType = elements.phaseType.value;
  const powerCode = elements.powerCode.value;

  if (!useType || !phaseType || !powerCode) {
    elements.requestStatus.textContent = "Formulario incompleto";
    return;
  }

  const payload = makePayload({ useType, phaseType, powerCode });

  elements.requestStatus.textContent = "Enviando…";
  elements.responsePreview.textContent = "Esperando respuesta...";

  try {
    const result = await submitSelection(payload);
    elements.responsePreview.textContent = JSON.stringify(result, null, 2);
    elements.requestStatus.textContent = "OK";
  } catch (error) {
    elements.responsePreview.textContent = String(error.message ?? error);
    elements.requestStatus.textContent = "Error";
  }
});

initialize();
