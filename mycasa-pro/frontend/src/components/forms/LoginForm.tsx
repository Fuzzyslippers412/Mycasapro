import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button, TextInput, PasswordInput, Stack, Alert } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

interface LoginFormProps {
  onSubmit: (data: LoginFormValues) => void;
  error?: string;
  loading?: boolean;
}

export function LoginForm({ onSubmit, error, loading }: LoginFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Stack gap="md">
        {error && (
          <Alert icon={<IconAlertCircle size={16} />} color="red" title="Login Error">
            {error}
          </Alert>
        )}
        <TextInput
          label="Username"
          placeholder="admin"
          {...register("username")}
          error={errors.username?.message}
        />
        <PasswordInput
          label="Password"
          placeholder="admin123"
          {...register("password")}
          error={errors.password?.message}
        />
        <Button type="submit" loading={loading}>
          Login
        </Button>
      </Stack>
    </form>
  );
}
