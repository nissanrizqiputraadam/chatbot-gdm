const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function sendMessage(message) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error("Server error");
  return res.json();
}