export function PageHeader({ eyebrow, title, body, children }: { eyebrow?: string; title: string; body?: string; children?: React.ReactNode }) {
  return (
    <div className="rise flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow ? <p className="font-mono text-xs font-bold uppercase tracking-widest text-accent">{eyebrow}</p> : null}
        <h1 className="text-3xl font-extrabold tracking-tight md:text-4xl">{title}</h1>
        {body ? <p className="mt-1.5 max-w-2xl text-sm text-muted">{body}</p> : null}
      </div>
      {children}
    </div>
  );
}
