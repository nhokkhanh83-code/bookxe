import React from "react";
import { formatBigInt } from "../lib/demoVault.js";

/** OraclePanel — Báo cáo tài chính từ bên thứ 3 (Verified) */
export default function OraclePanel({ v }) {
  const isDemo = v.isDemoMode;
  const data = isDemo ? v.demoData?.oracle : null;

  const renderDemo = () => {
    if (!data) return <div className="text-gray-500 text-center py-4">Đang tải dữ liệu...</div>;
    return (
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center">
            <svg className="w-4 h-4 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div>
            <h4 className="font-semibold text-dark-900">{data.operatorName}</h4>
            <p className="text-xs text-gray-500">{data.reportPeriod} • Verifier: {data.verifierAddress?.slice(0, 10)}...</p>
          </div>
          <span className="badge-emerald ml-auto">✓ {data.reportStatus === 3 ? "Đã xác minh" : data.reportStatus === 2 ? "Đang xử lý" : "Draft"}</span>
        </div>

        {/* Financial Data Grid */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
            <p className="text-xs text-gray-500 mb-1">Xe hoạt động</p>
            <p className="font-semibold text-dark-900">{data.totalVehicles} chiếc</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
            <p className="text-xs text-gray-500 mb-1">Doanh thu gộp</p>
            <p className="font-semibold text-dark-900 number-mono">{data.grossRevenue?.toLocaleString("vi-VN")} USDX</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
            <p className="text-xs text-gray-500 mb-1">Lợi nhuận ròng</p>
            <p className="font-semibold text-emerald-600 number-mono">{data.netProfit?.toLocaleString("vi-VN")} USDX</p>
          </div>
        </div>

        {/* Financial Summary */}
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Mức cam kết APY</h5>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold text-emerald-600">{(data.verifiedApyBps / 100).toFixed(2)}% / năm</p>
              <p className="text-xs text-gray-500 mt-1">APY thực tế - Simple Interest (Lãi đơn)</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">Auditor</p>
              <p className="font-semibold text-dark-900 text-sm">{data.auditorName}</p>
            </div>
          </div>
        </div>

        {/* Hash + Updated */}
        <div className="flex items-center justify-between text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
          <span className="font-mono">Report Hash: {data.reportHash}</span>
          <span>Cập nhật: {data.lastUpdated ? new Date(data.lastUpdated * 1000).toLocaleString("vi-VN") : "N/A"}</span>
        </div>

        {/* Simulate Oracle Update */}
        <button
          onClick={() => v.updateOracleDemo(1500, {
            grossRevenueUSD: 62000,
            operatingCostUSD: 42000,
            netProfitUSD: 20000,
            reportPeriod: "Q1 2027",
          })}
          className="w-full py-2.5 rounded-lg border border-dashed border-amber-300 text-amber-600 hover:bg-amber-50 transition-all font-semibold text-sm"
        >
          ⚙️ Mô phỏng Oracle cập nhật báo cáo mới
        </button>
      </div>
    );
  };

  return (
    <div className="glass-card p-5 rounded-xl">
      <h3 className="text-lg font-bold text-dark-900 mb-4 flex items-center gap-2">
        📊 Báo cáo tài chính từ bên thứ 3 (Verified)
      </h3>
      {isDemo ? renderDemo() : (
        <div className="text-center py-8">
          <p className="text-gray-500">Kết nối ví để xem báo cáo từ Oracle trên On-chain</p>
        </div>
      )}
    </div>
  );
}

// OraclePanel default export handled above
