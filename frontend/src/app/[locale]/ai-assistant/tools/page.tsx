"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Wrench,
  Plus,
  Trash2,
  Edit,
  ExternalLink,
  Check,
  X,
  Code,
  ArrowLeft,
} from "lucide-react";
import { useWebhookTools } from "@/modules/ai-assistant/hooks/useWebhookTools";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { getSafeHttpUrl } from "@/lib/safeUrls";

export default function WebhookToolsPage() {
  const locale = useLocale();
  const t = useTranslations("AIAssistantTools");
  const {
    tools,
    loading,
    createTool,
    updateTool,
    deleteTool,
  } = useWebhookTools();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingTool, setEditingTool] = useState<any>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    webhook_url: "",
    method: "POST",
    input_schema: JSON.stringify(
      {
        type: "object",
        properties: {
          param1: {
            type: "string",
            description: t("schemaParamDescription"),
          },
        },
        required: ["param1"],
      },
      null,
      2
    ),
    timeout_seconds: 30,
    is_enabled: true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const payload = {
        ...formData,
        input_schema: JSON.parse(formData.input_schema),
      };

      if (editingTool) {
        await updateTool(editingTool.id, payload);
      } else {
        await createTool(payload);
      }

      // Reset form
      setFormData({
        name: "",
        description: "",
        webhook_url: "",
        method: "POST",
        input_schema: JSON.stringify(
          {
            type: "object",
            properties: {},
            required: [],
          },
          null,
          2
        ),
        timeout_seconds: 30,
        is_enabled: true,
      });
      setIsCreateDialogOpen(false);
      setEditingTool(null);
    } catch (error) {
      console.error("Error saving tool:", error);
      alert(t("saveError"));
    }
  };

  const handleEdit = (tool: any) => {
    setEditingTool(tool);
    setFormData({
      name: tool.name,
      description: tool.description,
      webhook_url: tool.webhook_url,
      method: tool.method,
      input_schema: JSON.stringify(tool.input_schema, null, 2),
      timeout_seconds: tool.timeout_seconds,
      is_enabled: tool.is_enabled,
    });
    setIsCreateDialogOpen(true);
  };

  const handleDelete = async (toolId: string) => {
    if (confirm(t("deleteConfirm"))) {
      setActionError(null);
      try {
        await deleteTool(toolId);
      } catch {
        setActionError(t("deleteError"));
      }
    }
  };

  const handleOpenWebhook = (url: string) => {
    const safeUrl = getSafeHttpUrl(url);
    if (!safeUrl) {
      setActionError(t("invalidWebhookUrl"));
      return;
    }
    setActionError(null);
    window.open(safeUrl, "_blank", "noopener,noreferrer");
  };

  return (
    <>
      <Header />
      <div className="container mx-auto min-w-0 overflow-x-hidden py-6 sm:py-8 px-4 max-w-7xl">
        {/* Back Button */}
        <div className="mb-4">
          <Link href={`/${locale}/ai-assistant`}>
            <Button type="button" variant="ghost" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              {t("back")}
            </Button>
          </Link>
        </div>

        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <Wrench className="h-8 w-8 text-blue-500" />
              <div className="min-w-0">
                <h1 className="text-2xl sm:text-3xl font-bold break-words">
                  {t("title")}
                </h1>
                <p className="text-muted-foreground">
                  {t("description")}
                </p>
              </div>
            </div>
          </div>

          <Dialog
            open={isCreateDialogOpen}
            onOpenChange={(open) => {
              setIsCreateDialogOpen(open);
              if (!open) {
                setEditingTool(null);
                setFormData({
                  name: "",
                  description: "",
                  webhook_url: "",
                  method: "POST",
                  input_schema: JSON.stringify(
                    {
                      type: "object",
                      properties: {},
                      required: [],
                    },
                    null,
                    2
                  ),
                  timeout_seconds: 30,
                  is_enabled: true,
                });
              }
            }}
          >
            <DialogTrigger asChild>
              <Button type="button" className="w-full sm:w-auto">
                <Plus className="h-4 w-4 mr-2" />
                {t("newTool")}
              </Button>
            </DialogTrigger>

            <DialogContent className="max-h-[90vh] w-[calc(100vw-2rem)] max-w-3xl overflow-y-auto overflow-x-hidden">
              <DialogHeader>
                <DialogTitle>
                  {editingTool ? t("editToolTitle") : t("newToolTitle")}
                </DialogTitle>
                <DialogDescription>
                  {t("dialogDescription")}
                </DialogDescription>
              </DialogHeader>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Name */}
                <div>
                  <Label htmlFor="name">{t("toolName")}</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder="agendar_demo"
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {t("nameHelp")}
                  </p>
                </div>

                {/* Description */}
                <div>
                  <Label htmlFor="description">{t("toolDescription")}</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    placeholder={t("descriptionPlaceholder")}
                    rows={3}
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {t("descriptionHelp")}
                  </p>
                </div>

                {/* Webhook URL */}
                <div>
                  <Label htmlFor="webhook_url">{t("webhookUrl")}</Label>
                  <Input
                    id="webhook_url"
                    type="url"
                    value={formData.webhook_url}
                    onChange={(e) =>
                      setFormData({ ...formData, webhook_url: e.target.value })
                    }
                    placeholder="https://hook.us1.make.com/xyz..."
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {t("webhookHelp")}
                  </p>
                </div>

                {/* Method */}
                <div>
                  <Label htmlFor="method">{t("httpMethod")}</Label>
                  <Select
                    value={formData.method}
                    onValueChange={(value) =>
                      setFormData({ ...formData, method: value })
                    }
                  >
                    <SelectTrigger id="method">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="GET">GET</SelectItem>
                      <SelectItem value="POST">POST</SelectItem>
                      <SelectItem value="PUT">PUT</SelectItem>
                      <SelectItem value="PATCH">PATCH</SelectItem>
                      <SelectItem value="DELETE">DELETE</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Input Schema */}
                <div>
                  <Label htmlFor="input_schema">
                    {t("inputSchema")}
                  </Label>
                  <Textarea
                    id="input_schema"
                    value={formData.input_schema}
                    onChange={(e) =>
                      setFormData({ ...formData, input_schema: e.target.value })
                    }
                    rows={12}
                    className="font-mono text-sm"
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {t("schemaHelp")}
                  </p>
                </div>

                {/* Timeout */}
                <div>
                  <Label htmlFor="timeout">{t("timeoutSeconds")}</Label>
                  <Input
                    id="timeout"
                    type="number"
                    min={1}
                    max={300}
                    value={formData.timeout_seconds}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        timeout_seconds: parseInt(e.target.value),
                      })
                    }
                  />
                </div>

                {/* Is Enabled */}
                <div className="flex items-center space-x-2">
                  <Switch
                    id="is_enabled"
                    checked={formData.is_enabled}
                    onCheckedChange={(checked) =>
                      setFormData({ ...formData, is_enabled: checked })
                    }
                  />
                  <Label htmlFor="is_enabled">{t("enabled")}</Label>
                </div>

                <DialogFooter>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setIsCreateDialogOpen(false);
                      setEditingTool(null);
                    }}
                  >
                    {t("cancel")}
                  </Button>
                  <Button type="submit">
                    {editingTool ? t("updateTool") : t("createTool")}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {actionError && (
          <p className="mb-4 text-sm text-destructive" role="alert">
            {actionError}
          </p>
        )}

        {/* Tools List */}
        <div className="grid gap-4">
          {loading ? (
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-muted-foreground">
                  {t("loading")}
                </p>
              </CardContent>
            </Card>
          ) : tools.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Wrench className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">
                  {t("emptyTitle")}
                </h3>
                <p className="text-muted-foreground mb-4">
                  {t("emptyDescription")}
                </p>
                <Button type="button" onClick={() => setIsCreateDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  {t("createTool")}
                </Button>
              </CardContent>
            </Card>
          ) : (
            tools.map((tool) => (
              <Card key={tool.id}>
                <CardHeader>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <CardTitle className="text-lg">{tool.name}</CardTitle>
                        {tool.is_enabled ? (
                          <Badge className="bg-green-600">
                            <Check className="h-3 w-3 mr-1" />
                            {t("active")}
                          </Badge>
                        ) : (
                          <Badge variant="secondary">
                            <X className="h-3 w-3 mr-1" />
                            {t("inactive")}
                          </Badge>
                        )}
                      </div>
                      <CardDescription>{tool.description}</CardDescription>
                    </div>

                    <div className="flex shrink-0 gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => handleEdit(tool)}
                        aria-label={t("editToolAria", { name: tool.name })}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => handleDelete(tool.id)}
                        aria-label={t("deleteToolAria", { name: tool.name })}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="space-y-3">
                    {/* Webhook URL */}
                    <div>
                      <p className="text-sm font-medium mb-1">Webhook URL</p>
                      <div className="flex min-w-0 items-center gap-2">
                        <code className="min-w-0 text-xs bg-muted px-2 py-1 rounded flex-1 truncate">
                          {tool.webhook_url}
                        </code>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => handleOpenWebhook(tool.webhook_url)}
                          aria-label={t("openWebhookAria", { name: tool.name })}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    {/* Parameters */}
                    <div>
                      <p className="text-sm font-medium mb-1">{t("requiredParameters")}</p>
                      <div className="flex gap-2 flex-wrap">
                        {tool.input_schema.required?.map((param: string) => (
                          <Badge key={param} variant="secondary">
                            <Code className="h-3 w-3 mr-1" />
                            {param}
                          </Badge>
                        ))}
                        {(!tool.input_schema.required ||
                          tool.input_schema.required.length === 0) && (
                          <span className="text-sm text-muted-foreground">
                            {t("noRequiredParameters")}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Method & Timeout */}
                    <div className="flex flex-wrap gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">{t("method")}:</span>{" "}
                        <Badge variant="outline">{tool.method}</Badge>
                      </div>
                      <div>
                        <span className="text-muted-foreground">{t("timeout")}:</span>{" "}
                        {tool.timeout_seconds}s
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </>
  );
}
