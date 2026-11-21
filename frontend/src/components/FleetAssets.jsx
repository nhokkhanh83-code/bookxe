import React from "react";

/** FleetAssets — Đội xe ô tô & xe máy BookXe cho thuê tại Đà Nẵng */
export default function FleetAssets() {
  const vehicles = [
    { name: "Honda CR-V 2025", plate: "43A-666.66", monthlyRent: 2400, status: "Đang vận hành", fill: 88, value: 45000 },
    { name: "Toyota Vios 2023", plate: "43A-528.19", monthlyRent: 1350, status: "Đang vận hành", fill: 92, value: 22000 },
    { name: "VinFast VF8 Eco", plate: "43A-880.01", monthlyRent: 2200, status: "Đang vận hành", fill: 80, value: 48000 },
    { name: "Mazda 3 Luxury", plate: "43A-712.45", monthlyRent: 1600, status: "Đang vận hành", fill: 84, value: 28000 },
    { name: "Hyundai Accent 2024", plate: "43A-490.22", monthlyRent: 1200, status: "Đang bảo dưỡng", fill: 45, value: 20000 },
    { name: "Lô 5 xe Honda SH 160i", plate: "43D1-901.xx", monthlyRent: 1850, status: "Đang vận hành", fill: 95, value: 21000 },
    { name: "Lô 10 xe Honda AirBlade 2026", plate: "43D1-812.xx", monthlyRent: 2100, status: "Đang vận hành", fill: 90, value: 20000 },
    { name: "Lô 5 xe Yamaha NVX 155", plate: "43D1-745.xx", monthlyRent: 1150, status: "Đang vận hành", fill: 76, value: 11000 },
  ];

  const statusColors = {
    "Đang vận hành": "bg-emerald-50 text-emerald-600 border-emerald-200",
    "Đang bảo dưỡng": "bg-amber-50 text-amber-600 border-amber-200",
    "Đang chờ": "bg-gray-50 text-gray-500 border-gray-200",
  };

  return (
    <div className="glass-card p-5 rounded-xl h-full">
      <h3 className="text-lg font-bold text-dark-900 mb-4 flex items-center gap-2">
        🚗 Đội xe BookXe — Cho thuê tại Đà Nẵng
        <span className="badge-emerald">25 xe</span>
      </h3>

      <div className="space-y-3 max-h-[320px] overflow-y-auto pr-2">
        {vehicles.map((vehicle, idx) => (
          <div
            key={idx}
            className="flex items-center gap-4 p-3 rounded-lg border border-gray-100 hover:border-gray-200 transition-all"
          >
            {/* Vehicle icon */}
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center">
              <svg className="w-7 h-7 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="4" y="9" width="16" height="7" rx="1" />
                <path d="M6 22h12M6 22l1.5-4M18 22l-1.5-4" />
                <circle cx="7.5" cy="9" r="2" />
                <circle cx="16.5" cy="9" r="2" />
              </svg>
            </div>

            {/* Vehicle info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <h4 className="font-semibold text-dark-900 text-sm truncate">{vehicle.name}</h4>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${statusColors[vehicle.status] || statusColors["Đang vận hành"]}`}>
                  {vehicle.status}
                </span>
              </div>
              <p className="text-xs text-gray-500 font-mono">Biển số: {vehicle.plate}</p>
            </div>

            {/* Value */}
            <div className="text-right min-w-[70px]">
              <p className="text-xs text-gray-500">Giá trị xe</p>
              <p className="font-semibold text-dark-900 number-mono text-sm">
                {vehicle.value.toLocaleString("vi-VN")} USDX
              </p>
            </div>

            {/* Monthly rent */}
            <div className="text-right min-w-[80px]">
              <p className="text-xs text-gray-500">Thuê/tháng</p>
              <p className="font-semibold text-emerald-600 number-mono text-sm">
                ~{vehicle.monthlyRent.toLocaleString("vi-VN")} USDX
              </p>
            </div>

            {/* Fill level */}
            <div className="w-20">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{vehicle.fill}%</span>
                <span className="text-emerald-600">Lấp đầy</span>
              </div>
              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full progress-bar ${vehicle.fill >= 80 ? "bg-emerald-500" : vehicle.fill >= 50 ? "bg-amber-400" : "bg-red-400"}`}
                  style={{ width: `${vehicle.fill}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// FleetAssets default export handled above
