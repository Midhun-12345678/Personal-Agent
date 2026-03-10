import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'nano-bg': '#0a0a0f',
        'nano-card': '#12121a',
        'nano-border': '#1e1e2e',
        'nano-accent': '#6366f1',
        'nano-accent-hover': '#818cf8',
        'nano-text': '#e2e8f0',
        'nano-muted': '#64748b',
      },
    },
  },
  plugins: [],
}

export default config
