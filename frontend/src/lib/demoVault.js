// ============================================================
// DemoVault — Pure JavaScript Simulation of VehicleRWAVault
// BookXe RWA Fleet Investment Vault — Simple Interest Model
// ============================================================

const YEAR_SECONDS = BigInt(365 * 24 * 3600);

export class DemoVault {
  constructor() {
    // Vault config
    this.vaultName = "BookXe Partner Fleet Vault #01 — Đội xe Đà Nẵng";
    this.targetCap = 300000n * 1000000n; // 300,000 USDX (6 decimals)
    this.minApyBps = 500; // 5%
    this.maxApyBps = 3000; // 30%

    // Oracle info
    this.operatorName = "BookXe Partner Fleet — Đà Nẵng";
    this.reportPeriod = "Q4 2026";
    this.totalVehicles = 25; // 5 ô tô + 20 xe máy cho thuê du lịch Đà Nẵng
    this.grossRevenueUSD = 50000;
    this.operatingCostUSD = 35000;
    this.netProfitUSD = 15000;
    this.auditorName = "Independent RWA Auditor #01";
    this.reportHash = "0x" + "a".repeat(64);
    this.verifierAddress = "0xV".padEnd(42, "1");
    this.reportStatus = 3; // Verified
    this.reportCount = 1;
    this.lastUpdated = Math.floor(Date.now() / 1000);
    this.history = [];

    // Vault state
    this.totalDeposited = 0n;
    // 50,000 USDX với 6 decimals (phải khớp đơn vị của faucet/deposit)
    this.yieldReserve = 50000n * 1000000n;
    this.totalFundedRewards = 50000n * 1000000n;
    this.users = new Map();
    this.balances = new Map();
    this.timeOffset = 0; // Simulated extra seconds (for fast-forward)
    this.transactions = [];
    this.currentAddress = "0xDemoUser00000000000000000000000000000000";

    // APY (Bps)
    this.apyBps = 1200;
  }

  // ----- GETTERS -----
  getVaultName() { return this.vaultName; }
  getTargetCap() { return this.targetCap; }
  getTotalDeposited() { return this.totalDeposited; }
  getYieldReserve() { return this.yieldReserve; }
  getTotalFundedRewards() { return this.totalFundedRewards; }
  getCurrentAPY() { return this.apyBps; }
  getApyPercent() { return this.apyBps / 100; }
  isFrozen() { return this.frozen || false; }

  // ----- ORACLE -----
  getOracleInfo() {
    return {
      operatorName: this.operatorName,
      reportPeriod: this.reportPeriod,
      totalVehicles: this.totalVehicles,
      grossRevenue: this.grossRevenueUSD,
      operatingCost: this.operatingCostUSD,
      netProfit: this.netProfitUSD,
      verifiedApyBps: this.apyBps,
      auditorName: this.auditorName,
      reportHash: this.reportHash,
      lastUpdated: this.lastUpdated,
      verifierAddress: this.verifierAddress,
      reportStatus: this.reportStatus,
      reportCount: this.reportCount,
    };
  }

  /** Mock Oracle — cập nhật báo cáo tài chính mới */
  updateFinancialReport({ operatorName, reportPeriod, totalVehicles,
      grossRevenueUSD, operatingCostUSD, netProfitUSD, verifiedApyBps,
      auditorName, reportHash }) {
    if (operatorName) this.operatorName = operatorName;
    if (reportPeriod) this.reportPeriod = reportPeriod;
    if (totalVehicles) this.totalVehicles = totalVehicles;
    if (grossRevenueUSD) this.grossRevenueUSD = grossRevenueUSD;
    if (operatingCostUSD) this.operatingCostUSD = operatingCostUSD;
    if (netProfitUSD) this.netProfitUSD = netProfitUSD;
    if (verifiedApyBps) {
      // Kiểm tra giới hạn APY
      if (verifiedApyBps < this.minApyBps) {
        this.apyBps = this.minApyBps;
      } else if (verifiedApyBps > this.maxApyBps) {
        this.apyBps = this.maxApyBps;
      } else {
        this.apyBps = verifiedApyBps;
      }
    }
    if (auditorName) this.auditorName = auditorName;
    if (reportHash) this.reportHash = reportHash;
    this.lastUpdated = Math.floor(Date.now() / 1000);
    this.reportCount += 1;
    this.history.unshift(this.getOracleInfo());
    this.addTx("oracle-update", `Mô phỏng Oracle cập nhật báo cáo mới (APY: ${this.apyBps/100}%)`);
  }

  /** Fast-forward time in seconds for the simulated vault */
  fastForward(seconds) {
    const delta = Number(seconds);
    if (!Number.isFinite(delta) || delta <= 0) return;
    this.timeOffset += delta;
    this.addTx("time-advance", `Tua thời gian: +${delta/86400} ngày`);
  }

  // ----- INTERNAL -----
  _getUser(address) {
    if (!this.users.has(address)) {
      this.users.set(address, {
        depositedAmount: 0n,
        depositTimestamp: Date.now() / 1000,
        claimedYield: 0n,
        unclaimedYield: 0n,
        maturityDate: 0,
      });
    }
    return this.users.get(address);
  }

  _getBalance(address) {
    return this.balances.get(address) || 0n;
  }

  _addBalance(address, amount) {
    this.balances.set(address, this._getBalance(address) + amount);
  }

  _deductBalance(address, amount) {
    this.balances.set(address, this._getBalance(address) - amount);
  }

  _settleYield(address) {
    const user = this._getUser(address);
    if (user.depositedAmount === 0n) return;
    const pending = this.calculatePendingYield(address);
    if (pending > 0n) {
      user.unclaimedYield += pending;
      user.depositTimestamp = Date.now() / 1000;
      // Reset offset ngay sau khi chốt lãi để chu kỳ sau không tính trùng
      this.timeOffset = 0;
    }
  }

  // ----- FAUCET -----
  /** Nhận 10,000 USDX miễn phí */
  faucet(address) {
    const amount = 10000n * 1000000n; // 6 decimals
    this._addBalance(address, amount);
    this.addTx("faucet", `Nhận 10,000 USDX miễn phí (Faucet)`);
    return amount;
  }

  getBalance(address) {
    return this._getBalance(address);
  }

  // ----- DEPOSIT -----
  /** Nạp USDX vào Vault */
  deposit(address, amount) {
    if (amount <= 0n) return 0n;

    // Kiểm tra allowance (6 decimals)
    const user = this._getUser(address);
    const available = this._getBalance(address);
    if (available < amount) {
      console.warn(`Insufficient balance: ${available} < ${amount}`);
      return 0n;
    }

    // Chốt lãi cũ
    this._settleYield(address);

    // Kết nối với reserve
    if (this.yieldReserve >= amount) {
      this.yieldReserve -= amount;
      this.totalDeposited += amount;
      this._deductBalance(address, amount);

      if (user.depositedAmount === 0n) {
        user.depositTimestamp = Date.now() / 1000;
        user.maturityDate = Math.floor(Date.now() / 1000) + 1 * 365 * 86400;
      } else {
        user.depositTimestamp = Date.now() / 1000;
        user.maturityDate = Math.floor(Date.now() / 1000) + 1 * 365 * 86400;
      }
      user.depositedAmount += amount;

      this.addTx("deposit", `Nạp ${formatBigInt(amount, 6)} USDX vào Vault`);
      return amount;
    } else {
      console.warn("Yield reserve insufficient");
      return 0n;
    }
  }

  // ----- YIELD CALCULATION -----
  /**
   * Tính lãi đang sinh ra CHƯA nhận (bao gồm unclaimedYield)
   * Simple Interest: yield = principal * APY_bps * elapsed / (10000 * 365 days)
   */
  calculatePendingYield(address) {
    const user = this.users.get(address);
    if (!user || user.depositedAmount === 0n) return 0n;

    const apyBps = this.apyBps;
    const elapsed = Date.now() / 1000 - user.depositTimestamp + this.timeOffset;
    if (!Number.isFinite(elapsed) || elapsed <= 0) return 0n;

    // Simple Interest: yield = principal * APY_bps * elapsed / (10000 * 365 days)
    const yieldBigInt = (user.depositedAmount * BigInt(apyBps) * BigInt(Math.floor(elapsed))) /
      (10000n * YEAR_SECONDS);

    return yieldBigInt;
  }

  /** Tính lãi đã tích lũy chưa nhận (unclaimedYield) */
  calculateYieldOwed(address) {
    const user = this._getUser(address);
    return user.unclaimedYield;
  }

  /** Nhận lãi đã tích lũy */
  claimYield(address) {
    const user = this._getUser(address);
    if (user.depositedAmount === 0n) return 0n;

    // Chốt tất cả lãi đang sinh ra vào unclaimedYield
    this._settleYield(address);

    const totalToClaim = user.unclaimedYield;
    if (totalToClaim === 0n) return 0n;

    // Kiểm tra reserve
    if (this.yieldReserve < totalToClaim) {
      console.warn("Yield reserve insufficient for claim");
      return 0n;
    }

    // Transfer lãi từ reserve cho user
    this.yieldReserve -= totalToClaim;
    user.claimedYield += totalToClaim;
    user.unclaimedYield = 0n;
    user.depositTimestamp = Date.now() / 1000;
    this.timeOffset = 0; // Reset simulated time offset on claim

    this.addTx("claim", `Nhận lãi APY: ${formatBigInt(totalToClaim, 6)} USDX`);
    return totalToClaim;
  }

  // ----- WITHDRAW -----
  /** Rút tiền gốc */
  withdraw(address, amount) {
    if (amount <= 0n) return 0n;

    const user = this._getUser(address);
    if (user.depositedAmount < amount) {
      console.warn("Insufficient principal");
      return 0n;
    }

    // Chốt lãi cũ
    this._settleYield(address);

    // Rút vốn
    user.depositedAmount -= amount;
    this._addBalance(address, amount);
    this.totalDeposited -= amount;

    this.addTx("withdraw", `Rút ${formatBigInt(amount, 6)} USDX`);
    return amount;
  }

  /** Rút toàn bộ vốn (Redemption) */
  redeem(address) {
    const user = this._getUser(address);
    if (user.depositedAmount <= 0n) return 0n;

    this._settleYield(address);

    const amount = user.depositedAmount;
    user.depositedAmount = 0n;
    this._addBalance(address, amount);
    this.totalDeposited -= amount;

    this.addTx("redeem", `Rút toàn bộ vốn: ${formatBigInt(amount, 6)} USDX`);
    return amount;
  }

  // ----- USER INFO -----
  /** Lấy thông tin chi tiết của một nhà đầu tư */
  getUserInfo(address) {
    const user = this._getUser(address);
    const ownershipBps = this.totalDeposited > 0n
      ? Number((user.depositedAmount * 10000n) / this.totalDeposited)
      : 0;

    return {
      depositedAmount: user.depositedAmount,
      depositTimestamp: user.depositTimestamp,
      claimedYield: user.claimedYield,
      unclaimedYield: user.unclaimedYield,
      maturityDate: user.maturityDate,
      ownershipBps: ownershipBps,
    };
  }

  getUserOwnershipBps(address) {
    if (this.totalDeposited === 0n) return 0;
    const user = this.users.get(address);
    if (!user) return 0;
    return Number((user.depositedAmount * 10000n) / this.totalDeposited);
  }

  getTotalUnclaimedYield() {
    let total = 0n;
    for (const user of this.users.values()) {
      total += user.unclaimedYield;
    }
    return total;
  }

  // ----- ADMIN -----
  updateVaultName(newName) {
    if (newName && newName.length > 0) this.vaultName = newName;
  }

  updateTargetCap(newCap) {
    const cap = BigInt(newCap);
    if (cap >= this.totalDeposited) this.targetCap = cap;
  }

  freeze() {
    this.frozen = true;
  }

  unfreeze() {
    this.frozen = false;
  }

  // ----- UTILITIES -----
  /** Tạo bản sao đầy đủ state để React re-render mà không reset dữ liệu demo */
  clone() {
    const copy = Object.assign(new DemoVault(), this);
    copy.users = new Map(Array.from(this.users, ([key, user]) => [key, { ...user }]));
    copy.balances = new Map(this.balances);
    copy.history = [...this.history];
    copy.transactions = [...this.transactions];
    return copy;
  }

  addTx(type, desc) {
    this.transactions.unshift({
      id: Date.now() + Math.random(),
      type,
      desc,
      time: new Date().toLocaleTimeString("vi-VN"),
      hash: "0x" + Math.random().toString(16).slice(2, 18),
    });
  }

  getTransactions() {
    return this.transactions;
  }

  // ----- HELPERS -----
  getVaultBalance() {
    return this.totalDeposited + this.getTotalUnclaimedYield();
  }
}

/** Format BigInt to human-readable string with decimals */
export function formatBigInt(value, decimals = 6) {
  if (value === null || value === undefined || value === 0n) return "0";
  const v = BigInt(value);
  const negative = v < 0n;
  const absV = negative ? -v : v;
  let str = absV.toString().padStart(decimals + 1, "0");
  const intPart = str.slice(0, str.length - decimals);
  const frac = decimals > 0 ? str.slice(str.length - decimals).replace(/0+$/, "") : "";
  return (negative ? "-" : "") + intPart + (frac ? "." + frac : "");
}

export function parseBigInt(str, decimals = 6) {
  if (!str || str.trim() === "") return 0n;
  const clean = str.replace(/[,\s]/g, "");
  const value = Number(clean) * 10 ** decimals;
  // Chặn BigInt(NaN) gây RangeError → trắng trang khi người dùng gõ ký tự lạ
  if (!Number.isFinite(value)) return 0n;
  return BigInt(Math.round(value));
}

export function getFormatPrice(value, decimals = 6) {
  if (value === null || value === undefined) return "0";
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

export default DemoVault;
