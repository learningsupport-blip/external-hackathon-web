import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

export function EmptyState({ title, body, href, action }: { title: string; body: string; href?: string; action?: string }) {
  return (
    <div className="group rounded-2xl border-[1.5px] border-dashed border-ink/40 bg-card/70 px-4 py-10 text-center transition-colors hover:border-ink hover:bg-card">
      <span aria-hidden="true" className="mx-auto grid h-11 w-11 place-items-center rounded-xl border-[1.5px] border-ink bg-tint transition-transform duration-300 group-hover:-rotate-12 group-hover:scale-110 group-hover:bg-lime">
        <Sparkles className="h-5 w-5" />
      </span>
      <p className="mt-3 font-display text-lg font-bold">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-sm text-muted">{body}</p>
      {href && action ? (
        <Link className="btn btn-primary btn-sm mt-4" href={href}>
          {action}
          <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
        </Link>
      ) : null}
    </div>
  );
}
