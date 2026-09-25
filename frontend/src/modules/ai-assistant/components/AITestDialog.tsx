"use client";

import { useState, useRef, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Loader2,
  Send,
  Sparkles,
  Trash2,
  Bot,
  User,
  Clock,
  Zap,
  MessageSquare,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useTestAIConfig } from "../hooks/useAIAssistant";
import type { AIConfig, TestMessageResponse } from "../types";

interface AITestDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  config: AIConfig;
}

interface TestMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  metadata?: {
    tokens_used?: number;
    processing_time_ms?: number;
    provider?: string;
    model?: string;
  };
}

export function AITestDialog({
  open,
  onOpenChange,
  config,
}: AITestDialogProps) {
  const t = useTranslations("AIAssistant");
  const [inputMessage, setInputMessage] = useState("");
  const [testHistory, setTestHistory] = useState<TestMessage[]>([]);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const testMutation = useTestAIConfig();

  // Auto-scroll al final cuando hay nuevos mensajes
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]",
      );
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [testHistory]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || testMutation.isPending) return;

    const userMessage: TestMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: inputMessage.trim(),
      timestamp: new Date(),
    };

    // Agregar mensaje del usuario al historial
    setTestHistory((prev) => [...prev, userMessage]);
    setInputMessage("");

    try {
      // Enviar a la API
      const result = await testMutation.mutateAsync({
        configId: config.id,
        message: inputMessage.trim(),
      });

      // Agregar respuesta del asistente
      if (result.success && result.response) {
        const assistantMessage: TestMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: result.response,
          timestamp: new Date(),
          metadata: {
            tokens_used: result.tokens_used,
            processing_time_ms: result.processing_time_ms,
            provider: result.provider,
            model: result.model,
          },
        };
        setTestHistory((prev) => [...prev, assistantMessage]);
      } else if (!result.success && result.error) {
        // Mostrar error como mensaje del sistema
        const errorMessage: TestMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `❌ Error: ${result.error}`,
          timestamp: new Date(),
        };
        setTestHistory((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage: TestMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: "❌ Error al procesar el mensaje. Intenta de nuevo.",
        timestamp: new Date(),
      };
      setTestHistory((prev) => [...prev, errorMessage]);
    }
  };

  const handleClearHistory = () => {
    setTestHistory([]);
  };

  const handleClose = () => {
    onOpenChange(false);
  };

  const getTotalTokens = () => {
    return testHistory.reduce((total, msg) => {
      return total + (msg.metadata?.tokens_used || 0);
    }, 0);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("es-MX", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Sandbox de Pruebas - {config.phone_number}
          </DialogTitle>
          <DialogDescription>
            Prueba tu configuración de IA en un entorno aislado. El historial no
            se guarda en la base de datos.
          </DialogDescription>
        </DialogHeader>

        {/* Stats Bar */}
        <div className="flex items-center justify-between gap-4 p-3 rounded-lg bg-muted/50 border">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{testHistory.length}</span>
              <span className="text-muted-foreground">mensajes</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{getTotalTokens()}</span>
              <span className="text-muted-foreground">tokens</span>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearHistory}
            disabled={testHistory.length === 0}
          >
            <Trash2 className="h-4 w-4 mr-1.5" />
            Limpiar Historial
          </Button>
        </div>

        {/* Chat Area */}
        <div className="flex-1 min-h-0 flex flex-col gap-3">
          <ScrollArea ref={scrollAreaRef} className="flex-1 pr-4">
            {testHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <Bot className="h-12 w-12 text-muted-foreground/50 mb-3" />
                <p className="text-sm text-muted-foreground max-w-sm">
                  Envía un mensaje para comenzar a probar tu configuración de
                  IA. Puedes enviar múltiples mensajes para ver cómo mantiene el
                  contexto.
                </p>
              </div>
            ) : (
              <div className="space-y-4 pb-4">
                {testHistory.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {message.role === "assistant" && (
                      <div className="flex-shrink-0">
                        <div className="h-8 w-8 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                          <Bot className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                        </div>
                      </div>
                    )}

                    <div
                      className={`flex flex-col gap-1.5 max-w-[75%] ${
                        message.role === "user" ? "items-end" : "items-start"
                      }`}
                    >
                      <div
                        className={`rounded-lg px-4 py-2.5 ${
                          message.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted border"
                        }`}
                      >
                        <p className="text-sm whitespace-pre-wrap break-words">
                          {message.content}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 px-1">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {formatTime(message.timestamp)}
                        </div>

                        {message.metadata && (
                          <>
                            {message.metadata.tokens_used && (
                              <Badge variant="secondary" className="text-xs">
                                {message.metadata.tokens_used} tokens
                              </Badge>
                            )}
                            {message.metadata.processing_time_ms && (
                              <Badge variant="secondary" className="text-xs">
                                {message.metadata.processing_time_ms}ms
                              </Badge>
                            )}
                          </>
                        )}
                      </div>
                    </div>

                    {message.role === "user" && (
                      <div className="flex-shrink-0">
                        <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                          <User className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {testMutation.isPending && (
                  <div className="flex gap-3 justify-start">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                        <Bot className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                      </div>
                    </div>
                    <div className="bg-muted border rounded-lg px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-purple-500" />
                        <span className="text-sm text-muted-foreground">
                          Pensando...
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </ScrollArea>

          {/* Input Area */}
          <div className="border-t pt-3">
            <div className="flex gap-2">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Escribe un mensaje de prueba..."
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={testMutation.isPending}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={testMutation.isPending || !inputMessage.trim()}
                size="icon"
              >
                {testMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>

            {/* Config Info Compact */}
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <Badge variant="outline" className="text-xs">
                {config.provider} / {config.model}
              </Badge>
              <Badge variant="outline" className="text-xs">
                temp: {config.temperature.toFixed(1)}
              </Badge>
              <Badge variant="outline" className="text-xs">
                max: {config.max_tokens} tokens
              </Badge>
              {config.use_memory && (
                <Badge variant="outline" className="text-xs">
                  memoria: {config.memory_window} msgs
                </Badge>
              )}
              {config.auto_enhance_prompt && (
                <Badge variant="outline" className="text-xs">
                  auto-mejora
                </Badge>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
