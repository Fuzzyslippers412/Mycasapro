/**
 * MyCasa Pro Design Tokens
 * Modern color palette with vibrant accents and dark mode support
 */

export const tokens = {
  spacing: [4, 8, 12, 16, 20, 24, 32, 40, 48, 64],

  radius: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    full: 9999,
  },

  shadow: {
    subtle: "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)",
    medium: "0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)",
    elevated: "0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)",
    floating: "0 20px 25px rgba(0,0,0,0.15), 0 10px 10px rgba(0,0,0,0.04)",
    inset: "inset 0 2px 4px rgba(0,0,0,0.06)",
  },

  typography: {
    sizes: {
      xs: 12,
      sm: 13,
      md: 14,
      lg: 16,
      xl: 20,
      h1: 32,
      h2: 26,
      h3: 22,
    },
    weights: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    letterSpacing: {
      tight: '-0.025em',
      normal: '0',
      wide: '0.025em',
      wider: '0.05em',
    },
  },

  colors: {
    // Neutral palette - warmer grays
    neutral: {
      50: "#FAFAFA",
      100: "#F5F5F5",
      200: "#EEEEEE",
      300: "#E0E0E0",
      400: "#BDBDBD",
      500: "#9E9E9E",
      600: "#757575",
      700: "#616161",
      800: "#424242",
      900: "#212121",
    },

    // Primary - deeper blue
    primary: {
      50: "#E3F2FD",
      100: "#BBDEFB",
      200: "#90CAF9",
      300: "#64B5F6",
      400: "#42A5F5",
      500: "#1976D2",
      600: "#1565C0",
      700: "#0D47A1",  // Main primary color
      800: "#0A3D8F",
      900: "#082E6D",
    },

    // Accent - indigo (for secondary actions)
    accent: {
      50: "#E8EAF6",
      100: "#C5CAE9",
      200: "#9FA8DA",
      300: "#7986CB",
      400: "#5C6BC0",
      500: "#3F51B5",
      600: "#3949AB",
      700: "#303F9F",
      800: "#283593",
      900: "#1A237E",
    },

    // Success - vibrant green
    success: {
      50: "#E8F5E9",
      100: "#C8E6C9",
      200: "#A5D6A7",
      300: "#81C784",
      400: "#66BB6A",
      500: "#4CAF50",
      600: "#43A047",
      700: "#388E3C",
      800: "#2E7D32",
      900: "#1B5E20",
    },

    // Warning - warm orange
    warn: {
      50: "#FFF3E0",
      100: "#FFE0B2",
      200: "#FFCC80",
      300: "#FFB74D",
      400: "#FFA726",
      500: "#FF9800",
      600: "#FB8C00",
      700: "#F57C00",
      800: "#EF6C00",
      900: "#E65100",
    },

    // Error - vibrant red
    error: {
      50: "#FFEBEE",
      100: "#FFCDD2",
      200: "#EF9A9A",
      300: "#E57373",
      400: "#EF5350",
      500: "#F44336",
      600: "#E53935",
      700: "#D32F2F",
      800: "#C62828",
      900: "#B71C1C",
    },

    // Info - cyan
    info: {
      50: "#E0F7FA",
      100: "#B2EBF2",
      200: "#80DEEA",
      300: "#4DD0E1",
      400: "#26C6DA",
      500: "#00BCD4",
      600: "#00ACC1",
      700: "#0097A7",
      800: "#00838F",
      900: "#006064",
    },
  },

  // Gradient definitions
  gradients: {
    primary: "linear-gradient(135deg, #0D47A1 0%, #1976D2 100%)",
    primaryLight: "linear-gradient(135deg, #1976D2 0%, #42A5F5 100%)",
    accent: "linear-gradient(135deg, #303F9F 0%, #5C6BC0 100%)",
    success: "linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%)",
    warm: "linear-gradient(135deg, #F57C00 0%, #FFB74D 100%)",
    cool: "linear-gradient(135deg, #0097A7 0%, #4DD0E1 100%)",
    dark: "linear-gradient(135deg, #212121 0%, #424242 100%)",
    card: "linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)",
    cardHover: "linear-gradient(180deg, rgba(13,71,161,0.05) 0%, rgba(13,71,161,0) 100%)",
  },

  // Dark mode overrides
  dark: {
    background: "#121212",
    surface: "#1E1E1E",
    surfaceElevated: "#2D2D2D",
    border: "#333333",
    text: {
      primary: "#FFFFFF",
      secondary: "#B3B3B3",
      muted: "#808080",
    },
    gradients: {
      card: "linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 100%)",
      cardHover: "linear-gradient(180deg, rgba(66,165,245,0.08) 0%, rgba(66,165,245,0) 100%)",
    },
  },

  // Animation timing
  animation: {
    fast: '150ms',
    normal: '200ms',
    slow: '300ms',
    verySlow: '500ms',
    easing: {
      default: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    },
  },

  // Z-index scale
  zIndex: {
    dropdown: 100,
    sticky: 200,
    modal: 300,
    popover: 400,
    tooltip: 500,
    toast: 600,
  },
};

// Helper function to get CSS variable from token
export const cssVar = (path: string): string => {
  return `var(--mantine-${path.replace(/\./g, '-')})`;
};

// Status color mapping
export const statusColors = {
  healthy: tokens.colors.success[500],
  warning: tokens.colors.warn[500],
  error: tokens.colors.error[500],
  info: tokens.colors.info[500],
  neutral: tokens.colors.neutral[500],
  online: tokens.colors.success[500],
  offline: tokens.colors.neutral[400],
  busy: tokens.colors.warn[500],
};

// Priority color mapping
export const priorityColors = {
  urgent: tokens.colors.error[500],
  high: tokens.colors.warn[600],
  medium: tokens.colors.primary[500],
  low: tokens.colors.neutral[500],
};

export default tokens;
