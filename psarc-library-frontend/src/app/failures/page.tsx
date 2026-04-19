"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";

import { listFailedPsarc } from "@/lib/api";
import type { FailedPsarcEntry } from "@/lib/types";

const PAGE_SIZE = 50;

export default function FailuresPage() {
  const [failures, setFailures] = useState<FailedPsarcEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      try {
        const data = await listFailedPsarc(page * PAGE_SIZE, PAGE_SIZE);
        if (!cancelled) {
          setFailures(data.data);
          setTotal(data.total);
        }
      } catch (error) {
        if (!cancelled) {
          toast.error(
            error instanceof Error ? error.message : "Failed to load failures"
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const formatFileSize = (bytes: number | null) => {
    if (bytes === null) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Failed Entries</h1>
        <p className="text-sm text-text-secondary">
          PSARC files that failed to parse — inspect errors for debugging
        </p>
      </div>

      <div className="text-sm text-text-muted">
        {isLoading
          ? "Loading..."
          : `${total} failed file${total !== 1 ? "s" : ""}`}
      </div>

      {/* Failure List */}
      <div className="space-y-2">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-lg border border-terminal-border bg-card"
            />
          ))
        ) : failures.length === 0 ? (
          <div className="rounded-lg border border-terminal-border bg-card py-12 text-center text-text-muted">
            No failed entries — all files parsed successfully!
          </div>
        ) : (
          failures.map(entry => (
            <div
              key={entry.filename}
              className="rounded-lg border border-neon-red/20 bg-card"
            >
              {/* Header */}
              <button
                onClick={() =>
                  setExpanded(
                    expanded === entry.filename ? null : entry.filename
                  )
                }
                className="flex w-full items-center justify-between px-4 py-3 text-left"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <span
                    className={`flex h-5 w-5 flex-shrink-0 items-center justify-center text-xs text-neon-red transition-transform ${
                      expanded === entry.filename ? "rotate-90" : ""
                    }`}
                  >
                    ▶
                  </span>
                  <div className="overflow-hidden">
                    <span className="block truncate font-mono text-sm font-medium text-neon-red">
                      {entry.filename}
                    </span>
                    <span className="block truncate text-xs text-text-muted">
                      {entry.error_type}
                    </span>
                  </div>
                </div>
                <div className="flex flex-shrink-0 items-center gap-3 text-xs text-text-muted">
                  <span>{formatFileSize(entry.file_size)}</span>
                  <span>{new Date(entry.timestamp).toLocaleDateString()}</span>
                </div>
              </button>

              {/* Expanded Error Details */}
              {expanded === entry.filename && (
                <div className="border-t border-terminal-border px-4 pb-4 pt-3 space-y-3">
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-text-muted">File path: </span>
                      <span className="font-mono text-text-secondary break-all">
                        {entry.filepath}
                      </span>
                    </div>
                    <div>
                      <span className="text-text-muted">Error type: </span>
                      <span className="font-mono text-neon-red">
                        {entry.error_type}
                      </span>
                    </div>
                    <div>
                      <span className="text-text-muted">Timestamp: </span>
                      <span className="text-text-secondary">
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="text-text-muted">File size: </span>
                      <span className="text-text-secondary">
                        {formatFileSize(entry.file_size)}
                      </span>
                    </div>
                  </div>

                  {/* Error Message */}
                  <div>
                    <p className="mb-1 text-xs font-medium text-text-muted">
                      Error Message
                    </p>
                    <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-background p-3 font-mono text-xs text-neon-red">
                      {entry.error_message}
                    </pre>
                  </div>

                  {/* Raw Data */}
                  {entry.raw_data && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-text-muted">
                        Raw Data
                      </p>
                      <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded bg-background p-3 font-mono text-xs text-text-secondary">
                        {entry.raw_data}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="rounded-md border border-terminal-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-background-tertiary disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-3 text-sm text-text-muted">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="rounded-md border border-terminal-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-background-tertiary disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
