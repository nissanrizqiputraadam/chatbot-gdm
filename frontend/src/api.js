const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

async function postJson(path, body) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(`Tidak dapat menghubungi backend di ${API_URL}. Pastikan backend berjalan.`);
  }

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Backend merespons dengan HTTP ${res.status}${detail ? `: ${detail}` : ""}`);
  }

  return res.json();
}

export function sendMessage(message) {
  return postJson("/chat", { message });
}

export function getSummary(items) {
  return postJson("/summary", { items });
}