// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MockUSDX - BookXe USD Stablecoin
 * @notice ERC-20 token mô phỏng USDT/USDC cho môi trường test/PoC
 * @dev Token này có faucet miễn phí để người dùng/giám khảo nhận 10,000 USDX để test
 */
contract MockUSDX {
    string public constant name = "BookXe USD";
    string public constant symbol = "USDX";
    uint8 public constant decimals = 6;

    uint256 public totalSupply;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    /**
     * @notice Mỗi địa chỉ có thể nhận 10,000 USDX miễn phí để test
     */
    function faucet() external returns (uint256) {
        uint256 amount = 10_000 * 10 ** decimals;
        _mint(msg.sender, amount);
        return amount;
    }

    function balanceOf(address account) public view returns (uint256) {
        return _balances[account];
    }

    function allowance(address owner, address spender) public view returns (uint256) {
        return _allowances[owner][spender];
    }

    function approve(address spender, uint256 amount) public returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        require(to != address(0), "Transfer to zero address");
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        unchecked {
            _balances[msg.sender] -= amount;
            _balances[to] += amount;
        }
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(to != address(0), "Transfer to zero address");
        require(from != address(0), "Transfer from zero address");

        uint256 allowed = _allowances[from][msg.sender];
        if (allowed != type(uint256).max) {
            require(allowed >= amount, "Insufficient allowance");
            unchecked {
                _allowances[from][msg.sender] = allowed - amount;
            }
        }

        require(_balances[from] >= amount, "Insufficient balance");
        unchecked {
            _balances[from] -= amount;
            _balances[to] += amount;
        }
        emit Transfer(from, to, amount);
        return true;
    }

    function _mint(address to, uint256 amount) internal {
        require(to != address(0), "Mint to zero address");
        _balances[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "Approve from zero address");
        require(spender != address(0), "Approve to zero address");
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
}
