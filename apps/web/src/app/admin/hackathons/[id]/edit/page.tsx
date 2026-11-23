import { api } from "@/lib/api";
import type { Category, HackathonAdmin, User } from "@/lib/types";
import { HackathonEditor } from "@/components/hackathon-editor";

export const dynamic = "force-dynamic";

export default async function EditHackathonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [hackathon, categories, user] = await Promise.all([
    api<HackathonAdmin>(`/api/v1/admin/hackathons/${id}`),
    api<Category[]>("/api/v1/categories"),
    api<User>("/api/v1/auth/me"),
  ]);
  return <HackathonEditor categories={categories} initial={hackathon} role={user.role} />;
}
