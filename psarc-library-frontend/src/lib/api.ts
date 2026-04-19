import axios from "axios";
import { useEffect, useState } from "react";

import { getApiKey } from "@/lib/auth";
import type {
  HealthResponse,
  ListFailedPsarcResponse,
  ListPsarcDataResponse,
  LoginResponse,
  PsarcData,
  StatsResponse,
  SyncResponse,
  ToggleInGameResponse,
} from "@/lib/types";

// Determine the base URL based on environment
const getBaseURL = () => {
  if (typeof window === "undefined") return "";

  // In production static build, API is served from same origin
  if (process.env.NODE_ENV === "production") {
    return window.location.origin;
  }

  // In development, proxy to backend (handled by Next.js rewrites)
  return "";
};

// API client configuration
const api = axios.create({
  baseURL: getBaseURL() + "/api",
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor to include API key
api.interceptors.request.use(
  config => {
    const apiKey = getApiKey();
    if (apiKey) {
      config.headers["X-API-KEY"] = apiKey;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Health status type
export type HealthStatus = "online" | "offline" | "checking";

const extractErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      const errorData = error.response.data;

      if (errorData?.message) {
        return errorData.message;
      }

      if (errorData?.detail) {
        return typeof errorData.detail === "string"
          ? errorData.detail
          : JSON.stringify(errorData.detail);
      }

      return `Server error: ${error.response.status} ${error.response.statusText}`;
    } else if (error.request) {
      return "No response from server. Please check if the backend is running.";
    } else {
      return `Request failed: ${error.message}`;
    }
  }
  return "An unexpected error occurred";
};

// API functions
export const getHealth = async (): Promise<HealthResponse> => {
  try {
    const response = await api.get<HealthResponse>("/health");
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const login = async (apiKey: string): Promise<LoginResponse> => {
  try {
    const response = await api.get<LoginResponse>("/login", {
      headers: {
        "X-API-KEY": apiKey,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const listPsarcData = async (
  skip = 0,
  limit = 100
): Promise<ListPsarcDataResponse> => {
  try {
    const response = await api.get<ListPsarcDataResponse>("/psarc", {
      params: { skip, limit },
    });
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const fetchAllPsarcData = async (): Promise<PsarcData[]> => {
  const PAGE_LIMIT = 1000;
  const all: PsarcData[] = [];
  let skip = 0;

  while (true) {
    const response = await listPsarcData(skip, PAGE_LIMIT);
    all.push(...response.data);
    if (all.length >= response.total) break;
    skip += PAGE_LIMIT;
  }

  return all;
};

export const toggleInGame = async (
  filename: string
): Promise<ToggleInGameResponse> => {
  try {
    const response = await api.patch<ToggleInGameResponse>(
      "/psarc/toggle-in-game",
      null,
      { params: { filename } }
    );
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const syncPsarcDirectory = async (): Promise<SyncResponse> => {
  try {
    const response = await api.post<SyncResponse>("/sync");
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const listFailedPsarc = async (
  skip = 0,
  limit = 100
): Promise<ListFailedPsarcResponse> => {
  try {
    const response = await api.get<ListFailedPsarcResponse>("/failures", {
      params: { skip, limit },
    });
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const getStats = async (): Promise<StatsResponse> => {
  try {
    const response = await api.get<StatsResponse>("/stats");
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

// Health status hook
export function useHealthStatus(): HealthStatus {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        await getHealth();
        if (isMounted) {
          setStatus("online");
        }
      } catch {
        if (isMounted) {
          setStatus("offline");
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return status;
}

export default api;
