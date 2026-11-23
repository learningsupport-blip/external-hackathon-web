import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-16 text-center">
      <p aria-hidden="true" className="floaty mx-auto inline-block -rotate-3 rounded-2xl border-[1.5px] border-ink bg-lime px-5 py-2 font-display text-6xl font-extrabold shadow-[5px_5px_0_var(--ink)]">404</p>
      <h1 className="mt-8 text-3xl font-extrabold tracking-tight md:text-4xl">That page is not available</h1>
      <p className="mt-2 text-muted">The hackathon may be a draft, or the link is wrong.</p>
      <Link className="btn btn-primary mt-6" href="/hackathons">
        Back to explore
        <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
      </Link>
    </div>
  );
}
