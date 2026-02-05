/**
 * MFA Setup Modal
 * Two-step flow: 1) Display QR code 2) Verify TOTP code
 */
import { useState, useEffect } from 'react';
import { authApi } from '../../services/api';
import { Modal, Button, Input, Spinner } from '../ui';
import type { MFASetupResponse } from '../../types';

interface MFASetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function MFASetupModal({ isOpen, onClose, onSuccess }: MFASetupModalProps) {
  const [step, setStep] = useState<'qr' | 'verify'>('qr');
  const [setupData, setSetupData] = useState<MFASetupResponse | null>(null);
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen && !setupData) {
      setIsLoading(true);
      authApi.mfaSetup()
        .then(data => {
          setSetupData(data);
          setStep('qr');
        })
        .catch(e => setError(e.response?.data?.detail || 'Failed to initialize MFA setup'))
        .finally(() => setIsLoading(false));
    }
  }, [isOpen, setupData]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setStep('qr');
      setSetupData(null);
      setCode('');
      setError('');
    }
  }, [isOpen]);

  const handleVerify = async () => {
    if (!setupData || code.length !== 6) return;
    setIsLoading(true);
    setError('');
    try {
      await authApi.mfaConfirm(setupData.secret, code);
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
    <Modal isOpen={isOpen} onClose={onClose} title="Enable Two-Factor Authentication">
      {isLoading && !setupData ? (
        <div className="flex justify-center py-8"><Spinner size="lg" /></div>
      ) : step === 'qr' && setupData ? (
        <div className="space-y-4">
          <p className="text-gray-600 text-sm">
            Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.):
          </p>
          <div className="flex justify-center">
            <img src={setupData.qr_code} alt="MFA QR Code" className="w-48 h-48 border rounded" />
          </div>
          <details className="text-sm text-gray-500">
            <summary className="cursor-pointer hover:text-gray-700">Can't scan? Enter manually</summary>
            <code className="block mt-2 p-2 bg-gray-100 rounded text-xs break-all select-all">
              {setupData.manual_entry_key}
            </code>
          </details>
          <Button onClick={() => setStep('verify')} className="w-full">
            Continue
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-gray-600 text-sm">
            Enter the 6-digit code from your authenticator app:
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
            <Button variant="secondary" onClick={() => setStep('qr')} className="flex-1">
              Back
            </Button>
            <Button
              onClick={handleVerify}
              isLoading={isLoading}
              disabled={code.length !== 6}
              className="flex-1"
            >
              Verify & Enable
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
