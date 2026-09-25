"use client";

import React from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface FormContainerProps {
    title: string;
    description?: string;
    icon?: LucideIcon;
    children: React.ReactNode;
    footer?: React.ReactNode;
    className?: string;
}

export function FormContainer({
    title,
    description,
    icon: Icon,
    children,
    footer,
    className,
}: FormContainerProps) {
    return (
        <Card className={cn("overflow-hidden border-muted-foreground/10", className)}>
            <CardHeader className="space-y-1 bg-muted/20 pb-6">
                <div className="flex items-center gap-2">
                    {Icon && (
                        <div className="p-2 bg-primary/10 rounded-lg text-primary">
                            <Icon className="h-5 w-5" />
                        </div>
                    )}
                    <CardTitle className="text-xl font-bold tracking-tight">
                        {title}
                    </CardTitle>
                </div>
                {description && (
                    <CardDescription className="text-sm">
                        {description}
                    </CardDescription>
                )}
            </CardHeader>
            <CardContent className="pt-6 px-6">
                {children}
            </CardContent>
            {footer && (
                <div className="px-6 py-4 bg-muted/10 border-t border-muted-foreground/5">
                    {footer}
                </div>
            )}
        </Card>
    );
}
