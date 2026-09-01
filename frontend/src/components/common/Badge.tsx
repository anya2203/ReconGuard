import React from "react";

interface BadgeProps {
  variant?:
    | "auto_resolve"
    | "ai_investigation"
    | "human_review"
    | "escalate"
    | "high"
    | "medium"
    | "low"
    | "exact"
    | "fuzzy"
    | "aggregation"
    | "neutral";
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ variant = "neutral", children, className = "" }) => {
  const getVariantStyles = () => {
    switch (variant) {
      case "auto_resolve":
        return "bg-emerald-50 text-emerald-700 border-emerald-200 font-medium";
      case "ai_investigation":
        return "bg-sky-50 text-sky-700 border-sky-200 font-medium";
      case "human_review":
        return "bg-amber-50 text-amber-700 border-amber-200 font-medium";
      case "escalate":
      case "high":
        return "bg-rose-50 text-rose-700 border-rose-200 font-medium";
      case "medium":
        return "bg-amber-50 text-amber-700 border-amber-200 font-medium";
      case "low":
        return "bg-slate-50 text-slate-600 border-slate-200 font-medium";
      case "exact":
        return "bg-blue-50 text-blue-700 border-blue-200 font-medium";
      case "fuzzy":
        return "bg-indigo-50 text-indigo-700 border-indigo-200 font-medium";
      case "aggregation":
        return "bg-purple-50 text-purple-700 border-purple-200 font-medium";
      case "neutral":
      default:
        return "bg-slate-100 text-slate-700 border-slate-200 font-medium";
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs border tracking-tight ${getVariantStyles()} ${className}`}
    >
      {children}
    </span>
  );
};

export const DecisionBadge: React.FC<{ decision: string }> = ({ decision }) => {
  const norm = decision.toUpperCase();
  let variant: BadgeProps["variant"] = "neutral";
  if (norm === "AUTO_RESOLVE") variant = "auto_resolve";
  else if (norm === "AI_INVESTIGATION") variant = "ai_investigation";
  else if (norm === "HUMAN_REVIEW") variant = "human_review";
  else if (norm === "ESCALATE") variant = "escalate";

  return <Badge variant={variant}>{decision.replace("_", " ")}</Badge>;
};

export const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const norm = priority.toUpperCase();
  let variant: BadgeProps["variant"] = "neutral";
  if (norm === "HIGH") variant = "high";
  else if (norm === "MEDIUM") variant = "medium";
  else if (norm === "LOW") variant = "low";

  return <Badge variant={variant}>{priority}</Badge>;
};

