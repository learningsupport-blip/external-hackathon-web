export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`shimmer rounded-xl ${className}`} />;
}

export function CardSkeleton() {
  return (
    <div className="rounded-2xl border-[1.5px] border-line bg-card p-5">
      <Skeleton className="h-11 w-11" />
      <Skeleton className="mt-4 h-5 w-2/3" />
      <Skeleton className="mt-2 h-4 w-1/3" />
      <Skeleton className="mt-4 h-12 w-full" />
    </div>
  );
}

export function CardGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-5 md:grid-cols-2">
      {Array.from({ length: count }, (_, index) => <CardSkeleton key={index} />)}
    </div>
  );
}

export function HomeSkeleton() {
  return (
    <div className="space-y-8">
      <Skeleton className="h-72 w-full rounded-3xl" />
      <CardGridSkeleton count={2} />
      <CardGridSkeleton count={2} />
    </div>
  );
}

export function ExploreSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
      <Skeleton className="h-96 w-full" />
      <CardGridSkeleton />
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <div className="space-y-4">
        <Skeleton className="h-56 w-full rounded-3xl" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <Skeleton className="h-10 w-56" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {Array.from({ length: 5 }, (_, index) => <Skeleton key={index} className="h-20" />)}
      </div>
      <Skeleton className="h-40 w-full" />
      <CardGridSkeleton />
    </div>
  );
}

export function CalendarSkeleton() {
  return <Skeleton className="h-[32rem] w-full" />;
}
