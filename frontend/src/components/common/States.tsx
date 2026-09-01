import React from "react";
import { AlertCircle, Inbox, Loader2, RefreshCw } from "lucide-react";

export const LoadingState: React.FC<{ message?: string }> = ({
  message = "Loading operational reconciliation data...",
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <Loader2 className="w-7 h-7 text-sky-600 animate-spin mb-3" />
      <p className="text-sm font-medium text-slate-700">{message}</p>
      <p className="text-xs text-slate-400 mt-1">Connecting to ReconGuard FastAPI backend</p>
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
}> = ({
  title = "Unable to load data",
  message = "Check that the ReconGuard API backend is running at http://127.0.0.1:8000",
  onRetry,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 bg-rose-50/50 border border-rose-200 rounded-lg text-center my-4">
      <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center mb-3">
        <AlertCircle className="w-5 h-5 text-rose-600" />
      </div>
      <h4 className="text-sm font-semibold text-rose-900 mb-1">{title}</h4>
      <p className="text-xs text-rose-700 max-w-md mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-medium transition-colors shadow-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry Request
        </button>
      )}
    </div>
  );
};

export const EmptyState: React.FC<{
  title?: string;
  message?: string;
  icon?: React.ReactNode;
}> = ({
  title = "No records found",
  message = "No reconciliation cases match the current filter criteria.",
  icon,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-slate-50/50 border border-dashed border-slate-200 rounded-lg">
      <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
        {icon || <Inbox className="w-5 h-5" />}
      </div>
      <h4 className="text-sm font-semibold text-slate-800 mb-1">{title}</h4>
      <p className="text-xs text-slate-500 max-w-sm">{message}</p>
    </div>
  );
};

