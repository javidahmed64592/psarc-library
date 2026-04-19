"use client";

import { useState } from "react";
import toast from "react-hot-toast";

import { validatePsarcFile } from "@/lib/api";
import type { Tuning, ValidatePsarcResponse } from "@/lib/types";

const formatTuning = (tuning: Tuning): string => {
  switch (tuning.type) {
    case "Standard":
      return `${tuning.root} Standard`;
    case "Drop":
      return `Drop ${tuning.root}`;
    case "Custom":
      return "Custom Tuning";
  }
};

export default function ValidatePage() {
  const [file, setFile] = useState<File | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [result, setResult] = useState<ValidatePsarcResponse | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFile = (f: File) => {
    if (!f.name.endsWith(".psarc")) {
      toast.error("Please select a .psarc file");
      return;
    }
    setFile(f);
    setResult(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFile(droppedFile);
  };

  const handleValidate = async () => {
    if (!file) return;
    setIsValidating(true);
    setResult(null);
    try {
      const data = await validatePsarcFile(file);
      setResult(data);
      if (data.is_valid) {
        toast.success("File is valid!");
      } else {
        toast.error("File is invalid");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Validation failed");
    } finally {
      setIsValidating(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Validate PSARC</h1>
        <p className="text-sm text-text-secondary">
          Upload a .psarc file to check if it parses correctly before adding to
          your DLC folder
        </p>
      </div>

      {/* Upload Area */}
      <div
        onDragOver={e => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={`rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          isDragOver
            ? "border-neon-blue bg-neon-blue/5"
            : "border-terminal-border bg-card"
        }`}
      >
        <div className="space-y-3">
          <p className="text-3xl">📦</p>
          <div>
            <p className="text-sm text-text-secondary">
              Drag & drop a .psarc file here, or
            </p>
            <label className="mt-2 inline-block cursor-pointer rounded-md bg-neon-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90">
              Browse Files
              <input
                type="file"
                accept=".psarc"
                onChange={e => {
                  const selected = e.target.files?.[0];
                  if (selected) handleFile(selected);
                }}
                className="hidden"
              />
            </label>
          </div>
        </div>
      </div>

      {/* Selected File */}
      {file && (
        <div className="flex items-center justify-between rounded-lg border border-terminal-border bg-card px-4 py-3">
          <div className="overflow-hidden">
            <p className="truncate font-mono text-sm text-neon-blue">
              {file.name}
            </p>
            <p className="text-xs text-text-muted">
              {(file.size / (1024 * 1024)).toFixed(2)} MB
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleValidate}
              disabled={isValidating}
              className="rounded-md bg-neon-green px-4 py-2 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {isValidating ? (
                <span className="flex items-center gap-2">
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-background border-t-transparent" />
                  Validating...
                </span>
              ) : (
                "Validate"
              )}
            </button>
            <button
              onClick={() => {
                setFile(null);
                setResult(null);
              }}
              className="rounded-md border border-terminal-border px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-background-tertiary"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Validation Result */}
      {result && (
        <div
          className={`rounded-lg border p-5 ${
            result.is_valid
              ? "border-neon-green/30 bg-neon-green/5"
              : "border-neon-red/30 bg-neon-red/5"
          }`}
        >
          <div className="mb-3 flex items-center gap-2">
            <div
              className={`h-3 w-3 rounded-full ${
                result.is_valid ? "bg-neon-green" : "bg-neon-red"
              }`}
            />
            <h3 className="text-sm font-semibold text-text-primary">
              {result.is_valid ? "Valid PSARC File" : "Invalid PSARC File"}
            </h3>
            <span className="ml-auto font-mono text-xs text-text-muted">
              {result.filename}
            </span>
          </div>

          {/* Valid: Show parsed data */}
          {result.is_valid && result.data && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
                <span>
                  Songs:{" "}
                  <span className="text-neon-green">
                    {result.data.entries.length}
                  </span>
                </span>
                <span>
                  Model:{" "}
                  <span className="text-text-secondary">
                    {result.data.model_name || "—"}
                  </span>
                </span>
                <span>
                  Version:{" "}
                  <span className="text-text-secondary">
                    {result.data.iteration_version}
                  </span>
                </span>
              </div>
              <div className="overflow-x-auto rounded border border-terminal-border">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-terminal-border bg-background-secondary">
                    <tr>
                      <th className="px-3 py-2 font-medium text-text-secondary">
                        Title
                      </th>
                      <th className="px-3 py-2 font-medium text-text-secondary">
                        Artist
                      </th>
                      <th className="hidden px-3 py-2 font-medium text-text-secondary sm:table-cell">
                        Album
                      </th>
                      <th className="px-3 py-2 font-medium text-text-secondary">
                        Tuning
                      </th>
                      <th className="px-3 py-2 font-medium text-text-secondary">
                        Duration
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.data.entries.map((song, i) => (
                      <tr
                        key={i}
                        className="border-b border-terminal-border/50 last:border-b-0"
                      >
                        <td className="px-3 py-2 text-text-primary">
                          {song.title}
                        </td>
                        <td className="px-3 py-2 text-text-secondary">
                          {song.artist}
                        </td>
                        <td className="hidden px-3 py-2 text-text-secondary sm:table-cell">
                          {song.album}
                        </td>
                        <td className="px-3 py-2">
                          <span className="rounded bg-background-tertiary px-1.5 py-0.5 font-mono text-neon-purple">
                            {formatTuning(song.tuning)}
                          </span>
                        </td>
                        <td className="px-3 py-2 font-mono text-text-muted">
                          {formatDuration(song.length)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Invalid: Show error */}
          {!result.is_valid && result.error && (
            <div className="space-y-3">
              <div className="space-y-1 text-sm">
                <div>
                  <span className="text-text-muted">Error type: </span>
                  <span className="font-mono text-neon-red">
                    {result.error.error_type}
                  </span>
                </div>
              </div>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-background p-3 font-mono text-xs text-neon-red">
                {result.error.error_message}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
