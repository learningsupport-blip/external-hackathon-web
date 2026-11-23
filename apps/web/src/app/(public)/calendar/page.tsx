import { api } from "@/lib/api";
import type { Category, HackathonCard, PageResult } from "@/lib/types";
import { CalendarBoard } from "@/components/calendar-board";

export const dynamic = "force-dynamic";

export default async function CalendarPage() {
  const [categories, hackathons] = await Promise.all([
    api<Category[]>("/api/v1/categories"),
    api<PageResult<HackathonCard>>("/api/v1/hackathons?page_size=50"),
  ]);
  return (
    <CalendarBoard categories={categories} hackathons={hackathons.items} />
  );
}
