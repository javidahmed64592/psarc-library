"use client";

import { useState } from "react";
import toast from "react-hot-toast";

import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const [apiKey, setApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      toast.error("Please enter an API key");
      return;
    }

    setIsLoading(true);
    try {
      await login(apiKey.trim());
      toast.success("Authenticated successfully");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Authentication failed"
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="w-full max-w-md rounded-lg border border-terminal-border bg-card p-8">
        <div className="mb-6 text-center">
          <h1 className="mb-2 text-2xl font-bold text-text-primary">
            PSARC Library
          </h1>
          <p className="font-mono text-sm text-text-secondary">
            <span className="text-neon-green">$</span> authenticate --api-key
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="apiKey"
              className="mb-1 block text-sm font-medium text-text-secondary"
            >
              API Key
            </label>
            <input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="Enter your API key"
              className="w-full rounded-md border border-terminal-border bg-background px-4 py-2.5 font-mono text-sm text-text-primary placeholder-text-muted outline-none transition-colors focus:border-neon-blue"
              disabled={isLoading}
              autoFocus
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !apiKey.trim()}
            className="w-full rounded-md bg-neon-blue px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isLoading ? "Authenticating..." : "Connect"}
          </button>
        </form>

        <p className="mt-4 text-center font-mono text-xs text-text-muted">
          Generate a token with{" "}
          <code className="text-neon-green">uv run generate-new-token</code>
        </p>
      </div>
    </div>
  );
}
