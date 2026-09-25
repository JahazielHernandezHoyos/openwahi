"use client";

import { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import {
  useWhatsAppDevice,
  useWhatsAppDevices,
} from "../hooks/useWhatsAppDevices";
import { useWhatsAppWebSocket } from "../hooks/useWhatsAppWebSocket";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  CheckCircle2,
  QrCode,
  AlertCircle,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { useTranslations } from "next-intl";

interface WhatsAppQRScannerProps {
  deviceId: string | null;
  onConnected?: () => void;
}

export function WhatsAppQRScanner({
  deviceId,
  onConnected,
}: WhatsAppQRScannerProps) {
  const t = useTranslations("WhatsApp.qrScanner");
  const tCommon = useTranslations("WhatsApp");
  const { status, qrCode, qrStatus, loading, error, refetch, refetchQR } =
    useWhatsAppDevice(deviceId);
  const { refetch: refetchDevices } = useWhatsAppDevices();
  const [prevStatus, setPrevStatus] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  // Connect to WebSocket for real-time status updates
  const { lastMessage, isConnected: wsConnected } = useWhatsAppWebSocket({
    deviceId: deviceId || "",
    enabled: !!deviceId,
    onMessage: (message) => {
      // Handle device status updates
      if (message.type === "device_status") {
        // If device connected, trigger callbacks
        if (
          message.data?.status === "connected" ||
          message.status === "connected"
        ) {
          setIsConnecting(false);
          refetchDevices();
          refetch();
          onConnected?.();
        }
      }
    },
    autoReconnect: true,
    reconnectInterval: 3000,
    pingInterval: 30000,
  });

  // Check both status and qrStatus for connected state
  const isConnected =
    status?.status === "connected" || qrStatus === "connected";

  // Detect when device becomes connected (polling fallback)
  useEffect(() => {
    const currentStatus = status?.status || qrStatus;

    if (currentStatus === "connected" && prevStatus !== "connected") {
      setIsConnecting(false);

      // Invalidate and refetch devices
      refetchDevices();
      refetch();

      // Clear QR cache to prevent showing stale QR
      refetchQR();

      // Call connected callback
      onConnected?.();
    }

    // Show connecting state when QR is shown
    if (qrCode && prevStatus === null) {
      setIsConnecting(false);
    }

    setPrevStatus(currentStatus || null);
  }, [
    status?.status,
    qrStatus,
    prevStatus,
    onConnected,
    refetchDevices,
    refetch,
    refetchQR,
    qrCode,
  ]);

  // Auto-refresh QR code every 45 seconds (QR codes expire after ~60s)
  useEffect(() => {
    if (!qrCode || isConnected) return;

    const interval = setInterval(() => {
      refetchQR();
    }, 45000);

    return () => clearInterval(interval);
  }, [qrCode, isConnected, refetchQR]);

  // Handle manual refresh
  const handleRefresh = useCallback(() => {
    setIsConnecting(true);
    refetch();
    refetchQR();
  }, [refetch, refetchQR]);

  if (!deviceId) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8 text-muted-foreground">
            <QrCode className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>{t("selectDevice") || tCommon("noDevices")}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (loading && !status && !qrCode) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            {t("status")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-4">
            <Skeleton className="h-64 w-64" />
            <p className="text-sm text-muted-foreground">
              {t("status")}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isConnected) {
    return (
      <Alert variant="success">
        <CheckCircle2 className="h-5 w-5" />
        <AlertTitle className="font-semibold">{tCommon("connected")}</AlertTitle>
        <AlertDescription>
          <div className="flex items-center gap-2 mt-1">
            {status?.phone && (
              <span className="font-mono font-medium">{`+${status.phone}`}</span>
            )}
            {status?.name && (
              <>
                <span className="opacity-50">•</span>
                <span>{status.name}</span>
              </>
            )}
            {!status?.phone && !status?.name && (
              <span>{tCommon("linkedSuccessfully")}</span>
            )}
          </div>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <QrCode className="h-5 w-5" />
          {t("title")}
        </CardTitle>
        <CardDescription>
          {t("description")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex flex-col items-center gap-4">
          {qrCode ? (
            <>
              <div className="p-4 bg-white rounded-lg shadow-sm border">
                <Image
                  src={
                    qrCode.startsWith("data:")
                      ? qrCode
                      : qrCode.startsWith("http")
                        ? qrCode
                        : `data:image/png;base64,${qrCode}`
                  }
                  alt="WhatsApp QR Code"
                  width={256}
                  height={256}
                  className="h-64 w-64"
                  unoptimized
                />
              </div>
              <div className="flex flex-col items-center gap-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("waiting")}
                </div>
                {wsConnected && (
                  <div className="flex items-center gap-2 text-xs text-green-600">
                    <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    {tCommon("inbox.realtimeActive")}
                  </div>
                )}
              </div>
              <Button
                variant="outline"
                onClick={handleRefresh}
                className="flex items-center gap-2"
                size="sm"
              >
                <RefreshCw className="h-4 w-4" />
                {t("generateNew")}
              </Button>
            </>
          ) : (
            <>
              <div className="h-64 w-64 flex items-center justify-center bg-muted rounded-lg">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
              <p className="text-sm text-muted-foreground">
                {t("generating")}
              </p>
              <Button
                variant="outline"
                onClick={handleRefresh}
                className="flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                {t("retry")}
              </Button>
            </>
          )}
        </div>

        <div className="mt-4 p-3 bg-muted rounded-lg text-sm">
          <p className="font-medium mb-2">{t("instructions.title")}</p>
          <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
            <li>{t("instructions.step1")}</li>
            <li>{t("instructions.step2")}</li>
            <li>{t("instructions.step3")}</li>
            <li>{t("instructions.step4")}</li>
          </ol>
        </div>
      </CardContent>
    </Card>
  );
}
