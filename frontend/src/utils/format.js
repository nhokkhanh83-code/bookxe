// Formatting utilities for BookXe RWA Vault Frontend

/** Format a BigInt number with decimal places using ethers formatUnits logic */
export function formatNumber(value, decimals = 6, stripTrailingZeros = true) {
  if (value === null || value === undefined || value === 0n) return "0";

  let str = value.toString();
  const negative = str.startsWith("-");
  if (negative) str = str.slice(1);

  const d = Number(decimals);
  if (str.length <= d) {
    str = str.padStart(d + 1, "0");
  }

  const intPart = str.slice(0, str.length - d);
  let decPart = str.slice(str.length - d);

  // Remove trailing zeros from decimal part
  if (stripTrailingZeros) {
    decPart = decPart.replace(/0+$/, "");
  }

  const result = decPart ? `${intPart}.${decPart}` : intPart;
  return negative ? `-${result}` : result;
}

/** Format USDX with commas and decimals */
export function formatUSDX(value, decimals = 6) {
  const num = formatNumber(value, decimals, false);
  const [intPart, decPart] = num.split(".");
  const intFormatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return decPart ? `${intFormatted}.${decPart}` : intFormatted;
}

/** Format a percentage (bps to %) */
export function formatAPY(apyBps) {
  return (apyBps / 100).toFixed(2);
}

/** Format percentage (0-100 range) */
export function formatPct(pct, decimals = 2) {
  return pct.toFixed(decimals);
}

/** Format a timestamp to human-readable date */
export function formatDateTime(timestamp) {
  if (!timestamp) return "N/A";
  const date = new Date(Number(timestamp) * 1000);
  return date.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Format seconds into readable duration */
export function formatDuration(seconds) {
  const s = Math.floor(seconds);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
  return `${Math.floor(s / 86400)} ngày`;
}

/** Parse user input string to BigInt given decimals */
export function parseAmount(str, decimals = 6) {
  if (!str || str.trim() === "") return 0n;
  const clean = str.replace(/[,\s]/g, "");
  return BigInt(Math.round(parseFloat(clean) * 10 ** decimals));
}

/** Round BigInt to a number of decimals */
export function roundToDecimals(value, fromDecimals, toDecimals) {
  const shift = fromDecimals - toDecimals;
  if (shift <= 0) return value * 10n ** BigInt(-shift);
  return value / 10n ** BigInt(shift);
}

/** Get a random Ethereum address for demo */
export function getDemoAddress(index) {
  const hash = `0x${Math.random().toString(16).slice(2).padStart(40, "0")}`;
  return hash;
}

export { getDemoAddress as getRandomAddress };
