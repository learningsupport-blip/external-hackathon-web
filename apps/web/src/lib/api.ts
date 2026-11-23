import { cache } from "react";
import { cookies } from "next/headers";
import { ApiError, readError } from "@/lib/http";

function isPublicCatalog(path: string) {
  const bare = path.split("?")[0];
  return bare === "/api/v1/home" || bare === "/api/v1/categories" || bare === "/api/v1/calendar" || bare === "/api/v1/hackathons" || bare === "/api/v1/hackathons/due";
}

async function requestApi<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) headers.set("Content-Type", "application/json");
  const base = process.env.API_URL || "http://localhost:8000";
  const jar = await cookies();
  const cookie = jar.toString();
  if (cookie) headers.set("cookie", cookie);
  const method = (init?.method || "GET").toUpperCase();
  const reusable = method === "GET" && isPublicCatalog(path);
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers,
    ...(reusable ? { next: { revalidate: 60 } } : { cache: "no-store" as const }),
  });
  if (!response.ok) throw new ApiError(response.status, readError(await response.text()));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = cache(requestApi);

export { ApiError };
