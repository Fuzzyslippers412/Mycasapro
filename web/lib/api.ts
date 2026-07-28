export const appURL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:8081";

export async function apiFetch(path: string, init: RequestInit = {}) {
  return fetch(`${appURL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...init.headers,
    },
  });
}

export async function apiError(response: Response, fallback: string) {
  const payload = (await response.json().catch(() => null)) as { message?: string } | null;
  return payload?.message || fallback;
}
