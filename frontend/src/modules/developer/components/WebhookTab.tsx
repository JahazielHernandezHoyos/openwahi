"use client";

import { useState, useEffect } from "react";
import { useWebhook } from "../hooks/useWebhook";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  Webhook,
  Save,
  Trash2,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { useTranslations } from "next-intl";

export function WebhookTab() {
  const t = useTranslations("Developer");
  const { toast } = useToast();
  const {
    webhook,
    loading,
    error,
    refetch,
    upsertWebhook,
    isSaving,
    deleteWebhook,
    isDeleting,
    testWebhook,
    isTesting,
    testResult,
  } = useWebhook();

  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [showSecret, setShowSecret] = useState(false);

  // Initialize form with existing webhook data
  useEffect(() => {
    if (webhook) {
      setUrl(webhook.url);
      setIsActive(webhook.is_active);
      setSecret(""); // Don't show existing secret
    }
  }, [webhook]);

  const handleSave = async () => {
    if (!url.trim()) {
      toast({
        variant: "destructive",
        title: t("webhookUrlRequired"),
      });
      return;
    }

    try {
      await upsertWebhook({
        url: url.trim(),
        secret: secret.trim() || undefined,
        is_active: isActive,
      });
      setSecret(""); // Clear secret after save
      toast({
        title: t("webhookSaved"),
        description: t("webhookSavedDesc"),
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: t("webhookSaveError"),
        description: String(error),
      });
    }
  };

  const handleDelete = async () => {
    try {
      await deleteWebhook();
      setUrl("");
      setSecret("");
      setIsActive(true);
      toast({
        title: t("webhookDeleted"),
        description: t("webhookDeletedDesc"),
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: t("webhookDeleteError"),
        description: String(error),
      });
    }
  };

  const handleTest = async () => {
    try {
      const result = await testWebhook();
      if (result.success) {
        toast({
          title: t("webhookTestSuccess"),
          description: `${t("responseTime")}: ${result.response_time_ms}ms`,
        });
      } else {
        toast({
          variant: "destructive",
          title: t("webhookTestFailed"),
          description: result.message,
        });
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: t("webhookTestError"),
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

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Webhook className="h-5 w-5" />
            {t("webhookConfig")}
          </CardTitle>
          <CardDescription>{t("webhookConfigDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Webhook className="h-5 w-5" />
          {t("webhookConfig")}
        </CardTitle>
        <CardDescription>{t("webhookConfigDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Status Banner */}
        {webhook && (
          <div
            className={`p-4 rounded-lg border ${
              webhook.failure_count > 0
                ? "bg-destructive/5 border-destructive/20"
                : webhook.is_active
                ? "bg-green-500/5 border-green-500/20"
                : "bg-muted"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {webhook.failure_count > 0 ? (
                  <AlertTriangle className="h-5 w-5 text-destructive" />
                ) : webhook.is_active ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
                <div>
                  <p className="font-medium">
                    {webhook.failure_count > 0
                      ? t("webhookFailing")
                      : webhook.is_active
                      ? t("webhookActive")
                      : t("webhookInactive")}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t("lastTriggered")}: {formatDate(webhook.last_triggered_at)}
                  </p>
                </div>
              </div>
              {webhook.failure_count > 0 && (
                <span className="text-sm text-destructive">
                  {t("failureCount", { count: webhook.failure_count })}
                </span>
              )}
            </div>
          </div>
        )}

        {/* URL Input */}
        <div className="space-y-2">
          <Label htmlFor="webhook-url">{t("webhookUrl")}</Label>
          <Input
            id="webhook-url"
            placeholder="https://your-server.com/webhook"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <p className="text-sm text-muted-foreground">{t("webhookUrlHelp")}</p>
        </div>

        {/* Secret Input */}
        <div className="space-y-2">
          <Label htmlFor="webhook-secret">
            {t("webhookSecret")} ({t("optional")})
          </Label>
          <div className="flex gap-2">
            <Input
              id="webhook-secret"
              type={showSecret ? "text" : "password"}
              placeholder={webhook?.has_secret ? t("secretConfigured") : t("enterSecret")}
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
            />
            <Button
              variant="outline"
              type="button"
              onClick={() => setShowSecret(!showSecret)}
            >
              {showSecret ? t("hide") : t("show")}
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">{t("webhookSecretHelp")}</p>
        </div>

        {/* Active Toggle */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>{t("webhookEnabled")}</Label>
            <p className="text-sm text-muted-foreground">{t("webhookEnabledHelp")}</p>
          </div>
          <Switch checked={isActive} onCheckedChange={setIsActive} />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex gap-2">
            <Button onClick={handleSave} disabled={isSaving || !url.trim()}>
              <Save className="h-4 w-4 mr-2" />
              {isSaving ? t("saving") : t("save")}
            </Button>
            {webhook && (
              <Button
                variant="outline"
                onClick={handleTest}
                disabled={isTesting}
              >
                <Play className="h-4 w-4 mr-2" />
                {isTesting ? t("testing") : t("testWebhook")}
              </Button>
            )}
          </div>

          {webhook && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  <Trash2 className="h-4 w-4 mr-2" />
                  {t("delete")}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>{t("deleteWebhook")}</AlertDialogTitle>
                  <AlertDialogDescription>
                    {t("deleteWebhookDesc")}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleDelete}
                    className="bg-destructive text-destructive-foreground"
                  >
                    {isDeleting ? t("deleting") : t("delete")}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>

        {/* Test Result */}
        {testResult && (
          <div
            className={`p-4 rounded-lg border ${
              testResult.success
                ? "bg-green-500/5 border-green-500/20"
                : "bg-destructive/5 border-destructive/20"
            }`}
          >
            <div className="flex items-center gap-2">
              {testResult.success ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-destructive" />
              )}
              <span className="font-medium">
                {testResult.success ? t("testPassed") : t("testFailed")}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {testResult.message}
            </p>
            {testResult.response_time_ms && (
              <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                <Clock className="h-3 w-3" />
                {testResult.response_time_ms}ms
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
