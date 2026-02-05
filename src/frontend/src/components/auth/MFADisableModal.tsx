/**
 * MFA Disable Modal
 * Requires current TOTP code to disable MFA
 */
import { useState, useEffect } from 'react';
import { authApi } from '../../services/api';
import { Modal, Button, Input } from '../ui';

interface MFADisableModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function MFADisableModal({ isOpen, onClose, onSuccess }: MFADisableModalProps) {
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) {
      setCode('');
      setError('');
    }
  }, [isOpen]);

  const handleDisable = async () => {
    if (code.length !== 6) return;
    setIsLoading(true);
    setError('');
    try {
      await authApi.mfaDisable(code);
      onSuccess();
      onClose();
    } catch (e: unknown) {
      const axiosError = e as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || 'Invalid code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Disable Two-Factor Authentication">
      <div className="space-y-4">
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-800 text-sm">
            Warning: Disabling 2FA makes your account less secure. You'll only need your password to sign in.
          </p>
        </div>
        <p className="text-gray-600 text-sm">
          Enter your current 6-digit code to confirm:
        </p>
        <Input
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          placeholder="000000"
          className="text-center text-2xl tracking-widest font-mono"
          autoFocus
        />
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <div className="flex gap-3">
          <Button variant="secondary" onClick={onClose} className="flex-1">
            Cancel
          </Button>
          <Button
            onClick={handleDisable}
            isLoading={isLoading}
            disabled={code.length !== 6}
            className="flex-1 bg-red-600 hover:bg-red-700"
          >
            Disable 2FA
          </Button>
        </div>
      </div>
    </Modal>
  );
}
