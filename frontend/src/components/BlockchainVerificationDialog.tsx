import React from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ShieldCheck, AlertOctagon, Clock, FileText, CheckCircle2, Copy, ExternalLink, Box } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface VerificationResult {
    evidence_id: string;
    overall_status: string;
    verification_details: {
        verified: boolean;
        status: string;
        details: string;
        blockchain_record?: {
            timestamp: string;
            uploader_role: string;
            stored_hash: string;
        };
    };
    tx_hash: string;
    blockchain_provider: string;
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
    const { toast } = useToast();

    const handleCopyHash = () => {
        if (result?.tx_hash) {
            navigator.clipboard.writeText(result.tx_hash);
            toast({
                title: "Copied",
                description: "Transaction hash copied to clipboard",
            });
        }
    };

    if (!result && !loading) return null;

    const isVerified = result?.verification_details?.verified;
    const status = result?.verification_details?.status || "UNKNOWN";

    // Format timestamp if available
    const timestamp = result?.verification_details?.blockchain_record?.timestamp
        ? new Date(result.verification_details.blockchain_record.timestamp).toLocaleString()
        : "N/A";

    const truncateHash = (hash: string) => {
        if (!hash) return "";
        return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md border-primary/20 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                <DialogHeader className="text-center pb-2 border-b border-border/50">
                    <DialogTitle className="text-xl flex items-center justify-center gap-2">
                        <ShieldCheck className="h-6 w-6 text-primary" />
                        Digital Evidence Certificate
                    </DialogTitle>
                    <DialogDescription>
                        Blockchain Verification Record
                    </DialogDescription>
                </DialogHeader>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-10 space-y-4">
                        <div className="relative">
                            <div className="h-16 w-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Box className="h-6 w-6 text-primary/50 animate-pulse" />
                            </div>
                        </div>
                        <p className="text-muted-foreground animate-pulse">Verifying on-chain...</p>
                    </div>
                ) : (
                    <div className="space-y-6 pt-4">
                        {/* Status Banner */}
                        <div className={cn(
                            "p-4 rounded-lg flex flex-col items-center justify-center border",
                            isVerified
                                ? "bg-green-500/10 border-green-500/20 text-green-500"
                                : "bg-red-500/10 border-red-500/20 text-red-500"
                        )}>
                            {isVerified ? (
                                <CheckCircle2 className="h-12 w-12 mb-2" />
                            ) : (
                                <AlertOctagon className="h-12 w-12 mb-2" />
                            )}
                            <h3 className="text-xl font-bold tracking-tight">{status}</h3>
                            <p className="text-sm opacity-90 text-center mt-1">
                                {result?.verification_details?.details}
                            </p>
                        </div>

                        {/* Details Grid */}
                        <div className="space-y-3 text-sm">

                            {/* Transaction Hash */}
                            <div className="group p-3 bg-muted/50 rounded-md border border-border/50 transition-colors hover:bg-muted/80">
                                <label className="text-xs text-muted-foreground font-medium uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                                    <Box className="h-3 w-3" /> Transaction Hash
                                </label>
                                <div className="flex items-center justify-between font-mono">
                                    <span className="truncate text-primary" title={result?.tx_hash}>
                                        {truncateHash(result?.tx_hash || "")}
                                    </span>
                                    <Button variant="ghost" size="icon" className="h-6 w-6 hover:text-primary" onClick={handleCopyHash}>
                                        <Copy className="h-3 w-3" />
                                    </Button>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                {/* Timestamp */}
                                <div className="p-3 bg-muted/50 rounded-md border border-border/50">
                                    <label className="text-xs text-muted-foreground font-medium uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                                        <Clock className="h-3 w-3" /> Anchored At
                                    </label>
                                    <p className="font-medium">{timestamp}</p>
                                </div>

                                {/* Role */}
                                <div className="p-3 bg-muted/50 rounded-md border border-border/50">
                                    <label className="text-xs text-muted-foreground font-medium uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                                        <FileText className="h-3 w-3" /> Signer Role
                                    </label>
                                    <Badge variant="outline" className="font-normal border-primary/20 text-primary">
                                        {result?.verification_details?.blockchain_record?.uploader_role || "Unknown"}
                                    </Badge>
                                </div>
                            </div>

                            {/* Provider */}
                            <div className="flex items-center justify-between px-2 pt-2">
                                <span className="text-xs text-muted-foreground">Consensus Layer</span>
                                <span className="text-xs font-medium text-emerald-400 flex items-center gap-1">
                                    <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></div>
                                    {result?.blockchain_provider || "Polygon PoS"}
                                </span>
                            </div>

                        </div>
                    </div>
                )}

                <DialogFooter className="sm:justify-center pt-2">
                    {isVerified && (
                        <Button variant="outline" className="w-full gap-2 text-primary hover:text-primary border-primary/20 hover:bg-primary/5">
                            <ExternalLink className="h-4 w-4" /> View Block Explorer
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
