import React from "react";
import { formatBigInt } from "../lib/demoVault.js";

/** Header: Logo, Network, Faucet, USDX Balance, Connect/Disconnect */
export default function Header({ v }) {
  const isDemo = v.isDemoMode;
  const dd = v.demoData;

  const networkBadge = (
    <span className={`badge-emerald ${isDemo ? "bg-amber-50 text-amber-600 border-amber-200" : ""}`}>
      <span className="w-2 h-2 rounded-full bg-current inline-block"></span>
      {isDemo ? "Demo Mode" : `Ví: ${v.chainName}`}
    </span>
  );

  const displayBalance = isDemo
    ? formatBigInt(dd?.userBalance || 0n, 6)
    : v.walletBalance.toString();

  return (
    <header className="glass-card sticky top-0 z-50 border-b-2 border-gray-100 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center shadow-lg">
              <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M9 17V22" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M15 22V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M9 12v5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M15 12v5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M15 12h-6M15 7h-6M9 7H3M9 12H3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-dark-900 tracking-tight">BookXe RWA Vault</h1>
              <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">
                Cho thuê Xe máy & Ô tô Đà Nẵng · RWA Investment
              </p>
            </div>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            {/* Faucet Button */}
            <button
              onClick={isDemo ? v.faucetDemo : v.faucetWallet}
              disabled={v.loading || (isDemo && dd?.userBalance > 0n)}
              className={`px-4 py-2.5 rounded-lg font-semibold text-sm text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
            >
              {v.loading ? (
                <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <span><i className="bi bi-download me-1"></i>Nhận 10,000 USDX miễn phí</span>
              )}
            </button>

            {/* Balance */}
            <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gray-100 border border-gray-200 font-mono text-lg font-semibold text-dark-900">
              <span className="text-gray-500 text-sm font-normal">USDX:</span>
              <span className="number-mono">{displayBalance}</span>
            </div>

            {/* Network Badge */}
            {networkBadge}

            {/* Connect / Disconnect */}
            {isDemo ? (
              <button
                onClick={v.connectWallet}
                className="px-4 py-2.5 rounded-lg font-semibold text-sm text-dark-700 bg-white border-2 border-gray-200 hover:border-blue-500 hover:text-blue-600 transition-all"
              >
                ⚡ Connect Wallet
              </button>
            ) : (
              <button
                onClick={v.disconnectWallet}
                className="px-4 py-2.5 rounded-lg font-semibold text-sm text-gray-600 bg-white border-2 border-gray-200 hover:border-gray-400 transition-all"
              >
                Disconnect
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

// Header default export handled above
