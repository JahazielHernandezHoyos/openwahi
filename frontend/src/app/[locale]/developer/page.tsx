"use client";

import { Header } from "@/components/layout/Header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiTokensTab, WebhookTab, DocumentationTab } from "@/modules/developer";
import { useWhatsAppDevices } from "@/modules/whatsapp";
import { Code2, Key, Webhook, FileText } from "lucide-react";
import { useTranslations } from "next-intl";

export default function DeveloperPage() {
  const t = useTranslations("Developer");
  const { devices } = useWhatsAppDevices();

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Code2 className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">{t("title")}</h1>
            <p className="text-muted-foreground">{t("description")}</p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="tokens" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="tokens" className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              {t("tabTokens")}
            </TabsTrigger>
            <TabsTrigger value="webhook" className="flex items-center gap-2">
              <Webhook className="h-4 w-4" />
              {t("tabWebhook")}
            </TabsTrigger>
            <TabsTrigger value="docs" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              {t("tabDocs")}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="tokens">
            <ApiTokensTab />
          </TabsContent>

          <TabsContent value="webhook">
            <WebhookTab />
          </TabsContent>

          <TabsContent value="docs">
            <DocumentationTab devices={devices} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
