import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant =
  | "neutral"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "accent";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantClass: Record<BadgeVariant, string> = {
  neutral:
    "bg-[var(--color-surface-2)] text-[var(--color-fg-muted)] border border-[var(--color-border)]",
  success:
    "bg-[var(--color-success-soft)] text-[var(--color-success)]",
  warning:
    "bg-[var(--color-warning-soft)] text-[var(--color-warning)]",
  danger:
    "bg-[var(--color-danger-soft)] text-[var(--color-danger)]",
  info: "bg-[var(--color-info-soft)] text-[var(--color-info)]",
  accent:
    "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
};

export function Badge({
  variant = "neutral",
  className,
  ...rest
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantClass[variant],
        className
      )}
      {...rest}
    />
  );
}
