import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import type { Category, HackathonCard, PageResult } from "@/lib/types";
import { CalendarSkeleton } from "@/components/ui/skeleton";

const CalendarBoard = dynamic(
  () => import("@/components/calendar-board").then((mod) => mod.CalendarBoard),
  { ssr: false, loading: () => <CalendarSkeleton /> },
);

export default async function CalendarPage() {
  const [categories, hackathons] = await Promise.all([
    api<Category[]>("/api/v1/categories"),
    api<PageResult<HackathonCard>>("/api/v1/hackathons?page_size=50&browse=false"),
  ]);
  return <CalendarBoard categories={categories} hackathons={hackathons.items} />;
}
