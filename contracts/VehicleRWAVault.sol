// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./MockUSDX.sol";
import "./FleetFinancialOracle.sol";

/**
 * @title VehicleRWAVault - BookXe RWA Fleet Investment Vault
 * @notice Tài sản thế giới thực (RWA) — Đầu tư đội xe điện
 *         Nhà đầu tư nạp USDX để gửi tiền đầu tư và nhận lãi suất APY
 *         theo báo cáo tài chính được bên thứ 3 (Oracle) xác minh.
 *
 * @dev GIAI ĐOẠN 2: Đầu tư & Đơn giản hóa (không hợp đồng thuê xe, không đặt lịch)
 *
 *   - Lãi: SIMPLE INTEREST (lãi đơn), không hồi tố
 *   - APY: Lấy từ Oracle (verifiedApyBps)
 *   - Trả lãi: Từ yield reserve (admin phải fund đủ trước)
 *   - Time: Quy định rõ thời điểm hiệu lực APY và kỳ đầu tư
 *   - Quyền: Owner (admin) + Verifier (oracle) + Emergency Pause
 */
contract VehicleRWAVault {
    // ============================================================
    // TYPES & STRUCTS
    // ============================================================

    struct UserInfo {
        uint256 depositedAmount;      // Vốn gốc đã nạp
        uint256 depositTimestamp;     // Thời điểm bắt đầu tính lãi (effectiveAt)
        uint256 claimedYield;         // Tổng lãi đã nhận
        uint256 unclaimedYield;       // Lãi đã tích lũy chưa nhận
        uint256 maturityDate;         // Ngày đồng thời kỳ đầu tư
    }

    // ============================================================
    // STATE
    // ============================================================

    string public vaultName;
    uint256 public targetCapUSDX;       // Giới hạn vốn huy động
    uint256 public totalDeposited;      // Tổng vốn đã nạp
    uint256 public yieldReserve;        // Dự phòng trả lãi (fundRewards)
    uint256 public totalFundedRewards;  // Tổng đã fund

    mapping(address => UserInfo) private _users;

    // Contracts liên kết
    MockUSDX public immutable usdX;
    FleetFinancialOracle public immutable oracle;

    // Admin
    address public owner;
    address public verifier;

    // Emergency Pause
    bool private _frozen;

    // Events
    event Deposit(address indexed user, uint256 amount, uint256 totalDeposited);
    event Withdraw(address indexed user, uint256 amount, uint256 principalLeft);
    event YieldClaimed(address indexed user, uint256 amount, uint256 totalClaimed);
    event FundRewards(address indexed by, uint256 amount, uint256 newReserve);
    event EmergencyPause();
    event EmergencyUnpause();

    // ============================================================
    // MODIFIERS
    // ============================================================

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyVerifier() {
        require(msg.sender == verifier, "Not verifier");
        _;
    }

    modifier whenNotPaused() {
        require(!_frozen, "Vault is paused");
        _;
    }

    // ============================================================
    // CONSTRUCTOR
    // ============================================================

    constructor(
        address _usdX,
        address _oracle,
        address _verifier,
        string memory _vaultName,
        uint256 _targetCapUSDX
    ) {
        usdX = MockUSDX(_usdX);
        oracle = FleetFinancialOracle(_oracle);
        verifier = _verifier;
        vaultName = _vaultName;
        targetCapUSDX = _targetCapUSDX;
        owner = msg.sender;
    }

    // ============================================================
    // READ: VAULT INFO
    // ============================================================

    function getVaultName() public view returns (string memory) {
        return vaultName;
    }

    function getTargetCapUSDX() public view returns (uint256) {
        return targetCapUSDX;
    }

    function getTotalDeposited() public view returns (uint256) {
        return totalDeposited;
    }

    function getVaultBalance() public view returns (uint256) {
        return usdX.balanceOf(address(this));
    }

    function isFrozen() public view returns (bool) {
        return _frozen;
    }

    // ============================================================
    // READ: ORACLE (APY, Fleet Data)
    // ============================================================

    function getCurrentAPY() public view returns (uint256) {
        return oracle.verifiedApyBps();
    }

    function getOracleInfo() public view returns (
        string memory, string memory, uint256, uint256,
        uint256, uint256, uint256, string memory,
        string memory, uint256
    ) {
        return (
            oracle.operatorName(),
            oracle.reportPeriod(),
            oracle.totalVehicles(),
            oracle.grossRevenueUSD(),
            oracle.operatingCostUSD(),
            oracle.netProfitUSD(),
            oracle.verifiedApyBps(),
            oracle.auditorName(),
            oracle.reportHash(),
            oracle.lastUpdated()
        );
    }

    // ============================================================
    // ADMIN: OWNER & VERIFIER FUNCTIONS
    // ============================================================

    function updateVaultName(string memory _newName) public onlyOwner {
        require(bytes(_newName).length > 0, "Vault name cannot be empty");
        vaultName = _newName;
    }

    function updateTargetCapUSDX(uint256 _newCap) public onlyOwner {
        require(_newCap >= totalDeposited, "New cap must be >= current deposited");
        targetCapUSDX = _newCap;
    }

    function freeze() public onlyOwner {
        _frozen = true;
        emit EmergencyPause();
    }

    function unfreeze() public onlyOwner {
        _frozen = false;
        emit EmergencyUnpause();
    }

    // ============================================================
    // ADMIN: FUND REWARDS (Dự phòng trả lãi)
    // ============================================================

    function fundRewards(uint256 amount) public whenNotPaused {
        require(amount > 0, "Amount must be > 0");
        require(yieldReserve + amount >= yieldReserve, "Overflow");
        require(yieldReserve + amount <= type(uint256).max, "Yield reserve overflow");

        // Transfer từ Admin tới Vault
        usdX.transferFrom(msg.sender, address(this), amount);

        yieldReserve += amount;
        totalFundedRewards += amount;

        emit FundRewards(msg.sender, amount, yieldReserve);
    }

    function getTotalFundedRewards() public view returns (uint256) {
        return totalFundedRewards;
    }

    // ============================================================
    // DEPOSIT / WITHDRAW / REDEMPT
    // ============================================================

    function deposit(uint256 amount) external whenNotPaused {
        require(amount > 0, "Deposit amount must be > 0");
        require(totalDeposited + amount <= targetCapUSDX, "Deposit exceeds vault capacity");
        require(usdX.allowance(msg.sender, address(this)) >= amount, "Insufficient allowance");

        // Transfer từ user sang vault
        usdX.transferFrom(msg.sender, address(this), amount);

        // Chốt lãi cũ trước khi cộng thêm tiền gộp
        _settleYield(msg.sender);

        // Cập nhật thông tin nhà đầu tư
        UserInfo storage user = _users[msg.sender];
        if (user.depositedAmount == 0) {
            user.depositTimestamp = block.timestamp;
            user.maturityDate = block.timestamp + 365 days; // Bắt đầu tính kỳ đầu tư
        } else {
            user.depositTimestamp = block.timestamp;
            user.maturityDate = block.timestamp + 365 days;
        }
        user.depositedAmount += amount;

        totalDeposited += amount;

        emit Deposit(msg.sender, amount, totalDeposited);
    }

    function withdraw(uint256 amount) external whenNotPaused {
        require(amount > 0, "Withdraw amount must be > 0");

        UserInfo storage user = _users[msg.sender];
        require(user.depositedAmount >= amount, "Insufficient principal");

        // Chốt lãi cũ trước khi rút gốc
        _settleYield(msg.sender);

        // Chống over-withdraw
        require(usdX.balanceOf(address(this)) >= amount, "Insufficient vault balance");

        // Trừ tiền gốc
        user.depositedAmount -= amount;
        usdX.transfer(msg.sender, amount);
        totalDeposited -= amount;

        emit Withdraw(msg.sender, amount, user.depositedAmount);
    }

    function redeem() external whenNotPaused {
        UserInfo storage user = _users[msg.sender];
        require(user.depositedAmount > 0, "No principal deposited");

        _settleYield(msg.sender);

        uint256 amount = user.depositedAmount;
        require(amount > 0, "Nothing to redeem");
        require(usdX.balanceOf(address(this)) >= amount, "Insufficient vault balance");

        user.depositedAmount = 0;
        usdX.transfer(msg.sender, amount);
        totalDeposited -= amount;

        emit Withdraw(msg.sender, amount, 0);
    }

    // ============================================================
    // YIELD CALCULATION & CLAIM
    // ============================================================

    function calculateYieldOwed(address user) public view returns (uint256) {
        return _users[user].unclaimedYield;
    }

    function calculatePendingYield(address user) public view returns (uint256) {
        UserInfo storage info = _users[user];
        if (info.depositedAmount == 0) return 0;

        uint256 apyBps = oracle.verifiedApyBps();
        uint256 elapsed = block.timestamp > info.depositTimestamp
            ? block.timestamp - info.depositTimestamp
            : 0;

        // Simple Interest: yield = principal * APY_bps * elapsed / (10000 * 365 days)
        return (info.depositedAmount * apyBps * elapsed) / (10000 * 365 days);
    }

    function claimYield() external whenNotPaused {
        UserInfo storage user = _users[msg.sender];
        require(user.depositedAmount > 0, "No principal deposited");

        // Chốt tất cả lãi đang sinh ra vào unclaimedYield
        _settleYield(msg.sender);

        uint256 totalToClaim = user.unclaimedYield;
        if (totalToClaim == 0) return;

        // Kiểm tra YIELD RESERVE (lãi được trả từ reserve, không mai mội vốn)
        require(yieldReserve >= totalToClaim, "Insufficient yield reserve");

        // Kiểm tra số dư thực tế
        require(usdX.balanceOf(address(this)) >= totalToClaim, "Insufficient yield in vault");

        // Transfer lãi từ reserve cho user
        usdX.transfer(msg.sender, totalToClaim);
        user.claimedYield += totalToClaim;
        user.unclaimedYield = 0;
        user.depositTimestamp = block.timestamp;

        // Reserve giảm khi nhận lãi
        yieldReserve -= totalToClaim;

        emit YieldClaimed(msg.sender, totalToClaim, user.claimedYield);
    }

    // ============================================================
    // USER INFO & STATISTICS
    // ============================================================

    function getUserInfo(address user) external view returns (
        uint256 depositedAmount,
        uint256 depositTimestamp,
        uint256 claimedYield,
        uint256 unclaimedYield,
        uint256 maturityDate,
        uint256 ownershipBps
    ) {
        UserInfo storage info = _users[user];
        ownershipBps = totalDeposited > 0
            ? (info.depositedAmount * 10000) / totalDeposited
            : 0;

        return (
            info.depositedAmount,
            info.depositTimestamp,
            info.claimedYield,
            info.unclaimedYield,
            info.maturityDate,
            ownershipBps
        );
    }

    function getUserOwnershipBps(address user) public view returns (uint256) {
        if (totalDeposited == 0) return 0;
        return (_users[user].depositedAmount * 10000) / totalDeposited;
    }

    // ============================================================
    // INTERNAL
    // ============================================================

    function _settleYield(address user) internal {
        UserInfo storage info = _users[user];
        if (info.depositedAmount == 0) return;

        uint256 pending = calculatePendingYield(user);
        if (pending > 0) {
            info.unclaimedYield += pending;
            info.depositTimestamp = block.timestamp;
        }
    }
}
