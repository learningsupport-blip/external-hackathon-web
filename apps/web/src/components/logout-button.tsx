"use client";

export function LogoutButton() {
  return (
    <button
      className="btn btn-sm"
      onClick={async () => {
        await fetch("/api/v1/auth/logout", { method: "POST" });
        window.location.href = "/";
      }}
      type="button"
    >
      Log out
    </button>
  );
}
