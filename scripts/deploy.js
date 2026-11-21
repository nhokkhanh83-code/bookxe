const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

const VAULT_NAME = "BookXe RWA Fleet Vault - Electric Fleet Investment";
const TARGET_CAP = 300000; // USDX
const INITIAL_APY_BPS = 1200; // 12.00%
const MIN_APY_BPS = 500; // 5% minimum
const MAX_APY_BPS = 3000; // 30% maximum

async function main() {
  const [owner, verifier] = await ethers.getSigners();
  const ownerAddr = await owner.getAddress();
  const verifierAddr = await verifier.getAddress();
  console.log("Deployer (Owner):", ownerAddr);
  console.log("Verifier:", verifierAddr);

  // ---- 1. Deploy MockUSDX ----
  console.log("\n[1/5] Deploying MockUSDX...");
  const MockUSDX = await ethers.getContractFactory("MockUSDX");
  const usdX = await MockUSDX.deploy();
  await usdX.waitForDeployment();
  const usdXAddr = await usdX.getAddress();
  console.log("MockUSDX deployed at:", usdXAddr);

  // ---- 2. Deploy FleetFinancialOracle ----
  console.log("\n[2/5] Deploying FleetFinancialOracle...");
  const Oracle = await ethers.getContractFactory("FleetFinancialOracle");
  const oracle = await Oracle.deploy(ownerAddr, verifierAddr, MIN_APY_BPS, MAX_APY_BPS);
  await oracle.waitForDeployment();
  const oracleAddr = await oracle.getAddress();
  console.log("FleetFinancialOracle deployed at:", oracleAddr);

  // ---- 3. Deploy VehicleRWAVault ----
  console.log("\n[3/5] Deploying VehicleRWAVault...");
  const Vault = await ethers.getContractFactory("VehicleRWAVault");
  const vault = await Vault.deploy(
    usdXAddr,
    oracleAddr,
    verifierAddr,
    VAULT_NAME,
    TARGET_CAP
  );
  await vault.waitForDeployment();
  const vaultAddr = await vault.getAddress();
  console.log("VehicleRWAVault deployed at:", vaultAddr);

  // ---- 4. Set initial financial report ----
  console.log("\n[4/5] Setting initial financial report...");
  await oracle.updateFinancialReport(
    "Green Future EV Fleet",
    "Q4 2026",
    10,           // totalVehicles
    50000,        // grossRevenueUSD
    35000,        // operatingCostUSD
    15000,        // netProfitUSD
    INITIAL_APY_BPS, // verifiedApyBps = 1200 (12.00%)
    "Independent RWA Auditor #01",
    ethers.id("bookxe-rwa-report-q4-2026-v2")
  );
  console.log("Financial report set: APY =", INITIAL_APY_BPS / 100, "%");
  console.log("APY Range:", (MIN_APY_BPS / 100), "% -", (MAX_APY_BPS / 100), "%");

  // ---- 5. Fund rewards reserve (Demo: 5% of cap = $15,000) ----
  console.log("\n[5/5] Funding Yield Reserve...");
  await usdX.mint(ownerAddr, 50000); // Mint 50,000 USDX to Owner for funding
  await usdX.approve(vaultAddr, 50000);
  await vault.fundRewards(50000);
  console.log("Yield Reserve funded: 50,000 USDX");
  console.log("Yield Reserve balance:", await vault.yieldReserve());

  // ---- Export ABIs + addresses ----
  const outputDir = path.join(__dirname, "..", "frontend", "src");
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const contractsData = {
    network: process.env.HARDHAT_NETWORK || "localhost",
    deploymentTime: new Date().toISOString(),
    contracts: {
      usdX: {
        address: usdXAddr,
        abi: await usdX.interface.formatABI(ethers.FormatTypes.jsonFragment),
        name: "MockUSDX",
      },
      oracle: {
        address: oracleAddr,
        abi: await oracle.interface.formatABI(ethers.FormatTypes.jsonFragment),
        name: "FleetFinancialOracle",
      },
      vault: {
        address: vaultAddr,
        abi: await vault.interface.formatABI(ethers.FormatTypes.jsonFragment),
        name: "VehicleRWAVault",
      },
    },
    constants: {
      vaultName: VAULT_NAME,
      targetCap: TARGET_CAP,
      initialApyBps: INITIAL_APY_BPS,
      minApyBps: MIN_APY_BPS,
      maxApyBps: MAX_APY_BPS,
    },
  };

  fs.writeFileSync(
    path.join(outputDir, "contracts.json"),
    JSON.stringify(contractsData, null, 2)
  );
  console.log("\n✅ Contracts info exported to frontend/src/contracts.json");
  console.log("Vault Name:", VAULT_NAME);
  console.log("Target Cap:", TARGET_CAP, "USDX");
  console.log("APY:", INITIAL_APY_BPS / 100, "%");
  console.log("Yield Reserve:", await vault.yieldReserve(), "USDX");

  console.log("\n🎉 Deployment complete! Ready to demo!");
  console.log("\nNext steps:");
  console.log("  1. cd frontend && npm run dev");
  console.log("  2. Faucet → Nạp USDX → Deposit → Nhận lãi 12%/năm");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
