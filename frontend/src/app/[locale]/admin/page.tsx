"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { useMounted } from "@/tools/hooks/useMounted";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Users,
  MessageSquare,
  DollarSign,
  LayoutDashboard,
  RefreshCw,
  Shield,
  Bot,
} from "lucide-react";
import {
  useAdminStats,
  useAdminUsers,
  useAdminCosts,
  useUpdateUserPlan,
  useToggleSubscription,
} from "@/modules/admin/hooks/useAdmin";
import { useToast } from "@/hooks/use-toast";
import { AIProvidersView } from "@/modules/admin/components/AIProvidersView";
import { APP_NAME } from "@/config/brand";

function PlanBadge({ plan }: { plan: string }) {
  const variants: Record<string, "default" | "secondary" | "outline"> = {
    pro: "default",
    enterprise: "secondary",
    free: "outline",
  };
  const colors: Record<string, string> = {
    pro: "bg-primary/20 text-primary border-primary/30",
    enterprise: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    free: "bg-muted/40 text-muted-foreground",
  };
  return (
    <Badge variant={variants[plan] ?? "outline"} className={colors[plan] ?? ""}>
      {plan.toUpperCase()}
    </Badge>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isActive = status === "active";
  return (
    <Badge
      variant={isActive ? "default" : "outline"}
      className={isActive ? "bg-green-500/20 text-green-400 border-green-500/30" : ""}
    >
      {status}
    </Badge>
  );
}

function StatsCard({
  icon: Icon,
  title,
  value,
  subtitle,
  loading,
}: {
  icon: React.ElementType;
  title: string;
  value: string | number;
  subtitle?: string;
  loading?: boolean;
}) {
  return (
    <Card className="border-muted-foreground/10 bg-muted/5">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <>
            <div className="text-2xl font-bold">{value}</div>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function AdminDashboardPage() {
  const mounted = useMounted();
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useAdminStats();
  const { data: users, isLoading: usersLoading } = useAdminUsers();
  const { data: costs, isLoading: costsLoading } = useAdminCosts();
  const updatePlan = useUpdateUserPlan();
  const toggleSub = useToggleSubscription();
  const { toast } = useToast();
  const [updatingUser, setUpdatingUser] = useState<string | null>(null);
  const [view, setView] = useState<"usuarios" | "proveedores">("usuarios");

  if (!mounted) return null;

  const handlePlanChange = async (userId: string, newPlan: string) => {
    setUpdatingUser(userId);
    const userObj = (users ?? []).find((u) => u.user_id === userId);
    const label = userObj?.email || `${userId.slice(0, 12)}...`;
    try {
      await updatePlan.mutateAsync({ userId, plan: newPlan });
      toast({ title: "✅ Plan actualizado", description: `${label} → ${newPlan}` });
    } catch {
      toast({ title: "❌ Error", description: "No se pudo actualizar el plan", variant: "destructive" });
    } finally {
      setUpdatingUser(null);
    }
  };

  const handleToggle = async (userId: string, currentStatus: string) => {
    setUpdatingUser(userId);
    try {
      const result = await toggleSub.mutateAsync(userId);
      toast({ title: "✅ Suscripción actualizada", description: `Estado → ${result.new_status}` });
    } catch {
      toast({ title: "❌ Error", description: "No se pudo actualizar la suscripción", variant: "destructive" });
    } finally {
      setUpdatingUser(null);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div
        className="max-w-7xl mx-auto px-4 py-8 lg:py-12 space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-700"
        suppressHydrationWarning
      >
        {/* Header section */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg text-primary">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Admin Dashboard</h1>
              <p className="text-sm text-muted-foreground">Panel de gestión interno — {APP_NAME}</p>
            </div>
          </div>
          {view === "usuarios" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchStats()}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Actualizar
            </Button>
          )}
        </div>

        <Tabs
          value={view}
          onValueChange={(value) => setView(value === "proveedores" ? "proveedores" : "usuarios")}
        >
          <TabsList>
            <TabsTrigger value="usuarios" className="gap-2">
              <Users className="h-4 w-4" />Usuarios
            </TabsTrigger>
            <TabsTrigger value="proveedores" className="gap-2">
              <Bot className="h-4 w-4" />Proveedores IA
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {view === "usuarios" ? (
          <>
        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            icon={Users}
            title="Total Usuarios"
            value={stats?.total_users ?? 0}
            subtitle="Con suscripción activa"
            loading={statsLoading}
          />
          <StatsCard
            icon={MessageSquare}
            title="Conv. este mes"
            value={stats?.monthly_conversations ?? 0}
            subtitle={`${stats?.month}/${stats?.year}`}
            loading={statsLoading}
          />
          <StatsCard
            icon={DollarSign}
            title="Costo mensual"
            value={`$${(stats?.monthly_cost_usd ?? 0).toFixed(4)}`}
            subtitle="Solo managed (Pro)"
            loading={statsLoading}
          />
          <Card className="border-muted-foreground/10 bg-muted/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Planes</CardTitle>
              <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <Skeleton className="h-8 w-full" />
              ) : (
                <div className="flex gap-2 flex-wrap mt-1">
                  {Object.entries(stats?.plan_counts ?? {}).map(([plan, count]) => (
                    <span key={plan} className="text-sm">
                      <PlanBadge plan={plan} /> <span className="font-bold">{count}</span>
                    </span>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Users Table */}
        <Card className="border-muted-foreground/10">
          <CardHeader className="bg-muted/20 pb-4">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-primary/10 rounded-lg text-primary">
                <Users className="h-4 w-4" />
              </div>
              <CardTitle className="text-lg font-bold">Usuarios</CardTitle>
            </div>
            <CardDescription>Gestiona planes y suscripciones</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {usersLoading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/10 hover:bg-muted/10">
                      <TableHead className="font-semibold">Usuario</TableHead>
                      <TableHead className="font-semibold">Plan</TableHead>
                      <TableHead className="font-semibold">Status</TableHead>
                      <TableHead className="font-semibold text-right">Conv/mes</TableHead>
                      <TableHead className="font-semibold text-right">Costo/mes</TableHead>
                      <TableHead className="font-semibold text-center">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(users ?? []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                          No hay usuarios registrados
                        </TableCell>
                      </TableRow>
                    ) : (
                      (users ?? []).map((user) => (
                        <TableRow key={user.user_id} className="hover:bg-muted/5">
                          <TableCell className="font-mono text-xs text-muted-foreground">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="cursor-default">
                                    {user.email
                                      ? user.email
                                      : `${user.user_id.slice(0, 20)}...`}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent side="right" className="font-mono text-xs">
                                  <p className="text-muted-foreground text-[10px] mb-0.5">UID</p>
                                  {user.user_id}
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </TableCell>
                          <TableCell><PlanBadge plan={user.plan} /></TableCell>
                          <TableCell><StatusBadge status={user.status} /></TableCell>
                          <TableCell className="text-right font-medium">
                            {user.monthly_conversations}
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            ${user.monthly_cost_usd.toFixed(4)}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center justify-center gap-2">
                              <Select
                                value={user.plan}
                                onValueChange={(val) => handlePlanChange(user.user_id, val)}
                                disabled={updatingUser === user.user_id}
                              >
                                <SelectTrigger className="w-28 h-7 text-xs">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="free">Free</SelectItem>
                                  <SelectItem value="pro">Pro</SelectItem>
                                  <SelectItem value="enterprise">Enterprise</SelectItem>
                                </SelectContent>
                              </Select>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-7 text-xs px-2"
                                onClick={() => handleToggle(user.user_id, user.status)}
                                disabled={updatingUser === user.user_id}
                              >
                                {user.status === "active" ? "Pausar" : "Activar"}
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Costs table */}
        <Card className="border-muted-foreground/10">
          <CardHeader className="bg-muted/20 pb-4">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-primary/10 rounded-lg text-primary">
                <DollarSign className="h-4 w-4" />
              </div>
              <CardTitle className="text-lg font-bold">Costos por mes</CardTitle>
            </div>
            <CardDescription>Últimos 6 meses — solo managed (Plan Pro)</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {costsLoading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/10 hover:bg-muted/10">
                      <TableHead>Año</TableHead>
                      <TableHead>Mes</TableHead>
                      <TableHead>Proveedor</TableHead>
                      <TableHead className="text-right">Costo (USD)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(costs ?? []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                          Sin registros de costo
                        </TableCell>
                      </TableRow>
                    ) : (
                      (costs ?? []).map((row, i) => (
                        <TableRow key={i} className="hover:bg-muted/5">
                          <TableCell>{row.year}</TableCell>
                          <TableCell>{row.month.toString().padStart(2, "0")}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="font-mono text-xs">{row.provider}</Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            ${row.cost_usd.toFixed(6)}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
          </>
        ) : (
          <AIProvidersView />
        )}
      </div>
    </div>
  );
}
