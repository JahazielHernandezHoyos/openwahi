"use client";

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
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
import { useToast } from "@/hooks/use-toast";
import { useApiTokens } from "../hooks/useApiTokens";
import {
  Copy,
  Check,
  ExternalLink,
  FileText,
  Terminal,
  Code,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { API_BASE_URL } from "@/config/constants";

interface Device {
  id: string;
  name?: string;
  phone?: string;
  status: string;
}

interface DocumentationTabProps {
  devices: Device[];
}

export function DocumentationTab({ devices }: DocumentationTabProps) {
  const t = useTranslations("Developer");
  const { toast } = useToast();
  const { tokens } = useApiTokens();

  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const connectedDevices = useMemo(
    () => devices.filter((d) => d.status === "connected"),
    [devices],
  );

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
    toast({
      title: t("copied"),
      description: t("copiedToClipboard"),
    });
  };

  const curlExamples = useMemo(() => {
    const tokenPlaceholder =
      tokens.length > 0 ? `${tokens[0].token_prefix}...` : "YOUR_API_TOKEN";
    const deviceId = selectedDeviceId || "DEVICE_ID";

    return [
      {
        id: "list-devices",
        title: t("curlListDevices"),
        description: t("curlListDevicesDesc"),
        curl: `curl -X GET "${API_BASE_URL}/whatsapp/devices" \\
  -H "X-API-Key: ${tokenPlaceholder}"`,
      },
      {
        id: "send-message",
        title: t("curlSendMessage"),
        description: t("curlSendMessageDesc"),
        curl: `curl -X POST "${API_BASE_URL}/whatsapp/devices/${deviceId}/send" \\
  -H "X-API-Key: ${tokenPlaceholder}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "phone": "15551234567",
    "message": "Hello from API!"
  }'`,
      },
      {
        id: "get-device",
        title: t("curlGetDevice"),
        description: t("curlGetDeviceDesc"),
        curl: `curl -X GET "${API_BASE_URL}/whatsapp/devices/${deviceId}" \\
  -H "X-API-Key: ${tokenPlaceholder}"`,
      },
      {
        id: "list-messages",
        title: t("curlListMessages"),
        description: t("curlListMessagesDesc"),
        curl: `curl -X GET "${API_BASE_URL}/whatsapp/devices/${deviceId}/messages?limit=50&offset=0" \\
  -H "X-API-Key: ${tokenPlaceholder}"`,
      },
    ];
  }, [selectedDeviceId, tokens, t]);

  return (
    <div className="space-y-6">
      {/* Documentation Link Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {t("apiDocumentation")}
          </CardTitle>
          <CardDescription>{t("apiDocumentationDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Button asChild>
              <a
                href={`${API_BASE_URL}/api-docs`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                {t("openDocs")}
              </a>
            </Button>
            <p className="text-sm text-muted-foreground">
              {t("docsOpenInNewTab")}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* cURL Examples Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Terminal className="h-5 w-5" />
                {t("curlExamples")}
              </CardTitle>
              <CardDescription>{t("curlExamplesDesc")}</CardDescription>
            </div>
            {connectedDevices.length > 0 && (
              <Select
                value={selectedDeviceId}
                onValueChange={setSelectedDeviceId}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder={t("selectDevice")} />
                </SelectTrigger>
                <SelectContent>
                  {connectedDevices.map((device) => (
                    <SelectItem key={device.id} value={device.id}>
                      {device.name || device.phone || device.id.slice(0, 8)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {tokens.length === 0 && (
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-700 dark:text-yellow-400">
              <p className="text-sm">{t("noTokensWarning")}</p>
            </div>
          )}

          {curlExamples.map((example) => (
            <div key={example.id} className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">{example.title}</h4>
                  <p className="text-sm text-muted-foreground">
                    {example.description}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleCopy(example.curl, example.id)}
                >
                  {copiedId === example.id ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <pre className="p-4 bg-muted rounded-lg overflow-x-auto text-sm font-mono">
                <code>{example.curl}</code>
              </pre>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Webhook Payload Example */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code className="h-5 w-5" />
            {t("webhookPayload")}
          </CardTitle>
          <CardDescription>{t("webhookPayloadDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">{t("incomingMessage")}</h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  handleCopy(
                    JSON.stringify(
                      {
                        event: "message.received",
                        timestamp: "2024-01-15T10:30:00Z",
                        data: {
                          message_id: "uuid-example",
                          device_id: "device-uuid",
                          from_phone: "15551234567",
                          body: "Hello!",
                          message_type: "text",
                          timestamp: "2024-01-15T10:30:00Z",
                        },
                      },
                      null,
                      2,
                    ),
                    "webhook-payload",
                  )
                }
              >
                {copiedId === "webhook-payload" ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <pre className="p-4 bg-muted rounded-lg overflow-x-auto text-sm font-mono">
              <code>
                {JSON.stringify(
                  {
                    event: "message.received",
                    timestamp: "2024-01-15T10:30:00Z",
                    data: {
                      message_id: "uuid-example",
                      device_id: "device-uuid",
                      from_phone: "15551234567",
                      body: "Hello!",
                      message_type: "text",
                      timestamp: "2024-01-15T10:30:00Z",
                    },
                  },
                  null,
                  2,
                )}
              </code>
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
