"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Eye, Pencil, Trash2 } from "lucide-react";
import { readError } from "@/lib/http";

export function HackathonRowActions({ id, lifecycle }: { id: string; lifecycle: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const canDelete = lifecycle === "draft" || lifecycle === "published";

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center justify-end gap-1">
        <Link aria-label="Edit" className="grid h-8 w-8 place-items-center rounded-lg text-accent hover:bg-background" href={`/admin/hackathons/${id}/edit`} title="Edit">
          <Pencil aria-hidden="true" className="h-4 w-4" />
        </Link>
        <Link aria-label="Preview" className="grid h-8 w-8 place-items-center rounded-lg text-accent hover:bg-background" href={`/admin/hackathons/${id}/preview`} title="Preview">
          <Eye aria-hidden="true" className="h-4 w-4" />
        </Link>
        {canDelete ? (
          <button
            aria-label="Delete"
            className="grid h-8 w-8 place-items-center rounded-lg text-danger hover:bg-rose-50"
            onClick={async () => {
              const published = lifecycle === "published";
              if (!window.confirm(published ? "Delete this published hackathon? It will leave the public site." : "Delete this draft?")) return;
              setError(null);
              const response = await fetch(`/api/v1/admin/hackathons/${id}`, { method: "DELETE" });
              if (!response.ok) {
                setError(readError(await response.text()));
                return;
              }
              router.refresh();
            }}
            title="Delete"
            type="button"
          >
            <Trash2 aria-hidden="true" className="h-4 w-4" />
          </button>
        ) : null}
      </div>
      {error ? <p className="text-xs text-danger">{error}</p> : null}
    </div>
  );
}
