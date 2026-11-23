import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";

export function slicePage<T>(items: T[], page: number, size: number) {
  const pages = Math.max(1, Math.ceil(items.length / size));
  const current = Math.min(Math.max(page, 1), pages);
  const start = (current - 1) * size;
  return { items: items.slice(start, start + size), page: current, pages, total: items.length };
}

export function Pager({ page, pages, href }: { page: number; pages: number; href: (page: number) => string }) {
  if (pages <= 1) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 pt-2 text-sm font-semibold">
      {page > 1 ? (
        <Link className="btn btn-sm" href={href(page - 1)}>
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          Previous
        </Link>
      ) : null}
      <span className="font-mono text-xs text-muted">Page {page} of {pages}</span>
      {page < pages ? (
        <Link className="btn btn-sm" href={href(page + 1)}>
          Next
          <ArrowRight aria-hidden="true" className="icon-slide h-4 w-4" />
        </Link>
      ) : null}
    </div>
  );
}
