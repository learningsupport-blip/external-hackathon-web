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
