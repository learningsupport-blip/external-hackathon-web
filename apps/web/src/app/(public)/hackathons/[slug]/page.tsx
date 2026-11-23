import { notFound } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import type { HackathonPublic } from "@/lib/types";
import { HackathonDetail } from "@/components/hackathon-detail";

export const dynamic = "force-dynamic";

export default async function HackathonPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  try {
    const hackathon = await api<HackathonPublic>(`/api/v1/hackathons/${slug}`);
    return <HackathonDetail hackathon={hackathon} />;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}
