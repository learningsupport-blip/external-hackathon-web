"use client";

import { useState } from "react";
import { readError } from "@/lib/http";

export type FieldSpec = { key: string; label: string; multiline?: boolean; checkbox?: boolean; number?: boolean };

const inputClass = "w-full rounded-2xl border border-line px-3 py-2";
const STATES = [
  ["not_specified", "Not specified"],
  ["confirmed", "Confirmed"],
  ["not_announced", "Not announced"],
  ["awaiting_confirmation", "Awaiting confirmation"],
  ["not_applicable", "Not applicable"],
];

async function send(path: string, method: string, body?: unknown) {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(readError(await response.text()));
  if (response.status === 204) return null;
  return response.json();
}

export function SectionStateControl({
  hackathonId,
  section,
  caption = "Information state",
  value,
  onMessage,
  onError,
}: {
  hackathonId: string;
  section: string;
  caption?: string;
  value: string;
  onMessage: (value: string | null) => void;
  onError: (value: string | null) => void;
}) {
  const [state, setState] = useState(value || "not_specified");
  return (
    <label className="block text-sm font-semibold">
      {caption}
      <div className="mt-1 flex gap-2 font-normal">
        <select className={inputClass} value={state} onChange={(event) => setState(event.target.value)}>
          {STATES.map(([id, label]) => (
            <option key={id} value={id}>{label}</option>
          ))}
        </select>
        <button
          className="rounded-full border border-line px-4 py-2 text-sm font-semibold"
          onClick={async () => {
            try {
              await send(`/api/v1/admin/hackathons/${hackathonId}/sections`, "PATCH", { states: [{ section, state }] });
              onMessage("Information state saved.");
              onError(null);
            } catch (caught) {
              onError(caught instanceof Error ? caught.message : "Could not save the information state");
            }
          }}
          type="button"
        >
          Save state
        </button>
      </div>
    </label>
  );
}

export function CollectionEditor<T extends { id: string; position: number }>({
  endpoint,
  items,
  fields,
  blank,
  onChange,
  onError,
  onMessage,
}: {
  endpoint: string;
  items: T[];
  fields: FieldSpec[];
  blank: Record<string, string | boolean>;
  onChange: (items: T[]) => void;
  onError: (value: string | null) => void;
  onMessage: (value: string | null) => void;
}) {
  const [draft, setDraft] = useState(blank);
  const ordered = [...items].sort((a, b) => a.position - b.position);

  function payload(source: Record<string, unknown>) {
    const body: Record<string, unknown> = {};
    for (const field of fields) {
      const value = source[field.key];
      body[field.key] = (field.number || field.key === "published_at") && value === "" ? null : value;
    }
    return body;
  }

  async function run(action: () => Promise<void>) {
    try {
      await action();
      onError(null);
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Save failed");
    }
  }

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {ordered.map((item, index) => (
          <Row
            key={item.id}
            fields={fields}
            item={item}
            onSave={(body) =>
              run(async () => {
                const saved = (await send(`${endpoint}/${item.id}`, "PUT", body)) as T;
                onChange(items.map((row) => (row.id === item.id ? saved : row)));
                onMessage("Saved.");
              })
            }
            onRemove={() =>
              run(async () => {
                await send(`${endpoint}/${item.id}`, "DELETE");
                onChange(items.filter((row) => row.id !== item.id));
                onMessage("Removed.");
              })
            }
            onMove={
              index === 0
                ? undefined
                : () =>
                    run(async () => {
                      const previous = ordered[index - 1];
                      const [saved, swapped] = await Promise.all([
                        send(`${endpoint}/${item.id}`, "PUT", { ...payload(item as unknown as Record<string, unknown>), position: previous.position }),
                        send(`${endpoint}/${previous.id}`, "PUT", { ...payload(previous as unknown as Record<string, unknown>), position: item.position }),
                      ]);
                      onChange(items.map((row) => (row.id === item.id ? (saved as T) : row.id === previous.id ? (swapped as T) : row)));
                    })
            }
          />
        ))}
      </ul>
      <div className="grid gap-2 border-t border-line pt-4">
        {fields.map((field) => (
          <FieldInput key={field.key} field={field} value={draft[field.key]} onChange={(value) => setDraft({ ...draft, [field.key]: value })} />
        ))}
        <button
          className="w-fit rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white"
          onClick={() =>
            run(async () => {
              const created = (await send(endpoint, "POST", payload(draft))) as T;
              onChange([...items, created]);
              setDraft(blank);
              onMessage("Added.");
            })
          }
          type="button"
        >
          Add
        </button>
      </div>
    </div>
  );
}

function Row({
  item,
  fields,
  onSave,
  onRemove,
  onMove,
}: {
  item: Record<string, unknown>;
  fields: FieldSpec[];
  onSave: (body: Record<string, unknown>) => void;
  onRemove: () => void;
  onMove?: () => void;
}) {
  const [draft, setDraft] = useState(() => {
    const next: Record<string, string | boolean> = {};
    for (const field of fields) {
      const value = item[field.key];
      next[field.key] = field.checkbox ? Boolean(value) : value == null ? "" : String(value);
    }
    return next;
  });
  return (
    <li className="grid gap-2 rounded-2xl border border-line p-3">
      {fields.map((field) => (
        <FieldInput key={field.key} field={field} value={draft[field.key]} onChange={(value) => setDraft({ ...draft, [field.key]: value })} />
      ))}
      <div className="flex flex-wrap gap-3 text-sm font-semibold">
        <button
          onClick={() => {
            const body: Record<string, unknown> = {};
            for (const field of fields) {
              body[field.key] = (field.number || field.key === "published_at") && draft[field.key] === "" ? null : draft[field.key];
            }
            onSave(body);
          }}
          type="button"
        >
          Save
        </button>
        {onMove ? (
          <button onClick={onMove} type="button">
            Move up
          </button>
        ) : null}
        <button className="text-danger" onClick={onRemove} type="button">
          Remove
        </button>
      </div>
    </li>
  );
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: FieldSpec;
  value: string | boolean;
  onChange: (value: string | boolean) => void;
}) {
  if (field.checkbox) {
    return (
      <label className="flex items-center gap-2 text-sm">
        <input checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} type="checkbox" />
        {field.label}
      </label>
    );
  }
  if (field.multiline) {
    return (
      <textarea
        className={inputClass}
        placeholder={field.label}
        rows={3}
        value={String(value)}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }
  return (
    <input
      className={inputClass}
      placeholder={field.label}
      type={field.number ? "number" : "text"}
      value={String(value)}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
