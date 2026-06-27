import React from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export interface VerificationResult {
    evidence_id: string;
    overall_status: string;
    verdict: string;
    hashes: {
        recomputed_from_file: string;
        stored_on_blockchain: string;
        stored_in_db: string;
        match: boolean;
    };
    blockchain: {
        tx_hash?: string;
        provider?: string;
        timestamp?: string;
        uploader_role?: string;
        contract_address?: string;
        chain_id?: string | number;
        block_number?: number;
        gas_used?: number;
        network?: string;
        stored_hash?: string;
        previous_hash?: string;
    };
}

interface BlockchainVerificationDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    result: VerificationResult | null;
    loading: boolean;
}

export function BlockchainVerificationDialog({
    open,
    onOpenChange,
    result,
    loading,
}: BlockchainVerificationDialogProps) {
    if (!result && !loading) return null;

    const isVerified = result?.hashes?.match;
    const evidenceId = result?.evidence_id || "Unknown Evidence";
    const statusLabel = isVerified ? "✔ AUTHENTIC" : "✖ TAMPERED";
    const statusTitle = isVerified ? "VERIFIED" : "TAMPERED";
    const statusMessage = isVerified ? "Authentic Evidence" : "Integrity Check Failed";
    const statusDetail = isVerified ? "No Tampering Detected" : "Evidence Modified After Upload";

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md rounded-3xl border border-slate-200 bg-white shadow-xl">
                <DialogHeader className="text-center pb-4 border-b border-slate-200">
                    <DialogTitle className="text-2xl font-semibold text-slate-900">
                        Evidence Verification
                    </DialogTitle>
                </DialogHeader>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-12 space-y-4">
                        <div className="h-16 w-16 rounded-full border-4 border-slate-200 border-t-slate-500 animate-spin"></div>
                        <p className="text-sm text-slate-500">Verifying evidence, please wait...</p>
                    </div>
                ) : (
                    <div className="space-y-6 px-6 py-6">
                        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
                            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Evidence ID</p>
                            <p className="mt-2 text-lg font-semibold text-slate-900">{evidenceId}</p>
                        </div>

                        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <p className="text-3xl font-semibold text-slate-900">{statusTitle}</p>
                                    <p className="mt-2 text-sm text-slate-600">{statusMessage}</p>
                                </div>
                                <Badge
                                    variant="outline"
                                    className={`rounded-full px-4 py-2 text-sm font-semibold ${isVerified ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-700' : 'border-red-500/20 bg-red-500/10 text-red-700'}`}>
                                    {statusLabel}
                                </Badge>
                            </div>
                            <p className="mt-6 text-sm text-slate-600">{statusDetail}</p>
                        </div>
                    </div>
                )}

                <DialogFooter className="pt-0 px-6 pb-6">
                    <Button className="w-full" onClick={() => onOpenChange(false)}>
                        Close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
