import { notFound } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import type { HackathonPublic } from "@/lib/types";
import { HackathonDetail } from "@/components/hackathon-detail";

export const dynamic = "force-dynamic";

export default async function HackathonPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  try {
    const hackathon = await api<HackathonPublic>(`/api/v1/hackathons/${slug}`);
    let signedIn = false;
    try {
      await api("/api/v1/auth/me");
      signedIn = true;
    } catch (authError) {
      if (!(authError instanceof ApiError) || authError.status !== 401) throw authError;
    }
    return <HackathonDetail hackathon={hackathon} signedIn={signedIn} />;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}
