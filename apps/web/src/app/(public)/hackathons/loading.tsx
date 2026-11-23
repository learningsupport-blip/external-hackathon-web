import { CardSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <CardSkeleton />
      <CardSkeleton />
      <CardSkeleton />
      <CardSkeleton />
    </div>
  );
}
