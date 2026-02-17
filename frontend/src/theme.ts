import { createTheme } from '@mantine/core';

export const theme = createTheme({
  /** Material Design theme with high contrast readability */
  fontFamily: '"Manrope", "Sora", "Helvetica Neue", sans-serif',
  fontFamilyMonospace: '"Roboto Mono", "Courier New", monospace',
  defaultRadius: 'md',
  
  headings: {
    fontFamily: '"Sora", "Manrope", "Helvetica Neue", sans-serif',
    sizes: {
      h1: { fontSize: '2.25rem', fontWeight: '600', lineHeight: '1.2' },
      h2: { fontSize: '1.9rem', fontWeight: '600', lineHeight: '1.3' },
      h3: { fontSize: '1.75rem', fontWeight: '500', lineHeight: '1.4' },
      h4: { fontSize: '1.5rem', fontWeight: '600', lineHeight: '1.4' },
      h5: { fontSize: '1.25rem', fontWeight: '500', lineHeight: '1.5' },
      h6: { fontSize: '1rem', fontWeight: '500', lineHeight: '1.6' },
    },
  },
  
  // High contrast color palette for readability
  colors: {
    primary: [
      '#fafafa', // 0
      '#f5f5f5', // 1
      '#eeeeee', // 2
      '#e0e0e0', // 3
      '#bdbdbd', // 4
      '#9e9e9e', // 5
      '#757575', // 6
      '#616161', // 7
      '#424242', // 8
      '#212121', // 9
    ],
    secondary: [
      '#f3e5f5', // 0
      '#e1bee7', // 1
      '#ce93d8', // 2
      '#ba68c8', // 3
      '#ab47bc', // 4
      '#9c27b0', // 5
      '#8e24aa', // 6
      '#7b1fa2', // 7
      '#6a1b9a', // 8
      '#4a148c', // 9
    ],
    info: [
      '#e3f2fd', // 0
      '#bbdefb', // 1
      '#90caf9', // 2
      '#64b5f6', // 3
      '#42a5f5', // 4
      '#2196f3', // 5
      '#1e88e5', // 6
      '#1976d2', // 7
      '#1565c0', // 8
      '#0d47a1', // 9
    ],
    success: [
      '#e8f5e9', // 0
      '#c8e6c9', // 1
      '#a5d6a7', // 2
      '#81c784', // 3
      '#66bb6a', // 4
      '#4caf50', // 5
      '#43a047', // 6
      '#388e3c', // 7
      '#2e7d32', // 8
      '#1b5e20', // 9
    ],
    warning: [
      '#fff3e0', // 0
      '#ffe0b2', // 1
      '#ffcc80', // 2
      '#ffb74d', // 3
      '#ffa726', // 4
      '#ff9800', // 5
      '#fb8c00', // 6
      '#f57c00', // 7
      '#ef6c00', // 8
      '#e65100', // 9
    ],
    error: [
      '#ffebee', // 0
      '#ffcdd2', // 1
      '#ef9a9a', // 2
      '#e57373', // 3
      '#ef5350', // 4
      '#f44336', // 5
      '#e53935', // 6
      '#d32f2f', // 7
      '#c62828', // 8
      '#b71c1c', // 9
    ],
  },
  
  primaryColor: 'info',
  primaryShade: { light: 6, dark: 7 },

  shadows: {
    xs: '0 1px 2px rgba(0, 0, 0, 0.06)',
    sm: '0 2px 6px rgba(0, 0, 0, 0.08)',
    md: '0 6px 12px rgba(0, 0, 0, 0.12)',
    lg: '0 12px 24px rgba(0, 0, 0, 0.14)',
    xl: '0 18px 32px rgba(0, 0, 0, 0.16)',
  },
  
  components: {
    Card: {
      defaultProps: {
        shadow: 'xs',
        padding: 'xl',
        radius: 'lg',
      },
      styles: {
        root: {
          transition: 'transform 150ms ease, box-shadow 150ms ease, background 150ms ease',
          backgroundColor: 'var(--surface-1)',
          borderColor: 'var(--border-1)',
        },
      },
    },
    Button: {
      defaultProps: {
        radius: 'md',
      },
      styles: {
        root: {
          fontWeight: 600,
          transition: 'transform 120ms ease, box-shadow 120ms ease, background 120ms ease',
          '&:active': {
            transform: 'scale(0.98)',
          },
        },
      },
    },
    TextInput: {
      defaultProps: {
        radius: 'md',
      },
    },
    Paper: {
      defaultProps: {
        shadow: 'xs',
        radius: 'md',
      },
      styles: {
        root: {
          transition: 'box-shadow 150ms ease, background 150ms ease',
          backgroundColor: 'var(--surface-1)',
          borderColor: 'var(--border-1)',
        },
      },
    },
    Text: {
      defaultProps: {},
    },
    Badge: {
      styles: {
        root: {
          fontWeight: 600,
          letterSpacing: '0.02em',
          textTransform: 'uppercase',
        },
      },
    },
    Alert: {
      defaultProps: {
        radius: 'md',
      },
      styles: {
        root: {
          border: '1px solid var(--mantine-color-default-border)',
          background: 'var(--mantine-color-body)',
        },
        title: {
          fontWeight: 600,
        },
      },
    },
    ActionIcon: {
      defaultProps: {
        radius: 'md',
      },
      styles: {
        root: {
          transition: 'transform 120ms ease, background 120ms ease',
          '&:active': {
            transform: 'scale(0.96)',
          },
        },
      },
    },
  },
  
  defaultGradient: {
    from: 'info.6',
    to: 'info.4',
    deg: 45,
  },
});
