"use client";

import { useSyncExternalStore } from "react";
import type { User } from "@/lib/types";

export type Stance = "registered" | "missed";

export type ViewerSnapshot = {
  user: User | null;
  stances: Record<string, Stance>;
  interests: Record<string, boolean>;
};

const empty: ViewerSnapshot = { user: null, stances: {}, interests: {} };
let snapshot: ViewerSnapshot | null = null;
let started = false;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

function start() {
  if (started || typeof window === "undefined") return;
  started = true;
  fetch("/api/v1/me/summary", { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) return empty;
      const body = await response.json();
      const stances: Record<string, Stance> = {};
      for (const row of body.stances ?? []) stances[row.hackathon_slug] = row.stance;
      const interests: Record<string, boolean> = {};
      for (const slug of body.interests ?? []) interests[slug] = true;
      return { user: body.user as User, stances, interests };
    })
    .then((value) => {
      snapshot = value;
      emit();
    })
    .catch(() => {
      snapshot = empty;
      emit();
    });
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  start();
  return () => listeners.delete(listener);
}

export function useViewer(): ViewerSnapshot | null {
  return useSyncExternalStore(subscribe, () => snapshot, () => null);
}
