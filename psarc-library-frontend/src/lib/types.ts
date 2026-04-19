// TypeScript types matching FastAPI Pydantic models

// Base response types
export interface BaseResponse {
  message: string;
  timestamp: string;
}

// Authentication types
export interface AuthContextType {
  apiKey: string | null;
  isAuthenticated: boolean;
  login: (apiKey: string) => Promise<void>;
  logout: () => void;
}

// Response types
export interface HealthResponse extends BaseResponse {}

export interface LoginResponse extends BaseResponse {}

// Tuning types
export type TuningRoot =
  | "E"
  | "F"
  | "Gb"
  | "G"
  | "Ab"
  | "A"
  | "Bb"
  | "B"
  | "C"
  | "Db"
  | "D"
  | "Eb";

export type TuningType = "Standard" | "Drop" | "Custom";

export interface Tuning {
  root: TuningRoot;
  type: TuningType;
}

// Song data
export interface SongData {
  title: string;
  artist: string;
  album: string;
  year: number;
  tuning: Tuning;
  length: number;
  tempo: number;
  dlc: boolean;
  dlc_key: string;
}

// PSARC data
export interface PsarcData {
  filename: string;
  entries: SongData[];
  iteration_version: number;
  model_name: string;
  is_in_game: boolean;
}

// Flattened song row with associated PSARC metadata
export interface SongRow extends SongData {
  psarc_filename: string;
  is_in_game: boolean;
}

// Failed PSARC entry
export interface FailedPsarcEntry {
  filename: string;
  filepath: string;
  error_type: string;
  error_message: string;
  timestamp: string;
  file_size: number | null;
  raw_data: string | null;
}

// API Response types
export interface GetPsarcDataResponse extends BaseResponse {
  data: PsarcData;
  psarc_id: number;
}

export interface ListPsarcDataResponse extends BaseResponse {
  data: PsarcData[];
  total: number;
  skip: number;
  limit: number;
}

export interface SearchSongsResponse extends BaseResponse {
  data: SongData[];
  total: number;
}

export interface StatsResponse extends BaseResponse {
  total_psarc_files: number;
  total_songs: number;
  total_failed_files: number;
}

export interface SyncResponse extends BaseResponse {
  files_processed: number;
  files_added: number;
  files_failed: number;
  files_skipped: number;
  files_cleaned: number;
}

export interface ValidatePsarcResponse extends BaseResponse {
  filename: string;
  is_valid: boolean;
  data: PsarcData | null;
  error: FailedPsarcEntry | null;
}

export interface ListFailedPsarcResponse extends BaseResponse {
  data: FailedPsarcEntry[];
  total: number;
  skip: number;
  limit: number;
}

export interface ToggleInGameResponse extends BaseResponse {
  filename: string;
  is_in_game: boolean;
}
