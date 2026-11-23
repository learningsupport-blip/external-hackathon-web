import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { CardGridSkeleton, Skeleton } from "@/components/ui/skeleton";
import { BookmarksSection, CountsSection, FollowingSection, QuestionsSection, TimelineSection, UpdatesSection } from "./sections";

export const dynamic = "force-dynamic";

type Search = Record<string, string | string[] | undefined>;

function CountsFallback() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      {Array.from({ length: 5 }, (_, index) => <Skeleton key={index} className="h-20" />)}
    </div>
  );
}

export default async function DashboardPage({ searchParams }: { searchParams: Promise<Search> }) {
  const params = await searchParams;
  return (
    <div className="space-y-10">
      <PageHeader title="Your dashboard" body="The hackathons you follow, the deadlines still ahead, and the questions you have asked." />
      <Suspense fallback={<CountsFallback />}>
        <CountsSection />
      </Suspense>
      <Suspense fallback={<Skeleton className="h-40 w-full" />}>
        <TimelineSection params={params} />
      </Suspense>
      <Suspense fallback={<CardGridSkeleton />}>
        <BookmarksSection params={params} />
      </Suspense>
      <Suspense fallback={<CardGridSkeleton />}>
        <FollowingSection params={params} />
      </Suspense>
      <div className="grid gap-8 lg:grid-cols-2">
        <Suspense fallback={<Skeleton className="h-40 w-full" />}>
          <QuestionsSection params={params} />
        </Suspense>
        <Suspense fallback={<Skeleton className="h-40 w-full" />}>
          <UpdatesSection params={params} />
        </Suspense>
      </div>
    </div>
  );
}
