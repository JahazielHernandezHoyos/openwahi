"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
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
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Plus,
  Copy,
  Check,
  Code2,
  Trash2,
  PauseCircle,
  Globe,
  Key,
  Loader2,
} from "lucide-react";
import { useTranslations } from "next-intl";
import {
  useWidgetTokens,
  useCreateWidgetToken,
  useRevokeWidgetToken,
  useDeleteWidgetToken,
} from "../hooks/useAIAssistant";
import type { AIConfig, WidgetToken } from "../types";
import { API_BASE_URL } from "@/config/constants";

interface GetWidgetModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  config: AIConfig;
}

function buildSnippet(token: string) {
  return `<script
  src="${API_BASE_URL}/static/widget.js"
  data-widget-token="${token}">
</script>`;
}

export function GetWidgetModal({ open, onOpenChange, config }: GetWidgetModalProps) {
  const t = useTranslations("AIAssistant");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [tokenToRevoke, setTokenToRevoke] = useState<WidgetToken | null>(null);
  const [tokenToDelete, setTokenToDelete] = useState<WidgetToken | null>(null);

  const { data: allTokens, isLoading } = useWidgetTokens();
  const createMutation = useCreateWidgetToken();
  const revokeMutation = useRevokeWidgetToken();
  const deleteMutation = useDeleteWidgetToken();

  // Filter tokens for this specific config
  const tokens = allTokens?.filter((t) => t.ai_config_id === config.id) ?? [];

  const { register, handleSubmit, reset, formState: { errors } } = useForm<{
    name: string;
    allowed_origins: string;
  }>();

  const handleCopy = (token: WidgetToken) => {
    navigator.clipboard.writeText(buildSnippet(token.token));
    setCopiedId(token.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCreate = handleSubmit(async (data) => {
    await createMutation.mutateAsync({
      ai_config_id: config.id,
      name: data.name,
      allowed_origins: data.allowed_origins || undefined,
    });
    reset();
    setShowCreateForm(false);
  });

  const handleRevoke = async () => {
    if (!tokenToRevoke) return;
    await revokeMutation.mutateAsync(tokenToRevoke.id);
    setTokenToRevoke(null);
  };

  const handleDelete = async () => {
    if (!tokenToDelete) return;
    await deleteMutation.mutateAsync(tokenToDelete.id);
    setTokenToDelete(null);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Code2 className="h-5 w-5 text-purple-500" />
              {t("widgetTitle")}
            </DialogTitle>
            <DialogDescription>
              {t("widgetDesc")} —{" "}
              <span className="font-semibold text-foreground">
                {config.name ?? config.id.slice(0, 8)}
              </span>
            </DialogDescription>
          </DialogHeader>

          {/* Token list */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold">{t("widgetTokensTitle")}</p>
                <p className="text-xs text-muted-foreground">{t("widgetTokensDesc")}</p>
              </div>
              <Button
                size="sm"
                onClick={() => setShowCreateForm((v) => !v)}
                className="bg-purple-600 hover:bg-purple-700 gap-2"
              >
                <Plus className="h-4 w-4" />
                {t("createWidgetToken")}
              </Button>
            </div>

            {/* Create form */}
            {showCreateForm && (
              <form
                onSubmit={handleCreate}
                className="border border-purple-500/30 rounded-xl p-4 space-y-4 bg-purple-500/5"
              >
                <div className="space-y-1.5">
                  <Label htmlFor="token-name">{t("widgetTokenName")}</Label>
                  <Input
                    id="token-name"
                    placeholder={t("widgetTokenNamePlaceholder")}
                    {...register("name", { required: true })}
                    className={errors.name ? "border-red-500" : ""}
                  />
                  <p className="text-xs text-muted-foreground">{t("widgetTokenNameHelp")}</p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="allowed-origins">{t("allowedOrigins")}</Label>
                  <Input
                    id="allowed-origins"
                    placeholder={t("allowedOriginsPlaceholder")}
                    {...register("allowed_origins")}
                  />
                  <p className="text-xs text-muted-foreground">{t("allowedOriginsHelp")}</p>
                </div>
                <div className="flex gap-2 justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => { setShowCreateForm(false); reset(); }}
                  >
                    {t("cancel")}
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={createMutation.isPending}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {createMutation.isPending ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" />{t("create")}...</>
                    ) : (
                      t("create")
                    )}
                  </Button>
                </div>
              </form>
            )}

            <Separator />

            {/* Tokens */}
            {isLoading ? (
              <div className="py-8 text-center text-muted-foreground text-sm">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                Cargando tokens...
              </div>
            ) : tokens.length === 0 ? (
              <div className="text-center py-10 border-2 border-dashed rounded-xl">
                <Key className="h-10 w-10 mx-auto mb-3 text-muted-foreground/40" />
                <p className="font-medium">{t("noWidgetTokens")}</p>
                <p className="text-sm text-muted-foreground mt-1">{t("noWidgetTokensDesc")}</p>
              </div>
            ) : (
              <div className="space-y-4">
                {tokens.map((token) => (
                  <div
                    key={token.id}
                    className={`rounded-xl border p-4 space-y-3 transition-colors ${
                      token.is_active
                        ? "border-green-500/30 bg-green-500/5"
                        : "border-border bg-muted/30 opacity-60"
                    }`}
                  >
                    {/* Token header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">{token.name}</span>
                        <Badge
                          variant={token.is_active ? "default" : "secondary"}
                          className={token.is_active ? "bg-green-600" : ""}
                        >
                          {token.is_active ? t("tokenActive") : t("tokenInactive")}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-1">
                        {token.is_active && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setTokenToRevoke(token)}
                            className="text-muted-foreground hover:text-orange-400 h-8 px-2"
                          >
                            <PauseCircle className="h-4 w-4 mr-1" />
                            {t("revokeToken")}
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setTokenToDelete(token)}
                          className="text-muted-foreground hover:text-red-400 h-8 px-2"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    {/* Origins */}
                    {token.allowed_origins && (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Globe className="h-3.5 w-3.5" />
                        <span>{token.allowed_origins}</span>
                      </div>
                    )}

                    {/* Snippet */}
                    {token.is_active && (
                      <div className="space-y-2">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                          {t("scriptSnippet")}
                        </p>
                        <div className="relative">
                          <pre className="text-xs bg-background/80 border rounded-lg p-3 font-mono overflow-x-auto leading-relaxed text-green-400">
                            {buildSnippet(token.token)}
                          </pre>
                          <Button
                            size="sm"
                            variant="secondary"
                            className="absolute top-2 right-2 h-7 px-2 gap-1.5"
                            onClick={() => handleCopy(token)}
                          >
                            {copiedId === token.id ? (
                              <><Check className="h-3.5 w-3.5 text-green-500" />{t("snippetCopied")}</>
                            ) : (
                              <><Copy className="h-3.5 w-3.5" />{t("copySnippet")}</>
                            )}
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Revoke confirmation */}
      <AlertDialog open={!!tokenToRevoke} onOpenChange={(o) => !o && setTokenToRevoke(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("revokeTokenConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("revokeTokenConfirmDesc")}
              {tokenToRevoke && (
                <span className="block mt-2 font-mono font-semibold">{tokenToRevoke.name}</span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={revokeMutation.isPending}>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRevoke}
              disabled={revokeMutation.isPending}
              className="bg-orange-600 hover:bg-orange-700"
            >
              {revokeMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                t("revokeToken")
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete confirmation */}
      <AlertDialog open={!!tokenToDelete} onOpenChange={(o) => !o && setTokenToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTokenConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteTokenConfirmDesc")}
              {tokenToDelete && (
                <span className="block mt-2 font-mono font-semibold">{tokenToDelete.name}</span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                t("deleteToken")
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
