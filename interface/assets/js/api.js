import { UI_CONFIG } from "./config.js";

export async function submitSelection(payload) {
  const response = await fetch(UI_CONFIG.submitUrl, {
    method: UI_CONFIG.requestMethod,
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  const text = await response.text();
  let data;

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw_response: text };
  }

  if (!response.ok) {
    throw new Error(JSON.stringify(data, null, 2));
  }

  return data;
}
