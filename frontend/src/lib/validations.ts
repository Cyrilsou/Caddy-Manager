import { z } from "zod";

export const hostnameRegex = /^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;

export const domainSchema = z.object({
  hostname: z
    .string()
    .min(1, "Hostname is required")
    .max(253, "Hostname too long")
    .regex(hostnameRegex, "Invalid hostname format (e.g. app.example.com)"),
  backend_id: z.string().min(1, "Backend is required"),
  is_active: z.boolean().default(true),
  force_https: z.boolean().default(true),
  enable_websocket: z.boolean().default(false),
  maintenance_mode: z.boolean().default(false),
  path_prefix: z.string().default("/"),
  strip_prefix: z.boolean().default(false),
  notes: z.string().optional().default(""),
});

export type DomainFormData = z.infer<typeof domainSchema>;

export const backendSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name too long"),
  host: z
    .string()
    .min(1, "Host is required")
    .max(255, "Host too long"),
  port: z.coerce
    .number()
    .int()
    .min(1, "Port must be 1-65535")
    .max(65535, "Port must be 1-65535"),
  protocol: z.enum(["http", "https"]).default("http"),
  health_check_enabled: z.boolean().default(false),
  health_check_path: z.string().default("/"),
});

export type BackendFormData = z.infer<typeof backendSchema>;

export const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const passwordChangeSchema = z
  .object({
    current: z.string().min(1, "Current password is required"),
    new_password: z.string().min(8, "Password must be at least 8 characters"),
    confirm: z.string().min(1, "Confirmation is required"),
  })
  .refine((data) => data.new_password === data.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });

export type PasswordChangeFormData = z.infer<typeof passwordChangeSchema>;
