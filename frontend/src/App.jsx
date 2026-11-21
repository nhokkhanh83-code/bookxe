import React from "react";
import { useVault } from "./hooks/useVault.js";
import Header from "./components/Header.jsx";
import StatCard from "./components/StatCard.jsx";
import FleetAssets from "./components/FleetAssets.jsx";
import OraclePanel from "./components/OraclePanel.jsx";
import InvestmentPanel from "./components/InvestmentPanel.jsx";
import TxHistory from "./components/TxHistory.jsx";
import { formatBigInt } from "./lib/demoVault.js";

function App() {
  const v = useVault();
  const isDemo = v.isDemoMode;
  const dd = v.demoData;

  // Calculate TVL percent
  const tvlPercent = isDemo ? (dd?.totalDeposited > 0n
    ? Math.min(Number((dd.totalDeposited * 10000n) / BigInt(dd?.targetCap || 300000n * 1000000n)) / 100, 100)
    : 0) : 0;

  const progressWidth = Math.min(tvlPercent, 100);

  return (
    <div className="min-h-screen bg-gray-100">
      <Header v={v} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Transaction Status Message */}
        {v.txStatus && (
          <div className={`mb-6 px-4 py-3 rounded-lg border ${
            v.txStatus.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-700"
              : v.txStatus.type === "error"
              ? "bg-red-50 border-red-200 text-red-700"
              : "bg-amber-50 border-amber-200 text-amber-700"
          }`}>
            <p className="font-medium">{v.txStatus.message}</p>
          </div>
        )}

        {/* ============================================================
           A. OVERVIEW CARDS
        ============================================================ */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          {/* 1. Total Value Locked */}
          <StatCard
            title="Total Value Locked (TVL)"
            value={isDemo ? formatBigInt(dd?.totalDeposited || 0n, 6) : v.walletBalance.toString()}
            subtitle={{ text: `${progressWidth}% / 300,000 USDX`, className: "text-gray-500" }}
            icon={
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="18" width="20" height="4" rx="1" />
                <rect x="6" y="14" width="12" height="4" rx="1" />
                <rect x="10" y="10" width="4" height="4" rx="1" />
                <rect x="2" y="6" width="20" height="4" rx="1" />
              </svg>
            }
            iconBg="bg-blue-50"
            iconColor="text-blue-600"
          >
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full progress-bar" style={{ width: `${progressWidth}%` }} />
            </div>
          </StatCard>

          {/* 2. Current APY */}
          <StatCard
            title="Verified APY"
            value={`${(isDemo ? dd?.apyBps : v.contracts?.oracle?.verifiedApyBps?.() ?? 1200) / 100}% / year`}
            subtitle={{ text: "Audited & Verified", className: "text-emerald-600 font-semibold" }}
            icon={
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M12 8v4l2 2" />
                <path d="M8 14h8" />
              </svg>
            }
            iconBg="bg-emerald-50"
            iconColor="text-emerald-600"
            badge={
              <span className="badge-emerald">
                ✅ Verified by Oracle
              </span>
            }
          />

          {/* 3. Annualized Return */}
          <StatCard
            title="Annualized Return"
            value={`${isDemo ? (dd?.apyBps || 1200) / 100 : (v.contracts?.oracle?.verifiedApyBps?.() ?? 1200) / 100}% per year`}
            subtitle={{ text: "Simple Interest (No Compound)", className: "text-gray-500" }}
            icon={
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="23 6 13.5 15.5 8.5 15.5 1 15.5" />
                <polyline points="17 3 23 6 17 9" />
              </svg>
            }
            iconBg="bg-emerald-50"
            iconColor="text-emerald-600"
          />

          {/* 4. Investor Position */}
          <StatCard
            title="Investor Position"
            value={isDemo ? formatBigInt(dd?.userInfo?.depositedAmount || 0n, 6) : formatBigInt(v.walletBalance, 6)}
            subtitle={{
              text: `Ownership: ${isDemo ? ((dd?.userInfo?.ownershipBps || 0) / 100).toFixed(2) : 0}%`,
              className: "text-gray-500"
            }}
            icon={
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            }
            iconBg="bg-gray-50"
            iconColor="text-gray-600"
          />
        </div>

        {/* ============================================================
           B. INVESTOR POSITION DETAILS + INVESTMENT PANEL
        ============================================================ */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Left Column: Investment Panel */}
          <div className="lg:col-span-2 space-y-6">
            {/* Vault Header */}
            <div className="glass-card p-4 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" />
                    <path d="M2 17L12 22L22 17" />
                    <path d="M2 12L12 17L22 12" />
                  </svg>
                </div>
                <div>
                  <h2 className="font-bold text-dark-900">{isDemo ? dd?.vaultName : "BookXe Partner Fleet Vault #01 — Đội xe Đà Nẵng"}</h2>
                  <p className="text-xs text-gray-500">{isDemo ? "Demo — Cho thuê xe máy & ô tô tại Đà Nẵng" : "Real-time Yield Vault"}</p>
                </div>
              </div>
              <span className="badge-emerald">
                {isDemo ? "🆓 Demo Mode" : "🔗 On-Chain Vault"}
              </span>
            </div>

            <InvestmentPanel v={v} />
            <FleetAssets />
          </div>

          {/* Right Column: Oracle Panel + Tx History */}
          <div className="space-y-6">
            <OraclePanel v={v} />
            <TxHistory v={v} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
