"use client";

import { useMemo, useState } from "react";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import {
  useAdminAIChain,
  useAdminAIChainEvents,
  useCreateAIChainEntry,
  useDeleteAIChainEntry,
  useProbeAIChainEntry,
  useReorderAIChain,
  useUpdateAIChainEntry,
} from "@/modules/admin/hooks/useAdmin";
import type {
  AIChainEntry,
  AIChainEventType,
  AIProbeResult,
  CreateAIChainEntryInput,
  UpdateAIChainEntryInput,
} from "@/modules/admin/service";
import {
  ArrowDown,
  ArrowUp,
  Bot,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Stethoscope,
  Trash2,
} from "lucide-react";

type ProviderFormValues = {
  provider_name: string;
  model: string;
  base_url: string;
  api_key: string;
  requires_tools: boolean;
};

const emptyForm: ProviderFormValues = {
  provider_name: "",
  model: "",
  base_url: "",
  api_key: "",
  requires_tools: false,
};

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Ocurrió un error inesperado";
}

function ProviderForm({
  values,
  onChange,
  editing,
}: {
  values: ProviderFormValues;
  onChange: (values: ProviderFormValues) => void;
  editing: boolean;
}) {
  return (
    <div className="grid gap-4 py-2">
      <div className="grid gap-2">
        <Label htmlFor={`${editing ? "edit" : "create"}-provider`}>Proveedor</Label>
        <Input
          id={`${editing ? "edit" : "create"}-provider`}
          value={values.provider_name}
          onChange={(event) => onChange({ ...values, provider_name: event.target.value })}
          placeholder="groq"
          disabled={editing}
          required
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${editing ? "edit" : "create"}-model`}>Modelo</Label>
        <Input
          id={`${editing ? "edit" : "create"}-model`}
          value={values.model}
          onChange={(event) => onChange({ ...values, model: event.target.value })}
          placeholder="llama-3.3-70b-versatile"
          required
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${editing ? "edit" : "create"}-url`}>URL base (opcional)</Label>
        <Input
          id={`${editing ? "edit" : "create"}-url`}
          value={values.base_url}
          onChange={(event) => onChange({ ...values, base_url: event.target.value })}
          placeholder="https://api.example.com/v1"
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${editing ? "edit" : "create"}-key`}>API key (opcional)</Label>
        <Input
          id={`${editing ? "edit" : "create"}-key`}
          type="password"
          autoComplete="new-password"
          value={values.api_key}
          onChange={(event) => onChange({ ...values, api_key: event.target.value })}
          placeholder={editing ? "Dejar vacío para mantener" : "API key"}
        />
      </div>
      <div className="flex items-center justify-between rounded-md border p-3">
        <div>
          <Label htmlFor={`${editing ? "edit" : "create"}-tools`}>Requiere tools</Label>
          <p className="text-xs text-muted-foreground">Este eslabón debe soportar llamadas a herramientas.</p>
        </div>
        <Switch
          id={`${editing ? "edit" : "create"}-tools`}
          checked={values.requires_tools}
          onCheckedChange={(checked) => onChange({ ...values, requires_tools: checked })}
        />
      </div>
    </div>
  );
}

function CreateProviderDialog() {
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState(emptyForm);
  const createEntry = useCreateAIChainEntry();
  const { toast } = useToast();

  const submit = async () => {
    const input: CreateAIChainEntryInput = {
      provider_name: values.provider_name.trim(),
      model: values.model.trim(),
      requires_tools: values.requires_tools,
    };
    if (values.base_url.trim()) input.base_url = values.base_url.trim();
    if (values.api_key.trim()) input.api_key = values.api_key.trim();

    try {
      await createEntry.mutateAsync(input);
      toast({ title: "Proveedor añadido", description: "El eslabón se añadió al final de la cadena." });
      setValues(emptyForm);
      setOpen(false);
    } catch (error) {
      toast({ title: "No se pudo añadir", description: errorMessage(error), variant: "destructive" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2"><Plus className="h-4 w-4" />Añadir proveedor</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Añadir proveedor</DialogTitle>
          <DialogDescription>Crea un nuevo eslabón en la cadena de respaldo.</DialogDescription>
        </DialogHeader>
        <ProviderForm values={values} onChange={setValues} editing={false} />
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
          <Button
            onClick={submit}
            disabled={!values.provider_name.trim() || !values.model.trim() || createEntry.isPending}
          >
            {createEntry.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Añadir
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditProviderDialog({ entry }: { entry: AIChainEntry }) {
  const initialValues = (): ProviderFormValues => ({
    provider_name: entry.provider_name,
    model: entry.model,
    base_url: entry.base_url ?? "",
    api_key: "",
    requires_tools: entry.requires_tools,
  });
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState(initialValues);
  const updateEntry = useUpdateAIChainEntry();
  const { toast } = useToast();

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) setValues(initialValues());
    setOpen(nextOpen);
  };

  const submit = async () => {
    const input: UpdateAIChainEntryInput = {
      model: values.model.trim(),
      base_url: values.base_url.trim() || null,
      requires_tools: values.requires_tools,
    };
    if (values.api_key.trim()) input.api_key = values.api_key.trim();

    try {
      await updateEntry.mutateAsync({ id: entry.id, input });
      toast({ title: "Proveedor actualizado" });
      setOpen(false);
    } catch (error) {
      toast({ title: "No se pudo actualizar", description: errorMessage(error), variant: "destructive" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Pencil className="h-3.5 w-3.5" />Editar
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar proveedor</DialogTitle>
          <DialogDescription>Actualiza la conexión sin exponer la API key guardada.</DialogDescription>
        </DialogHeader>
        <ProviderForm values={values} onChange={setValues} editing />
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
          <Button onClick={submit} disabled={!values.model.trim() || updateEntry.isPending}>
            {updateEntry.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Guardar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function HealthBadge({ entry }: { entry: AIChainEntry }) {
  if (!entry.is_enabled) {
    return <Badge variant="outline" className="bg-muted text-muted-foreground">Pausado</Badge>;
  }
  if (!entry.is_healthy) {
    return <Badge variant="outline" className="border-red-500/30 bg-red-500/15 text-red-500">Circuito abierto</Badge>;
  }
  return <Badge variant="outline" className="border-green-500/30 bg-green-500/15 text-green-500">Sano</Badge>;
}

const eventLabels: Record<AIChainEventType, string> = {
  failure: "Fallo",
  recovery: "Recuperación",
  probe_ok: "Probe correcto",
  probe_fail: "Probe fallido",
  circuit_open: "Circuito abierto",
  circuit_close: "Circuito cerrado",
};

const eventColors: Record<AIChainEventType, string> = {
  failure: "border-red-500/30 bg-red-500/15 text-red-500",
  recovery: "border-green-500/30 bg-green-500/15 text-green-500",
  probe_ok: "border-green-500/30 bg-green-500/15 text-green-500",
  probe_fail: "border-red-500/30 bg-red-500/15 text-red-500",
  circuit_open: "border-amber-500/30 bg-amber-500/15 text-amber-500",
  circuit_close: "border-blue-500/30 bg-blue-500/15 text-blue-500",
};

function EventsFeed({ entries }: { entries: AIChainEntry[] }) {
  const { data: events, isLoading, isFetching, refetch } = useAdminAIChainEvents();
  const entryMap = useMemo(
    () => new Map(entries.map((entry) => [entry.id, `${entry.provider_name} / ${entry.model}`])),
    [entries]
  );
  const latestEvents = useMemo(
    () => [...(events ?? [])].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)).slice(0, 30),
    [events]
  );

  return (
    <Card className="border-muted-foreground/10">
      <CardHeader className="bg-muted/20 pb-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-lg">Eventos de salud</CardTitle>
            <CardDescription>Últimos 30 cambios, probes y fallos registrados.</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />Actualizar
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-2 p-6">{[1, 2, 3].map((item) => <Skeleton key={item} className="h-9 w-full" />)}</div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead><TableHead>Tipo</TableHead><TableHead>Proveedor / modelo</TableHead>
                  <TableHead className="text-right">Latencia</TableHead><TableHead>Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {latestEvents.length === 0 ? (
                  <TableRow><TableCell colSpan={5} className="py-8 text-center text-muted-foreground">Sin eventos de salud</TableCell></TableRow>
                ) : latestEvents.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {new Intl.DateTimeFormat("es-MX", { dateStyle: "short", timeStyle: "medium" }).format(new Date(event.created_at))}
                    </TableCell>
                    <TableCell><Badge variant="outline" className={eventColors[event.event_type]}>{eventLabels[event.event_type]}</Badge></TableCell>
                    <TableCell className="max-w-72 truncate font-mono text-xs">{entryMap.get(event.entry_id) ?? "Proveedor eliminado"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{event.latency_ms == null ? "—" : `${event.latency_ms} ms`}</TableCell>
                    <TableCell className="max-w-64 truncate text-xs text-red-500" title={event.error ?? undefined}>{event.error ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AIProvidersView() {
  const { data: entries = [], isLoading, isFetching, refetch } = useAdminAIChain();
  const updateEntry = useUpdateAIChainEntry();
  const deleteEntry = useDeleteAIChainEntry();
  const reorderChain = useReorderAIChain();
  const probeEntry = useProbeAIChainEntry();
  const { toast } = useToast();
  const [probeResults, setProbeResults] = useState<Record<string, AIProbeResult>>({});

  const reorder = async (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= entries.length) return;
    const orderedIds = entries.map((entry) => entry.id);
    [orderedIds[index], orderedIds[target]] = [orderedIds[target], orderedIds[index]];
    try {
      await reorderChain.mutateAsync(orderedIds);
    } catch (error) {
      toast({ title: "No se pudo reordenar", description: errorMessage(error), variant: "destructive" });
    }
  };

  const toggleEnabled = async (entry: AIChainEntry, checked: boolean) => {
    try {
      await updateEntry.mutateAsync({ id: entry.id, input: { is_enabled: checked } });
      toast({ title: checked ? "Proveedor activado" : "Proveedor pausado" });
    } catch (error) {
      toast({ title: "No se pudo cambiar el estado", description: errorMessage(error), variant: "destructive" });
    }
  };

  const probe = async (entry: AIChainEntry) => {
    try {
      const result = await probeEntry.mutateAsync(entry.id);
      setProbeResults((current) => ({ ...current, [entry.id]: result }));
    } catch (error) {
      setProbeResults((current) => ({
        ...current,
        [entry.id]: { ok: false, latency_ms: 0, error: errorMessage(error) },
      }));
    }
  };

  const remove = async (entry: AIChainEntry) => {
    try {
      await deleteEntry.mutateAsync(entry.id);
      toast({ title: "Proveedor eliminado", description: `${entry.provider_name} se quitó de la cadena.` });
    } catch (error) {
      toast({ title: "No se pudo eliminar", description: errorMessage(error), variant: "destructive" });
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold">Cadena de proveedores</h2>
          <p className="text-sm text-muted-foreground">El primer eslabón disponible es el proveedor principal.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />Actualizar
          </Button>
          <CreateProviderDialog />
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-4">{[1, 2, 3].map((item) => <Skeleton key={item} className="h-52 w-full" />)}</div>
      ) : entries.length === 0 ? (
        <Card className="border-dashed"><CardContent className="flex flex-col items-center gap-2 py-12 text-center">
          <Bot className="h-8 w-8 text-muted-foreground" /><p className="font-medium">La cadena está vacía</p>
          <p className="text-sm text-muted-foreground">Añade un proveedor para comenzar.</p>
        </CardContent></Card>
      ) : (
        <div className="space-y-4">
          {entries.map((entry, index) => {
            const probing = probeEntry.isPending && probeEntry.variables === entry.id;
            const probeResult = probeResults[entry.id];
            return (
              <Card key={entry.id} className="border-muted-foreground/10">
                <CardContent className="p-5">
                  <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1 space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">#{index + 1}{index === 0 ? " Principal" : ""}</Badge>
                        <h3 className="font-semibold">{entry.provider_name}</h3>
                        <code className="rounded bg-muted px-2 py-1 text-xs">{entry.model}</code>
                        <HealthBadge entry={entry} />
                        {entry.requires_tools && <Badge variant="outline">tools</Badge>}
                        {!entry.has_api_key && <Badge variant="outline" className="border-amber-500/30 bg-amber-500/15 text-amber-500">sin API key</Badge>}
                      </div>
                      {entry.base_url && <p className="truncate font-mono text-xs text-muted-foreground" title={entry.base_url}>{entry.base_url}</p>}
                      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
                        <span>Último probe: {entry.last_probe_latency_ms == null ? "sin datos" : `${entry.last_probe_latency_ms} ms`}</span>
                        <span>24 h: {entry.summary_24h.calls} llamadas</span>
                        <span>{entry.summary_24h.failures} fallos</span>
                        <span>${entry.summary_24h.cost_usd.toFixed(4)} USD</span>
                        {entry.consecutive_failures > 0 && <span>{entry.consecutive_failures} fallos consecutivos</span>}
                      </div>
                      {entry.last_error && <p className="text-xs text-red-500">Último error: {entry.last_error}</p>}
                      {probeResult && (
                        <p className={`text-xs ${probeResult.ok ? "text-green-500" : "text-red-500"}`}>
                          {probeResult.ok ? `Probe correcto · ${probeResult.latency_ms} ms` : `Probe fallido${probeResult.error ? ` · ${probeResult.error}` : ""}`}
                        </p>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                      <Button variant="outline" size="icon" aria-label="Subir proveedor" onClick={() => reorder(index, -1)} disabled={index === 0 || reorderChain.isPending}>
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                      <Button variant="outline" size="icon" aria-label="Bajar proveedor" onClick={() => reorder(index, 1)} disabled={index === entries.length - 1 || reorderChain.isPending}>
                        <ArrowDown className="h-4 w-4" />
                      </Button>
                      <div className="flex items-center gap-2 rounded-md border px-3 py-2">
                        <Label htmlFor={`enabled-${entry.id}`} className="text-xs">Activo</Label>
                        <Switch id={`enabled-${entry.id}`} checked={entry.is_enabled} onCheckedChange={(checked) => toggleEnabled(entry, checked)} disabled={updateEntry.isPending} />
                      </div>
                      <Button variant="outline" size="sm" className="gap-1.5" onClick={() => probe(entry)} disabled={probeEntry.isPending}>
                        {probing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Stethoscope className="h-3.5 w-3.5" />}Probar
                      </Button>
                      <EditProviderDialog entry={entry} />
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="outline" size="sm" className="gap-1.5 text-red-500 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" />Eliminar</Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Eliminar proveedor</AlertDialogTitle>
                            <AlertDialogDescription>Se eliminará {entry.provider_name} / {entry.model} de la cadena. Esta acción no se puede deshacer.</AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancelar</AlertDialogCancel>
                            <AlertDialogAction onClick={() => remove(entry)} className="bg-red-600 text-white hover:bg-red-700">Eliminar</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <EventsFeed entries={entries} />
    </div>
  );
}
