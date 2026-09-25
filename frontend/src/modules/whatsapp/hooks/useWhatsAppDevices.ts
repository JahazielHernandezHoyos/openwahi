/**
 * Hook for managing WhatsApp devices with WebSocket updates
 */
import { useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { whatsappApi } from "../services/whatsappApi";
import { DeviceCreateRequest } from "../types";

export const DEVICES_QUERY_KEY = ["whatsapp-devices"];

export function useWhatsAppDevices() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Fetch devices - NO polling, will be updated via WebSocket
  // Only fetch if user is authenticated
  const {
    data: devicesData,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: DEVICES_QUERY_KEY,
    queryFn: () => whatsappApi.getDevices(),
    enabled: !!user, // Only run query if authenticated
    staleTime: 30000, // Consider data fresh for 30s
    refetchOnWindowFocus: false, // Don't refetch on focus, WebSocket handles updates
  });

  // Create device mutation
  const createMutation = useMutation({
    mutationFn: (data?: DeviceCreateRequest) => whatsappApi.createDevice(data),
    onMutate: async (newDeviceRequest) => {
      // Cancel refetches
      await queryClient.cancelQueries({ queryKey: DEVICES_QUERY_KEY });

      // Snapshot previous
      const previousDevices = queryClient.getQueryData<any>(DEVICES_QUERY_KEY);

      // Optimistically add
      if (previousDevices) {
        queryClient.setQueryData(DEVICES_QUERY_KEY, {
          ...previousDevices,
          devices: [
            ...previousDevices.devices,
            {
              id: `temp-${Date.now()}`,
              name: newDeviceRequest?.name || "New Device",
              status: "pending",
              created_at: new Date().toISOString(),
              device_id: "pending...",
            },
          ],
        });
      }

      return { previousDevices };
    },
    onError: (err, newDevice, context) => {
      if (context?.previousDevices) {
        queryClient.setQueryData(DEVICES_QUERY_KEY, context.previousDevices);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: DEVICES_QUERY_KEY });
    },
  });

  // Delete device mutation
  const deleteMutation = useMutation({
    mutationFn: (deviceId: string) => whatsappApi.deleteDevice(deviceId),
    onMutate: async (deviceId) => {
      await queryClient.cancelQueries({ queryKey: DEVICES_QUERY_KEY });
      const previousDevices = queryClient.getQueryData<any>(DEVICES_QUERY_KEY);

      if (previousDevices) {
        queryClient.setQueryData(DEVICES_QUERY_KEY, {
          ...previousDevices,
          devices: previousDevices.devices.filter(
            (d: any) => d.id !== deviceId,
          ),
        });
      }

      return { previousDevices };
    },
    onError: (err, deviceId, context) => {
      if (context?.previousDevices) {
        queryClient.setQueryData(DEVICES_QUERY_KEY, context.previousDevices);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: DEVICES_QUERY_KEY });
    },
  });

  // Function to invalidate devices cache (called from WebSocket)
  const invalidateDevices = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: DEVICES_QUERY_KEY });
  }, [queryClient]);

  return {
    devices: devicesData?.devices || [],
    total: devicesData?.total || 0,
    loading,
    error: error?.message || null,
    refetch,
    invalidateDevices,
    createDevice: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error?.message || null,
    deleteDevice: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
  };
}

export function useWhatsAppDevice(deviceId: string | null) {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Fetch single device status - NO polling, WebSocket handles updates
  const {
    data: status,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["whatsapp-device-status", deviceId],
    queryFn: () => (deviceId ? whatsappApi.getDeviceStatus(deviceId) : null),
    enabled: !!deviceId && !!user,
    staleTime: 30000,
    refetchOnWindowFocus: false,
  });

  // Get QR code - only when pending and no QR yet
  const qrQuery = useQuery({
    queryKey: ["whatsapp-device-qr", deviceId],
    queryFn: () => (deviceId ? whatsappApi.getDeviceQR(deviceId) : null),
    enabled:
      !!deviceId &&
      !!user &&
      status?.status === "pending",
    refetchInterval: false,
    staleTime: 25000, // QR is valid for ~30s
  });

  // Poll status when QR is displayed (every 3 seconds)
  useEffect(() => {
    if (!deviceId || status?.status !== "pending") return;

    const interval = setInterval(() => {
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-device-status", deviceId],
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [deviceId, status?.status, queryClient]);

  // If QR response says connected, invalidate status query
  const qrStatus = qrQuery.data?.status;
  useEffect(() => {
    if (qrStatus === "connected" && status?.status !== "connected") {
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-device-status", deviceId],
      });
      queryClient.invalidateQueries({ queryKey: DEVICES_QUERY_KEY });
    }
  }, [qrStatus, status?.status, deviceId, queryClient]);

  // Function to invalidate device status (called from WebSocket)
  const invalidateStatus = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ["whatsapp-device-status", deviceId],
    });
  }, [queryClient, deviceId]);

  return {
    status,
    qrCode: qrQuery.data?.qr_code || null,
    qrStatus: qrQuery.data?.status || null,
    loading,
    error: error?.message || null,
    refetch,
    refetchQR: qrQuery.refetch,
    invalidateStatus,
  };
}
