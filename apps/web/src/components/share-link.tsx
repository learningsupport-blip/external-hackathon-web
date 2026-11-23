"use client";

import { useState } from "react";

export function ShareLink() {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className={`btn ${copied ? "btn-lime" : ""}`}
      onClick={async () => {
        await navigator.clipboard.writeText(window.location.href);
        setCopied(true);
      }}
      type="button"
    >
      {copied ? "Link copied" : "Share link"}
    </button>
  );
}
