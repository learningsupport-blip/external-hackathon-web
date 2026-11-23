import { ApiError, api } from "@/lib/api";
import type { User } from "@/lib/types";

export type Stance = "registered" | "missed";

type Summary = {
  user: User;
  stances: { hackathon_slug: string; stance: Stance }[];
  interests: string[];
};

export async function viewerContext(activeOnly = false): Promise<{ signedIn: boolean; stances: Record<string, Stance>; interests: Record<string, boolean> }> {
  const empty = { signedIn: false, stances: {}, interests: {} };
  try {
    const summary = await api<Summary>(`/api/v1/me/summary${activeOnly ? "?active=true" : ""}`);
    return {
      signedIn: true,
      stances: Object.fromEntries(summary.stances.map((row) => [row.hackathon_slug, row.stance])),
      interests: Object.fromEntries(summary.interests.map((slug) => [slug, true])),
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return empty;
    return empty;
  }
}
