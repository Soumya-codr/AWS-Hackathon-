"use client";

import React from "react";
import {
  LayoutDashboard,
  ShieldCheck,
  Cpu,
  Boxes,
  Settings,
  Lock,
  Terminal,
  ExternalLink,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
}

export default function Sidebar({ activeTab, onSelectTab }: SidebarProps) {
  const navigationItems = [
    {
      id: "dashboard",
      name: "Dashboard",
      icon: LayoutDashboard,
      badge: "Live",
    },
    {
      id: "scans",
      name: "Infrastructure Scans",
      icon: ShieldCheck,
      badge: "Cedar",
    },
    {
      id: "agents",
      name: "Agent Swarm Live Feed",
      icon: Cpu,
      badge: "Strands",
    },
    {
      id: "sandbox",
      name: "Sandbox Simulation",
      icon: Boxes,
      badge: "Moto/SAM",
    },
    {
      id: "settings",
      name: "Settings & Policies",
      icon: Settings,
    },
  ];

  return (
    <aside className="flex h-[calc(100vh-4rem)] w-64 flex-col justify-between border-r border-zinc-800/80 bg-zinc-950/60 p-4">
      {/* Navigation Links */}
      <div className="space-y-6">
        <div>
          <p className="px-3 text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
            Platform Navigation
          </p>
          <nav className="mt-2 space-y-1">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-xs font-medium transition-all ${
                    isActive
                      ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/30 shadow-sm shadow-indigo-500/10"
                      : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${isActive ? "text-indigo-400" : "text-zinc-400"}`} />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                        isActive
                          ? "bg-indigo-500/20 text-indigo-300"
                          : "bg-zinc-800/80 text-zinc-400"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Security Posture Status Widget */}
        <div className="rounded-xl border border-zinc-800/90 bg-zinc-900/50 p-3.5 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
            <Lock className="h-3.5 w-3.5 text-emerald-400" />
            <span>Fail-Closed Gatekeeper</span>
          </div>
          <p className="mt-1.5 text-[11px] leading-relaxed text-zinc-400">
            Static authorization halts any critical violation before reaching cloud simulation.
          </p>
          <div className="mt-2.5 flex items-center justify-between border-t border-zinc-800 pt-2 text-[10px]">
            <span className="text-zinc-400">Policy Mode:</span>
            <span className="font-semibold text-emerald-400">AWS Cedar Zero-Trust</span>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="border-t border-zinc-800/80 pt-3">
        <div className="flex items-center justify-between text-[11px] text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Terminal className="h-3.5 w-3.5 text-zinc-400" />
            <span>CLI Version 0.1.0</span>
          </span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 hover:text-indigo-400"
          >
            <span>API Docs</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </aside>
  );
}
