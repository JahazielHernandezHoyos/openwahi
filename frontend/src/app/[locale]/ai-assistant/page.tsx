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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sparkles, Bot, Zap, AlertCircle, Smartphone, Wrench } from "lucide-react";
import { useTranslations } from "next-intl";
import { useWhatsAppDevices } from "@/modules/whatsapp/hooks/useWhatsAppDevices";
import { AIConfigPanel } from "@/modules/ai-assistant/components/AIConfigPanel";
import { StandaloneConfigsPanel } from "@/modules/ai-assistant/components/StandaloneConfigsPanel";
import { useAIConfigs } from "@/modules/ai-assistant/hooks/useAIAssistant";
import Link from "next/link";
import { useLocale } from "next-intl";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function AIAssistantPage() {
  const t = useTranslations("AIAssistant");
  const tWhatsApp = useTranslations("WhatsApp");
  const locale = useLocale();
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");

  const { devices, loading: devicesLoading } = useWhatsAppDevices();
  const { data: configs } = useAIConfigs(selectedDeviceId || null);

  // Filter connected devices
  const connectedDevices = devices.filter((d) => d.status === "connected");

  // Auto-select first connected device
  if (!selectedDeviceId && connectedDevices.length > 0 && !devicesLoading) {
    setSelectedDeviceId(connectedDevices[0].id);
  }

  // Count active configs
  const activeConfigsCount = configs?.filter((c) => c.is_enabled).length || 0;

  return (
    <>
      <Header />
      <div className="container mx-auto min-w-0 overflow-x-hidden py-6 sm:py-8 px-4 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-2">
            <div className="flex min-w-0 items-center gap-3">
              <Sparkles className="h-8 w-8 text-purple-500" />
              <div className="min-w-0">
                <h1 className="text-2xl sm:text-3xl font-bold break-words">{t("title")}</h1>
                <p className="text-muted-foreground">{t("description")}</p>
              </div>
            </div>

            <Link className="self-start sm:self-auto" href={`/${locale}/ai-assistant/tools`}>
              <Button variant="outline" className="gap-2">
                <Wrench className="h-4 w-4" />
                {t("webhookTools")}
              </Button>
            </Link>
          </div>

          {/* Stats */}
          {selectedDeviceId && configs && (
            <div className="flex flex-wrap gap-4 mt-4">
              <Badge variant="outline" className="gap-2 px-3 py-1">
                <Bot className="h-4 w-4" />
                {configs.length} {t("messages", { count: configs.length })}
              </Badge>
              {activeConfigsCount > 0 && (
                <Badge className="gap-2 px-3 py-1 bg-green-600">
                  <Zap className="h-4 w-4" />
                  {activeConfigsCount} {t("enabled")}
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* Tabs: WhatsApp vs Widget */}
        <Tabs defaultValue="whatsapp" className="w-full">
          <TabsList className="mb-6 grid h-auto w-full grid-cols-2 sm:inline-grid sm:w-auto">
            <TabsTrigger value="whatsapp" className="gap-2">
              <Smartphone className="h-4 w-4" />
              {tWhatsApp("title")}
            </TabsTrigger>
            <TabsTrigger value="standalone" className="gap-2">
              <Bot className="h-4 w-4" />
              {t("standaloneTab")}
            </TabsTrigger>
          </TabsList>

          {/* ── WhatsApp tab ───────────────────────────────────── */}
          <TabsContent value="whatsapp">
            {/* Device Selector */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Smartphone className="h-5 w-5" />
                  {tWhatsApp("selectDevice")}
                </CardTitle>
                <CardDescription>
                  {t("selectDeviceDesc")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {devicesLoading ? (
                  <Skeleton className="h-10 w-full" />
                ) : connectedDevices.length === 0 ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {tWhatsApp("noDevices")} - {t("needsDeviceFirst")}
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-2">
                    <Select
                      value={selectedDeviceId}
                      onValueChange={(value) => {
                        setSelectedDeviceId(value);
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder={t("selectDevicePlaceholder")} />
                      </SelectTrigger>
                      <SelectContent>
                        {connectedDevices.map((device) => (
                          <SelectItem key={device.id} value={device.id}>
                            <div className="flex min-w-0 items-center gap-2 overflow-hidden">
                              <Badge variant="outline" className="text-green-600">
                                {tWhatsApp("status.connected")}
                              </Badge>
                              <span className="truncate font-mono">{device.phone}</span>
                              {device.name && (
                                <span className="text-muted-foreground">
                                  - {device.name}
                                </span>
                              )}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      {t("onlyConnectedDevices")}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Info Alert */}
            {selectedDeviceId && (
              <div className="mb-6 p-4 rounded-xl border border-purple-500/20 bg-purple-500/5 backdrop-blur-sm flex items-start gap-3">
                <Sparkles className="h-5 w-5 text-purple-400 shrink-0 mt-0.5" />
                <p className="text-sm text-purple-100/80 leading-relaxed">
                  <strong className="text-purple-300">{t("howItWorks")}</strong>{" "}
                  {t("howItWorksDesc")}
                </p>
              </div>
            )}

            {/* Configurations Panel */}
            {selectedDeviceId ? (
              <AIConfigPanel deviceId={selectedDeviceId} />
            ) : (
              <Card>
                <CardContent className="py-12">
                  <div className="text-center">
                    <Smartphone className="h-16 w-16 mx-auto mb-4 opacity-30" />
                    <h3 className="text-lg font-medium mb-2">
                      {tWhatsApp("selectDevice")}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {t("selectDeviceForAI")}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Help Section */}
            {selectedDeviceId && (
              <Card className="mt-6 border-blue-500/20 bg-blue-500/5 backdrop-blur-sm shadow-xl">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2 text-blue-300">
                    <AlertCircle className="h-5 w-5 text-blue-400" />
                    {t("quickGuide")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <strong className="text-blue-200">{t("guideStep1Title")}</strong>
                      <p className="text-blue-100/60 mt-1">
                        {t("guideStep1Desc").split("console.groq.com/keys")[0]}
                        <a
                          href="https://console.groq.com/keys"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 transition-colors underline underline-offset-4"
                        >
                          console.groq.com/keys
                        </a>
                        {t("guideStep1Desc").split("console.groq.com/keys")[1]}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3 border-t border-blue-500/10 pt-4">
                    <div className="flex-1">
                      <strong className="text-blue-200">{t("guideStep2Title")}</strong>
                      <p className="text-blue-100/60 mt-1">{t("guideStep2Desc")}</p>
                    </div>
                  </div>
                  <div className="flex gap-3 border-t border-blue-500/10 pt-4">
                    <div className="flex-1">
                      <strong className="text-blue-200">{t("guideStep3Title")}</strong>
                      <p className="text-blue-100/60 mt-1">{t("guideStep3Desc")}</p>
                    </div>
                  </div>
                  <div className="mt-2 p-3 rounded-lg bg-blue-400/10 border border-blue-400/20">
                    <p className="text-blue-200 flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      <strong>{t("proTip")}</strong>
                    </p>
                    <p className="text-blue-100/70 mt-1 italic">{t("proTipDesc")}</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* ── Standalone / Widget tab ────────────────────────── */}
          <TabsContent value="standalone">
            <StandaloneConfigsPanel />
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}

