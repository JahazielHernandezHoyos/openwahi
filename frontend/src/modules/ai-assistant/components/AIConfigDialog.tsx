"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Sparkles, Info, Database, BookOpen } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useTranslations } from "next-intl";
import type { AIConfig, AIConfigCreate, AIConfigUpdate } from "../types";
import { DEFAULT_PROMPTS, AVAILABLE_PROVIDERS } from "../types";
import { useCreateAIConfig, useUpdateAIConfig, useKnowledgeBases, useCreateStandaloneConfig } from "../hooks/useAIAssistant";
import { useWhatsAppDevices } from "@/modules/whatsapp/hooks/useWhatsAppDevices";
import { WhatsAppDevice } from "@/modules/whatsapp/types";

interface AIConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deviceId?: string;  // Optional when standalone=true
  config?: AIConfig; // If provided, we're editing
  mode: "create" | "edit";
  standalone?: boolean; // When true, not tied to a WhatsApp device
  configName?: string; // Name for standalone config
  onConfigCreated?: (config: AIConfig) => void; // Callback after creation
}

interface FormData {
  name: string;
  phone_number: string;
  provider: string;
  model: string;
  api_key: string;
  system_prompt: string;
  temperature: number;
  max_tokens: number;
  use_memory: boolean;
  memory_window: number;
  auto_enhance_prompt: boolean;
  // RAG settings
  use_knowledge_base: boolean;
  knowledge_base_ids: string[];
  rag_top_k: number;
  rag_min_score: number;
}

export function AIConfigDialog({
  open,
  onOpenChange,
  deviceId = "",
  config,
  mode,
  standalone = false,
  configName = "",
  onConfigCreated,
}: AIConfigDialogProps) {
  const t = useTranslations("AIAssistant");
  const [selectedProvider, setSelectedProvider] = useState<string>("llamacpp");
  const [selectedTemplate, setSelectedTemplate] = useState<string>("generic");

  const createMutation = useCreateAIConfig(deviceId);
  const createStandaloneMutation = useCreateStandaloneConfig();
  const updateMutation = useUpdateAIConfig();
  const { data: knowledgeBases = [], isLoading: isLoadingKBs } = useKnowledgeBases();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      name: config?.name || configName || "",
      phone_number: config?.phone_number || "",
      provider: config?.provider || "llamacpp",
      model: config?.model || "Qwen3.5-0.8B-Q8_0",
      api_key: "",
      system_prompt: config?.system_prompt || DEFAULT_PROMPTS.generic,
      temperature: config?.temperature || 0.7,
      max_tokens: config?.max_tokens || 1000,
      use_memory: config?.use_memory ?? true,
      memory_window: config?.memory_window || 10,
      auto_enhance_prompt: config?.auto_enhance_prompt ?? true,
      // RAG defaults
      use_knowledge_base: config?.use_knowledge_base ?? false,
      knowledge_base_ids: config?.knowledge_base_ids || [],
      rag_top_k: config?.rag_top_k || 3,
      rag_min_score: config?.rag_min_score || 0.75,
    },
  });

  const watchProvider = watch("provider");
  const watchTemperature = watch("temperature");
  const watchUseMemory = watch("use_memory");
  const watchAutoEnhance = watch("auto_enhance_prompt");
  const watchUseKnowledgeBase = watch("use_knowledge_base");
  const watchKnowledgeBaseIds = watch("knowledge_base_ids");
  const watchRagMinScore = watch("rag_min_score");

  // Get current device phone
  const { devices } = useWhatsAppDevices();
  const currentDevice = devices.find((d: WhatsAppDevice) => d.id === deviceId);

  // Update selected provider when it changes
  useEffect(() => {
    setSelectedProvider(watchProvider);
  }, [watchProvider]);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      if (config) {
        // Editing mode
        reset({
          name: config.name || "",
          phone_number: config.phone_number ?? "",
          provider: config.provider,
          model: config.model,
          api_key: "", // Don't pre-fill API key for security
          system_prompt: config.system_prompt || DEFAULT_PROMPTS.generic,
          temperature: config.temperature,
          max_tokens: config.max_tokens,
          use_memory: config.use_memory,
          memory_window: config.memory_window,
          auto_enhance_prompt: config.auto_enhance_prompt,
          // RAG fields
          use_knowledge_base: config.use_knowledge_base,
          knowledge_base_ids: config.knowledge_base_ids || [],
          rag_top_k: config.rag_top_k,
          rag_min_score: config.rag_min_score,
        });
        setSelectedProvider(config.provider);
      } else {
        // Creating mode
        reset({
          name: configName || "",
          phone_number: standalone ? "" : (currentDevice?.phone || ""),
          provider: "llamacpp",
          model: "Qwen3.5-0.8B-Q8_0",
          api_key: "",
          system_prompt: DEFAULT_PROMPTS.generic,
          temperature: 0.7,
          max_tokens: 1000,
          use_memory: true,
          memory_window: 10,
          auto_enhance_prompt: true,
          // RAG defaults
          use_knowledge_base: false,
          knowledge_base_ids: [],
          rag_top_k: 3,
          rag_min_score: 0.75,
        });
        setSelectedProvider("llamacpp");
      }
    }
  }, [open, config, reset, currentDevice, standalone, configName]);

  const onSubmit = async (data: FormData) => {
    try {
      if (mode === "create") {
        const configData: AIConfigCreate = {
          name: data.name || undefined,
          phone_number: standalone ? undefined : data.phone_number,
          provider: data.provider,
          model: data.model,
          api_key: data.api_key || undefined,
          system_prompt: data.system_prompt,
          temperature: data.temperature,
          max_tokens: data.max_tokens,
          use_memory: data.use_memory,
          memory_window: data.memory_window,
          auto_enhance_prompt: data.auto_enhance_prompt,
          // RAG settings
          use_knowledge_base: data.use_knowledge_base,
          knowledge_base_ids: data.knowledge_base_ids,
          rag_top_k: data.rag_top_k,
          rag_min_score: data.rag_min_score,
        };

        if (standalone) {
          const newConfig = await createStandaloneMutation.mutateAsync(configData);
          onConfigCreated?.(newConfig);
        } else {
          await createMutation.mutateAsync(configData);
        }
      } else if (config) {
        const updates: AIConfigUpdate = {
          system_prompt: data.system_prompt,
          temperature: data.temperature,
          max_tokens: data.max_tokens,
          use_memory: data.use_memory,
          memory_window: data.memory_window,
          auto_enhance_prompt: data.auto_enhance_prompt,
          // RAG settings
          use_knowledge_base: data.use_knowledge_base,
          knowledge_base_ids: data.knowledge_base_ids,
          rag_top_k: data.rag_top_k,
          rag_min_score: data.rag_min_score,
        };

        // Only include API key if it was provided
        if (data.api_key) {
          updates.api_key = data.api_key;
        }

        // Only include provider/model if they changed
        if (data.provider !== config.provider) {
          updates.provider = data.provider;
        }
        if (data.model !== config.model) {
          updates.model = data.model;
        }

        await updateMutation.mutateAsync({
          configId: config.id,
          updates,
        });
      }

      onOpenChange(false);
    } catch (error) {
      // Error is handled by the mutation hooks
    }
  };

  const applyTemplate = (template: string) => {
    const prompt = DEFAULT_PROMPTS[template as keyof typeof DEFAULT_PROMPTS];
    if (prompt) {
      setValue("system_prompt", prompt);
      setSelectedTemplate(template);
    }
  };

  const isLoading = createMutation.isPending || createStandaloneMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            {mode === "create" ? t("createConfig") : t("editConfig")}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? t("createConfigDesc")
              : t("editConfigDesc")}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <Tabs defaultValue="basic" className="w-full">
            <TabsList className="grid h-auto w-full grid-cols-2 gap-1 sm:grid-cols-4">
              <TabsTrigger className="h-full min-w-0 whitespace-normal px-2 text-xs sm:text-sm" value="basic">{t("basicSettings")}</TabsTrigger>
              <TabsTrigger className="h-full min-w-0 whitespace-normal px-2 text-xs sm:text-sm" value="prompt">{t("systemPrompt")}</TabsTrigger>
              <TabsTrigger className="h-full min-w-0 whitespace-normal px-2 text-xs sm:text-sm" value="advanced">{t("advancedSettings")}</TabsTrigger>
              <TabsTrigger value="knowledge" className="flex h-full min-w-0 items-center gap-1 whitespace-normal px-2 text-xs sm:text-sm">
                <Database className="h-3 w-3" />
                RAG
              </TabsTrigger>
            </TabsList>

            {/* BASIC SETTINGS */}
            <TabsContent value="basic" className="space-y-4 mt-4">
              {/* Name — shown for standalone configs */}
              {standalone && (
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    Nombre del asistente <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="name"
                    placeholder="Ej: Asistente de Soporte Web"
                    {...register("name", { required: "El nombre es requerido" })}
                  />
                  {errors.name && (
                    <p className="text-sm text-red-500">{errors.name.message}</p>
                  )}
                  <p className="text-xs text-muted-foreground/70 italic">
                    Nombre para identificar este asistente en el dashboard
                  </p>
                </div>
              )}

              {/* Phone number — only for device-bound configs */}
              {!standalone && (
              <div className="space-y-2">
                <Label htmlFor="phone_number" className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  {t("phoneNumber")}
                </Label>
                <div className="relative">
                  <Input
                    id="phone_number"
                    placeholder="15551234567"
                    disabled={true} // Always disabled as it's tied to the device now
                    className="bg-muted/50 font-mono"
                    {...register("phone_number", {
                      required: t("phoneNumberRequired"),
                    })}
                  />
                </div>
                <p className="text-xs text-muted-foreground/70 italic">
                  {t("phoneNumberIdentifier")}
                </p>
              </div>
              )}

              {/* Provider */}
              <div className="space-y-2">
                <Label htmlFor="provider">
                  {t("provider")} <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={watchProvider}
                  onValueChange={(value) => {
                    setValue("provider", value);
                    // Reset model when provider changes
                    const defaultModel =
                      AVAILABLE_PROVIDERS[value]?.models[0] || "";
                    setValue("model", defaultModel);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.values(AVAILABLE_PROVIDERS).map((provider) => (
                      <SelectItem key={provider.id} value={provider.id}>
                        {provider.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Model */}
              <div className="space-y-2">
                <Label htmlFor="model">
                  {t("model")} <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={watch("model")}
                  onValueChange={(value) => setValue("model", value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AVAILABLE_PROVIDERS[selectedProvider]?.models.map(
                      (model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      )
                    )}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {t("modelHelp")}
                </p>
              </div>

              {/* API Key */}
              <div className="space-y-2">
                <Label htmlFor="api_key">
                  {t("apiKey")}{" "}
                  {mode === "create" && watchProvider !== "llamacpp" && (
                    <span className="text-red-500">*</span>
                  )}
                </Label>
                <Input
                  id="api_key"
                  type="password"
                  placeholder={
                    mode === "edit"
                      ? t("apiKeyPlaceholderEdit")
                      : watchProvider === "llamacpp"
                        ? "No requerida para el modelo local"
                        : "gsk_..."
                  }
                  {...register("api_key", {
                    required:
                      mode === "create" && watchProvider !== "llamacpp"
                        ? t("apiKeyRequired")
                        : false,
                  })}
                />
                {errors.api_key && (
                  <p className="text-sm text-red-500">
                    {errors.api_key.message}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  {mode === "edit" ? t("apiKeyHelpEdit") : t("apiKeyHelp")}
                </p>
              </div>
            </TabsContent>

            {/* SYSTEM PROMPT */}
            <TabsContent value="prompt" className="space-y-4 mt-4">
              {/* Template Selector */}
              <div className="space-y-2">
                <Label>{t("promptTemplates")}</Label>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {Object.keys(DEFAULT_PROMPTS).map((template) => (
                    <Button
                      key={template}
                      type="button"
                      variant={
                        selectedTemplate === template ? "default" : "outline"
                      }
                      size="sm"
                      className="h-auto min-h-9 whitespace-normal"
                      onClick={() => applyTemplate(template)}
                    >
                      {t(`template_${template}`)}
                    </Button>
                  ))}
                </div>
              </div>

              {/* System Prompt */}
              <div className="space-y-2">
                <Label htmlFor="system_prompt">{t("systemPrompt")}</Label>
                <Textarea
                  id="system_prompt"
                  rows={10}
                  placeholder={t("systemPromptPlaceholder")}
                  {...register("system_prompt")}
                />
                <p className="text-xs text-muted-foreground">
                  {t("systemPromptHelp")}
                </p>
              </div>

              {/* Auto Enhance Prompt */}
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="auto_enhance_prompt">
                      {t("autoEnhancePrompt")}
                    </Label>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="h-4 w-4 text-muted-foreground" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="max-w-xs">
                            {t("autoEnhancePromptTooltip")}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {t("autoEnhancePromptDesc")}
                  </p>
                </div>
                <Switch
                  id="auto_enhance_prompt"
                  checked={watchAutoEnhance}
                  onCheckedChange={(checked) =>
                    setValue("auto_enhance_prompt", checked)
                  }
                />
              </div>
            </TabsContent>

            {/* ADVANCED SETTINGS */}
            <TabsContent value="advanced" className="space-y-4 mt-4">
              {/* Temperature */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="temperature">{t("temperature")}</Label>
                  <span className="text-sm text-muted-foreground">
                    {watchTemperature.toFixed(2)}
                  </span>
                </div>
                <Slider
                  id="temperature"
                  min={0}
                  max={1}
                  step={0.1}
                  value={[watchTemperature]}
                  onValueChange={(value) => setValue("temperature", value[0])}
                />
                <p className="text-xs text-muted-foreground">
                  {t("temperatureHelp")}
                </p>
              </div>

              {/* Max Tokens */}
              <div className="space-y-2">
                <Label htmlFor="max_tokens">{t("maxTokens")}</Label>
                <Input
                  id="max_tokens"
                  type="number"
                  min={100}
                  max={4000}
                  step={100}
                  {...register("max_tokens", {
                    valueAsNumber: true,
                    min: 100,
                    max: 4000,
                  })}
                />
                <p className="text-xs text-muted-foreground">
                  {t("maxTokensHelp")}
                </p>
              </div>

              {/* Use Memory */}
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label htmlFor="use_memory">{t("useMemory")}</Label>
                  <p className="text-sm text-muted-foreground">
                    {t("useMemoryDesc")}
                  </p>
                </div>
                <Switch
                  id="use_memory"
                  checked={watchUseMemory}
                  onCheckedChange={(checked) =>
                    setValue("use_memory", checked)
                  }
                />
              </div>

              {/* Memory Window */}
              {watchUseMemory && (
                <div className="space-y-2">
                  <Label htmlFor="memory_window">{t("memoryWindow")}</Label>
                  <Input
                    id="memory_window"
                    type="number"
                    min={1}
                    max={50}
                    {...register("memory_window", {
                      valueAsNumber: true,
                      min: 1,
                      max: 50,
                    })}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t("memoryWindowHelp")}
                  </p>
                </div>
              )}
            </TabsContent>

            {/* KNOWLEDGE BASE / RAG SETTINGS */}
            <TabsContent value="knowledge" className="space-y-4 mt-4">
              {/* Enable Knowledge Base */}
              <div className="flex items-center justify-between rounded-lg border p-4 bg-gradient-to-r from-purple-500/5 to-blue-500/5">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-purple-500" />
                    <Label htmlFor="use_knowledge_base" className="font-semibold">
                      Habilitar Base de Conocimientos (RAG)
                    </Label>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Permite al bot consultar tus documentos para responder con información específica
                  </p>
                </div>
                <Switch
                  id="use_knowledge_base"
                  checked={watchUseKnowledgeBase}
                  onCheckedChange={(checked) =>
                    setValue("use_knowledge_base", checked)
                  }
                />
              </div>

              {watchUseKnowledgeBase && (
                <>
                  {/* Knowledge Base Selector */}
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4" />
                      Bases de Conocimiento
                    </Label>
                    {isLoadingKBs ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground p-4 border rounded-lg">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Cargando bases de conocimiento...
                      </div>
                    ) : knowledgeBases.length === 0 ? (
                      <div className="text-sm text-muted-foreground p-4 border rounded-lg bg-muted/50">
                        <p className="font-medium">No tienes bases de conocimiento</p>
                        <p className="text-xs mt-1">
                          Ve a la sección de Knowledge Base para crear una y subir documentos
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto border rounded-lg p-2">
                        {knowledgeBases.filter(kb => kb.is_active).map((kb) => (
                          <label
                            key={kb.id}
                            className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                              watchKnowledgeBaseIds.includes(kb.id)
                                ? "border-purple-500 bg-purple-500/10"
                                : "border-border hover:bg-muted/50"
                            }`}
                          >
                            <input
                              type="checkbox"
                              className="sr-only"
                              checked={watchKnowledgeBaseIds.includes(kb.id)}
                              onChange={(e) => {
                                const newIds = e.target.checked
                                  ? [...watchKnowledgeBaseIds, kb.id]
                                  : watchKnowledgeBaseIds.filter((id) => id !== kb.id);
                                setValue("knowledge_base_ids", newIds);
                              }}
                            />
                            <div
                              className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                                watchKnowledgeBaseIds.includes(kb.id)
                                  ? "border-purple-500 bg-purple-500"
                                  : "border-muted-foreground"
                              }`}
                            >
                              {watchKnowledgeBaseIds.includes(kb.id) && (
                                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-sm truncate">{kb.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {kb.total_documents} docs · {kb.total_chunks} chunks
                              </p>
                            </div>
                          </label>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Selecciona las bases de conocimiento que el bot consultará
                    </p>
                  </div>

                  {/* RAG Top K */}
                  <div className="space-y-2">
                    <Label htmlFor="rag_top_k">Resultados a Recuperar (Top K)</Label>
                    <Input
                      id="rag_top_k"
                      type="number"
                      min={1}
                      max={10}
                      {...register("rag_top_k", {
                        valueAsNumber: true,
                        min: 1,
                        max: 10,
                      })}
                    />
                    <p className="text-xs text-muted-foreground">
                      Número de fragmentos relevantes a incluir en el contexto (1-10)
                    </p>
                  </div>

                  {/* RAG Min Score */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="rag_min_score">Score Mínimo de Relevancia</Label>
                      <span className="text-sm text-muted-foreground">
                        {watchRagMinScore.toFixed(2)}
                      </span>
                    </div>
                    <Slider
                      id="rag_min_score"
                      min={0}
                      max={1}
                      step={0.05}
                      value={[watchRagMinScore]}
                      onValueChange={(value) => setValue("rag_min_score", value[0])}
                    />
                    <p className="text-xs text-muted-foreground">
                      Solo se incluirán resultados con score mayor a este valor (0.5-0.9 recomendado)
                    </p>
                  </div>
                </>
              )}

              {/* Info Box */}
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
                <div className="flex gap-3">
                  <Info className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-blue-400">¿Qué es RAG?</p>
                    <p className="text-muted-foreground mt-1">
                      RAG (Retrieval Augmented Generation) permite que el bot busque información
                      relevante en tus documentos antes de responder, proporcionando respuestas
                      más precisas basadas en tu base de conocimientos.
                    </p>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {mode === "create" ? t("create") : t("save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
