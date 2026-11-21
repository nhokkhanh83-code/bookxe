import React from "react";

/** StatCard — Thẻ thống kê RWA Vault */
export default function StatCard({
  title,
  value,
  subtitle,
  icon,
  iconBg,
  iconColor,
  badge,
  children,
}) {
  return (
    <div className="glass-card p-5 rounded-xl hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{title}</p>
          <h3 className="text-2xl font-bold text-dark-900 number-mono">{value}</h3>
          {subtitle && (
            <p className={`text-sm mt-1 ${subtitle.className || "text-gray-500"}`}>{subtitle.text}</p>
          )}
        </div>
        {icon && (
          <div className={`w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center ${iconColor}`}>
            {icon}
          </div>
        )}
      </div>
      {badge && <div className="mb-2">{badge}</div>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

// StatCard default export handled above
