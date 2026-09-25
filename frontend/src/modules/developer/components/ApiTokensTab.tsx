"use client";

import { useState } from "react";
import { useApiTokens } from "../hooks/useApiTokens";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";
import {
  AlertCircle,
  Key,
  Plus,
  Trash2,
  Copy,
  Check,
  Clock,
  RefreshCw,
} from "lucide-react";
import { useTranslations } from "next-intl";

export function ApiTokensTab() {
  const t = useTranslations("Developer");
  const { toast } = useToast();
  const {
    tokens,
    loading,
    error,
    refetch,
    createToken,
    isCreating,
    revokeToken,
    isRevoking,
  } = useApiTokens();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [tokenName, setTokenName] = useState("");
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreateToken = async () => {
    if (!tokenName.trim()) return;

    try {
      const result = await createToken(tokenName.trim());
      setNewToken(result.token);
      setTokenName("");
    } catch (error) {
      toast({
        variant: "destructive",
        title: t("tokenCreateError"),
        description: String(error),
      });
    }
  };

  const handleCopyToken = async () => {
    if (newToken) {
      await navigator.clipboard.writeText(newToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast({
        title: t("tokenCopied"),
        description: t("tokenCopiedDesc"),
      });
    }
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setNewToken(null);
    setTokenName("");
    setCopied(false);
  };

  const handleRevokeToken = async (tokenId: string) => {
    try {
      await revokeToken(tokenId);
      toast({
        title: t("tokenRevoked"),
        description: t("tokenRevokedDesc"),
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: t("tokenRevokeError"),
        description: String(error),
      });
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return t("never");
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              {t("apiTokens")}
            </CardTitle>
            <CardDescription>{t("apiTokensDesc")}</CardDescription>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" disabled={Boolean(error)}>
                <Plus className="h-4 w-4 mr-1" />
                {t("createToken")}
              </Button>
            </DialogTrigger>
            <DialogContent>
              {!newToken ? (
                <>
                  <DialogHeader>
                    <DialogTitle>{t("createNewToken")}</DialogTitle>
                    <DialogDescription>{t("createTokenDesc")}</DialogDescription>
                  </DialogHeader>
                  <div className="py-4">
                    <Input
                      placeholder={t("tokenNamePlaceholder")}
                      value={tokenName}
                      onChange={(e) => setTokenName(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleCreateToken()}
                    />
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={handleCloseDialog}>
                      {t("cancel")}
                    </Button>
                    <Button onClick={handleCreateToken} disabled={isCreating || !tokenName.trim()}>
                      {isCreating ? t("creating") : t("create")}
                    </Button>
                  </DialogFooter>
                </>
              ) : (
                <>
                  <DialogHeader>
                    <DialogTitle>{t("tokenCreated")}</DialogTitle>
                    <DialogDescription>{t("tokenCreatedDesc")}</DialogDescription>
                  </DialogHeader>
                  <div className="py-4">
                    <div className="flex items-center gap-2">
                      <code className="flex-1 p-3 bg-muted rounded-md font-mono text-sm break-all">
                        {newToken}
                      </code>
                      <Button variant="outline" size="icon" onClick={handleCopyToken}>
                        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      </Button>
                    </div>
                    <p className="text-sm text-destructive mt-2">{t("tokenWarning")}</p>
                  </div>
                  <DialogFooter>
                    <Button onClick={handleCloseDialog}>{t("done")}</Button>
                  </DialogFooter>
                </>
              )}
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : error ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>{t("loadError")}</AlertTitle>
            <AlertDescription className="space-y-3">
              <p>{t("loadErrorDesc")}</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void refetch()}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                {t("retry")}
              </Button>
            </AlertDescription>
          </Alert>
        ) : tokens.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Key className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p>{t("noTokens")}</p>
            <p className="text-sm">{t("noTokensDesc")}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tokens.map((token) => (
              <div
                key={token.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="space-y-1">
                  <div className="font-medium">{token.name}</div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="font-mono">{token.token_prefix}...</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {t("lastUsed")}: {formatDate(token.last_used_at)}
                    </span>
                  </div>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="ghost" size="icon" className="text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>{t("revokeToken")}</AlertDialogTitle>
                      <AlertDialogDescription>
                        {t("revokeTokenDesc", { name: token.name })}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => handleRevokeToken(token.id)}
                        className="bg-destructive text-destructive-foreground"
                      >
                        {isRevoking ? t("revoking") : t("revoke")}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
