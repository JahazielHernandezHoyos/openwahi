"use client";

import { Link } from "@/i18n/routing";
import { useAuth } from "@/context/AuthContext";
import { Header } from "@/components/layout/Header";
import { useMounted } from "@/tools/hooks/useMounted";
import { useWhatsAppDevices } from "@/modules/whatsapp";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FormContainer } from "@/components/shared/FormContainer";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  MessageSquare,
  ArrowRight,
  Smartphone,
  CheckCircle2,
  AlertCircle,
  History,
  Clock,
  Bot,
  Send,
} from "lucide-react";

import { useTranslations, useLocale } from "next-intl";
import { useWhatsAppChats } from "@/modules/whatsapp/hooks/useWhatsAppChats";
import { useAIConfigs } from "@/modules/ai-assistant/hooks/useAIAssistant";
import { formatDistanceToNow } from "date-fns";
import { es, enUS } from "date-fns/locale";

export default function DashboardPage() {
  const t = useTranslations("Dashboard");
  const locale = useLocale();
  const { user, loading } = useAuth();
  const mounted = useMounted();
  const { devices, loading: devicesLoading } = useWhatsAppDevices();

  const connectedDevice = devices.find((d) => d.status === "connected");
  const {
    chats,
    loading: chatsLoading,
    total: chatsTotal,
  } = useWhatsAppChats(connectedDevice?.id);

  // Fetch AI configs for the connected device (if any)
  const { data: aiConfigs, isLoading: aiLoading } = useAIConfigs(
    connectedDevice?.id || null,
  );
  const activeBots = aiConfigs?.filter((c) => c.is_enabled).length || 0;

  const showLoading = !mounted || loading;

  const connectedDevices = devices.filter((d) => d.status === "connected");
  const hasConnected = connectedDevices.length > 0;

  if (showLoading) {
    return (
      <div className="min-h-screen bg-background" suppressHydrationWarning>
        <Header />
        <div
          className="max-w-7xl mx-auto px-4 py-8 lg:py-12 space-y-8 animate-in fade-in duration-500"
          suppressHydrationWarning
        >
          <div className="space-y-4">
            <Skeleton className="h-10 w-64" />
            <Skeleton className="h-6 w-96" />
          </div>
          <div
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
            suppressHydrationWarning
          >
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" suppressHydrationWarning>
      <Header />

      <div
        className="max-w-7xl mx-auto px-4 py-8 lg:py-12 animate-in fade-in slide-in-from-bottom-2 duration-700"
        suppressHydrationWarning
      >
        {/* Welcome Section */}
        <div className="mb-10 space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">
            {t("title")}
          </h1>
          <p className="text-muted-foreground text-lg" suppressHydrationWarning>
            {t("welcome")},{" "}
            <span className="text-foreground font-semibold">{user?.email}</span>
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card className="bg-green-500/5 border-green-500/10 hover:bg-green-500/10 transition-colors cursor-default group">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 rounded-full bg-green-500/10 flex items-center justify-center text-green-500 group-hover:scale-110 transition-transform">
                <Smartphone className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-green-600/70 font-medium uppercase tracking-wider">
                  {t("device")}
                </p>
                <p className="text-2xl font-bold">{connectedDevices.length}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-blue-500/5 border-blue-500/10 hover:bg-blue-500/10 transition-colors cursor-default group">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500 group-hover:scale-110 transition-transform">
                <MessageSquare className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-blue-600/70 font-medium uppercase tracking-wider">
                  {t("totalChats")}
                </p>
                <p className="text-2xl font-bold">
                  {chatsLoading ? "..." : chatsTotal}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-purple-500/5 border-purple-500/10 hover:bg-purple-500/10 transition-colors cursor-default group">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-500 group-hover:scale-110 transition-transform">
                <History className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-purple-600/70 font-medium uppercase tracking-wider">
                  {t("active")}
                </p>
                <p className="text-2xl font-bold">
                  {hasConnected ? t("active") : t("inactive")}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-orange-500/5 border-orange-500/10 hover:bg-orange-500/10 transition-colors cursor-default group">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 rounded-full bg-orange-500/10 flex items-center justify-center text-orange-500 group-hover:scale-110 transition-transform">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-orange-600/70 font-medium uppercase tracking-wider">
                  {t("aiBots")}
                </p>
                <p className="text-2xl font-bold">
                  {aiLoading ? "..." : activeBots}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-8">
            <FormContainer
              title={t("systemSummary")}
              description={t("systemSummaryDesc")}
              icon={LayoutDashboard}
            >
              <div className="grid sm:grid-cols-2 gap-4 mt-2">
                {/* WhatsApp Status Card */}
                <Card className="bg-background/50 border-muted-foreground/10 hover:border-primary/20 transition-all group">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <MessageSquare className="h-5 w-5 text-green-500" />
                      {hasConnected ? (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-green-500/10 rounded-full">
                          <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                          <span className="text-[10px] font-bold text-green-600 uppercase tracking-wider">
                            {t("active")}
                          </span>
                        </div>
                      ) : (
                        <div className="px-2 py-0.5 bg-muted rounded-full">
                          <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                            {t("inactive")}
                          </span>
                        </div>
                      )}
                    </div>
                    <CardTitle className="text-lg mt-3">WhatsApp</CardTitle>
                    <CardDescription
                      className="flex flex-col gap-1"
                      suppressHydrationWarning
                    >
                      <span>
                        {hasConnected
                          ? t("connectedDevices", {
                              count: connectedDevices.length,
                            })
                          : t("noLinkedDevices")}
                      </span>
                      {hasConnected && !chatsLoading && (
                        <span className="text-xs text-primary font-medium">
                          {t("totalChats")}: {chatsTotal}
                        </span>
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <Link href="/whatsapp-devices">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full group-hover:bg-primary group-hover:text-primary-foreground transition-all"
                      >
                        {t("manage")}
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </Button>
                    </Link>
                  </CardContent>
                </Card>

                {/* AI Assistant Card */}
                <Card className="bg-background/50 border-muted-foreground/10 hover:border-primary/20 transition-all group">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <Bot className="h-5 w-5 text-orange-500" />
                      {activeBots > 0 ? (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-orange-500/10 rounded-full">
                          <div className="h-1.5 w-1.5 rounded-full bg-orange-500 animate-pulse" />
                          <span className="text-[10px] font-bold text-orange-600 uppercase tracking-wider">
                            {t("active")}
                          </span>
                        </div>
                      ) : (
                        <div className="px-2 py-0.5 bg-muted rounded-full">
                          <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                            {t("inactive")}
                          </span>
                        </div>
                      )}
                    </div>
                    <CardTitle className="text-lg mt-3">
                      {t("aiAssistant")}
                    </CardTitle>
                    <CardDescription className="flex flex-col gap-1">
                      <span>{t("activeBots", { count: activeBots })}</span>
                      {hasConnected && aiConfigs && aiConfigs.length > 0 && (
                        <span className="text-xs text-primary font-medium">
                          {aiConfigs[0].model} ({aiConfigs[0].provider})
                        </span>
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <Link href="/ai-assistant">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full group-hover:bg-primary group-hover:text-primary-foreground transition-all"
                      >
                        {t("configureAI")}
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              </div>
            </FormContainer>

            {/* Recent Chats Activity */}
            <FormContainer
              title={t("recentActivity")}
              description={t("viewAllChats")}
              icon={History}
            >
              <div className="space-y-3 mt-2">
                {chatsLoading ? (
                  <div className="space-y-3">
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-16 w-full" />
                  </div>
                ) : chats.length > 0 ? (
                  chats.slice(0, 3).map((chat) => (
                    <Link key={chat.phone} href="/whatsapp-chats">
                      <div className="flex items-center justify-between p-4 rounded-xl bg-muted/20 border border-muted-foreground/5 hover:bg-muted/40 transition-all mb-2">
                        <div className="flex items-center gap-4">
                          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                            <MessageSquare className="h-5 w-5" />
                          </div>
                          <div>
                            <p className="font-semibold text-sm">
                              +{chat.phone}
                            </p>
                            <p className="text-xs text-muted-foreground truncate max-w-[200px] sm:max-w-md">
                              {chat.last_message || "..."}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-[10px] text-muted-foreground font-medium flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {chat.last_message_timestamp
                              ? formatDistanceToNow(
                                  new Date(chat.last_message_timestamp),
                                  {
                                    addSuffix: true,
                                    locale: locale === "es" ? es : enUS,
                                  },
                                )
                              : ""}
                          </p>
                        </div>
                      </div>
                    </Link>
                  ))
                ) : (
                  <div className="text-center py-8 rounded-xl border border-dashed border-muted-foreground/20">
                    <p className="text-sm text-muted-foreground">
                      {t("noRecentChats")}
                    </p>
                  </div>
                )}
                {chats.length > 3 && (
                  <Link href="/whatsapp-chats">
                    <Button variant="link" size="sm" className="px-0 text-xs">
                      {t("viewAllChats")}
                    </Button>
                  </Link>
                )}
              </div>
            </FormContainer>
          </div>

          {/* Sidebar / Quick Actions */}
          <div className="space-y-6">
            <Card className="border-muted-foreground/10 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-bold uppercase tracking-widest text-muted-foreground">
                  {t("whatsappStatus")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {devicesLoading ? (
                  <Skeleton className="h-20 w-full" />
                ) : devices.length > 0 ? (
                  <div className="space-y-3">
                    {devices.slice(0, 3).map((device) => (
                      <div
                        key={device.id}
                        className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-muted-foreground/5"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={
                              device.status === "connected"
                                ? "text-green-500"
                                : "text-muted-foreground/40"
                            }
                          >
                            <Smartphone className="h-4 w-4" />
                          </div>
                          <div className="text-xs">
                            <p className="font-semibold">
                              {device.name
                                ? device.name.replace(
                                    /^WhatsApp\.device\s*/i,
                                    `${t("device")} WhatsApp `,
                                  )
                                : t("device")}
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                              +{device.phone || t("pending")}
                            </p>
                          </div>
                        </div>
                        {device.status === "connected" ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                        ) : (
                          <AlertCircle className="h-3.5 w-3.5 text-yellow-500" />
                        )}
                      </div>
                    ))}
                    {devices.length > 3 && (
                      <p className="text-[10px] text-center text-muted-foreground">
                        {t("plusMore", { count: devices.length - 3 })}
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-4 space-y-3">
                    <p className="text-xs text-muted-foreground">
                      {t("noLinkedDevices")}
                    </p>
                    <Link href="/whatsapp-devices">
                      <Button
                        size="sm"
                        variant="link"
                        className="text-xs h-auto p-0"
                      >
                        {t("linkNow")}
                      </Button>
                    </Link>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="border-muted-foreground/10 shadow-sm overflow-hidden">
              <CardHeader className="bg-muted/30 pb-3">
                <CardTitle className="text-sm font-bold uppercase tracking-widest text-muted-foreground">
                  {t("quickActions")}
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-2 p-3">
                <Link href="/whatsapp-devices">
                  <Button
                    variant="ghost"
                    className="w-full justify-start text-xs font-semibold h-10 hover:bg-primary/10 hover:text-primary transition-all"
                  >
                    <Smartphone className="h-4 w-4 mr-2" />
                    {t("linkDevice")}
                  </Button>
                </Link>
                <Link href="/ai-assistant">
                  <Button
                    variant="ghost"
                    className="w-full justify-start text-xs font-semibold h-10 hover:bg-primary/10 hover:text-primary transition-all"
                  >
                    <Bot className="h-4 w-4 mr-2" />
                    {t("configureAI")}
                  </Button>
                </Link>
                <Link href="/whatsapp-devices">
                  <Button
                    variant="ghost"
                    className="w-full justify-start text-xs font-semibold h-10 hover:bg-primary/10 hover:text-primary transition-all"
                  >
                    <Send className="h-4 w-4 mr-2" />
                    {t("sendTest")}
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
