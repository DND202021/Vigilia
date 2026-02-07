/**
 * Device Provisioning Store (Zustand)
 *
 * Manages the multi-step wizard state for single-device provisioning.
 * Steps: ProfileSelection -> DeviceDetails -> CredentialGeneration -> CredentialDownload -> ActivationWait
 */
import { create } from 'zustand';
import type { DeviceProvisionResponse, DeviceProfile, Building } from '../types';
import { provisioningApi, deviceProfilesApi, buildingsApi } from '../services/api';

interface ProvisioningFormData {
  profileId: string | null;
  deviceType: 'microphone' | 'camera' | 'sensor' | 'gateway';
  name: string;
  buildingId: string;
  credentialType: 'access_token' | 'x509';
  serialNumber: string;
  manufacturer: string;
  model: string;
}

export interface ProvisioningCredentials {
  deviceId: string | null;
  accessToken: string | null;
  certificatePem: string | null;
  privateKeyPem: string | null;
  certificateCn: string | null;
  certificateExpiry: string | null;
}

export type ActivationStatus = 'idle' | 'pending' | 'active' | 'timeout';

interface ProvisioningStore {
  // Wizard navigation
  currentStep: number;
  maxStepReached: number;

  // Form data (persists across steps)
  formData: ProvisioningFormData;

  // Generated credentials (one-time, cleared after download)
  credentials: ProvisioningCredentials | null;

  // Device ID (persists even after credentials cleared, needed for activation step)
  provisionedDeviceId: string | null;

  // Activation status
  activationStatus: ActivationStatus;

  // Loading/error
  isProvisioning: boolean;
  error: string | null;

  // Device profiles (for step 1)
  profiles: DeviceProfile[];
  isLoadingProfiles: boolean;

  // Buildings (for step 2)
  buildings: Building[];
  isLoadingBuildings: boolean;

  // Actions
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: number) => void;
  updateFormData: (data: Partial<ProvisioningFormData>) => void;
  fetchProfiles: () => Promise<void>;
  fetchBuildings: () => Promise<void>;
  provisionDevice: () => Promise<void>;
  setActivationStatus: (status: ActivationStatus) => void;
  clearCredentials: () => void;
  resetWizard: () => void;
  clearError: () => void;
}

const initialFormData: ProvisioningFormData = {
  profileId: null,
  deviceType: 'microphone',
  name: '',
  buildingId: '',
  credentialType: 'access_token',
  serialNumber: '',
  manufacturer: '',
  model: '',
};

export const useProvisioningStore = create<ProvisioningStore>((set, get) => ({
  currentStep: 0,
  maxStepReached: 0,
  formData: initialFormData,
  credentials: null,
  provisionedDeviceId: null,
  activationStatus: 'idle',
  isProvisioning: false,
  error: null,
  profiles: [],
  isLoadingProfiles: false,
  buildings: [],
  isLoadingBuildings: false,

  nextStep: () => set((state) => {
    const newStep = Math.min(state.currentStep + 1, 4);
    return {
      currentStep: newStep,
      maxStepReached: Math.max(state.maxStepReached, newStep),
    };
  }),

  prevStep: () => set((state) => ({
    currentStep: Math.max(state.currentStep - 1, 0),
  })),

  goToStep: (step) => set((state) => ({
    currentStep: Math.min(Math.max(step, 0), state.maxStepReached),
  })),

  updateFormData: (data) => set((state) => ({
    formData: { ...state.formData, ...data },
  })),

  fetchProfiles: async () => {
    set({ isLoadingProfiles: true, error: null });
    try {
      const response = await deviceProfilesApi.list({ page_size: 100 });
      set({ profiles: response.items, isLoadingProfiles: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch device profiles',
        isLoadingProfiles: false,
      });
    }
  },

  fetchBuildings: async () => {
    set({ isLoadingBuildings: true, error: null });
    try {
      const response = await buildingsApi.list({ page_size: 100 });
      set({ buildings: response.items, isLoadingBuildings: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch buildings',
        isLoadingBuildings: false,
      });
    }
  },

  provisionDevice: async () => {
    const { formData } = get();
    set({ isProvisioning: true, error: null });
    try {
      const response: DeviceProvisionResponse = await provisioningApi.provision({
        name: formData.name,
        device_type: formData.deviceType,
        building_id: formData.buildingId,
        profile_id: formData.profileId || undefined,
        credential_type: formData.credentialType,
        serial_number: formData.serialNumber || undefined,
        manufacturer: formData.manufacturer || undefined,
        model: formData.model || undefined,
      });

      // Store credentials (one-time) and device ID (persists)
      set({
        credentials: {
          deviceId: response.device_id,
          accessToken: response.access_token || null,
          certificatePem: response.certificate_pem || null,
          privateKeyPem: response.private_key_pem || null,
          certificateCn: response.certificate_cn || null,
          certificateExpiry: response.certificate_expiry || null,
        },
        provisionedDeviceId: response.device_id,
        activationStatus: 'pending',
        isProvisioning: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to provision device',
        isProvisioning: false,
      });
      throw error;
    }
  },

  setActivationStatus: (status) => set({ activationStatus: status }),

  clearCredentials: () => set({ credentials: null }), // Note: provisionedDeviceId is preserved

  resetWizard: () => set({
    currentStep: 0,
    maxStepReached: 0,
    formData: initialFormData,
    credentials: null,
    provisionedDeviceId: null,
    activationStatus: 'idle',
    error: null,
  }),

  clearError: () => set({ error: null }),
}));
