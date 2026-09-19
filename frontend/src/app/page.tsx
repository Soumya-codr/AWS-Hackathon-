"use client";

import React, { useState } from "react";
import GlobalHeader from "@/components/GlobalHeader";
import PRGatekeeperTab from "@/components/PRGatekeeperTab";
import CedarPolicyStudioTab from "@/components/CedarPolicyStudioTab";
import AuditLedgerTab from "@/components/AuditLedgerTab";

export default function Home() {
  const [activeTab, setActiveTab] = useState("pr-gatekeeper");

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-300">
      {/* Sleek Minimalist SaaS Header */}
      <GlobalHeader activeTab={activeTab} setActiveTab={setActiveTab} prBlockedCount={2} />

      {/* Main Spacious Content */}
      <main className="w-full pt-16 pb-16 flex-1 flex flex-col">
        {activeTab === "pr-gatekeeper" && <PRGatekeeperTab />}
        {activeTab === "cedar-studio" && <CedarPolicyStudioTab />}
        {activeTab === "audit-ledger" && <AuditLedgerTab />}
      </main>
    </div>
  );
}
