"use client";

import React from "react";
import { ShieldCheck, GitPullRequest, Sliders, PlayCircle, GitBranch } from "lucide-react";

interface GlobalHeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  prBlockedCount?: number;
}

export default function GlobalHeader({
  activeTab,
  setActiveTab,
  prBlockedCount = 2,
}: GlobalHeaderProps) {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 bg-zinc-950/80 backdrop-blur-md border-b border-zinc-800/80">
      <div className="max-w-7xl mx-auto h-full px-6 flex items-center justify-between">
        {/* Left: Brand & Repo Context */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-semibold text-sm tracking-tight text-zinc-100">
                CloudSentinel
              </span>
              <span className="text-[11px] font-mono text-zinc-400">enterprise</span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-400">
            <GitBranch className="w-3.5 h-3.5 text-zinc-400" />
            <span className="font-mono text-zinc-300">acme-corp/infra</span>
            <span className="text-zinc-600">/</span>
            <span className="font-mono text-zinc-400">main</span>
          </div>
        </div>

        {/* Center: Clean Segmented Navigation */}
        <nav className="flex items-center p-1 rounded-lg bg-zinc-900/90 border border-zinc-800 text-xs">
          <button
            onClick={() => setActiveTab("pr-gatekeeper")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md font-medium transition-all cursor-pointer ${
              activeTab === "pr-gatekeeper"
                ? "bg-zinc-800 text-zinc-100 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <GitPullRequest className="w-3.5 h-3.5 text-emerald-400" />
            <span>Interactive PR Gatekeeper</span>
            {prBlockedCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-rose-500/20 text-rose-300 font-mono text-[10px] font-semibold border border-rose-500/30">
                {prBlockedCount} Blocked
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("cedar-studio")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md font-medium transition-all cursor-pointer ${
              activeTab === "cedar-studio"
                ? "bg-zinc-800 text-zinc-100 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            <span>Cedar Policies (6 Rules)</span>
          </button>

          <button
            onClick={() => setActiveTab("audit-ledger")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md font-medium transition-all cursor-pointer ${
              activeTab === "audit-ledger"
                ? "bg-zinc-800 text-zinc-100 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <PlayCircle className="w-3.5 h-3.5 text-amber-400" />
            <span>IaC Playground</span>
          </button>
        </nav>

        {/* Right: Engine Telemetry Beacon */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-mono text-[11px] font-medium">Rust Cedar & Ollama Active</span>
          </div>

          <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-mono text-zinc-300">
            SO
          </div>
        </div>
      </div>
    </header>
  );
}
