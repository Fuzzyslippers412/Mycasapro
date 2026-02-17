import { createTheme, MantineColorsTuple, rem, virtualColor } from "@mantine/core";
import { tokens } from "./tokens";

// Primary color palette (deeper blue)
const primary: MantineColorsTuple = [
  tokens.colors.primary[50],
  tokens.colors.primary[100],
  tokens.colors.primary[200],
  tokens.colors.primary[300],
  tokens.colors.primary[400],
  tokens.colors.primary[500],
  tokens.colors.primary[600],
  tokens.colors.primary[700],
  tokens.colors.primary[800],
  tokens.colors.primary[900],
];

// Accent color palette (indigo)
const accent: MantineColorsTuple = [
  tokens.colors.accent[50],
  tokens.colors.accent[100],
  tokens.colors.accent[200],
  tokens.colors.accent[300],
  tokens.colors.accent[400],
  tokens.colors.accent[500],
  tokens.colors.accent[600],
  tokens.colors.accent[700],
  tokens.colors.accent[800],
  tokens.colors.accent[900],
];

// Success color palette
const success: MantineColorsTuple = [
  tokens.colors.success[50],
  tokens.colors.success[100],
  tokens.colors.success[200],
  tokens.colors.success[300],
  tokens.colors.success[400],
  tokens.colors.success[500],
  tokens.colors.success[600],
  tokens.colors.success[700],
  tokens.colors.success[800],
  tokens.colors.success[900],
];

// Warning color palette
const warning: MantineColorsTuple = [
  tokens.colors.warn[50],
  tokens.colors.warn[100],
  tokens.colors.warn[200],
  tokens.colors.warn[300],
  tokens.colors.warn[400],
  tokens.colors.warn[500],
  tokens.colors.warn[600],
  tokens.colors.warn[700],
  tokens.colors.warn[800],
  tokens.colors.warn[900],
];

// Error color palette
const error: MantineColorsTuple = [
  tokens.colors.error[50],
  tokens.colors.error[100],
  tokens.colors.error[200],
  tokens.colors.error[300],
  tokens.colors.error[400],
  tokens.colors.error[500],
  tokens.colors.error[600],
  tokens.colors.error[700],
  tokens.colors.error[800],
  tokens.colors.error[900],
];

// Info color palette
const info: MantineColorsTuple = [
  tokens.colors.info[50],
  tokens.colors.info[100],
  tokens.colors.info[200],
  tokens.colors.info[300],
  tokens.colors.info[400],
  tokens.colors.info[500],
  tokens.colors.info[600],
  tokens.colors.info[700],
  tokens.colors.info[800],
  tokens.colors.info[900],
];

// Neutral color palette (warmer grays)
const neutral: MantineColorsTuple = [
  tokens.colors.neutral[50],
  tokens.colors.neutral[100],
  tokens.colors.neutral[200],
  tokens.colors.neutral[300],
  tokens.colors.neutral[400],
  tokens.colors.neutral[500],
  tokens.colors.neutral[600],
  tokens.colors.neutral[700],
  tokens.colors.neutral[800],
  tokens.colors.neutral[900],
];

export const theme = createTheme({
  primaryColor: "primary",
  primaryShade: { light: 6, dark: 5 },
  defaultRadius: "md",

  // Keep Mantine font stack aligned with globals.css
  fontFamily: "var(--font-sans)",

  headings: {
    fontFamily: "var(--font-sans)",
    fontWeight: "700",
    sizes: {
      h1: { fontSize: rem(32), lineHeight: "1.2", fontWeight: "700" },
      h2: { fontSize: rem(26), lineHeight: "1.25", fontWeight: "700" },
      h3: { fontSize: rem(22), lineHeight: "1.3", fontWeight: "600" },
      h4: { fontSize: rem(18), lineHeight: "1.35", fontWeight: "600" },
      h5: { fontSize: rem(16), lineHeight: "1.4", fontWeight: "600" },
      h6: { fontSize: rem(14), lineHeight: "1.4", fontWeight: "600" },
    },
  },

  fontSizes: {
    xs: rem(12),
    sm: rem(14),
    md: rem(16),
    lg: rem(20),
    xl: rem(24),
  },

  spacing: {
    xs: rem(8),
    sm: rem(16),
    md: rem(24),
    lg: rem(32),
    xl: rem(40),
  },

  radius: {
    xs: rem(6),
    sm: rem(8),
    md: rem(10),
    lg: rem(12),
    xl: rem(16),
  },

  shadows: {
    xs: "var(--shadow-1)",
    sm: "var(--shadow-1)",
    md: "var(--shadow-2)",
    lg: "var(--shadow-2)",
    xl: "var(--shadow-2)",
  },

  focusRing: "auto",

  colors: {
    primary,
    accent,
    success,
    warning,
    error,
    info,
    neutral,
    dark: [
      tokens.colors.neutral[50],
      tokens.colors.neutral[100],
      tokens.colors.neutral[200],
      tokens.colors.neutral[300],
      tokens.colors.neutral[400],
      tokens.colors.neutral[500],
      tokens.colors.neutral[600],
      tokens.colors.neutral[700],
      tokens.colors.neutral[800],
      tokens.colors.neutral[900],
    ],
  },

  cursorType: "pointer",

  components: {
    Card: {
      defaultProps: {
        padding: "md",
        radius: "md",
        withBorder: true,
      },
      styles: () => ({
        root: {
          backgroundColor: "var(--surface-1)",
          borderColor: "var(--border-1)",
          boxShadow: "var(--shadow-1)",
          transition: `border-color ${tokens.animation.fast} ${tokens.animation.easing.default}`,
          "&:hover": {
            borderColor: "var(--border-color-strong)",
          },
        },
      }),
    },

    Paper: {
      defaultProps: {
        radius: "md",
      },
      styles: () => ({
        root: {
          backgroundColor: "var(--surface-1)",
          borderColor: "var(--border-1)",
          boxShadow: "var(--shadow-1)",
          transition: `border-color ${tokens.animation.fast} ${tokens.animation.easing.default}`,
        },
      }),
    },

    Button: {
      defaultProps: {
        radius: "md",
      },
      styles: () => ({
        root: {
          fontWeight: 600,
          transition: `transform ${tokens.animation.fast} ${tokens.animation.easing.default},
                       box-shadow ${tokens.animation.fast} ${tokens.animation.easing.default},
                       background ${tokens.animation.fast} ${tokens.animation.easing.default}`,
          "&:active": {
            transform: "scale(0.98)",
          },
        },
      }),
    },

    ActionIcon: {
      defaultProps: {
        radius: "md",
      },
      styles: () => ({
        root: {
          transition: `transform ${tokens.animation.fast} ${tokens.animation.easing.default},
                       background ${tokens.animation.fast} ${tokens.animation.easing.default}`,
          "&:active": {
            transform: "scale(0.95)",
          },
        },
      }),
    },

    Input: {
      defaultProps: {
        radius: "md",
      },
      styles: () => ({
        input: {
          transition: `border-color ${tokens.animation.fast} ${tokens.animation.easing.default},
                       box-shadow ${tokens.animation.fast} ${tokens.animation.easing.default}`,
        },
      }),
    },

    TextInput: {
      defaultProps: {
        radius: "md",
      },
    },

    Select: {
      defaultProps: {
        radius: "md",
      },
    },

    Textarea: {
      defaultProps: {
        radius: "md",
      },
    },

    Modal: {
      defaultProps: {
        radius: "lg",
        overlayProps: {
          blur: 4,
          opacity: 0.55,
        },
        transitionProps: {
          transition: "slide-up",
          duration: 200,
        },
      },
      styles: () => ({
        content: {
          boxShadow: tokens.shadow.floating,
        },
      }),
    },

    Drawer: {
      defaultProps: {
        radius: "lg",
        overlayProps: {
          blur: 4,
          opacity: 0.55,
        },
        transitionProps: {
          duration: 250,
        },
      },
    },

    Popover: {
      defaultProps: {
        radius: "md",
        shadow: "lg",
        transitionProps: {
          transition: "pop",
          duration: 150,
        },
      },
    },

    Menu: {
      defaultProps: {
        radius: "md",
        shadow: "md",
        transitionProps: {
          transition: "pop",
          duration: 150,
        },
      },
      styles: () => ({
        dropdown: {
          padding: rem(6),
        },
        item: {
          borderRadius: rem(8),
          padding: `${rem(8)} ${rem(12)}`,
        },
      }),
    },

    Tooltip: {
      defaultProps: {
        radius: "sm",
        transitionProps: {
          transition: "fade",
          duration: 150,
        },
      },
    },

    Table: {
      defaultProps: {
        striped: true,
        highlightOnHover: true,
        withTableBorder: false,
        withColumnBorders: false,
        verticalSpacing: "sm",
        horizontalSpacing: "md",
      },
      styles: () => ({
        thead: {
          position: "sticky",
          top: 0,
          backgroundColor: "var(--mantine-color-body)",
          zIndex: 1,
        },
        th: {
          fontWeight: 600,
          textTransform: "uppercase",
          fontSize: rem(11),
          letterSpacing: "0.05em",
        },
        tr: {
          transition: `background ${tokens.animation.fast} ${tokens.animation.easing.default}`,
        },
      }),
    },

    NavLink: {
      defaultProps: {
        radius: "md",
      },
      styles: () => ({
        root: {
          transition: `background ${tokens.animation.fast} ${tokens.animation.easing.default}`,
        },
      }),
    },

    Badge: {
      defaultProps: {
        radius: "sm",
      },
      styles: () => ({
        root: {
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.02em",
        },
      }),
    },

    Alert: {
      defaultProps: {
        radius: "md",
      },
      styles: () => ({
        root: {
          border: "1px solid var(--border-1)",
          backgroundColor: "var(--surface-2)",
          backgroundImage: "none",
        },
        title: {
          fontWeight: 600,
        },
      }),
    },

    Notification: {
      defaultProps: {
        radius: "md",
      },
      styles: () => ({
        root: {
          border: "1px solid var(--border-1)",
          backgroundColor: "var(--surface-1)",
          boxShadow: "var(--shadow-1)",
        },
        title: {
          fontWeight: 600,
        },
      }),
    },

    Tabs: {
      styles: () => ({
        tab: {
          fontWeight: 500,
          transition: `color ${tokens.animation.fast} ${tokens.animation.easing.default},
                       border-color ${tokens.animation.fast} ${tokens.animation.easing.default}`,
        },
      }),
    },

    Skeleton: {
      styles: () => ({
        root: {
          "&::after": {
            background: `linear-gradient(
              90deg,
              transparent,
              rgba(255, 255, 255, 0.4),
              transparent
            )`,
            animation: "shimmer 1.5s infinite",
          },
        },
      }),
    },

    Loader: {
      defaultProps: {
        type: "dots",
      },
    },

    ThemeIcon: {
      defaultProps: {
        radius: "md",
      },
    },

    Avatar: {
      defaultProps: {
        radius: "xl",
      },
    },

    Switch: {
      styles: () => ({
        track: {
          transition: `background ${tokens.animation.fast} ${tokens.animation.easing.default}`,
        },
        thumb: {
          transition: `transform ${tokens.animation.fast} ${tokens.animation.easing.bounce}`,
        },
      }),
    },

    Checkbox: {
      styles: () => ({
        input: {
          transition: `background ${tokens.animation.fast} ${tokens.animation.easing.default},
                       border-color ${tokens.animation.fast} ${tokens.animation.easing.default}`,
        },
      }),
    },

    Progress: {
      defaultProps: {
        radius: "xl",
      },
    },

    Breadcrumbs: {
      styles: () => ({
        separator: {
          color: "var(--mantine-color-dimmed)",
        },
        breadcrumb: {
          transition: `color ${tokens.animation.fast} ${tokens.animation.easing.default}`,
          "&:hover": {
            textDecoration: "none",
          },
        },
      }),
    },

    Spotlight: {
      defaultProps: {
        radius: "lg",
      },
      styles: () => ({
        content: {
          boxShadow: tokens.shadow.floating,
        },
      }),
    },
  },

  other: {
    // Custom properties for our app
    headerHeight: 64,
    sidebarWidth: 280,
    sidebarCollapsedWidth: 72,
    gradients: tokens.gradients,
    dark: tokens.dark,
    animation: tokens.animation,
    statusColors: {
      healthy: tokens.colors.success[500],
      warning: tokens.colors.warn[500],
      error: tokens.colors.error[500],
      info: tokens.colors.info[500],
    },
  },
});

export default theme;
