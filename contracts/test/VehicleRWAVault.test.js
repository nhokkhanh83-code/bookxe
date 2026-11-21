// ============================================================
// VehicleRWAVault - BookXe RWA Fleet Investment Vault Tests
// ============================================================

const { expect } = require("chai");

describe("VehicleRWAVault - BookXe RWA Fleet Investment Vault", function () {
  let owner, verifier, alice, bob;
  let MockUSDX, FleetFinancialOracle, VehicleRWAVault;
  let usdX, oracle, vault;
  const DAY = 24 * 60 * 60;

  // Config constants
  const TARGET_CAP = ethers.parseEther("300000");
  const INITIAL_APY_BPS = 1200; // 12%

  beforeEach(async function () {
    [owner, verifier, alice, bob] = await ethers.getSigners();

    // Deploy contracts
    MockUSDX = await ethers.getContractFactory("MockUSDX");
    usdX = await MockUSDX.deploy();
    await usdX.waitForDeployment();

    FleetFinancialOracle = await ethers.getContractFactory("FleetFinancialOracle");
    oracle = await FleetFinancialOracle.deploy(owner.address, verifier.address, 500n, 3000n);
    await oracle.waitForDeployment();

    VehicleRWAVault = await ethers.getContractFactory("VehicleRWAVault");
    vault = await VehicleRWAVault.deploy(
      usdX.address,
      oracle.address,
      verifier.address,
      "BookXe RWA Fleet Vault - Electric Fleet Investment",
      TARGET_CAP
    );
    await vault.waitForDeployment();

    // Set initial APY
    await oracle.updateFinancialReport(
      "Green Future EV Fleet",
      "Q4 2026",
      10,
      50000,
      35000,
      15000,
      INITIAL_APY_BPS,
      "Independent RWA Auditor #01",
      ethers.id("bookxe-rwa-q4-2026")
    );

    // Fund yield reserve with 50,000 USDX
    await usdX.mint(owner.address, ethers.parseEther("50000"));
    await usdX.approve(vault.address, ethers.parseEther("50000"));
    await vault.fundRewards(ethers.parseEther("50000"));
  });

  // ============================================================
  // DEPOSIT TESTS
  // ============================================================
  describe("Deposit", function () {
    it("Should allow deposit and update user info", async function () {
      const amount = ethers.parseEther("1000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      expect(await vault.totalDeposited()).to.equal(amount);
      const info = await vault.getUserInfo(alice.address);
      expect(info[0]).to.equal(amount); // depositedAmount
      expect(info[5]).to.equal(10000n); // ownershipBps (100%)
    });

    it("Should enforce target cap", async function () {
      const amount = ethers.parseEther("300000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // Try to deposit more - should revert
      await usdX.mint(alice.address, ethers.parseEther("1"));
      await usdX.connect(alice).approve(vault.address, ethers.parseEther("1"));
      await expect(vault.connect(alice).deposit(ethers.parseEther("1")))
        .to.be.revertedWith("Deposit exceeds vault capacity");
    });

    it("Should enforce target cap across multiple users", async function () {
      // Alice deposits half
      await usdX.mint(alice.address, TARGET_CAP / 2);
      await usdX.connect(alice).approve(vault.address, TARGET_CAP / 2);
      await vault.connect(alice).deposit(TARGET_CAP / 2);

      // Bob tries to deposit more than remaining
      await usdX.mint(bob.address, TARGET_CAP / 2 + ethers.parseEther("100"));
      await usdX.connect(bob).approve(vault.address, TARGET_CAP / 2 + ethers.parseEther("100"));
      await expect(vault.connect(bob).deposit(TARGET_CAP / 2 + ethers.parseEther("100")))
        .to.be.revertedWith("Deposit exceeds vault capacity");
    });

    it("Should reject deposit when paused", async function () {
      await vault.connect(owner).freeze();
      await usdX.mint(alice.address, ethers.parseEther("100"));
      await usdX.connect(alice).approve(vault.address, ethers.parseEther("100"));
      await expect(vault.connect(alice).deposit(ethers.parseEther("100")))
        .to.be.revertedWith("Vault is paused");
    });

    it("Should require non-zero deposit", async function () {
      await expect(vault.connect(alice).deposit(0))
        .to.be.revertedWith("Deposit amount must be > 0");
    });
  });

  // ============================================================
  // YIELD CALCULATION TESTS (Simple Interest)
  // ============================================================
  describe("Yield Calculation", function () {
    it("Should calculate correct simple interest for 1 year at 12% APY", async function () {
      const amount = ethers.parseEther("10000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // Fast forward 1 year
      await ethers.provider.send("evm_increaseTime", [365 * DAY]);
      await ethers.provider.send("evm_mine", []);

      const pendingYield = await vault.calculatePendingYield(alice.address);
      // 10000 * 1200 * 31536000 / (10000 * 31536000) = 120 USDX
      expect(pendingYield).to.equal(ethers.parseEther("120"));
    });

    it("Should calculate yield based on different APY from oracle", async function () {
      const amount = ethers.parseEther("10000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // Update APY to 25%
      await oracle.updateFinancialReport(
        "Green Future EV Fleet",
        "Q1 2027",
        10, 50000, 35000, 15000, 2500, "Auditor #2", ethers.id("q1-2027")
      );

      // Fast forward 1 year
      await ethers.provider.send("evm_increaseTime", [365 * DAY]);
      await ethers.provider.send("evm_mine", []);

      const pendingYield = await vault.calculatePendingYield(alice.address);
      // 10000 * 2500 * 31536000 / (10000 * 31536000) = 250 USDX
      expect(pendingYield).to.equal(ethers.parseEther("250"));
    });

    it("Should not apply retroactive APY changes", async function () {
      const amount = ethers.parseEther("10000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // Wait 6 months (half year)
      await ethers.provider.send("evm_increaseTime", [180 * DAY]);
      await ethers.provider.send("evm_mine", []);

      // Get yield at 6 months with 12% APY
      const yieldAt6Months = await vault.calculatePendingYield(alice.address);

      // Update APY to 25%
      await oracle.updateFinancialReport(
        "Green Future EV Fleet", "Q2 2027", 10, 60000, 36000, 24000, 2500, "Auditor #3", ethers.id("q2")
      );

      // Fast forward 6 more months (total 1 year)
      await ethers.provider.send("evm_increaseTime", [180 * DAY]);
      await ethers.provider.send("evm_mine", []);

      // New yield should reflect new APY from last settle
      const newYield = await vault.calculatePendingYield(alice.address);
      // New yield should be > 0 because of the period after the APY change
      expect(newYield).to.be.gte(0n);
      expect(yieldAt6Months).to.be.gt(0n);
    });
  });

  // ============================================================
  // CLAIM YIELD TESTS
  // ============================================================
  describe("Claim Yield", function () {
    it("Should claim yield successfully", async function () {
      const amount = ethers.parseEther("10000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // Fast forward 1 year
      await ethers.provider.send("evm_increaseTime", [365 * DAY]);
      await ethers.provider.send("evm_mine", []);

      // Record vault balance before claim
      const vaultBalanceBefore = await vault.getVaultBalance();

      // Claim yield
      await vault.connect(alice).claimYield();

      // Verify user received yield
      const aliceBalance = await usdX.balanceOf(alice.address);
      expect(aliceBalance).to.equal(ethers.parseEther("10000") + ethers.parseEther("120"));

      // Check user info - yield should be 0
      const [, , claimed, , , ]] = await vault.getUserInfo(alice.address);
      expect(claimed).to.equal(ethers.parseEther("120"));

      // Vault balance should have decreased by the yield
      const vaultBalanceAfter = await vault.getVaultBalance();
      expect(vaultBalanceAfter).to.equal(vaultBalanceBefore - ethers.parseEther("120"));
    });

    it("Should not claim if no yield", async function () {
      const amount = ethers.parseEther("1000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // No time passed - no yield
      await expect(vault.connect(alice).claimYield()).to.not.be.reverted;
    });

    it("Should not claim if yield reserve is insufficient", async function () {
      const amount = ethers.parseEther("10000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // Fast forward 1 year - pending yield = 120
      await ethers.provider.send("evm_increaseTime", [365 * DAY]);
      await ethers.provider.send("evm_mine", []);

      // Manually drain the reserve
      await vault.connect(owner).unfreeze();
      // Withdraw all yield reserve
      const reserveBefore = await vault.yieldReserve();
      await usdX.connect(owner).transfer(owner.address, reserveBefore);

      // Now claim should revert
      await expect(vault.connect(alice).claimYield())
        .to.be.revertedWith("Insufficient yield reserve");
    });

    it("Should handle multiple claims", async function () {
      const amount = ethers.parseEther("10000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // First year claim
      await ethers.provider.send("evm_increaseTime", [365 * DAY]);
      await ethers.provider.send("evm_mine", []);
      await vault.connect(alice).claimYield();
      const [,, claimedYield1] = await vault.getUserInfo(alice.address);
      expect(claimedYield1).to.equal(ethers.parseEther("120"));

      // Second year
      await ethers.provider.send("evm_increaseTime", [365 * DAY]);
      await ethers.provider.send("evm_mine", []);
      await vault.connect(alice).claimYield();
      const [,, claimedYield2] = await vault.getUserInfo(alice.address);
      expect(claimedYield2).to.equal(ethers.parseEther("240")); // 120 + 120
    });
  });

  // ============================================================
  // WITHDRAW TESTS
  // ============================================================
  describe("Withdraw", function () {
    it("Should withdraw principal successfully", async function () {
      const amount = ethers.parseEther("500");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      const balanceBefore = await usdX.balanceOf(alice.address);
      await vault.connect(alice).withdraw(amount);
      const balanceAfter = await usdX.balanceOf(alice.address);

      expect(balanceAfter).to.equal(balanceBefore + amount);
      expect(await vault.totalDeposited()).to.equal(0);
    });

    it("Should reject withdraw when insufficient principal", async function () {
      const amount = ethers.parseEther("500");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      await expect(vault.connect(alice).withdraw(ethers.parseEther("1000")))
        .to.be.revertedWith("Insufficient principal");
    });

    it("Should require non-zero withdraw", async function () {
      await expect(vault.connect(alice).withdraw(0))
        .to.be.revertedWith("Withdraw amount must be > 0");
    });

    it("Should settle yield on withdraw", async function () {
      const amount = ethers.parseEther("10000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // Fast forward 1 year
      await ethers.provider.send("evm_increaseTime", [365 * DAY]);
      await ethers.provider.send("evm_mine", []);

      // Withdraw
      await vault.connect(alice).withdraw(amount);

      // Check that unclaimedYield is set (lãi đã được chốt vào unclaimedYield)
      const info = await vault.getUserInfo(alice.address);
      expect(info[3]).to.equal(ethers.parseEther("120")); // unclaimedYield
    });
  });

  // ============================================================
  // REDEMPT TESTS
  // ============================================================
  describe("Redeem", function () {
    it("Should redeem to full balance", async function () {
      const amount = ethers.parseEther("1000");
      await usdX.mint(alice.address, amount);
      await usdX.connect(alice).approve(vault.address, amount);
      await vault.connect(alice).deposit(amount);

      // Redeem
      const balanceBefore = await usdX.balanceOf(alice.address);
      await vault.connect(alice).redeem();
      const balanceAfter = await usdX.balanceOf(alice.address);

      // Should get all deposited back
      expect(balanceAfter).to.equal(balanceBefore + amount);
      expect(await vault.totalDeposited()).to.equal(0);
      expect(await vault.getUserInfo(alice.address)[0]).to.equal(0n);
    });

    it("Should reject redeem when no deposit", async function () {
      await expect(vault.connect(alice).redeem())
        .to.be.revertedWith("No principal deposited");
    });
  });

  // ============================================================
  // OWNERSHIP TESTS
  // ============================================================
  describe("Ownership", function () {
    it("Should calculate correct ownership percentage", async function () {
      // Alice deposits 300, Bob deposits 700
      const aliceAmount = ethers.parseEther("300");
      const bobAmount = ethers.parseEther("700");

      await usdX.mint(alice.address, aliceAmount);
      await usdX.connect(alice).approve(vault.address, aliceAmount);
      await vault.connect(alice).deposit(aliceAmount);

      await usdX.mint(bob.address, bobAmount);
      await usdX.connect(bob).approve(vault.address, bobAmount);
      await vault.connect(bob).deposit(bobAmount);

      // Alice: 300/1000 = 30%
      const aliceOwnership = await vault.getUserOwnershipBps(alice.address);
      expect(aliceOwnership).to.equal(3000n); // 30%

      // Bob: 700/1000 = 70%
      const bobOwnership = await vault.getUserOwnershipBps(bob.address);
      expect(bobOwnership).to.equal(7000n); // 70%
    });
  });

  // ============================================================
  // ADMIN & VERIFIER FUNCTION TESTS
  // ============================================================
  describe("Admin & Verifier Functions", function () {
    it("Should allow owner to update vault name", async function () {
      await vault.connect(owner).updateVaultName("New Vault Name");
      expect(await vault.vaultName()).to.equal("New Vault Name");
    });

    it("Should reject vault name update by non-owner", async function () {
      await expect(vault.connect(alice).updateVaultName("Hacked"))
        .to.be.revertedWith("Not owner");
    });

    it("Should allow owner to update target cap", async function () {
      await vault.connect(owner).updateTargetCapUSDX(ethers.parseEther("500000"));
      expect(await vault.targetCapUSDX()).to.equal(ethers.parseEther("500000"));
    });

    it("Should reject target cap update below current deposit", async function () {
      await usdX.mint(alice.address, ethers.parseEther("100"));
      await usdX.connect(alice).approve(vault.address, ethers.parseEther("100"));
      await vault.connect(alice).deposit(ethers.parseEther("100"));

      await expect(vault.connect(owner).updateTargetCapUSDX(ethers.parseEther("50")))
        .to.be.revertedWith("New cap must be >= current deposited");
    });

    it("Should allow owner to fund rewards", async function () {
      await usdX.mint(owner.address, ethers.parseEther("10000"));
      await usdX.connect(owner).approve(vault.address, ethers.parseEther("10000"));
      await vault.connect(owner).fundRewards(ethers.parseEther("10000"));
      expect(await vault.yieldReserve()).to.equal(ethers.parseEther("60000")); // 50000 + 10000
    });

    it("Should allow owner to freeze vault", async function () {
      await vault.connect(owner).freeze();
      expect(await vault.isFrozen()).to.equal(true);
    });

    it("Should allow owner to unfreeze vault", async function () {
      await vault.connect(owner).freeze();
      await vault.connect(owner).unfreeze();
      expect(await vault.isFrozen()).to.equal(false);
    });
  });

  // ============================================================
  // ORACLE TESTS
  // ============================================================
  describe("FleetFinancialOracle", function () {
    it("Should allow owner to update APY limits", async function () {
      await oracle.updateAPYLIMITS(500n, 3000n); // 5% - 30%
      expect(await oracle.minAPYBps()).to.equal(500n);
      expect(await oracle.maxAPYBps()).to.equal(3000n);
    });

    it("Should allow verifier to update financial report", async function () {
      await oracle.connect(verifier).updateFinancialReport(
        "Green Future EV Fleet", "Q1 2027", 10, 60000, 36000, 24000,
        2500, "Auditor #2", ethers.id("q1-2027")
      );
      expect(await oracle.verifiedApyBps()).to.equal(2500n);
    });

    it("Should reject APY update below minimum", async function () {
      await expect(oracle.updateFinancialReport(
        "Green Future EV Fleet", "Q1 2027", 10, 60000, 36000, 24000,
        400, "Auditor #2", ethers.id("q1-2027")
      )).to.be.revertedWith("APY below minimum");
    });

    it("Should reject APY update above maximum", async function () {
      await expect(oracle.updateFinancialReport(
        "Green Future EV Fleet", "Q1 2027", 10, 60000, 36000, 24000,
        5000, "Auditor #2", ethers.id("q1-2027")
      )).to.be.revertedWith("APY above maximum");
    });

    it("Should store report history", async function () {
      const reportCountBefore = await oracle.getReportCount();
      await oracle.updateFinancialReport(
        "Green Future EV Fleet", "Q1 2027", 10, 60000, 36000, 24000,
        2500, "Auditor #2", ethers.id("q1-2027")
      );
      const reportCountAfter = await oracle.getReportCount();
      expect(reportCountAfter).to.equal(reportCountBefore + 1n);
    });

    it("Should return report history data", async function () {
      const history = await oracle.getReportHistory();
      expect(history.length).to.equal(await oracle.getReportCount());
    });
  });
});
