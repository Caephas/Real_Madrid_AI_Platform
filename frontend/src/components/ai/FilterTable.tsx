"use client";

import { useState } from "react";

/* ─────────────────────────────────────────────────────────
 * FILTER TABLE
 * Status chips directly filter the task table.
 * ───────────────────────────────────────────────────────── */

export type FilterStatus = "todo" | "progress" | "done";

export type FilterRow = {
  task: string;
  date: string;
  status: FilterStatus;
  owner: string;
};

const PILLS: Record<FilterStatus, { label: string; cls: string }> = {
  todo: { label: "To do", cls: "filter-status-todo" },
  progress: { label: "In Progress", cls: "filter-status-progress" },
  done: { label: "Completed", cls: "filter-status-done" },
};

export default function FilterTable({
  rows,
  filterLabels,
  headers = ["Task name", "Date", "Status", "Advisor"],
}: {
  rows: FilterRow[];
  filterLabels?: Record<FilterStatus, string>;
  headers?: [string, string, string, string];
}) {
  const [filter, setFilter] = useState<"all" | FilterStatus>("all");
  const FILTERS: { key: "all" | FilterStatus; label: string; dot?: string; count: number }[] = [
    { key: "all", label: "All", count: rows.length },
    {
      key: "todo",
      label: filterLabels?.todo ?? PILLS.todo.label,
      dot: "#f09a2f",
      count: rows.filter((r) => r.status === "todo").length,
    },
    {
      key: "progress",
      label: filterLabels?.progress ?? PILLS.progress.label,
      dot: "#16a6c7",
      count: rows.filter((r) => r.status === "progress").length,
    },
    {
      key: "done",
      label: filterLabels?.done ?? PILLS.done.label,
      dot: "#25a878",
      count: rows.filter((r) => r.status === "done").length,
    },
  ];

  return (
    <div className="w-full max-w-105">
      {/* filter chips */}
      <div
        className="-mx-1 mb-1 flex items-center gap-1 overflow-x-auto px-1 py-1"
        style={{ scrollbarWidth: "none" }}
      >
        {FILTERS.map((f) => {
          const active = filter === f.key;
          return (
            <button
              key={f.key}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(f.key)}
              className={`flex h-6.5 shrink-0 items-center gap-1.5 rounded-full px-2.5 text-[12px]
                font-medium transition-[background-color,box-shadow,color] duration-200
                ${active ? "bg-surface text-ink shadow-btn" : "text-ink-2 hover:bg-hover"}`}
            >
              {f.dot && <span className="size-1.5 rounded-full" style={{ background: f.dot }} />}
              {f.label}
              <span
                className={`rounded-[4px] px-1 text-[10.5px] tabular-nums
                  ${active ? "bg-field text-ink-2" : "text-ink-3"}`}
              >
                {f.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* table */}
      <div
        aria-label="Scrollable task table"
        className="overflow-x-auto rounded-card bg-surface shadow-card"
        role="region"
        tabIndex={0}
        style={{ scrollbarWidth: "none" }}
      >
        <div className="min-w-[420px]">
          <div className="grid grid-cols-[1.3fr_0.6fr_0.95fr_0.9fr] border-b border-line px-3 py-2 text-[11.5px] font-medium text-ink-3">
            <span>{headers[0]}</span>
            <span>{headers[1]}</span>
            <span>{headers[2]}</span>
            <span>{headers[3]}</span>
          </div>
          {rows.map((row) => {
            const shown = filter === "all" || row.status === filter;
            const pill = PILLS[row.status];
            return (
              <div
                key={row.task}
                className="grid transition-[grid-template-rows,opacity] duration-300"
                style={{
                  gridTemplateRows: shown ? "1fr" : "0fr",
                  opacity: shown ? 1 : 0,
                  transitionTimingFunction: "cubic-bezier(0.23, 1, 0.32, 1)",
                }}
              >
                <div className="overflow-hidden">
                  <div
                    className="grid grid-cols-[1.3fr_0.6fr_0.95fr_0.9fr] items-center border-b
                      border-line px-3 py-2 text-[12px] transition-colors duration-100
                      last:border-0 hover:bg-hover"
                  >
                    <span className="truncate font-medium text-ink">{row.task}</span>
                    <span className="text-ink-2 tabular-nums">{row.date}</span>
                    <span>
                      <span
                        className={`inline-flex h-5 items-center rounded-[5px] px-1.5
                          text-[11px] font-medium ${pill.cls}`}
                      >
                        {filterLabels?.[row.status] ?? pill.label}
                      </span>
                    </span>
                    <span className="truncate text-ink-2">{row.owner}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
