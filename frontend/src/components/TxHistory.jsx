import React from "react";
import { formatBigInt } from "../lib/demoVault.js";

/** TxHistory — Lịch sử giao dịch */
export default function TxHistory({ v }) {
  const isDemo = v.isDemoMode;
  const txs = isDemo ? v.demoData?.transactions || [] : [];

  const typeConfig = {
    deposit: { color: "bg-blue-50 text-blue-600", icon: "↓", label: "Nạp" },
    claim: { color: "bg-emerald-50 text-emerald-600", icon: "🌿", label: "Nhận lãi" },
    withdraw: { color: "bg-emerald-50 text-emerald-600", icon: "💸", label: "Rút vốn" },
    redeem: { color: "bg-red-50 text-red-600", icon: "🔄", label: "Rút toàn bộ" },
    oracle: { color: "bg-amber-50 text-amber-600", icon: "⚙️", label: "Oracle" },
    "oracle-update": { color: "bg-amber-50 text-amber-600", icon: "⚙️", label: "Oracle" },
    time: { color: "bg-amber-50 text-amber-600", icon: "⏰", label: "Tua thời gian" },
    "time-advance": { color: "bg-amber-50 text-amber-600", icon: "⏰", label: "Tua thời gian" },
    faucet: { color: "bg-blue-50 text-blue-600", icon: "💧", label: "Faucet" },
  };

  return (
    <div className="glass-card p-5 rounded-xl">
      <h3 className="text-lg font-bold text-dark-900 mb-4 flex items-center gap-2">
        📜 Lịch sử giao dịch
      </h3>

      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
        {txs.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">Chưa có giao dịch. Bấm Faucet hoặc Nạp tiền để bắt đầu!</p>
          </div>
        ) : (
          txs.map((tx) => {
            const config = typeConfig[tx.type] || typeConfig.oracle;
            return (
              <div key={tx.id} className={`flex items-center gap-3 p-3 rounded-lg border-b border-gray-100 last:border-b-0`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${config.color}`}>
                  {config.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-dark-900">{tx.desc}</p>
                  <p className="text-xs text-gray-400">{tx.time}</p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono text-gray-400">{tx.hash.slice(0, 12)}...</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// TxHistory default export handled above
