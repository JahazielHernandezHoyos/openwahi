"use client";

import { useState, useCallback, useEffect } from "react";
import { useMounted } from "@/tools/hooks/useMounted";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useWhatsAppDevices,
  WhatsAppDeviceList,
  WhatsAppQRScanner,
  WhatsAppSendMessage,
  WhatsAppInbox,
} from "@/modules/whatsapp";
import { Plus, Smartphone, MessageSquare, CheckCircle2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSubscription } from "@/modules/subscription/hooks/useSubscription";

export default function WhatsAppPage() {
  const t = useTranslations("WhatsApp");
  const mounted = useMounted();
  const { data: subscription, isLoading: subscriptionLoading } = useSubscription();
  const deviceLimit = subscription?.device_limit ?? 1;
  const {
    devices,
    loading: devicesLoading,
    createDevice,
    isCreating,
    deleteDevice,
    isDeleting,
    refetch,
    invalidateDevices,
  } = useWhatsAppDevices();

  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [showNewDevice, setShowNewDevice] = useState(false);
  const [newDeviceId, setNewDeviceId] = useState<string | null>(null);

  // Auto-select first connected device if none selected
  useEffect(() => {
    if (!selectedDeviceId && devices.length > 0) {
      const connectedDevice = devices.find((d) => d.status === "connected");
      if (connectedDevice) {
        setSelectedDeviceId(connectedDevice.id);
        setShowNewDevice(false);
      }
    }
  }, [devices, selectedDeviceId]);

  // Get selected device
  const selectedDevice = devices.find((d) => d.id === selectedDeviceId);
  const isConnected = selectedDevice?.status === "connected";

  // Check if any device is connected
  const hasConnectedDevice = devices.some((d) => d.status === "connected");

  // Handle creating new device
  const handleCreateDevice = async () => {
    try {
      const result = await createDevice({
        name: `${t("device")} ${devices.length + 1}`,
      });

      // Check if error (max devices reached)
      if (result.qr?.status === "error") {
        alert(result.qr.message || "Error creating device");
        return;
      }

      setSelectedDeviceId(result.device.id);

      // If device is already connected (GOWA had existing session), don't show QR
      if (
        result.device.status === "connected" ||
        result.qr?.status === "connected"
      ) {
        setShowNewDevice(false);
        setNewDeviceId(null);
        refetch();
      } else {
        setNewDeviceId(result.device.id);
        setShowNewDevice(true);
      }
    } catch (error) {
      // Error silenciado
    }
  };

  // Handle device connection
  const handleDeviceConnected = useCallback(() => {
    setShowNewDevice(false);
    setNewDeviceId(null);
    refetch();
  }, [refetch]);

  // Handle delete device
  const handleDeleteDevice = async (deviceId: string) => {
    try {
      await deleteDevice(deviceId);
      if (selectedDeviceId === deviceId) {
        setSelectedDeviceId(null);
      }
    } catch (error) {
      // Error silenciado
    }
  };

  // Handle select device
  const handleSelectDevice = (deviceId: string) => {
    setSelectedDeviceId(deviceId);
    setShowNewDevice(false);
    setNewDeviceId(null);
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <MessageSquare className="h-8 w-8 text-green-500" />
            <div>
              <h1 className="text-3xl font-bold">{t("title")}</h1>
              <p className="text-muted-foreground">
                {t("description")}
              </p>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Devices */}
          <div className="space-y-6">
            {/* Devices List */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2" suppressHydrationWarning>
                    <Smartphone className="h-5 w-5" />
                    {t("devices")}
                  </CardTitle>
                  <Button
                    size="sm"
                    onClick={handleCreateDevice}
                    disabled={
                      isCreating ||
                      subscriptionLoading ||
                      devices.length >= deviceLimit
                    }
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    {isCreating ? t("creating") : t("add")}
                  </Button>
                </div>
                {subscriptionLoading ? (
                  <Skeleton className="h-4 w-40" />
                ) : (
                  <CardDescription suppressHydrationWarning>
                    {t("devicesCount", {
                      count: devices.length,
                      limit: deviceLimit,
                    })}
                    {devices.length >= deviceLimit && ` ${t("deviceLimitReached")}`}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                {devicesLoading && devices.length === 0 ? (
                  <div className="space-y-3" suppressHydrationWarning>
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-16 w-full" />
                  </div>
                ) : (
                  <WhatsAppDeviceList
                    devices={devices}
                    selectedDeviceId={selectedDeviceId}
                    onSelectDevice={handleSelectDevice}
                    onDeleteDevice={handleDeleteDevice}
                    isDeleting={isDeleting}
                  />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column - QR/Messages */}
          <div className="lg:col-span-2 space-y-6" suppressHydrationWarning>
            {/* QR Scanner - Show when pending or new device */}
            {(showNewDevice || selectedDevice?.status === "pending") &&
              !isConnected && (
                <WhatsAppQRScanner
                  deviceId={newDeviceId || selectedDeviceId}
                  onConnected={handleDeviceConnected}
                />
              )}

            {/* Connected Device View */}
            {isConnected && selectedDevice && (
              <>
                {/* Connection Status Banner */}
                <Card className="border-green-500/20 bg-green-500/[0.03] dark:bg-green-500/[0.05] shadow-sm overflow-hidden">
                  <CardContent className="p-5">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                      <div className="flex items-center gap-4 w-full">
                        <div className="flex-shrink-0 p-3 bg-green-500/10 rounded-xl">
                          <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h3 className="text-lg font-bold text-green-800 dark:text-green-300">
                              {t("connected")}
                            </h3>
                            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                          </div>
                          <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-sm font-medium text-green-700/70 dark:text-green-400/70">
                            {selectedDevice.phone && (
                              <span className="flex items-center gap-1.5 px-2 py-0.5 bg-green-500/10 rounded-md font-mono">
                                <Smartphone className="h-3.5 w-3.5" />
                                {`+${selectedDevice.phone}`}
                              </span>
                            )}
                            {selectedDevice.name && (
                              <span className="flex items-center gap-1">
                                <span className="opacity-50">•</span>
                                {selectedDevice.name}
                              </span>
                            )}
                            {!selectedDevice.phone && !selectedDevice.name && (
                              <span>{t("linkedSuccessfully")}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 w-full md:w-auto">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => refetch()}
                          className="flex-1 md:flex-none bg-background/50 border-green-500/20 hover:bg-green-500/10 hover:text-green-700 dark:hover:text-green-300 transition-all font-medium"
                        >
                          {t("update")}
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteDevice(selectedDevice.id)}
                          disabled={isDeleting}
                          className="flex-1 md:flex-none shadow-sm font-medium"
                        >
                          {isDeleting ? t("disconnecting") : t("disconnect")}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Send Message */}
                <WhatsAppSendMessage
                  deviceId={selectedDeviceId}
                  isConnected={isConnected}
                />

                {/* Inbox */}
                <WhatsAppInbox
                  deviceId={selectedDeviceId}
                  onDeviceStatusChange={invalidateDevices}
                />
              </>
            )}

            {/* No device selected and no connected device */}
            {!selectedDeviceId && !showNewDevice && !hasConnectedDevice && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center py-12 text-muted-foreground" suppressHydrationWarning>
                    <MessageSquare className="h-16 w-16 mx-auto mb-4 opacity-30" />
                    <h3 className="text-lg font-medium mb-2">
                      {t("linkYourWhatsapp")}
                    </h3>
                    <p className="text-sm mb-4">
                      {t("scanQrDesc")}
                    </p>
                    <Button onClick={handleCreateDevice} disabled={isCreating}>
                      <Plus className="h-4 w-4 mr-2" />
                      {t("linkWhatsappButton")}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Disconnected device */}
            {selectedDevice && selectedDevice.status === "disconnected" && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center py-8 text-muted-foreground">
                    <Smartphone className="h-12 w-12 mx-auto mb-4 opacity-30" />
                    <h3 className="text-lg font-medium mb-2 text-destructive">
                      {t("deviceDisconnected")}
                    </h3>
                    <p className="text-sm mb-4">
                      {t("reconnectDesc")}
                    </p>
                    <Button
                      onClick={() => {
                        setNewDeviceId(selectedDeviceId);
                        setShowNewDevice(true);
                      }}
                    >
                      {t("reconnect")}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
