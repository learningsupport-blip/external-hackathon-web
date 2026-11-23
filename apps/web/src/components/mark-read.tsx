"use client";

export function MarkRead({ id }: { id: string }) {
  return (
    <button
      className="btn btn-sm mt-3"
      onClick={async () => {
        await fetch(`/api/v1/notifications/${id}/read`, { method: "POST" });
        window.location.reload();
      }}
      type="button"
    >
      Mark read
    </button>
  );
}
