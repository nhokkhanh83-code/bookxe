# 🚗 BookXe RWA Vault — Frontend

React + Vite + Tailwind CSS + Ethers.js v6 — Dashboard cho BookXe RWA Vault

## 🚀 Cài đặt & Chạy

```bash
# Cài đặt dependencies
npm install

# Chạy dev server (http://localhost:5173)
npm run dev

# Build cho production
npm run build
```

## 🔗 Kết nối với Backend

Sau khi chạy `npm run deploy:local` (hoặc `npm run deploy:fuji`), file `src/contracts.json`
sẽ được tự động tạo/cập nhật với địa chỉ Contract và ABI.

## 🎨 Bảng màu

| Màu | Sử dụng |
|-----|---------|
| `#FFFFFF` (35%) | Nền thẻ dữ liệu, form Deposit/Withdraw |
| `#0F172A` (16%) | Navbar, Footer, TVL, nút chính |
| `#64748B`, `#E2E8F0`, `#F8FAFC` (14%) | Nền trang, viền, nhãn |
| `#10B981` | APY 12.0%, huy hiệu *Verified* |
| `#2563EB` | Connect Wallet, Deposit |

## 🎮 Chế độ Chạy

1. **Demo Mode** (mặc định) — Giả lập toàn bộ logic trên trình duyệt, không cần MetaMask
2. **Wallet Mode** — Kết nối MetaMask với Smart Contract trên Fuji Testnet/Localhost

## 📁 Cấu trúc Component

```
src/
├── App.jsx                    # Dashboard chính
├── components/
│   ├── Header.jsx            # Logo, Network, Faucet, Balance, Connect
│   ├── StatCard.jsx          # Thẻ thống kê tổng quát
│   ├── FleetAssets.jsx       # Danh sách xe thực tế
│   ├── OraclePanel.jsx       # Báo cáo tài chính từ Oracle
│   ├── VaultForm.jsx         # Form Deposit/Withdraw
│   └── TxHistory.jsx         # Lịch sử giao dịch
├── hooks/
│   └── useVault.js           # Hook quản lý kết nối + state
├── lib/
│   └── demoVault.js          # Demo Vault simulation class
└── utils/
    └── format.js             # Utility format functions
```

---

**Kết nối lên được ngay — Demo đầu tiên nhận Faucet ngay lập tức!**
