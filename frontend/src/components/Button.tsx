import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'lg' | 'md';
  icon?: ReactNode;
  fullWidth?: boolean;
}

export default function Button({
  variant = 'primary',
  size = 'lg',
  icon,
  fullWidth = true,
  children,
  className = '',
  ...rest
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-2xl font-semibold transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none focus:outline-none focus-visible:ring-4 focus-visible:ring-leaf-200';

  const variants: Record<string, string> = {
    primary: 'bg-leaf-600 text-white shadow-lg shadow-leaf-600/20 hover:bg-leaf-700',
    secondary: 'bg-wheat-400 text-earth-800 shadow-md hover:bg-wheat-500',
    outline: 'bg-white text-leaf-700 border-2 border-leaf-600 hover:bg-leaf-50',
    ghost: 'bg-leaf-50 text-leaf-800 hover:bg-leaf-100',
  };

  const sizes: Record<string, string> = {
    lg: 'text-base sm:text-lg px-6 py-4 min-h-[52px]',
    md: 'text-sm px-4 py-3 min-h-[44px]',
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${fullWidth ? 'w-full' : ''} ${className}`}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
}
