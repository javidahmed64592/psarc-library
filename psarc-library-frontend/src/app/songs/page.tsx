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
      return `${tuning.root} Custom`;
  }
};

const compareTunings = (a: Tuning, b: Tuning): number => {
  // Root note order: E, Eb, D, Db, C, B, Bb, A, Ab, G, Gb, F
  const rootOrder = [
    "E",
    "Eb",
    "D",
    "Db",
    "C",
    "B",
    "Bb",
    "A",
    "Ab",
    "G",
    "Gb",
    "F",
  ];
  const rootCmp = rootOrder.indexOf(a.root) - rootOrder.indexOf(b.root);
  if (rootCmp !== 0) return rootCmp;

  // Type order: Drop, Standard, Custom
  const typeOrder = ["Drop", "Standard", "Custom"];
  return typeOrder.indexOf(a.type) - typeOrder.indexOf(b.type);
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
    inGameFilter: "all" as "all" | "in-game" | "not-in-game",
  });
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else {
        setSortColumn(null);
        setSortDirection("asc");
      }
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

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
    const filtered = allSongs.filter(song => {
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
      if (filters.inGameFilter === "in-game" && !song.is_in_game) return false;
      if (filters.inGameFilter === "not-in-game" && song.is_in_game)
        return false;
      return true;
    });

    if (!sortColumn) return filtered;

    return [...filtered].sort((a, b) => {
      let cmp = 0;
      switch (sortColumn) {
        case "title":
          cmp = a.title.localeCompare(b.title);
          break;
        case "artist":
          cmp = a.artist.localeCompare(b.artist);
          break;
        case "album":
          cmp = a.album.localeCompare(b.album);
          break;
        case "year":
          cmp = a.year - b.year;
          break;
        case "tuning":
          cmp = compareTunings(a.tuning, b.tuning);
          break;
        case "duration":
          cmp = a.length - b.length;
          break;
        case "bpm":
          cmp = a.tempo - b.tempo;
          break;
        case "psarc":
          cmp = a.psarc_filename.localeCompare(b.psarc_filename);
          break;
        case "inGame":
          cmp = Number(a.is_in_game) - Number(b.is_in_game);
          break;
      }
      return sortDirection === "desc" ? -cmp : cmp;
    });
  }, [allSongs, filters, sortColumn, sortDirection]);

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
        <select
          value={filters.inGameFilter}
          onChange={e =>
            setFilters(f => ({
              ...f,
              inGameFilter: e.target.value as "all" | "in-game" | "not-in-game",
            }))
          }
          className="rounded-md border border-terminal-border bg-background px-3 py-2 text-sm text-text-primary outline-none focus:border-neon-blue"
        >
          <option value="all">All Songs</option>
          <option value="in-game">In Game Only</option>
          <option value="not-in-game">Not In Game</option>
        </select>
        <button
          type="button"
          onClick={() => {
            setFilters({
              title: "",
              artist: "",
              album: "",
              year: "",
              inGameFilter: "all",
            });
            setSortColumn(null);
            setSortDirection("asc");
          }}
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
              <SortableHeader
                label="Title"
                column="title"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                label="Artist"
                column="artist"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                label="Album"
                column="album"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                className="hidden md:table-cell"
              />
              <SortableHeader
                label="Year"
                column="year"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                className="hidden sm:table-cell"
              />
              <SortableHeader
                label="Tuning"
                column="tuning"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                className="hidden lg:table-cell"
              />
              <SortableHeader
                label="Duration"
                column="duration"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                className="hidden sm:table-cell"
              />
              <SortableHeader
                label="BPM"
                column="bpm"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                className="hidden lg:table-cell"
              />
              <SortableHeader
                label="PSARC File"
                column="psarc"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                className="hidden xl:table-cell"
              />
              <SortableHeader
                label="In Game"
                column="inGame"
                sortColumn={sortColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                align="center"
              />
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
                  <td className="hidden w-16 px-4 py-3 text-text-muted sm:table-cell">
                    {song.year}
                  </td>
                  <td className="hidden w-32 px-4 py-3 lg:table-cell">
                    <span className="whitespace-nowrap rounded bg-background-tertiary px-2 py-0.5 font-mono text-xs text-neon-purple">
                      {formatTuning(song.tuning)}
                    </span>
                  </td>
                  <td className="hidden w-20 px-4 py-3 font-mono text-text-muted sm:table-cell">
                    {formatDuration(song.length)}
                  </td>
                  <td className="hidden w-16 px-4 py-3 font-mono text-text-muted lg:table-cell">
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

function SortableHeader({
  label,
  column,
  sortColumn,
  sortDirection,
  onSort,
  className = "",
  align = "left",
}: {
  label: string;
  column: string;
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  className?: string;
  align?: "left" | "center";
}) {
  const isActive = sortColumn === column;
  return (
    <th
      className={`px-4 py-3 font-medium text-text-secondary ${className} ${align === "center" ? "text-center" : ""}`}
    >
      <button
        onClick={() => onSort(column)}
        className={`inline-flex cursor-pointer items-center gap-1 transition-colors hover:text-text-primary ${
          isActive ? "text-neon-blue" : ""
        }`}
      >
        {label}
        <span className="text-xs">
          {isActive ? (sortDirection === "asc" ? "▲" : "▼") : "⇅"}
        </span>
      </button>
    </th>
  );
}
