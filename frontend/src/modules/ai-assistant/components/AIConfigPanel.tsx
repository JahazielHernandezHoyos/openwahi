"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Plus,
  MoreVertical,
  Edit,
  Trash2,
  TestTube,
  Sparkles,
  Brain,
  Zap,
  Phone,
  Database,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { AIConfigDialog } from "./AIConfigDialog";
import { AITestDialog } from "./AITestDialog";
import {
  useAIConfigs,
  useToggleAIConfig,
  useDeleteAIConfig,
} from "../hooks/useAIAssistant";
import type { AIConfig } from "../types";

interface AIConfigPanelProps {
  deviceId: string;
}

export function AIConfigPanel({ deviceId }: AIConfigPanelProps) {
  const t = useTranslations("AIAssistant");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<AIConfig | undefined>();
  const [configToDelete, setConfigToDelete] = useState<AIConfig | null>(null);
  const [dialogMode, setDialogMode] = useState<"create" | "edit">("create");

  const { data: configs, isLoading } = useAIConfigs(deviceId);
  const toggleMutation = useToggleAIConfig();
  const deleteMutation = useDeleteAIConfig();

  const handleCreate = () => {
    setSelectedConfig(undefined);
    setDialogMode("create");
    setDialogOpen(true);
  };

  const handleEdit = (config: AIConfig) => {
    setSelectedConfig(config);
    setDialogMode("edit");
    setDialogOpen(true);
  };

  const handleTest = (config: AIConfig) => {
    setSelectedConfig(config);
    setTestDialogOpen(true);
  };

  const handleToggle = async (config: AIConfig, enabled: boolean) => {
    await toggleMutation.mutateAsync({
      configId: config.id,
      enabled,
    });
  };

  const handleDeleteConfirm = async () => {
    if (configToDelete) {
      await deleteMutation.mutateAsync(configToDelete.id);
      setConfigToDelete(null);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-2 h-4 w-full max-w-96" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-500" />
                {t("title")}
              </CardTitle>
              <CardDescription>{t("description")}</CardDescription>
            </div>
            {(!configs || configs.length === 0) && (
              <Button onClick={handleCreate} size="sm" className="self-start bg-purple-600 hover:bg-purple-700 sm:shrink-0">
                <Plus className="h-4 w-4 mr-2" />
                {t("createConfig")}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {!configs || configs.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed rounded-lg">
              <Sparkles className="h-12 w-12 mx-auto mb-4 text-purple-500/50" />
              <h3 className="text-lg font-semibold mb-2">{t("noConfigs")}</h3>
              <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
                {t("noConfigsDesc")}
              </p>
              <Button onClick={handleCreate} className="bg-purple-600 hover:bg-purple-700 h-10 px-8">
                <Plus className="h-4 w-4 mr-2" />
                {t("createFirstConfig")}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Only show the first config as per the new rule: one config per device */}
              {configs.slice(0, 1).map((config) => (
                <div
                  key={config.id}
                  className={`relative overflow-hidden rounded-xl border transition-all ${config.is_enabled
                      ? "border-green-500/30 bg-green-500/5"
                      : "border-border bg-card/50"
                    }`}
                >
                  {/* Decorative Gradient for active state */}
                  {config.is_enabled && (
                    <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 blur-[50px] -mr-16 -mt-16 pointer-events-none" />
                  )}

                  <div className="p-4 sm:p-6">
                    <div className="relative z-10 flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0 flex-1 space-y-4">
                        {/* Status Badges */}
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="flex items-center gap-2 bg-background/50 backdrop-blur-sm border rounded-full px-3 py-1">
                            <Zap className={`h-4 w-4 ${config.is_enabled ? "text-green-500" : "text-muted-foreground"}`} />
                            <span className="text-sm font-medium">
                              {config.is_enabled ? t("enabled") : t("disabled")}
                            </span>
                          </div>

                          {config.auto_enhance_prompt && (
                            <Badge variant="secondary" className="gap-1 bg-purple-500/10 text-purple-400 border-purple-500/20">
                              <Sparkles className="h-3 w-3" />
                              {t("autoEnhanced")}
                            </Badge>
                          )}
                          {config.use_memory && (
                            <Badge variant="secondary" className="gap-1 bg-blue-500/10 text-blue-400 border-blue-500/20">
                              <Brain className="h-3 w-3" />
                              {t("memoryEnabled")}
                            </Badge>
                          )}
                          {config.use_knowledge_base && (
                            <Badge variant="secondary" className="gap-1 bg-green-500/10 text-green-400 border-green-500/20">
                              <Database className="h-3 w-3" />
                              RAG ({config.knowledge_base_ids?.length || 0} KB)
                            </Badge>
                          )}
                        </div>

                        {/* Model Info */}
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                              {t("provider")}
                            </p>
                            <p className="text-sm font-medium flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-purple-500" />
                              {config.provider.toUpperCase()}
                            </p>
                          </div>
                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                              {t("model")}
                            </p>
                            <p className="break-all font-mono text-sm font-medium">
                              {config.model}
                            </p>
                          </div>
                        </div>

                        {/* System Prompt */}
                        {config.system_prompt && (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                              {t("systemPrompt")}
                            </p>
                            <div className="bg-background/40 backdrop-blur-sm rounded-lg p-3 border border-border/50">
                              <p className="text-sm text-foreground/80 line-clamp-3 leading-relaxed">
                                {config.system_prompt}
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Settings Grid */}
                        <div className="flex flex-wrap gap-x-6 gap-y-2 pt-2">
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="w-1 h-1 rounded-full bg-border" />
                            <strong>{t("temperature")}:</strong> {config.temperature.toFixed(1)}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="w-1 h-1 rounded-full bg-border" />
                            <strong>{t("maxTokens")}:</strong> {config.max_tokens}
                          </div>
                          {config.use_memory && (
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <span className="w-1 h-1 rounded-full bg-border" />
                              <strong>{t("memoryWindow")}:</strong> {config.memory_window}
                            </div>
                          )}
                          {config.use_knowledge_base && (
                            <>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span className="w-1 h-1 rounded-full bg-green-500" />
                                <strong>Top K:</strong> {config.rag_top_k}
                              </div>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span className="w-1 h-1 rounded-full bg-green-500" />
                                <strong>Min Score:</strong> {config.rag_min_score?.toFixed(2)}
                              </div>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Actions Column */}
                      <div className="flex w-full flex-col items-stretch gap-3 sm:ml-4 sm:w-auto sm:shrink-0 sm:items-end sm:gap-4">
                        <div className="flex items-center gap-3 bg-background/50 p-2 rounded-lg border">
                          <span className="text-xs font-medium text-muted-foreground">Status</span>
                          <Switch
                            checked={config.is_enabled}
                            onCheckedChange={(checked) =>
                              handleToggle(config, checked)
                            }
                            disabled={toggleMutation.isPending}
                            className="data-[state=checked]:bg-green-500"
                          />
                        </div>

                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleTest(config)}
                            className="bg-background/50"
                          >
                            <TestTube className="h-4 w-4 mr-2" />
                            {t("testConfig")}
                          </Button>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="outline" size="sm" className="bg-background/50">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48">
                              <DropdownMenuItem onClick={() => handleEdit(config)}>
                                <Edit className="h-4 w-4 mr-2" />
                                {t("edit")}
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => setConfigToDelete(config)}
                                className="text-red-500 focus:text-red-500 focus:bg-red-500/10"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                {t("delete")}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <AIConfigDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        deviceId={deviceId}
        config={selectedConfig}
        mode={dialogMode}
      />

      {/* Test Dialog */}
      {selectedConfig && (
        <AITestDialog
          open={testDialogOpen}
          onOpenChange={setTestDialogOpen}
          config={selectedConfig}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={!!configToDelete}
        onOpenChange={(open) => !open && setConfigToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteConfirmDesc")}
              {configToDelete && (
                <span className="block mt-2 font-mono font-semibold">
                  {configToDelete.phone_number}
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              {t("cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleteMutation.isPending ? t("deleting") : t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
