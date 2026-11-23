const tones: Record<string, string> = {
  open: "border-emerald-300 bg-emerald-100 text-emerald-900",
  upcoming: "border-amber-300 bg-amber-100 text-amber-900",
  closed: "border-slate-300 bg-slate-100 text-slate-600",
  draft: "border-slate-300 bg-slate-100 text-slate-600",
  published: "border-indigo-300 bg-indigo-100 text-indigo-900",
  postponed: "border-amber-300 bg-amber-100 text-amber-900",
  cancelled: "border-rose-300 bg-rose-100 text-rose-900",
  archived: "border-slate-300 bg-slate-100 text-slate-600",
  completed: "border-slate-300 bg-slate-100 text-slate-700",
  answered: "border-indigo-300 bg-indigo-100 text-indigo-900",
  featured: "border-ink bg-sun text-ink",
  public: "border-indigo-300 bg-indigo-100 text-indigo-900",
  private: "border-slate-300 bg-slate-100 text-slate-600",
};

export function Badge({ tone, children }: { tone: string; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-bold capitalize ${tones[tone] || tones.draft}`}>
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full bg-current ${tone === "open" ? "live-dot" : ""}`} />
      {children}
    </span>
  );
}
