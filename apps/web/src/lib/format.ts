type Parts = { year: number; month: number; day: number; hour: number; minute: number };

export function zonedParts(date: Date, timeZone: string): Parts {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const bag: Record<string, string> = {};
  for (const part of formatter.formatToParts(date)) bag[part.type] = part.value;
  return {
    year: Number(bag.year),
    month: Number(bag.month),
    day: Number(bag.day),
    hour: Number(bag.hour),
    minute: Number(bag.minute),
  };
}

function pad(value: number) {
  return String(value).padStart(2, "0");
}

export function isoToZonedInput(iso: string | null, timeZone: string) {
  if (!iso) return "";
  const parts = zonedParts(new Date(iso), timeZone);
  return `${parts.year}-${pad(parts.month)}-${pad(parts.day)}T${pad(parts.hour)}:${pad(parts.minute)}`;
}

export function zonedInputToIso(value: string, timeZone: string) {
  if (!value) return null;
  const [date, time] = value.split("T");
  const [year, month, day] = date.split("-").map(Number);
  const [hour, minute] = time.split(":").map(Number);
  let utc = Date.UTC(year, month - 1, day, hour, minute);
  for (let pass = 0; pass < 3; pass += 1) {
    const got = zonedParts(new Date(utc), timeZone);
    const asUtc = Date.UTC(got.year, got.month - 1, got.day, got.hour, got.minute);
    const target = Date.UTC(year, month - 1, day, hour, minute);
    if (asUtc === target) break;
    utc -= asUtc - target;
  }
  return new Date(utc).toISOString();
}

export function formatWhen(iso: string | null, timeZone: string) {
  if (!iso) return "Date not set";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

export const REGISTRATION_LABEL: Record<string, string> = {
  open: "Registration open",
  upcoming: "Upcoming",
  closed: "Registration closed",
  completed: "Completed",
  draft: "Draft",
  postponed: "Postponed",
  cancelled: "Cancelled",
  archived: "Archived",
};

export const MILESTONE_LABEL: Record<string, string> = {
  registration_opens: "Registration opens",
  registration_closes: "Registration closes",
  team_formation: "Team formation",
  idea_submission: "Idea submission",
  prototype_submission: "Prototype submission",
  round_one: "Round one",
  round_two: "Round two",
  final_submission: "Final submission",
  grand_finale: "Grand finale",
  results: "Results",
  workshop: "Workshop",
  meeting: "Meeting",
  other: "Other",
};

export type TimeLeft = { label: string; tone: "hot" | "warm" | "calm" | "past" };

export function timeLeft(iso: string | null, nowMs: number = Date.now()): TimeLeft | null {
  if (!iso) return null;
  const diff = new Date(iso).getTime() - nowMs;
  if (Number.isNaN(diff)) return null;
  if (diff < 0) return { label: "Passed", tone: "past" };
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return { label: "Under 1h left", tone: "hot" };
  if (hours < 24) return { label: `${hours}h left`, tone: "hot" };
  const days = Math.floor(hours / 24);
  if (days < 7) return { label: `${days} ${days === 1 ? "day" : "days"} left`, tone: "warm" };
  return { label: `${days} days left`, tone: "calm" };
}
