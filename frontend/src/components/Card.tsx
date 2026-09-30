import { ReactNode } from 'react';

export default function Card({
  children,
  className = '',
  onClick,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl shadow-sm border border-leaf-100 p-5 ${
        onClick ? 'cursor-pointer active:scale-[0.99] transition-transform' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}
