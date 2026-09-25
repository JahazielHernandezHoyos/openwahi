"use client";

import { WhatsAppDevice } from "../types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Smartphone, Trash2, CheckCircle2, Clock, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";

interface WhatsAppDeviceListProps {
  devices: WhatsAppDevice[];
  selectedDeviceId: string | null;
  onSelectDevice: (deviceId: string) => void;
  onDeleteDevice: (deviceId: string) => void;
  isDeleting: boolean;
}

export function WhatsAppDeviceList({
  devices,
  selectedDeviceId,
  onSelectDevice,
  onDeleteDevice,
  isDeleting,
}: WhatsAppDeviceListProps) {
  const t = useTranslations("WhatsApp");
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "connected":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "connected":
        return (
          <Badge variant="default" className="bg-green-500">
            {t("status.connected")}
          </Badge>
        );
      case "pending":
        return <Badge variant="secondary">{t("status.pending")}</Badge>;
      default:
        return <Badge variant="destructive">{t("status.disconnected")}</Badge>;
    }
  };

  if (devices.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Smartphone className="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>{t("noDevices")}</p>
        <p className="text-sm">{t("clickToLink")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {devices.map((device) => (
        <Card
          key={device.id}
          className={`group relative overflow-hidden cursor-pointer transition-all duration-200 ${
            selectedDeviceId === device.id
              ? "border-primary bg-primary/5 ring-1 ring-primary/20"
              : "hover:border-muted-foreground/30 hover:bg-muted/30"
          }`}
          onClick={() => onSelectDevice(device.id)}
        >
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div
                  className={`p-2.5 rounded-xl transition-colors flex-shrink-0 ${
                    selectedDeviceId === device.id
                      ? "bg-primary/20 text-primary"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  <Smartphone className="h-5 w-5" />
                </div>
                <div className="space-y-1 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">
                      {device.name
                        ? device.name.replace(
                            /^WhatsApp\.device\s*/i,
                            `${t("device")} WhatsApp `,
                          )
                        : device.phone || t("unnamed")}
                    </span>
                    {getStatusIcon(device.status)}
                  </div>
                  {device.phone && (
                    <p className="text-xs font-mono text-muted-foreground">
                      +{device.phone}
                    </p>
                  )}
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
                    {t("id")}: {device.device_id.substring(0, 12)}...
                  </p>
                  <div className="pt-1">{getStatusBadge(device.status)}</div>
                </div>
              </div>

              <div className="flex items-center gap-1 flex-shrink-0">
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                    <AlertDialogHeader>
                      <AlertDialogTitle>{t("unlinkDevice")}</AlertDialogTitle>
                      <AlertDialogDescription>
                        {t("unlinkDesc", {
                          name: device.name
                            ? device.name.replace(
                                /^WhatsApp\.device\s*/i,
                                `${t("device")} WhatsApp `,
                              )
                            : device.phone || device.device_id,
                        })}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => onDeleteDevice(device.id)}
                        disabled={isDeleting}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        {isDeleting ? t("unlinking") : t("unlink")}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          </CardContent>
          {selectedDeviceId === device.id && (
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary" />
          )}
        </Card>
      ))}
    </div>
  );
}
