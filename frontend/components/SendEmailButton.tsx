"use client";

import * as React from "react";
import { Mail, Loader2, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { triggerSendEmail, type SendEmailResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface SendEmailButtonProps {
  userId: string;
}

const getEmailTypeBadgeStyle = (type: string | undefined) => {
  if (!type) return "bg-slate-700/50 text-slate-300 border-slate-600/50";
  const t = type.toLowerCase();
  if (t.includes("retention") || t.includes("churn"))
    return "bg-red-500/15 text-red-400 border-red-500/30";
  if (t.includes("cart"))
    return "bg-amber-500/15 text-amber-400 border-amber-500/30";
  if (t.includes("recommend") || t.includes("upsell"))
    return "bg-indigo-500/15 text-indigo-400 border-indigo-500/30";
  if (t.includes("review"))
    return "bg-violet-500/15 text-violet-400 border-violet-500/30";
  return "bg-indigo-500/15 text-indigo-400 border-indigo-500/30";
};

export default function SendEmailButton({ userId }: SendEmailButtonProps) {
  const [open, setOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<SendEmailResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const handleSend = async () => {
    setLoading(true);
    setOpen(true);
    setResult(null);
    setError(null);
    try {
      const res = await triggerSendEmail(userId);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to trigger email campaign");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        id="send-campaign-btn"
        onClick={handleSend}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-semibold text-sm text-white cursor-pointer
          bg-gradient-to-r from-indigo-600 to-violet-600
          hover:from-indigo-500 hover:to-violet-500
          transition-all duration-200
          shadow-[0_0_20px_rgba(99,102,241,0.25)] hover:shadow-[0_0_28px_rgba(99,102,241,0.4)]
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0f1e]
          disabled:opacity-40 disabled:pointer-events-none"
      >
        <Mail className="h-4 w-4" />
        Send Campaign Email
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Email Dispatch Status</DialogTitle>
            <DialogDescription>
              Orchestrating campaign decisioning and LLM generation pipeline…
            </DialogDescription>
          </DialogHeader>

          <div className="py-6 flex flex-col items-center justify-center min-h-[180px] text-center space-y-4">
            {loading && (
              <div className="space-y-4">
                <div className="relative">
                  <Loader2 className="h-12 w-12 animate-spin text-indigo-500 mx-auto" />
                  <div className="absolute inset-0 h-12 w-12 mx-auto rounded-full bg-indigo-500/10 animate-ping" />
                </div>
                <p className="text-sm font-medium text-slate-300">
                  Running decision engine &amp; generating content…
                </p>
                <p className="text-xs text-slate-500">This may take 5–15 seconds</p>
              </div>
            )}

            {error && (
              <div className="space-y-3">
                <XCircle className="h-12 w-12 text-red-400 mx-auto" />
                <p className="text-sm font-semibold text-slate-100">
                  Pipeline Execution Failed
                </p>
                <p className="text-xs text-slate-400 max-w-sm leading-relaxed">{error}</p>
              </div>
            )}

            {!loading && !error && result && (
              <div className="w-full space-y-4">
                {result.status === "skipped" ? (
                  <>
                    <AlertTriangle className="h-12 w-12 text-amber-400 mx-auto" />
                    <div>
                      <p className="text-sm font-semibold text-slate-100">
                        Dispatch Skipped
                      </p>
                      <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto leading-relaxed">
                        This user is within the email cooldown period (
                        {result.reason || "active"}).
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-12 w-12 text-emerald-400 mx-auto" />
                    <div className="space-y-3">
                      <p className="text-sm font-semibold text-slate-100">
                        Email Dispatched Successfully!
                      </p>
                      {/* Result details card */}
                      <div className="rounded-lg border border-[rgba(99,102,241,0.2)] bg-[rgba(15,23,41,0.7)] p-4 text-left space-y-3 max-w-xs mx-auto">
                        {result.email_type && (
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-400 font-medium">Campaign Type</span>
                            <span
                              className={`text-xs font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wide ${getEmailTypeBadgeStyle(result.email_type)}`}
                            >
                              {result.email_type.replace(/_/g, " ")}
                            </span>
                          </div>
                        )}
                        {result.subject && (
                          <div>
                            <span className="text-xs text-slate-400 font-medium block mb-1">Subject</span>
                            <span className="text-sm text-slate-100 font-medium italic leading-snug">
                              &ldquo;{result.subject}&rdquo;
                            </span>
                          </div>
                        )}
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-400 font-medium">Status</span>
                          <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            {result.status}
                          </span>
                        </div>
                        {result.tokens_used !== undefined && (
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-400 font-medium">LLM Tokens</span>
                            <span className="text-xs text-slate-500 font-medium">
                              {result.tokens_used > 0
                                ? result.tokens_used.toLocaleString()
                                : "0 (fallback)"}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              onClick={() => setOpen(false)}
              variant="secondary"
              className="w-full sm:w-auto"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
