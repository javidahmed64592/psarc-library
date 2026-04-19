"use client";

import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import {
  fetchAllPsarcData,
  getStats,
  syncPsarcDirectory,
  toggleInGame,
} from "@/lib/api";
import type { SongRow, StatsResponse, SyncResponse, Tuning } from "@/lib/types";

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

export default function SongsPage() {
  const [allSongs, setAllSongs] = useState<SongRow[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [syncResult, setSyncResult] = useState<SyncResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [filters, setFilters] = useState({
    title: "",
    artist: "",
    album: "",
    year: "",
    inGameOnly: false,
  });

  const flattenPsarcData = (
    psarcFiles: Awaited<ReturnType<typeof fetchAllPsarcData>>
  ): SongRow[] =>
    psarcFiles.flatMap(psarc =>
      psarc.entries.map(song => ({
        ...song,
        psarc_filename: psarc.filename,
        is_in_game: psarc.is_in_game,
      }))
    );

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      try {
        const [psarcFiles, statsData] = await Promise.all([
          fetchAllPsarcData(),
          getStats(),
        ]);
        if (cancelled) return;
        setAllSongs(flattenPsarcData(psarcFiles));
        setStats(statsData);
      } catch (error) {
        if (cancelled) return;
        toast.error(
          error instanceof Error ? error.message : "Failed to load songs"
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncResult(null);
    try {
      const result = await syncPsarcDirectory();
      setSyncResult(result);
      toast.success("Sync completed");
      const [psarcFiles, statsData] = await Promise.all([
        fetchAllPsarcData(),
        getStats(),
      ]);
      setAllSongs(flattenPsarcData(psarcFiles));
      setStats(statsData);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Sync failed");
    } finally {
      setIsSyncing(false);
    }
  };

  const filteredSongs = useMemo(() => {
    return allSongs.filter(song => {
      if (
        filters.title &&
        !song.title.toLowerCase().includes(filters.title.toLowerCase())
      )
        return false;
      if (
        filters.artist &&
        !song.artist.toLowerCase().includes(filters.artist.toLowerCase())
      )
        return false;
      if (
        filters.album &&
        !song.album.toLowerCase().includes(filters.album.toLowerCase())
      )
        return false;
      if (filters.year && song.year !== parseInt(filters.year, 10))
        return false;
      if (filters.inGameOnly && !song.is_in_game) return false;
      return true;
    });
  }, [allSongs, filters]);

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const handleToggleInGame = async (psarcFilename: string) => {
    try {
      const result = await toggleInGame(psarcFilename);
      setAllSongs(prev =>
        prev.map(song =>
          song.psarc_filename === psarcFilename
            ? { ...song, is_in_game: result.is_in_game }
            : song
        )
      );
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to toggle in-game"
      );
    }
  };

  return (
    <div className="space-y-4">
      {/* Header + Sync */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            PSARC Library
          </h1>
          <p className="text-sm text-text-secondary">
            Browse and search all songs across PSARC files
          </p>
        </div>
        <button
          onClick={handleSync}
          disabled={isSyncing}
          className="rounded-md bg-neon-green px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isSyncing ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
              Syncing...
            </span>
          ) : (
            "Sync Directory"
          )}
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="PSARC Files"
          value={stats?.total_psarc_files}
          isLoading={isLoading}
          color="text-neon-blue"
        />
        <StatCard
          label="Songs"
          value={stats?.total_songs}
          isLoading={isLoading}
          color="text-neon-green"
        />
        <StatCard
          label="Failed Files"
          value={stats?.total_failed_files}
          isLoading={isLoading}
          color={
            stats?.total_failed_files ? "text-neon-red" : "text-text-secondary"
          }
        />
      </div>

      {/* Sync Result */}
      {syncResult && <SyncResultCard result={syncResult} />}

      {/* Filter Bar */}
      <div className="grid grid-cols-1 gap-3 rounded-lg border border-terminal-border bg-card p-4 sm:grid-cols-2 lg:grid-cols-6">
        <input
          type="text"
          placeholder="Title"
          value={filters.title}
          onChange={e => setFilters(f => ({ ...f, title: e.target.value }))}
          className="rounded-md border border-terminal-border bg-background px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:border-neon-blue"
        />
        <input
          type="text"
          placeholder="Artist"
          value={filters.artist}
          onChange={e => setFilters(f => ({ ...f, artist: e.target.value }))}
          className="rounded-md border border-terminal-border bg-background px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:border-neon-blue"
        />
        <input
          type="text"
          placeholder="Album"
          value={filters.album}
          onChange={e => setFilters(f => ({ ...f, album: e.target.value }))}
          className="rounded-md border border-terminal-border bg-background px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:border-neon-blue"
        />
        <input
          type="number"
          placeholder="Year"
          value={filters.year}
          onChange={e => setFilters(f => ({ ...f, year: e.target.value }))}
          className="rounded-md border border-terminal-border bg-background px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:border-neon-blue"
        />
        <label className="flex items-center gap-2 rounded-md border border-terminal-border bg-background px-3 py-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            checked={filters.inGameOnly}
            onChange={e =>
              setFilters(f => ({ ...f, inGameOnly: e.target.checked }))
            }
            className="accent-neon-green"
          />
          In Game Only
        </label>
        <button
          type="button"
          onClick={() =>
            setFilters({
              title: "",
              artist: "",
              album: "",
              year: "",
              inGameOnly: false,
            })
          }
          className="rounded-md border border-terminal-border px-4 py-2 text-sm text-text-secondary transition-colors hover:bg-background-tertiary"
        >
          Clear Filters
        </button>
      </div>

      {/* Results count */}
      <div className="text-sm text-text-secondary">
        {isLoading
          ? "Loading songs..."
          : `${filteredSongs.length.toLocaleString()} of ${allSongs.length.toLocaleString()} song${allSongs.length !== 1 ? "s" : ""}`}
      </div>

      {/* Results Table */}
      <div className="overflow-x-auto rounded-lg border border-terminal-border">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-terminal-border bg-background-secondary">
            <tr>
              <th className="px-4 py-3 font-medium text-text-secondary">
                Title
              </th>
              <th className="px-4 py-3 font-medium text-text-secondary">
                Artist
              </th>
              <th className="hidden px-4 py-3 font-medium text-text-secondary md:table-cell">
                Album
              </th>
              <th className="hidden px-4 py-3 font-medium text-text-secondary sm:table-cell">
                Year
              </th>
              <th className="hidden px-4 py-3 font-medium text-text-secondary lg:table-cell">
                Tuning
              </th>
              <th className="hidden px-4 py-3 font-medium text-text-secondary sm:table-cell">
                Duration
              </th>
              <th className="hidden px-4 py-3 font-medium text-text-secondary lg:table-cell">
                BPM
              </th>
              <th className="hidden px-4 py-3 font-medium text-text-secondary xl:table-cell">
                PSARC File
              </th>
              <th className="px-4 py-3 text-center font-medium text-text-secondary">
                In Game
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr
                  key={i}
                  className="border-b border-terminal-border last:border-b-0"
                >
                  {Array.from({ length: 9 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 w-24 animate-pulse rounded bg-background-tertiary" />
                    </td>
                  ))}
                </tr>
              ))
            ) : filteredSongs.length === 0 ? (
              <tr>
                <td
                  colSpan={9}
                  className="px-4 py-12 text-center text-text-muted"
                >
                  {allSongs.length === 0
                    ? "No songs found. Try syncing the directory."
                    : "No songs match the current filters."}
                </td>
              </tr>
            ) : (
              filteredSongs.map((song, i) => (
                <tr
                  key={`${song.dlc_key}-${song.psarc_filename}-${i}`}
                  className="border-b border-terminal-border transition-colors last:border-b-0 hover:bg-card-hover"
                >
                  <td className="px-4 py-3 font-medium text-text-primary">
                    {song.title}
                  </td>
                  <td className="px-4 py-3 text-text-secondary">
                    {song.artist}
                  </td>
                  <td className="hidden px-4 py-3 text-text-secondary md:table-cell">
                    {song.album}
                  </td>
                  <td className="hidden px-4 py-3 text-text-muted sm:table-cell">
                    {song.year}
                  </td>
                  <td className="hidden px-4 py-3 lg:table-cell">
                    <span className="rounded bg-background-tertiary px-2 py-0.5 font-mono text-xs text-neon-purple">
                      {formatTuning(song.tuning)}
                    </span>
                  </td>
                  <td className="hidden px-4 py-3 font-mono text-text-muted sm:table-cell">
                    {formatDuration(song.length)}
                  </td>
                  <td className="hidden px-4 py-3 font-mono text-text-muted lg:table-cell">
                    {song.tempo}
                  </td>
                  <td className="hidden px-4 py-3 xl:table-cell">
                    <span className="font-mono text-xs text-neon-cyan">
                      {song.psarc_filename}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleToggleInGame(song.psarc_filename)}
                      className="cursor-pointer"
                      title={song.is_in_game ? "In Game" : "Not In Game"}
                    >
                      <span
                        className={`inline-block h-2.5 w-2.5 rounded-full ${
                          song.is_in_game
                            ? "bg-neon-green"
                            : "bg-background-tertiary"
                        }`}
                      />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  isLoading,
  color,
}: {
  label: string;
  value: number | undefined;
  isLoading: boolean;
  color: string;
}) {
  return (
    <div className="rounded-lg border border-terminal-border bg-card p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
        {label}
      </p>
      {isLoading ? (
        <div className="mt-2 h-8 w-16 animate-pulse rounded bg-background-tertiary" />
      ) : (
        <p className={`mt-1 text-3xl font-bold ${color}`}>
          {value?.toLocaleString() ?? "—"}
        </p>
      )}
    </div>
  );
}

function SyncResultCard({ result }: { result: SyncResponse }) {
  const formatTimestamp = (ts: string) => {
    // Backend returns ISO with +00:00Z suffix — normalize before parsing
    const date = new Date(ts.replace(/\+00:00Z$/, "Z"));
    return isNaN(date.getTime()) ? ts : date.toLocaleString();
  };

  const metrics = [
    {
      label: "Processed",
      value: result.files_processed,
      color: "text-text-primary",
    },
    { label: "Added", value: result.files_added, color: "text-neon-green" },
    { label: "Failed", value: result.files_failed, color: "text-neon-red" },
    {
      label: "Skipped",
      value: result.files_skipped,
      color: "text-text-secondary",
    },
    {
      label: "Cleaned",
      value: result.files_cleaned,
      color: "text-neon-yellow",
    },
  ];

  return (
    <div className="rounded-lg border border-terminal-border bg-card p-5">
      <div className="mb-3 flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-neon-green" />
        <h3 className="text-sm font-semibold text-text-primary">
          Last Sync Result
        </h3>
        <span className="ml-auto font-mono text-xs text-text-muted">
          {formatTimestamp(result.timestamp)}
        </span>
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {metrics.map(m => (
          <div key={m.label} className="flex items-baseline gap-1.5">
            <span className={`font-mono text-lg font-bold ${m.color}`}>
              {m.value}
            </span>
            <span className="text-xs text-text-muted">{m.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
