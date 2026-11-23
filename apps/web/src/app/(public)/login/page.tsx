"use client";

import { FormEvent, useEffect, useState } from "react";
import { Bell, Bookmark, CalendarClock, Check, MessageCircleQuestionMark, Zap } from "lucide-react";
import { readError } from "@/lib/http";

type Options = {
  countries: { code: string; dial: string; label: string }[];
  universities: string[];
  batches: string[];
};

const field = "field";
const label = "mb-1.5 block text-sm font-bold";

function EyeIcon({ hidden }: { hidden: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
      {hidden ? null : <path d="M4 20 20 4" />}
    </svg>
  );
}

const perks = [
  [Bell, "Follow a hackathon to get reminders for its public deadlines."],
  [Bookmark, "Bookmark hackathons and find them again on your dashboard."],
  [CalendarClock, "See the next date for everything you track in one timeline."],
  [MessageCircleQuestionMark, "Ask a question and read the official answer."],
] as const;

function destination(role: string) {
  return role === "student" ? "/" : "/admin";
}

export default function LoginPage() {
  const [mode, setMode] = useState<"create" | "signin">("create");
  const [options, setOptions] = useState<Options | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [codeEmail, setCodeEmail] = useState<string | null>(null);
  const [verifiedEmail, setVerifiedEmail] = useState<string | null>(null);
  const [verificationToken, setVerificationToken] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/auth/options")
      .then((response) => response.json())
      .then((body: Options) => setOptions(body))
      .catch(() => setError("The signup options could not be loaded."));
  }, []);

  function resetVerification() {
    setVerifiedEmail(null);
    setVerificationToken(null);
    setDevCode(null);
    setCodeEmail(null);
    setCode("");
  }

  async function sendCode(email: string) {
    setBusy(true);
    setError(null);
    setInfo(null);
    resetVerification();
    const response = await fetch("/api/v1/auth/email/code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    setBusy(false);
    const text = await response.text();
    if (!response.ok) {
      setError(readError(text));
      return;
    }
    const body = JSON.parse(text) as { message: string; dev_code: string | null };
    setInfo(body.message);
    setDevCode(body.dev_code);
    setCodeEmail(email.trim().toLowerCase());
  }

  async function confirmCode(email: string) {
    setBusy(true);
    setError(null);
    const response = await fetch("/api/v1/auth/email/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, code }),
    });
    setBusy(false);
    const text = await response.text();
    if (!response.ok) {
      setError(readError(text));
      return;
    }
    const body = JSON.parse(text) as { verification_token: string };
    setVerificationToken(body.verification_token);
    setVerifiedEmail(email.trim().toLowerCase());
    setInfo("Email verified. You can create your account.");
    setDevCode(null);
  }

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") || "").trim().toLowerCase();
    const password = String(data.get("password") || "");
    const confirm = String(data.get("confirm") || "");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (!verificationToken || verifiedEmail !== email) {
      setError("Verify your email to create your account.");
      return;
    }
    setBusy(true);
    setError(null);
    const response = await fetch("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        verification_token: verificationToken,
        first_name: String(data.get("first_name") || ""),
        last_name: String(data.get("last_name") || ""),
        phone_country: String(data.get("phone_country") || "IN"),
        phone: String(data.get("phone") || ""),
        university: String(data.get("university") || ""),
        batch: String(data.get("batch") || ""),
        niat_id: String(data.get("niat_id") || ""),
        password,
      }),
    });
    setBusy(false);
    const text = await response.text();
    if (!response.ok) {
      setError(readError(text));
      return;
    }
    const user = JSON.parse(text) as { role: string };
    window.location.href = destination(user.role);
  }

  async function onSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    const response = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: String(data.get("email") || ""),
        password: String(data.get("password") || ""),
      }),
    });
    setBusy(false);
    const text = await response.text();
    if (!response.ok) {
      setError(readError(text));
      return;
    }
    const user = JSON.parse(text) as { role: string };
    window.location.href = destination(user.role);
  }

  return (
    <div className="rise mx-auto grid max-w-5xl overflow-hidden rounded-3xl border-[1.5px] border-ink bg-card shadow-[6px_6px_0_var(--ink)] lg:grid-cols-[0.9fr_1.1fr]">
      <aside className="ink-grid hidden flex-col justify-between gap-10 p-8 lg:flex">
        <div>
          <span aria-hidden="true" className="floaty grid h-12 w-12 -rotate-6 place-items-center rounded-xl border-[1.5px] border-ink bg-lime text-ink shadow-[3px_3px_0_var(--sky)]">
            <Zap className="h-6 w-6 fill-ink" />
          </span>
          <h2 className="mt-6 text-4xl font-extrabold leading-[1.05]">
            Every deadline, <span className="text-lime">one login.</span>
          </h2>
          <p className="mt-3 text-white/75">An account keeps the hackathons you care about in one place.</p>
        </div>
        <ul className="space-y-3 text-sm">
          {perks.map(([Icon, text]) => (
            <li key={text} className="group flex items-start gap-3 rounded-xl border border-white/15 bg-white/5 p-3 transition-colors hover:border-lime hover:bg-white/10">
              <Icon aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-lime transition-transform group-hover:scale-125" />
              {text}
            </li>
          ))}
        </ul>
      </aside>
      <div className="p-6 md:p-8">
      <div aria-label="Account" className="seg mb-6" role="group">
        <button aria-pressed={mode === "create"} className={mode === "create" ? "is-on" : ""} type="button" onClick={() => { setMode("create"); setError(null); }}>
          Create account
        </button>
        <button aria-pressed={mode === "signin"} className={mode === "signin" ? "is-on" : ""} type="button" onClick={() => { setMode("signin"); setError(null); }}>
          Sign in
        </button>
      </div>
      <h1 className="text-3xl font-extrabold tracking-tight md:text-4xl">{mode === "create" ? "Create your account" : "Sign in"}</h1>

      {mode === "signin" ? (
        <form className="mt-6 space-y-4" onSubmit={onSignIn}>
          <div>
            <label className={label} htmlFor="signin-email">Email <span className="text-danger">*</span></label>
            <input id="signin-email" name="email" type="email" required autoComplete="email" className={field} />
          </div>
          <div>
            <label className={label} htmlFor="signin-password">Password <span className="text-danger">*</span></label>
            <input id="signin-password" name="password" type="password" required autoComplete="current-password" className={field} />
          </div>
          {error ? <p className="rise rounded-xl border-[1.5px] border-danger bg-rose-50 px-3 py-2 text-sm font-semibold text-danger" role="alert">{error}</p> : null}
          <button className="btn btn-primary w-full py-3" disabled={busy} type="submit">
            Sign in
          </button>
          <p className="text-center text-sm text-muted">
            Need an account?{" "}
            <button className="link-arrow" type="button" onClick={() => { setMode("create"); setError(null); }}>
              Create one
            </button>
          </p>
        </form>
      ) : (
        <form className="mt-6 space-y-4" onSubmit={onCreate}>
          <div>
            <label className={label} htmlFor="phone">Mobile number <span className="text-danger">*</span></label>
            <div className="grid grid-cols-[7.5rem_1fr] gap-2">
              <select id="phone-country" name="phone_country" className={field} defaultValue="IN" aria-label="Country code">
                {(options?.countries || [{ code: "IN", dial: "+91", label: "+91 IN" }]).map((country) => (
                  <option key={country.code} value={country.code}>{country.label}</option>
                ))}
              </select>
              <input id="phone" name="phone" inputMode="numeric" autoComplete="tel" required placeholder="9876543210" className={field} />
            </div>
          </div>

          <div>
            <label className={label} htmlFor="email">Email <span className="text-danger">*</span></label>
            <div className="grid grid-cols-[1fr_auto] gap-2">
              <input
                id="email"
                name="email"
                type="email"
                required
                autoComplete="email"
                className={field}
                onChange={(event) => {
                  const next = event.target.value.trim().toLowerCase();
                  if ((verifiedEmail && next !== verifiedEmail) || (codeEmail && next !== codeEmail)) resetVerification();
                }}
              />
              <button
                className="btn px-4"
                disabled={busy}
                type="button"
                onClick={(event) => {
                  const email = new FormData(event.currentTarget.form!).get("email");
                  if (!email || !String(email).includes("@")) {
                    setError("Enter an email address");
                    return;
                  }
                  void sendCode(String(email));
                }}
              >
                {verifiedEmail ? <Check aria-hidden="true" className="h-4 w-4" /> : null}
                {verifiedEmail ? "Verified" : "Verify"}
              </button>
            </div>
            {codeEmail && !verifiedEmail ? (
              <div className="rise mt-2 space-y-2 rounded-xl border-[1.5px] border-ink bg-tint p-3">
                {info ? <p className="text-sm text-muted">{info}{devCode ? ` Code: ${devCode}` : ""}</p> : null}
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <input
                    aria-label="Verification code"
                    inputMode="numeric"
                    maxLength={6}
                    value={code}
                    onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                    placeholder="6-digit code"
                    className={field}
                  />
                  <button
                    className="btn px-4"
                    disabled={busy || code.length !== 6}
                    type="button"
                    onClick={(event) => {
                      const email = String(new FormData(event.currentTarget.form!).get("email") || "");
                      void confirmCode(email);
                    }}
                  >
                    Confirm
                  </button>
                </div>
              </div>
            ) : null}
            {verifiedEmail ? <p className="rise mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700"><Check aria-hidden="true" className="h-4 w-4" />Email verified.</p> : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={label} htmlFor="first-name">First name <span className="text-danger">*</span></label>
              <input id="first-name" name="first_name" required autoComplete="given-name" className={field} />
            </div>
            <div>
              <label className={label} htmlFor="last-name">Last name <span className="text-danger">*</span></label>
              <input id="last-name" name="last_name" required autoComplete="family-name" className={field} />
            </div>
          </div>

          <div>
            <label className={label} htmlFor="university">University name <span className="text-danger">*</span></label>
            <select id="university" name="university" required className={field} defaultValue="">
              <option value="" disabled>Select university</option>
              {(options?.universities || []).map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={label} htmlFor="batch">Batch <span className="text-danger">*</span></label>
            <select id="batch" name="batch" required className={field} defaultValue="">
              <option value="" disabled>Select batch</option>
              {(options?.batches || []).map((batch) => (
                <option key={batch} value={batch}>{batch}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={label} htmlFor="niat-id">NIAT ID <span className="text-danger">*</span></label>
            <input id="niat-id" name="niat_id" required placeholder="N25H05F9974" autoCapitalize="characters" className={field} />
            <p className="mt-1.5 text-xs text-muted">For example: N25H05F9974</p>
          </div>

          <div>
            <label className={label} htmlFor="password">Password <span className="text-danger">*</span></label>
            <div className="relative">
              <input id="password" name="password" type={showPassword ? "text" : "password"} required autoComplete="new-password" className={`${field} pr-11`} />
              <button className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md text-muted hover:scale-110 hover:text-ink" type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)}>
                <EyeIcon hidden={!showPassword} />
              </button>
            </div>
            <p className="mt-1.5 text-xs text-muted">At least 8 characters, with a letter and a number</p>
          </div>

          <div>
            <label className={label} htmlFor="confirm">Confirm password <span className="text-danger">*</span></label>
            <div className="relative">
              <input id="confirm" name="confirm" type={showConfirm ? "text" : "password"} required autoComplete="new-password" className={`${field} pr-11`} />
              <button className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md text-muted hover:scale-110 hover:text-ink" type="button" aria-label={showConfirm ? "Hide password" : "Show password"} onClick={() => setShowConfirm((value) => !value)}>
                <EyeIcon hidden={!showConfirm} />
              </button>
            </div>
          </div>

          {error ? <p className="rise rounded-xl border-[1.5px] border-danger bg-rose-50 px-3 py-2 text-sm font-semibold text-danger" role="alert">{error}</p> : null}
          {info && verifiedEmail ? <p className="text-sm text-muted">{info}</p> : null}
          <button className="btn btn-primary w-full py-3" disabled={busy} type="submit">
            Create account
          </button>
          <p className="text-center text-sm text-muted">Verify your email to create your account.</p>
          <p className="text-center text-sm text-muted">
            Already have an account?{" "}
            <button className="link-arrow" type="button" onClick={() => { setMode("signin"); setError(null); }}>
              Sign in
            </button>
          </p>
        </form>
      )}
      </div>
    </div>
  );
}
