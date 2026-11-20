const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function sendMessage(message) {
  let res;
  try {
    res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
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