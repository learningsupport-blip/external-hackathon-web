const tones: Record<string, string> = {
  "ai-ml": "bg-violet-100 text-violet-800",
  "web-development": "bg-blue-100 text-blue-800",
  "open-source": "bg-emerald-100 text-emerald-800",
  "cloud-computing": "bg-sky-100 text-sky-800",
  cybersecurity: "bg-rose-100 text-rose-800",
  sustainability: "bg-green-100 text-green-800",
  "social-impact": "bg-amber-100 text-amber-800",
  robotics: "bg-orange-100 text-orange-800",
  "product-development": "bg-pink-100 text-pink-800",
  other: "bg-slate-100 text-slate-700",
  python: "bg-violet-100 text-violet-800",
  git: "bg-emerald-100 text-emerald-800",
  health: "bg-rose-100 text-rose-800",
  climate: "bg-green-100 text-green-800",
  prototype: "bg-amber-100 text-amber-800",
};

const fallback = ["bg-indigo-50 text-indigo-800", "bg-teal-50 text-teal-800", "bg-fuchsia-50 text-fuchsia-800", "bg-cyan-50 text-cyan-800"];

export function topicClass(tone?: string) {
  const key = (tone || "").toLowerCase();
  if (tones[key]) return tones[key];
  const index = [...key].reduce((sum, char) => sum + char.charCodeAt(0), 0) % fallback.length;
  return fallback[index];
}

export function TopicTag({ label, tone }: { label: string; tone?: string }) {
  return <span className={`chip inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${topicClass(tone || label)}`}>{label}</span>;
}
