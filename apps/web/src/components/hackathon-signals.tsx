"use client";

import { useState } from "react";
import Link from "next/link";
import { readError } from "@/lib/http";
import { useViewer } from "@/lib/viewer-store";

type Stance = "registered" | "missed" | null;

export function HackathonSignals({
  slug,
  signedIn,
  stance,
  interested = false,
  registrationState,
}: {
  slug: string;
  signedIn: boolean;
  stance: Stance;
  interested?: boolean;
  registrationState: string;
}) {
  const viewer = useViewer();
  const live = Boolean(viewer?.user);
  const active = live || signedIn;
  const stanceNow = live ? viewer?.stances[slug] ?? null : stance;
  const interestedNow = live ? Boolean(viewer?.interests[slug]) : interested;
  const [current, setCurrent] = useState<Stance>(stanceNow);
  const [starred, setStarred] = useState(interestedNow);
  const [source, setSource] = useState({ active, stance: stanceNow, interested: interestedNow });
  if (source.active !== active || source.stance !== stanceNow || source.interested !== interestedNow) {
    setSource({ active, stance: stanceNow, interested: interestedNow });
    setCurrent(stanceNow);
    setStarred(interestedNow);
  }
  const [ask, setAsk] = useState(false);
  const [body, setBody] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closed = registrationState === "closed" || registrationState === "completed";

  async function choose(next: Exclude<Stance, null>) {
    if (!active) return;
    setError(null);
    const clearing = current === next;
    const response = await fetch(`/api/v1/hackathons/${slug}/stance`, {
      method: clearing ? "DELETE" : "PUT",
      headers: clearing ? undefined : { "Content-Type": "application/json" },
      body: clearing ? undefined : JSON.stringify({ stance: next }),
    });
    if (!response.ok) {
      setError(readError(await response.text()));
      return;
    }
    setCurrent(clearing ? null : next);
    setMessage(clearing ? "Mark removed." : next === "registered" ? "Marked as registered." : "Marked as missed.");
  }

  async function toggleInterest() {
    if (!active) return;
    setError(null);
    const response = await fetch(`/api/v1/hackathons/${slug}/interest`, { method: starred ? "DELETE" : "PUT" });
    if (!response.ok) {
      setError(readError(await response.text()));
      return;
    }
    setStarred(!starred);
    setMessage(starred ? "Interest removed." : "We'll remind you three days before the deadline.");
  }

  const up = "sig";
  const upOn = "sig-up";
  const downOn = "sig-down";
  const askOn = "sig-ask";

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {active ? (
          <button aria-pressed={current === "registered"} className={`${up} ${upOn}`} onClick={() => choose("registered")} title="I registered" type="button">
            <Thumb />
            <span className="sr-only">I registered</span>
          </button>
        ) : (
          <Link aria-label="Log in to mark that you registered" className={`${up} ${upOn}`} href="/login" title="I registered">
            <Thumb />
          </Link>
        )}
        {active ? (
          <button aria-pressed={current === "missed"} className={`${up} ${downOn}`} onClick={() => choose("missed")} title="I missed this" type="button">
            <Thumb down />
            <span className="sr-only">I missed this</span>
          </button>
        ) : (
          <Link aria-label="Log in to mark that you missed this" className={`${up} ${downOn}`} href="/login" title="I missed this">
            <Thumb down />
          </Link>
        )}
        {active ? (
          <button aria-pressed={starred} className={`${up} sig-interest`} onClick={() => void toggleInterest()} title="Interested" type="button">
            <Star />
            <span className="sr-only">Interested</span>
          </button>
        ) : (
          <Link aria-label="Log in to mark that you are interested" className={`${up} sig-interest`} href="/login" title="Interested">
            <Star />
          </Link>
        )}
        {active ? (
          <button aria-expanded={ask} className={`${up} ${askOn}`} onClick={() => setAsk((value) => !value)} title="Ask a question" type="button">
            ?
            <span className="sr-only">Ask a question</span>
          </button>
        ) : (
          <Link aria-label="Log in to ask a question" className={`${up} ${askOn}`} href="/login" title="Ask a question">
            ?
          </Link>
        )}
        <span className={`text-xs font-semibold ${current === "registered" ? "text-emerald-700" : current === "missed" ? "text-rose-700" : "text-muted"}`}>
          {current === "registered" ? "Registered" : current === "missed" ? "Missed" : starred ? "Interested" : closed ? "Registration closed" : "Mark yours"}
        </span>
      </div>
      {ask && active ? (
        <form
          className="rise grid gap-2 rounded-xl border-[1.5px] border-ink bg-tint p-3"
          onSubmit={async (event) => {
            event.preventDefault();
            setError(null);
            const response = await fetch(`/api/v1/hackathons/${slug}/queries`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ body, is_public: isPublic }),
            });
            if (!response.ok) {
              setError(readError(await response.text()));
              return;
            }
            setBody("");
            setAsk(false);
            setMessage(isPublic ? "Question sent. It appears on the page after an official answer." : "Private question sent.");
          }}
        >
          <textarea
            className="field"
            placeholder="Ask a question about this hackathon"
            rows={3}
            value={body}
            onChange={(event) => setBody(event.target.value)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input checked={isPublic} onChange={(event) => setIsPublic(event.target.checked)} type="checkbox" />
            Show this on the public page after it is answered
          </label>
          <button className="btn btn-primary btn-sm w-fit" type="submit">
            Send question
          </button>
        </form>
      ) : null}
      {message ? <p className="rise text-xs font-semibold text-accent" role="status">{message}</p> : null}
      {error ? <p className="rise text-xs font-semibold text-danger" role="alert">{error}</p> : null}
    </div>
  );
}

function Star() {
  return (
    <svg aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24">
      <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 16.8 6.6 19.8l1-6.1L3.2 9.4l6.1-.9L12 3Z" />
    </svg>
  );
}

function Thumb({ down = false }: { down?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={`h-4 w-4 ${down ? "rotate-180" : ""}`}>
      <path d="M8 11V20H5.5A1.5 1.5 0 0 1 4 18.5v-6A1.5 1.5 0 0 1 5.5 11H8zm0 0 2.2-5.2A2 2 0 0 1 12 4.6V11h5.2a2 2 0 0 1 2 2.3l-.8 5.2a2 2 0 0 1-2 1.7H8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}
