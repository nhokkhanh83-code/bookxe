// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FleetFinancialOracle - Fleet Financial Oracle
 * @notice Giả lập bên thứ 3 kiểm toán & xác minh báo cáo tài chính của
 *         công ty vận hành đội xe (VD: "Green Future EV Fleet")
 *
 * @dev GIAI ĐOẠN 2: Xuất bản báo cáo - Có thứ tự báo cáo, người xác minh
 */
contract FleetFinancialOracle {
    // ============================================================
    // STATE
    // ============================================================

    string public operatorName;
    string public reportPeriod;
    uint256 public totalVehicles;
    uint256 public grossRevenueUSD;
    uint256 public operatingCostUSD;
    uint256 public netProfitUSD;
    uint256 public verifiedApyBps;

    string public auditorName;
    string public reportHash;
    uint256 public lastUpdated;

    address public verifierAddress;
    uint256 public reportStatus; // 1=draft, 2=pending, 3=verified, 4=superseded

    // Thông tin báo cáo trước đó (để làm cơ sở so sánh)
    uint256 private _previousApyBps;

    // Giới hạn APY được phép (min, max)
    uint256 public minAPYBps;
    uint256 public maxAPYBps;

    // Events
    event FinancialReportUpdated(
        uint256 indexed reportSequence,
        string operatorName,
        string reportPeriod,
        uint256 totalVehicles,
        uint256 grossRevenueUSD,
        uint256 operatingCostUSD,
        uint256 netProfitUSD,
        uint256 verifiedApyBps,
        string auditorName,
        string reportHash,
        uint256 lastUpdated,
        address verifierAddress
    );
    event ReportVerified(uint256 indexed reportSequence);
    event APYUpdated(uint256 oldAPYBps, uint256 newAPYBps, uint256 effectiveAt);

    // ============================================================
    // CONSTRUCTOR
    // ============================================================

    constructor(
        address _owner,
        address _verifier,
        uint256 _minAPYBps,
        uint256 _maxAPYBps
    ) {
        owner = _owner;
        verifierAddress = _verifier;
        minAPYBps = _minAPYBps;
        maxAPYBps = _maxAPYBps;
        reportStatus = 1; // Draft
    }

    // ============================================================
    // STATE: Owner, Verifier
    // ============================================================

    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyVerifier() {
        require(msg.sender == verifierAddress, "Not authorized verifier");
        _;
    }

    // ============================================================
    // MOCK V3: LỊCH SỬ BÁO CÁO (REPORT HISTORY)
    // ============================================================

    struct ReportHistory {
        string operatorName;
        string reportPeriod;
        uint256 totalVehicles;
        uint256 grossRevenueUSD;
        uint256 operatingCostUSD;
        uint256 netProfitUSD;
        uint256 verifiedApyBps;
        string auditorName;
        string reportHash;
        uint256 lastUpdated;
    }

    ReportHistory[] private _reportHistory;

    /**
     * @notice Lấy lịch sử các báo cáo đã publish
     * @return Array các báo cáo đã xác minh
     */
    function getReportHistory() public view returns (ReportHistory[] memory) {
        // Chỉ trả về các báo cáo đã verify
        uint256 verifiedCount = 0;
        for (uint256 i = 0; i < _reportHistory.length; i++) {
            if (_reportHistory[i].lastUpdated > 0) verifiedCount++;
        }

        ReportHistory[] memory result = new ReportHistory[](verifiedCount);
        uint256 idx = 0;
        for (uint256 i = 0; i < _reportHistory.length; i++) {
            if (_reportHistory[i].lastUpdated > 0) {
                result[idx] = _reportHistory[i];
                idx++;
            }
        }
        return result;
    }

    /**
     * @notice Lấy số lượng báo cáo đã publish
     */
    function getReportCount() public view returns (uint256) {
        return _reportHistory.length;
    }

    /**
     * @notice Lấy báo cáo hiện tại theo index
     */
    function getReportAt(uint256 index) public view returns (
        string memory, string memory, uint256, uint256,
        uint256, uint256, uint256, string memory,
        string memory, uint256
    ) {
        require(index < _reportHistory.length, "Index out of bounds");
        ReportHistory storage r = _reportHistory[index];
        return (
            r.operatorName, r.reportPeriod, r.totalVehicles, r.grossRevenueUSD,
            r.operatingCostUSD, r.netProfitUSD, r.verifiedApyBps, r.auditorName,
            r.reportHash, r.lastUpdated
        );
    }

    // ============================================================
    // ADMIN: Cập nhật APY limits
    // ============================================================

    function updateAPYLIMITS(uint256 _minAPYBps, uint256 _maxAPYBps) public onlyOwner {
        require(_minAPYBps <= _maxAPYBps, "Min must be <= max");
        minAPYBps = _minAPYBps;
        maxAPYBps = _maxAPYBps;
    }

    // ============================================================
    // V3: UPDATE FINANCIAL REPORT (Mock - Owner or Verifier)
    // ============================================================

    /**
     * @notice Cập nhật báo cáo tài chính mới (Owner hoặc Verifier)
     * @dev Ghi vào _reportHistory, update verifiedApyBps
     */
    function updateFinancialReport(
        string memory _operatorName,
        string memory _reportPeriod,
        uint256 _totalVehicles,
        uint256 _grossRevenueUSD,
        uint256 _operatingCostUSD,
        uint256 _netProfitUSD,
        uint256 _verifiedApyBps,
        string memory _auditorName,
        string memory _reportHash
    ) public {
        require(
            msg.sender == owner || msg.sender == verifierAddress,
            "Only Owner or Verifier can update reports"
        );

        // Kiểm tra APY trong giới hạn
        require(_verifiedApyBps >= minAPYBps, "APY below minimum");
        require(_verifiedApyBps <= maxAPYBps, "APY above maximum");

        // Lưu vào current state
        operatorName = _operatorName;
        reportPeriod = _reportPeriod;
        totalVehicles = _totalVehicles;
        grossRevenueUSD = _grossRevenueUSD;
        operatingCostUSD = _operatingCostUSD;
        netProfitUSD = _netProfitUSD;
        verifiedApyBps = _verifiedApyBps;
        auditorName = _auditorName;
        reportHash = _reportHash;
        lastUpdated = block.timestamp;

        // Kiểm tra trước khi thêm vào history
        // Nếu có báo cáo trước đó với cùng APY và cùng kỳ, bỏ qua
        bool alreadyExists = false;
        for (uint256 i = 0; i < _reportHistory.length; i++) {
            if (
                keccak256(bytes(_reportPeriod)) == keccak256(bytes(_reportHistory[i].reportPeriod)) &&
                _verifiedApyBps == _reportHistory[i].verifiedApyBps
            ) {
                alreadyExists = true;
                break;
            }
        }

        // Thêm vào history nếu chưa tồn tại (hoặc nếu là báo cáo đầu tiên)
        if (!alreadyExists && _reportHistory.length == 0) {
            _reportHistory.push(ReportHistory({
                operatorName: _operatorName,
                reportPeriod: _reportPeriod,
                totalVehicles: _totalVehicles,
                grossRevenueUSD: _grossRevenueUSD,
                operatingCostUSD: _operatingCostUSD,
                netProfitUSD: _netProfitUSD,
                verifiedApyBps: _verifiedApyBps,
                auditorName: _auditorName,
                reportHash: _reportHash,
                lastUpdated: block.timestamp
            }));
            reportStatus = 3; // Verified
        } else if (!alreadyExists) {
            // Có báo cáo mới nhưng vẫn thêm vào history
            _reportHistory.push(ReportHistory({
                operatorName: _operatorName,
                reportPeriod: _reportPeriod,
                totalVehicles: _totalVehicles,
                grossRevenueUSD: _grossRevenueUSD,
                operatingCostUSD: _operatingCostUSD,
                netProfitUSD: _netProfitUSD,
                verifiedApyBps: _verifiedApyBps,
                auditorName: _auditorName,
                reportHash: _reportHash,
                lastUpdated: block.timestamp
            }));
            reportStatus = 3;
        }

        emit FinancialReportUpdated(
            _reportHistory.length - 1,
            _operatorName,
            _reportPeriod,
            _totalVehicles,
            _grossRevenueUSD,
            _operatingCostUSD,
            _netProfitUSD,
            _verifiedApyBps,
            _auditorName,
            _reportHash,
            block.timestamp,
            msg.sender
        );
    }

    /**
     * @notice Lấy thông tin của báo cáo hiện tại
     */
    function getCurrentReport() public view returns (
        string memory, string memory, uint256, uint256,
        uint256, uint256, uint256, string memory,
        string memory, uint256, address
    ) {
        return (
            operatorName, reportPeriod, totalVehicles, grossRevenueUSD,
            operatingCostUSD, netProfitUSD, verifiedApyBps, auditorName,
            reportHash, lastUpdated, verifierAddress
        );
    }

    /**
     * @notice Lấy mức APY (%) dưới dạng phần trăm
     */
    function getApyPercent() public view returns (uint256) {
        return verifiedApyBps / 100;
    }

    /**
     * @notice Lấy trạng thái của báo cáo hiện tại
     */
    function getReportStatus() public view returns (uint256) {
        return reportStatus;
    }
}
