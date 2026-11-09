import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-info/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:opacity-90",
        outline: "border bg-card hover:bg-accent",
        ghost: "hover:bg-accent",
        danger: "border border-fail/40 text-fail hover:bg-fail-soft",
      },
      size: { default: "h-9 px-4", sm: "h-8 px-3", xs: "h-7 px-2 text-xs", icon: "size-8" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants>) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

const badgeVariants = cva("inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium whitespace-nowrap", {
  variants: {
    tone: {
      neutral: "bg-muted text-muted-foreground border-transparent",
      pass: "bg-pass-soft text-pass border-transparent",
      fail: "bg-fail-soft text-fail border-transparent",
      warn: "bg-warn-soft text-warn border-transparent",
      info: "bg-info-soft text-info border-transparent",
      outline: "bg-transparent text-muted-foreground",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export function Badge({ className, tone, ...props }: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export function Card({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("rounded-lg border bg-card", className)} {...props} />;
}

export function CardHeader({ title, children, className }: { title: React.ReactNode; children?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2 border-b px-4 py-2.5", className)}>
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="ml-auto flex items-center gap-2">{children}</div>
    </div>
  );
}

export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      className={cn("h-8 rounded-md border bg-card px-2.5 text-sm outline-none focus:ring-2 focus:ring-info/40", className)}
      {...props}
    />
  );
}

export function Select({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn("h-8 rounded-md border bg-card px-2 text-sm outline-none focus:ring-2 focus:ring-info/40", className)}
      {...props}
    />
  );
}

export function Th({ className, ...props }: React.ComponentProps<"th">) {
  return <th className={cn("h-9 px-3 text-left text-xs font-medium text-muted-foreground", className)} {...props} />;
}

export function Td({ className, ...props }: React.ComponentProps<"td">) {
  return <td className={cn("px-3 py-2 align-middle", className)} {...props} />;
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">{children}</div>;
}

export function Mono({ className, ...props }: React.ComponentProps<"pre">) {
  return (
    <pre
      className={cn("overflow-auto rounded-md bg-muted p-2.5 font-mono text-[12px] leading-relaxed whitespace-pre-wrap break-words", className)}
      {...props}
    />
  );
}
