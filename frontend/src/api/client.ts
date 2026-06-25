// Minimal API client. In dev, Vite proxies /api to the Django backend.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}
