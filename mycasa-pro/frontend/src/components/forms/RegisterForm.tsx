import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button, TextInput, PasswordInput, Stack, Alert } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";

const registerSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Valid email required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type RegisterFormValues = z.infer<typeof registerSchema>;

interface RegisterFormProps {
  onSubmit: (data: RegisterFormValues) => void;
  error?: string;
  loading?: boolean;
}

export function RegisterForm({ onSubmit, error, loading }: RegisterFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Stack gap="md">
        {error && (
          <Alert icon={<IconAlertCircle size={16} />} color="red" title="Registration Error">
            {error}
          </Alert>
        )}
        <TextInput
          label="Username"
          placeholder="galidima"
          {...register("username")}
          error={errors.username?.message}
        />
        <TextInput
          label="Email"
          placeholder="you@example.com"
          {...register("email")}
          error={errors.email?.message}
        />
        <PasswordInput
          label="Password"
          placeholder="••••••••"
          {...register("password")}
          error={errors.password?.message}
        />
        <Button type="submit" loading={loading}>
          Create account
        </Button>
      </Stack>
    </form>
  );
}
