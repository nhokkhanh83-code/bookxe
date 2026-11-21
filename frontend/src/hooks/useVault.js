// ============================================================
// useVault — React Hook quản lý kết nối VehicleRWAVault
// Hỗ trợ 2 chế độ:
//   1. MetaMask mode (Wallet) — Kết nối toàn bộ Smart Contracts
//   2. Demo Mode — Giả lập trên trình duyệt
// ============================================================

import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { ethers } from "ethers";
import { DemoVault, formatBigInt } from "../lib/demoVault.js";
import contractsData from "../contracts.json";

const AVALANCHE_FUJI_CHAIN_ID = 43113; // 0xA869

// Chain info
const CHAIN_INFO = {
  [AVALANCHE_FUJI_CHAIN_ID]: {
    name: "Avalanche Fuji Testnet",
    rpcUrl: "https://api.avax-test.network/ext/bc/C/rpc",
  },
  43114: {
    name: "Avalanche C-Chain Mainnet",
    rpcUrl: "https://api.avax.network/ext/bc/C/rpc",
  },
};

function useLocalStorage(key, initialValue) {
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = (value) => {
    setStoredValue(value);
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {}
  };

  return [storedValue, setValue];
}

export function useVault() {
  // ----- Trạng thái chế độ -----
  const [mode, setMode] = useLocalStorage("bookxe_vault_mode", "demo");
  const [isDemoMode, setIsDemoMode] = useState(mode === "demo");

  // ----- Trạng thái Wallet Mode -----
  const [provider, setProvider] = useState(null);
  const [signer, setSigner] = useState(null);
  const [connectedAddr, setConnectedAddr] = useState("");
  const [chainId, setChainId] = useState(AVALANCHE_FUJI_CHAIN_ID);
  const [chainName, setChainName] = useState(CHAIN_INFO[AVALANCHE_FUJI_CHAIN_ID].name);
  const [walletBalance, setWalletBalance] = useState(0n); // USDX balance of connected wallet
  const [txStatus, setTxStatus] = useState(null);
  const [txHash, setTxHash] = useState("");

  // ----- Trạng thái Demo Mode -----
  const [demoVault, setDemoVault] = useState(() => new DemoVault());

  // ----- Trạng thái chung -----
  const [loading, setLoading] = useState(false);

  // ----- Contracts (Wallet Mode) -----
  const contractsRef = useRef(null);

  const contracts = useMemo(() => {
    if (!contractsData || !contractsData.contracts || !contractsData.contracts.vault) {
      return null;
    }
    const cd = contractsData.contracts;
    return {
      usdX: new ethers.Contract(cd.usdX.address, cd.usdX.abi, provider || undefined),
      oracle: new ethers.Contract(cd.oracle.address, cd.oracle.abi, provider || undefined),
      vault: new ethers.Contract(cd.vault.address, cd.vault.abi, signer || undefined),
    };
  }, [provider, signer]);

  contractsRef.current = contracts;

  // ----- Helpers -----
  const setTx = useCallback((type, message) => {
    setTxStatus({ type, message });
  }, []);

  // ----- Mode Switching -----
  const toggleMode = useCallback((newMode) => {
    setIsDemoMode(newMode === "demo");
    setMode(newMode);
  }, [setMode]);

  // ----- Wallet Functions -----
  const connectWallet = useCallback(async () => {
    if (!window.ethereum) {
      setTx("error", "Không tìm thấy MetaMask! Hãy cài đặt MetaMask để dùng mode Wallet.");
      return;
    }

    try {
      setLoading(true);
      setTx("info", "Đang kết nối ví...");

      // Switch to Fuji Testnet (0xA869 = 43113)
      const targetChainId = '0xA869'; // Avalanche Fuji Testnet
      await window.ethereum.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: targetChainId }] })
        .catch((e) => { if (e.code !== -32603 && e.code !== 4902) throw e; });

      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      const addr = accounts[0];

      const prov = new ethers.BrowserProvider(window.ethereum);
      const sig = await prov.getSigner(addr);
      const network = await prov.getNetwork();

      setChainId(network.chainId);
      setChainName(CHAIN_INFO[network.chainId]?.name || `Chain #${network.chainId}`);
      setProvider(prov);
      setSigner(sig);
      setConnectedAddr(addr);

      setTx("success", `✅ Đã kết nối: ${addr.slice(0, 6)}...${addr.slice(-4)} trên ${CHAIN_INFO[network.chainId]?.name}`);
      setMode("wallet");
      setIsDemoMode(false);
    } catch (err) {
      if (err.code === 'ERR_ACCOUNT_UNAUTHORIZED' || err.code === 'ERR_USER_REJECTED' || err.code === -32603 || err.code === 4902) {
        setTx("error", "Bạn đã hủy yêu cầu kết nối. Hãy chuyển tài khoản MetaMask sang Fuji Testnet.");
      } else if (err.message.includes('wallet_addEthereumChain')) {
        setTx("error", "Vui lòng thêm Avalanche Fuji Testnet vào MetaMask.");
      } else {
        setTx("error", `Lỗi kết nối: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const disconnectWallet = useCallback(async () => {
    setProvider(null);
    setSigner(null);
    setConnectedAddr("");
    setChainId(AVALANCHE_FUJI_CHAIN_ID);
    setChainName(CHAIN_INFO[AVALANCHE_FUJI_CHAIN_ID].name);
    setWalletBalance(0n);
    setTxStatus(null);
    setMode("demo");
    setIsDemoMode(true);
  }, []);

  // ----- Wallet Actions -----
  const faucetWallet = useCallback(async () => {
    if (!signer || !contracts) {
      setTx("error", "Vui lòng kết nối ví trước.");
      return;
    }
    try {
      setLoading(true);
      setTx("info", "Đang gửi giao dịch Faucet...");
      const tx = await contracts.usdX.faucet();
      setTxHash(tx.hash);
      await tx.wait();
      const bal = await contracts.usdX.balanceOf(await signer.getAddress());
      setWalletBalance(bal);
      setTx("success", `✅ Nhận 10,000 USDX thành công (TxID: ${tx.hash.slice(0, 10)}...)`);
    } catch (err) {
      setTx("error", `❌ Faucet thất bại: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [signer, contracts]);

  const depositWallet = useCallback(async (amount) => {
    if (!signer || !contracts || !amount) {
      setTx("error", "Vui lòng nhập số tiền và kết nối ví.");
      return;
    }
    try {
      setLoading(true);
      setTx("info", "Đang xử lý Approve...");
      const addr = await signer.getAddress();
      await contracts.usdX.approve(contractsData.contracts.vault.address, amount);

      setTx("info", "Đang gửi giao dịch Deposit...");
      const tx = await contracts.vault.deposit(amount);
      setTxHash(tx.hash);
      await tx.wait();
      setTx("success", `✅ Nạp tiền vào Vault thành công!`);
      const bal = await contracts.usdX.balanceOf(addr);
      setWalletBalance(bal);
    } catch (err) {
      setTx("error", `❌ Deposit thất bại: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [signer, contracts]);

  const claimYieldWallet = useCallback(async () => {
    if (!signer || !contracts) {
      setTx("error", "Vui lòng kết nối ví.");
      return;
    }
    try {
      setLoading(true);
      setTx("info", "Đang gửi giao dịch Claim Yield...");
      const tx = await contracts.vault.claimYield();
      setTxHash(tx.hash);
      await tx.wait();
      setTx("success", `✅ Nhận lãi thành công!`);
    } catch (err) {
      setTx("error", `❌ Claim thất bại: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [signer, contracts]);

  const withdrawWallet = useCallback(async (amount) => {
    if (!signer || !contracts || !amount) {
      setTx("error", "Vui lòng nhập số tiền.");
      return;
    }
    try {
      setLoading(true);
      setTx("info", "Đang gửi giao dịch Withdraw...");
      const tx = await contracts.vault.withdraw(amount);
      setTxHash(tx.hash);
      await tx.wait();
      setTx("success", `✅ Rút vốn thành công!`);
      const bal = await contracts.usdX.balanceOf(await signer.getAddress());
      setWalletBalance(bal);
    } catch (err) {
      setTx("error", `❌ Withdraw thất bại: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [signer, contracts]);

  const redeemWallet = useCallback(async () => {
    if (!signer || !contracts) {
      setTx("error", "Vui lòng kết nối ví.");
      return;
    }
    try {
      setLoading(true);
      setTx("info", "Đang gửi giao dịch Redeem...");
      const tx = await contracts.vault.redeem();
      setTxHash(tx.hash);
      await tx.wait();
      setTx("success", `✅ Rút toàn bộ vốn thành công!`);
    } catch (err) {
      setTx("error", `❌ Redeem thất bại: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [signer, contracts]);

  // ----- Demo Actions -----
  const faucetDemo = useCallback(() => {
    const address = demoVault.currentAddress;
    demoVault.faucet(address);
    setDemoVault(demoVault.clone()); // giữ nguyên state, chỉ tạo bản sao để re-render
    setTx("success", "✅ Nhận 10,000 USDX (Demo)");
  }, [demoVault]);

  const depositDemo = useCallback((amount) => {
    if (!amount || amount <= 0n) {
      setTx("error", "Vui lòng nhập số tiền > 0.");
      return;
    }
    demoVault.deposit(demoVault.currentAddress, amount);
    setDemoVault(demoVault.clone());
    setTx("success", `✅ Nạp tiền vào Vault: ${formatBigInt(amount, 6)} USDX (Demo)`);
  }, [demoVault]);

  const claimYieldDemo = useCallback(() => {
    const pending = demoVault.claimYield(demoVault.currentAddress);
    if (pending > 0n) {
      setTx("success", `✅ Nhận lãi APY: ${formatBigInt(pending, 6)} USDX (Demo)`);
    } else {
      setTx("info", "Không có lãi sinh ra để nhận.");
    }
    setDemoVault(demoVault.clone());
  }, [demoVault]);

  const withdrawDemo = useCallback((amount) => {
    if (!amount || amount <= 0n) return;
    const withdrawn = demoVault.withdraw(demoVault.currentAddress, amount);
    if (withdrawn > 0n) {
      setTx("success", `✅ Rút vốn: ${formatBigInt(withdrawn, 6)} USDX (Demo)`);
    }
    setDemoVault(demoVault.clone());
  }, [demoVault]);

  const redeemDemo = useCallback(() => {
    const redeemed = demoVault.redeem(demoVault.currentAddress);
    if (redeemed > 0n) {
      setTx("success", `✅ Rút toàn bộ vốn: ${formatBigInt(redeemed, 6)} USDX (Demo)`);
    }
    setDemoVault(demoVault.clone());
  }, [demoVault]);

  const updateOracleDemo = useCallback((apyBps, other = {}) => {
    demoVault.updateFinancialReport({ verifiedApyBps: apyBps, ...other });
    setDemoVault(demoVault.clone());
    setTx("success", `✅ Mô phỏng Oracle cập nhật APY: ${apyBps/100}%/năm`);
  }, [demoVault]);

  const fastForwardDemo = useCallback((seconds = 365 * 24 * 3600) => {
    demoVault.fastForward(seconds);
    setDemoVault(demoVault.clone());
    setTx("info", `⏰ Tua thời gian: +${seconds/86400} ngày`);
  }, [demoVault]);

  // ----- Data getters -----
  const demoData = useMemo(() => {
    if (!isDemoMode) return null;
    const dv = demoVault;
    const addr = dv.currentAddress;
    const userInfo = dv.getUserInfo(addr);
    const oracleInfo = dv.getOracleInfo();

    return {
      vaultName: dv.vaultName,
      totalDeposited: dv.totalDeposited,
      targetCap: dv.targetCap,
      yieldReserve: dv.yieldReserve,
      totalFundedRewards: dv.totalFundedRewards,
      userBalance: dv.getBalance(addr),
      userInfo,
      apyBps: dv.apyBps,
      ownershipBps: userInfo.ownershipBps,
      pendingYield: dv.calculatePendingYield(addr),
      claimedYield: userInfo.claimedYield,
      oracle: oracleInfo,
      transactions: dv.getTransactions(),
    };
  }, [isDemoMode, demoVault]);

  return {
    // State
    mode,
    isDemoMode,
    chainName,
    chainId,
    connectedAddr,
    loading,
    txStatus,
    txHash,
    walletBalance,

    // Demo data
    demoData,

    // Functions
    toggleMode,
    connectWallet,
    disconnectWallet,

    // Wallet mode
    faucetWallet,
    depositWallet,
    claimYieldWallet,
    withdrawWallet,
    redeemWallet,

    // Demo mode
    faucetDemo,
    depositDemo,
    claimYieldDemo,
    withdrawDemo,
    redeemDemo,
    updateOracleDemo,
    fastForwardDemo,

    // Contracts (wallet mode)
    contracts,
    signer,
  };
}

export default useVault;
