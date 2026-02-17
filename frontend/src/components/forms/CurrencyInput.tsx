import { NumberInput } from "@mantine/core";

interface CurrencyInputProps {
  value: number | string;
  onChange: (v: number | string) => void;
  label?: string;
  placeholder?: string;
}

export function CurrencyInput({ value, onChange, label, placeholder }: CurrencyInputProps) {
  return (
    <NumberInput
      value={value}
      onChange={onChange}
      label={label}
      placeholder={placeholder}
      thousandSeparator="," 
      decimalScale={2}
      fixedDecimalScale
      prefix="$"
    />
  );
}
