/**
 * Toast Component
 *
 * Displays toast notifications with different severity levels.
 */

import { useToastStore, type Toast as ToastType } from '../../stores/toastStore';

const typeStyles: Record<ToastType['type'], { bg: string; border: string; text: string; icon: string }> = {
  error: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-700',
    icon: '✕',
  },
  success: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    text: 'text-green-700',
    icon: '✓',
  },
  warning: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    text: 'text-yellow-700',
    icon: '⚠',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-700',
    icon: 'ℹ',
  },
};

function ToastItem({ toast }: { toast: ToastType }) {
  const { removeToast } = useToastStore();
  const styles = typeStyles[toast.type];

  return (
    <div
      className={`${styles.bg} ${styles.border} border rounded-lg shadow-lg p-3 flex items-start gap-2 min-w-[300px] max-w-[400px] animate-slide-in`}
      role="alert"
    >
      <span className={`${styles.text} font-bold flex-shrink-0`}>{styles.icon}</span>
      <span className={`${styles.text} text-sm flex-1`}>{toast.message}</span>
      <button
        onClick={() => removeToast(toast.id)}
        className={`${styles.text} hover:opacity-70 text-lg leading-none flex-shrink-0`}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { toasts } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  );
}

export default ToastContainer;
