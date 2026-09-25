"use client";

import { useState, useRef } from "react";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
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
} from "@/components/ui/alert-dialog";
import {
  useKnowledgeBases,
  useCreateKnowledgeBase,
  useDeleteKnowledgeBase,
  useToggleKnowledgeBase,
  useKnowledgeBaseDocuments,
  useUploadDocument,
  useDeleteDocument,
} from "@/modules/knowledge-base/hooks/useKnowledgeBase";
import type {
  KnowledgeBase,
  KnowledgeDocument,
} from "@/modules/knowledge-base/types";
import {
  Database,
  Plus,
  FileText,
  Trash2,
  Upload,
  RefreshCw,
  Search,
  ToggleLeft,
  ToggleRight,
  ChevronDown,
  ChevronUp,
  File,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  Download,
} from "lucide-react";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function DocumentStatusBadge({ status }: { status: string }) {
  switch (status) {
    case "ready":
      return (
        <Badge variant="default" className="bg-green-500">
          <CheckCircle className="w-3 h-3 mr-1" />
          Ready
        </Badge>
      );
    case "processing":
      return (
        <Badge variant="secondary">
          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
          Processing
        </Badge>
      );
    case "pending":
      return (
        <Badge variant="outline">
          <Clock className="w-3 h-3 mr-1" />
          Pending
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="destructive">
          <AlertCircle className="w-3 h-3 mr-1" />
          Failed
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function KnowledgeBaseCard({
  kb,
  onDelete,
  onToggle,
}: {
  kb: KnowledgeBase;
  onDelete: (id: string) => void;
  onToggle: (id: string, isActive: boolean) => void;
}) {
  const t = useTranslations("KnowledgeBase");
  const [expanded, setExpanded] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: documents, isLoading: loadingDocs } = useKnowledgeBaseDocuments(
    expanded ? kb.id : "",
  );
  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file size (5MB limit for small VPS)
      const maxSizeMB = 5;
      const maxSizeBytes = maxSizeMB * 1024 * 1024;

      if (file.size > maxSizeBytes) {
        alert(
          `File size exceeds ${maxSizeMB}MB limit. Please choose a smaller file.`,
        );
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      try {
        await uploadMutation.mutateAsync({ kbId: kb.id, file });
        setUploadOpen(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      } catch (error) {
        // Error silenciado
      }
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    try {
      await deleteMutation.mutateAsync({ kbId: kb.id, docId });
    } catch (error) {
      // Error silenciado
    }
  };

  return (
    <Card className={`min-w-0 ${!kb.is_active ? "opacity-60" : ""}`}>
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <Database className="h-5 w-5 shrink-0 text-primary" />
            <div className="min-w-0">
              <CardTitle className="break-words text-lg">{kb.name}</CardTitle>
              {kb.description && (
                <CardDescription className="mt-1 break-words">
                  {kb.description}
                </CardDescription>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onToggle(kb.id, !kb.is_active)}
              title={kb.is_active ? t("deactivate") : t("activate")}
            >
              {kb.is_active ? (
                <ToggleRight className="w-5 h-5 text-green-500" />
              ) : (
                <ToggleLeft className="w-5 h-5 text-gray-400" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(kb.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mb-4">
          <span className="flex items-center gap-1">
            <FileText className="w-4 h-4" />
            {kb.total_documents} {t("documents")}
          </span>
          <span>{kb.total_chunks} chunks</span>
          <span>{formatBytes(kb.total_size_bytes)}</span>
          <Badge variant="outline">{kb.embedding_model}</Badge>
        </div>

        <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
          <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="w-full sm:w-auto">
                <Upload className="w-4 h-4 mr-2" />
                {t("uploadDocument")}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t("uploadDocument")}</DialogTitle>
                <DialogDescription>{t("uploadDescription")}</DialogDescription>
              </DialogHeader>
              <div className="py-4">
                <Input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv,.pdf,.txt,.md,.docx,.json"
                  onChange={handleFileSelect}
                  disabled={uploadMutation.isPending}
                />
                <div className="space-y-1 mt-2">
                  <p className="text-xs text-muted-foreground">
                    {t("supportedFormats")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    <span className="font-medium">Max file size:</span> 5 MB
                  </p>
                </div>
              </div>
              {uploadMutation.isPending && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t("uploading")}
                </div>
              )}
            </DialogContent>
          </Dialog>

          <Button
            variant="ghost"
            size="sm"
            className="w-full sm:w-auto"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>
                <ChevronUp className="w-4 h-4 mr-1" />
                {t("hideDocuments")}
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4 mr-1" />
                {t("showDocuments")}
              </>
            )}
          </Button>
        </div>

        {expanded && (
          <div className="mt-4 border-t pt-4">
            {loadingDocs ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                {t("loadingDocuments")}
              </div>
            ) : documents && documents.length > 0 ? (
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex min-w-0 flex-col gap-2 rounded-lg bg-muted/50 p-2 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <File className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <p className="break-all text-sm font-medium">{doc.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatBytes(doc.file_size_bytes)} |{" "}
                          {doc.total_chunks} chunks
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2 sm:shrink-0">
                      <DocumentStatusBadge status={doc.status} />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={async () => {
                          try {
                            const { knowledgeBaseApi } =
                              await import("@/modules/knowledge-base/services/knowledgeBaseApi");
                            await knowledgeBaseApi.downloadDocument(
                              kb.id,
                              doc.id,
                              doc.filename,
                            );
                          } catch (error) {
                            // Error silenciado
                          }
                        }}
                        title="Download document"
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteDocument(doc.id)}
                        disabled={deleteMutation.isPending}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {t("noDocuments")}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function KnowledgeBasePage() {
  const t = useTranslations("KnowledgeBase");
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [newKb, setNewKb] = useState({
    name: "",
    description: "",
  });

  const { data: knowledgeBases, isLoading, refetch } = useKnowledgeBases(true);
  const createMutation = useCreateKnowledgeBase();
  const deleteMutation = useDeleteKnowledgeBase();
  const toggleMutation = useToggleKnowledgeBase();

  const handleCreate = async () => {
    if (!newKb.name.trim()) return;
    try {
      await createMutation.mutateAsync({
        name: newKb.name,
        description: newKb.description || undefined,
      });
      setCreateOpen(false);
      setNewKb({ name: "", description: "" });
    } catch (error) {
      // Error silenciado
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await deleteMutation.mutateAsync(deleteId);
      setDeleteId(null);
    } catch (error) {
      // Error silenciado
    }
  };

  const handleToggle = async (id: string, isActive: boolean) => {
    try {
      await toggleMutation.mutateAsync({ id, isActive });
    } catch (error) {
      // Error silenciado
    }
  };

  return (
    <>
      <Header />
      <div className="container mx-auto py-6 px-4 max-w-5xl">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold">{t("title")}</h1>
            <p className="break-words text-muted-foreground">{t("description")}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:shrink-0">
            <Button className="flex-1 sm:flex-none" variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              {t("refresh")}
            </Button>
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <DialogTrigger asChild>
                <Button className="w-full sm:w-auto">
                  <Plus className="w-4 h-4 mr-2" />
                  {t("create")}
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t("createTitle")}</DialogTitle>
                  <DialogDescription>
                    {t("createDescription")}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">{t("name")}</Label>
                    <Input
                      id="name"
                      value={newKb.name}
                      onChange={(e) =>
                        setNewKb({ ...newKb, name: e.target.value })
                      }
                      placeholder={t("namePlaceholder")}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">{t("descriptionLabel")}</Label>
                    <Textarea
                      id="description"
                      value={newKb.description}
                      onChange={(e) =>
                        setNewKb({ ...newKb, description: e.target.value })
                      }
                      placeholder={t("descriptionPlaceholder")}
                      rows={3}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setCreateOpen(false)}
                  >
                    {t("cancel")}
                  </Button>
                  <Button
                    onClick={handleCreate}
                    disabled={!newKb.name.trim() || createMutation.isPending}
                  >
                    {createMutation.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Plus className="w-4 h-4 mr-2" />
                    )}
                    {t("create")}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : knowledgeBases && knowledgeBases.length > 0 ? (
          <div className="space-y-4">
            {knowledgeBases.map((kb) => (
              <KnowledgeBaseCard
                key={kb.id}
                kb={kb}
                onDelete={setDeleteId}
                onToggle={handleToggle}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Database className="w-12 h-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">{t("empty")}</h3>
              <p className="text-muted-foreground text-center mb-4">
                {t("emptyDescription")}
              </p>
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                {t("createFirst")}
              </Button>
            </CardContent>
          </Card>
        )}

        <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
              <AlertDialogDescription>
                {t("deleteDescription")}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4 mr-2" />
                )}
                {t("delete")}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </>
  );
}
