import React from "react";

interface FormatMoneyProps {
  amount: number | null | undefined;
  currency?: string;
  className?: string;
  showCurrency?: boolean;
}

export const formatINR = (val: number | null | undefined): string => {
  if (val === null || val === undefined || isNaN(val)) return "₹0.00";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(val);
};

export const FormatMoney: React.FC<FormatMoneyProps> = ({
  amount,
  className = "",
}) => {
  return <span className={`font-mono ${className}`}>{formatINR(amount)}</span>;
};

