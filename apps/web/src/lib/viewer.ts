import { ApiError, api } from "@/lib/api";
import type { User } from "@/lib/types";

export type Stance = "registered" | "missed";

export async function viewerContext(activeOnly = false): Promise<{ signedIn: boolean; stances: Record<string, Stance>; interests: Record<string, boolean> }> {
  const empty = { signedIn: false, stances: {}, interests: {} };
  try {
    await api<User>("/api/v1/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return empty;
    return empty;
  }
  try {
    const [rows, interests] = await Promise.all([
      api<{ hackathon_slug: string; stance: Stance }[]>(activeOnly ? "/api/v1/me/stances?active=true" : "/api/v1/me/stances"),
      api<string[]>("/api/v1/me/interests"),
    ]);
    return {
      signedIn: true,
      stances: Object.fromEntries(rows.map((row) => [row.hackathon_slug, row.stance])),
      interests: Object.fromEntries(interests.map((slug) => [slug, true])),
    };
  } catch {
    return { signedIn: true, stances: {}, interests: {} };
  }
}
