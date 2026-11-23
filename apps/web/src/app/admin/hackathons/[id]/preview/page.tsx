import { api } from "@/lib/api";
import type { HackathonAdmin } from "@/lib/types";
import { HackathonDetail } from "@/components/hackathon-detail";

export const dynamic = "force-dynamic";

export default async function PreviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const hackathon = await api<HackathonAdmin>(`/api/v1/admin/hackathons/${id}`);
  return (
    <div className="space-y-4">
      <p className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">Preview of a {hackathon.lifecycle} hackathon. Internal notes are not shown.</p>
      <HackathonDetail hackathon={hackathon} />
    </div>
  );
}
