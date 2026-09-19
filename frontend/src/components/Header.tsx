"use client";

import React, { useEffect, useState } from "react";
import {
  Shield,
  Cpu,
  Boxes,
  DollarSign,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { fetchHealth, HealthResponse } from "@/lib/api";

export default function Header() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadHealth = async () => {
    try {
      setLoading(true);
      const data = await fetchHealth();
      setHealth(data);
    } catch {
      // Fallback display if server is starting
      setHealth({
        status: "OFFLINE",
        version: "0.1.0",
        cedar_engine: "STANDBY",
        moto_simulation: "STANDBY",
        ollama_status: "DISCONNECTED",
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 30000); // 30s poll
    return () => clearInterval(interval);
  }, []);

  const isCedarReady = health?.cedar_engine.includes("READY");
  const isOllamaConnected = health?.ollama_status.includes("CONNECTED");

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Title & Tagline */}
        <div className="flex items-center space-x-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 shadow-lg shadow-indigo-500/20">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold tracking-tight text-white">
                CloudSentinel
              </h1>
              <span className="rounded-full bg-cyan-500/10 px-2 py-0.5 text-[10px] font-medium text-cyan-400 border border-cyan-500/20">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-zinc-400">
              Zero-Trust AI-Generated IaC Security Gatekeeper
            </p>
          </div>
        </div>

        {/* System Status Badges */}
        <div className="flex items-center gap-2.5">
          {/* Cedar Engine Status */}
          <div className="flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900/90 px-3 py-1.5 shadow-sm">
            <span className="relative flex h-2 w-2">
              <span
                className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
                  isCedarReady ? "bg-emerald-400" : "bg-amber-400"
                }`}
              />
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  isCedarReady ? "bg-emerald-500" : "bg-amber-500"
                }`}
              />
            </span>
            <Shield className="h-3.5 w-3.5 text-zinc-400" />
            <div className="text-xs">
              <span className="font-medium text-zinc-300">Cedar Engine: </span>
              <span
                className={`font-semibold ${
                  isCedarReady ? "text-emerald-400" : "text-amber-400"
                }`}
              >
                {isCedarReady ? "Online (Rust)" : "Standby"}
              </span>
            </div>
          </div>

          {/* Ollama Local Model Status */}
          <div className="flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900/90 px-3 py-1.5 shadow-sm">
            <span className="relative flex h-2 w-2">
              <span
                className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
                  isOllamaConnected ? "bg-cyan-400" : "bg-zinc-500"
                }`}
              />
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  isOllamaConnected ? "bg-cyan-500" : "bg-zinc-500"
                }`}
              />
            </span>
            <Cpu className="h-3.5 w-3.5 text-zinc-400" />
            <div className="text-xs">
              <span className="font-medium text-zinc-300">Ollama Model: </span>
              <span
                className={`font-semibold ${
                  isOllamaConnected ? "text-cyan-400" : "text-zinc-400"
                }`}
              >
                {isOllamaConnected ? "gemma4:latest" : "Deterministic Mode"}
              </span>
            </div>
          </div>

          {/* Sandbox Status */}
          <div className="flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900/90 px-3 py-1.5 shadow-sm">
            <Boxes className="h-3.5 w-3.5 text-purple-400" />
            <div className="text-xs">
              <span className="font-medium text-zinc-300">Sandbox: </span>
              <span className="font-semibold text-purple-400">Moto / SAM Ready</span>
            </div>
          </div>

          {/* Billing Risk Badge */}
          <div className="flex items-center gap-1.5 rounded-md border border-emerald-500/20 bg-emerald-950/30 px-3 py-1.5 text-xs text-emerald-400">
            <DollarSign className="h-3.5 w-3.5" />
            <span className="font-semibold">Zero Billing Risk ($0.00)</span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={loadHealth}
            title="Refresh System Health"
            className="flex h-8 w-8 items-center justify-center rounded-md border border-zinc-800 bg-zinc-900 text-zinc-400 transition hover:bg-zinc-800 hover:text-white"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>
    </header>
  );
}
