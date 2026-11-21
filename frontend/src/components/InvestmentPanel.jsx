import React, { useState, useMemo, useRef, useEffect } from "react";
import { useVault } from "../hooks/useVault.js";
import { formatBigInt, parseBigInt } from "../lib/demoVault.js";

/** InvestmentPanel — Panel đầu tư: Nạp/Rút/Nhận lãi/Rút toàn bộ */
export default function InvestmentPanel({ v }) {
  const isDemo = v.isDemoMode;
  const dd = v.demoData;
  const [activeTab, setActiveTab] = useState("deposit"); // deposit | withdraw
  const [amountInput, setAmountInput] = useState("");
  const [selectedPercent, setSelectedPercent] = useState("custom");
  const timeoutRef = useRef(null);

  // Get user info
  const userInfo = isDemo ? dd?.userInfo : null;
  const userPosition = isDemo ? (dd?.userInfo?.depositedAmount || 0n) : v.walletBalance;
  const balance = isDemo ? dd?.userBalance : v.walletBalance;
  // ethers v6 trả Promise khi gọi view method → phải ép về số, nếu không BigInt() sẽ ném lỗi
  const rawApy = isDemo ? dd?.apyBps : v.contracts?.oracle?.verifiedApyBps?.();
  const apyBps = Number.isFinite(Number(rawApy)) ? Number(rawApy) : 1200;
  const pendingYield = isDemo ? dd?.pendingYield : 0n;
  const claimedYield = isDemo ? userInfo?.claimedYield : 0n;

  // Tick for real-time update
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  // Calculate input amount
  const inputAmount = useMemo(() => parseBigInt(amountInput, 6), [amountInput]);

  // Calculate yield for projection (using input amount if deposit, or principal if withdraw)
  const projectedYield = useMemo(() => {
    const principal = activeTab === "deposit" ? inputAmount : userPosition;
    if (principal <= 0n) return 0n;
    // Simple interest: 1 year at current APY
    const oneYearSeconds = 365 * 24 * 3600;
    const elapsed = oneYearSeconds + (isDemo ? dd?.timeOffset || 0 : 0);
    return (principal * BigInt(apyBps) * BigInt(Math.floor(elapsed))) / (10000n * 365n * 24n * 3600n);
  }, [activeTab, inputAmount, userPosition, apyBps, isDemo, dd]);

  // Handle deposit
  const handleDeposit = () => {
    if (!inputAmount || inputAmount <= 0n) return;
    if (isDemo) v.depositDemo(inputAmount);
    else v.depositWallet(inputAmount);
    setAmountInput("");
    setSelectedPercent("custom");
  };

  // Handle withdraw
  const handleWithdraw = () => {
    if (!inputAmount || inputAmount <= 0n) return;
    if (isDemo) v.withdrawDemo(inputAmount);
    else v.withdrawWallet(inputAmount);
    setAmountInput("");
  };

  // Handle redeem
  const handleRedeem = () => {
    if (isDemo) v.redeemDemo();
    else v.redeemWallet();
  };

  // Handle claim — bị thiếu gây ReferenceError → trắng trang
  const handleClaim = () => {
    if (isDemo) v.claimYieldDemo();
    else v.claimYieldWallet();
  };

  // Quick percent buttons
  const handlePercent = (pct) => {
    const pctNum = pct === "MAX" ? 100 : Number(pct.replace("%", ""));
    const amount = balance > 0n ? (balance * BigInt(pctNum)) / 100n : 0n;
    setAmountInput(formatBigInt(amount, 6).replace(/,/g, ""));
    setSelectedPercent(pct);
  };

  // Clear timeout
  useEffect(() => () => clearTimeout(timeoutRef.current), []);

  return (
    <div className="glass-card p-5 rounded-xl">
      <h3 className="text-lg font-bold text-dark-900 mb-4 flex items-center gap-2">
        <i className="bi bi-wallet2 text-primary-blue"></i> Đầu tư & Nhận lãi
      </h3>

      {/* Tab Switcher */}
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1">
        <button
          onClick={() => setActiveTab("deposit")}
          className={`flex-1 px-4 py-2.5 rounded-md font-semibold text-sm transition-all ${
            activeTab === "deposit" ? "bg-white shadow text-blue-600" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <i className="bi bi-arrow-down-circle me-1"></i> Nạp tiền góp vốn
        </button>
        <button
          onClick={() => setActiveTab("withdraw")}
          className={`flex-1 px-4 py-2.5 rounded-md font-semibold text-sm transition-all ${
            activeTab === "withdraw" ? "bg-white shadow text-blue-600" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <i className="bi bi-arrow-up-circle me-1"></i> Rút vốn
        </button>
      </div>

      {/* Quick Percentage Buttons (Deposit Only) */}
      {isDemo && activeTab === "deposit" && balance > 0n && (
        <div className="flex gap-2 mb-4">
          {["25%", "50%", "MAX"].map((pct) => (
            <button
              key={pct}
              onClick={() => handlePercent(pct)}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-semibold border transition-all ${
                selectedPercent === pct
                  ? "bg-blue-50 text-blue-600 border-blue-300"
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
              }`}
            >
              {pct === "MAX" ? `MAX (${formatBigInt(balance, 6)})` : pct}
            </button>
          ))}
        </div>
      )}

      {/* Amount Input */}
      <div className="relative mb-4">
        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
          Số tiền USDX ({isDemo ? formatBigInt(balance, 6) : "Số dư"})
        </label>
        <div className="relative">
          <input
            type="text"
            placeholder={`Ví dụ: 1,000 USDX`}
            value={amountInput}
            onChange={(e) => {
              setAmountInput(e.target.value);
              setSelectedPercent("custom");
            }}
            className="input-styled pr-20 font-mono text-lg"
            disabled={v.loading}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-medium">USDX</div>
        </div>
        {isDemo && activeTab === "deposit" && balance > 0n && inputAmount > balance && (
          <p className="text-xs text-red-500 mt-1">⚠️ Vượt quá số dư ví! Tối đa: {formatBigInt(balance, 6)}</p>
        )}
      </div>

      {/* Auto-calc Section */}
      {isDemo && userPosition > 0n && (
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 mb-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            📊 Bảng tính nhẩm lợi nhuận tự động
          </h4>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Tỷ lệ sở hữu đội xe:</span>
              <span className="text-sm font-semibold text-dark-900">
                {((dd?.userInfo?.ownershipBps || 0) / 100).toFixed(2)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Lãi ước tính 1 năm:</span>
              <span className="text-sm font-semibold text-emerald-600 number-mono">
                {formatBigInt(projectedYield, 6)} USDX
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Lãi mỗi tháng:</span>
              <span className="text-sm font-semibold text-emerald-600 number-mono">
                {formatBigInt(projectedYield / 12n, 6)} USDX
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Số dư lãi đang tích lũy:</span>
              <span className="text-sm font-semibold text-emerald-600 number-mono">
                {formatBigInt(dd?.userInfo?.unclaimedYield || 0n, 6)} USDX
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="space-y-3">
        {activeTab === "deposit" ? (
          <>
            <button
              onClick={handleDeposit}
              disabled={v.loading || !inputAmount || inputAmount <= 0n || (isDemo && inputAmount > balance)}
              className="w-full py-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-base transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30"
            >
              {v.loading ? "Đang xử lý..." : "✅ Nạp tiền góp vốn"}
            </button>

            {isDemo && (
              <button
                onClick={() => v.fastForwardDemo(365 * 24 * 3600)}
                className="w-full py-3 rounded-lg border-2 border-dashed border-amber-300 text-amber-600 font-semibold text-sm hover:border-amber-400 hover:bg-amber-50 transition-all"
              >
                ⏰ Tua thời gian +1 năm để test nhận lãi
              </button>
            )}

            <button
              onClick={handleClaim}
              disabled={v.loading || pendingYield <= 0n}
              className={`w-full py-3 rounded-lg border-2 transition-all font-semibold text-sm ${
                pendingYield > 0n
                  ? "border-emerald-400 text-emerald-600 hover:bg-emerald-50 bg-emerald-50/50"
                  : "border-gray-200 text-gray-400 cursor-not-allowed"
              }`}
            >
              🌿 Nhận lãi APY
              {pendingYield > 0n && (
                <span className="ml-2">— {formatBigInt(pendingYield, 6)} USDX khả dụng</span>
              )}
            </button>
          </>
        ) : (
          <>
            <button
              onClick={handleWithdraw}
              disabled={v.loading || !inputAmount || inputAmount <= 0n || (isDemo && inputAmount > userPosition)}
              className="w-full py-4 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-base transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/20"
            >
              {v.loading ? "Đang xử lý..." : "💸 Rút vốn ra ví"}
            </button>

            <button
              onClick={handleRedeem}
              disabled={v.loading || userPosition <= 0n}
              className="w-full py-3 rounded-lg border-2 border-red-300 text-red-600 font-semibold text-sm hover:bg-red-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              🚫 Rút toàn bộ vốn (Redeem)
            </button>
          </>
        )}
      </div>

      {/* Total Yield Info */}
      {isDemo && userPosition > 0n && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">Lãi đã nhận:</span>
            <span className="font-semibold text-emerald-600 number-mono">
              {formatBigInt(claimedYield, 6)} USDX
            </span>
          </div>
          <div className="flex justify-between items-center text-sm mt-2">
            <span className="text-gray-600">Ngày đồng thời:</span>
            <span className="text-gray-500">
              {userInfo?.maturityDate ? new Date(userInfo.maturityDate * 1000).toLocaleDateString('vi-VN') : "N/A"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// InvestmentPanel default export handled above
