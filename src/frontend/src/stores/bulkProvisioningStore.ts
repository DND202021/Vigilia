/**
 * Bulk Device Provisioning Store (Zustand)
 *
 * Manages CSV upload flow for bulk device provisioning.
 */
import { create } from 'zustand';
import type { BulkProvisionResultItem } from '../types';
import { provisioningApi } from '../services/api';

interface BulkProvisioningStore {
  // CSV state
  csvFile: File | null;
  csvData: any[];
  csvHeaders: string[];
  validationErrors: Record<number, string>;
  totalRows: number;
  validRows: number;

  // Upload state
  isUploading: boolean;
  uploadProgress: number;
  results: BulkProvisionResultItem[] | null;
  uploadError: string | null;

  // Summary
  successCount: number;
  failCount: number;

  // Actions
  setCSVFile: (file: File | null) => void;
  setCSVData: (data: any[], headers: string[], errors: Record<number, string>) => void;
  uploadCSV: () => Promise<void>;
  downloadTemplate: () => Promise<void>;
  downloadFailedRows: () => void;
  reset: () => void;
  clearUploadError: () => void;
}

export const useBulkProvisioningStore = create<BulkProvisioningStore>((set, get) => ({
  csvFile: null,
  csvData: [],
  csvHeaders: [],
  validationErrors: {},
  totalRows: 0,
  validRows: 0,
  isUploading: false,
  uploadProgress: 0,
  results: null,
  uploadError: null,
  successCount: 0,
  failCount: 0,

  setCSVFile: (file) => set({ csvFile: file }),

  setCSVData: (data, headers, errors) => {
    const totalRows = data.length;
    const validRows = totalRows - Object.keys(errors).length;
    set({
      csvData: data,
      csvHeaders: headers,
      validationErrors: errors,
      totalRows,
      validRows,
    });
  },

  uploadCSV: async () => {
    const { csvFile } = get();
    if (!csvFile) {
      set({ uploadError: 'No CSV file selected' });
      return;
    }

    set({ isUploading: true, uploadProgress: 0, uploadError: null });
    try {
      // Simulate progress for UX (API is synchronous)
      const progressInterval = setInterval(() => {
        set((state) => ({
          uploadProgress: Math.min(state.uploadProgress + 10, 90),
        }));
      }, 300);

      const response = await provisioningApi.bulkProvision(csvFile);

      clearInterval(progressInterval);

      set({
        results: response.results,
        successCount: response.successful,
        failCount: response.failed,
        uploadProgress: 100,
        isUploading: false,
      });
    } catch (error) {
      set({
        uploadError: error instanceof Error ? error.message : 'Failed to upload CSV',
        isUploading: false,
        uploadProgress: 0,
      });
      throw error;
    }
  },

  downloadTemplate: async () => {
    try {
      const blob = await provisioningApi.downloadTemplate();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'device_provision_template.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      set({
        uploadError: error instanceof Error ? error.message : 'Failed to download template',
      });
    }
  },

  downloadFailedRows: () => {
    const { results } = get();
    if (!results) return;

    const failedResults = results.filter((r) => r.status === 'error');
    if (failedResults.length === 0) return;

    // Generate CSV content
    const headers = ['row', 'error'];
    const rows = failedResults.map((r) => [r.row, r.error || 'Unknown error']);
    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n');

    // Trigger download
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'failed_provisions.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },

  reset: () => set({
    csvFile: null,
    csvData: [],
    csvHeaders: [],
    validationErrors: {},
    totalRows: 0,
    validRows: 0,
    isUploading: false,
    uploadProgress: 0,
    results: null,
    uploadError: null,
    successCount: 0,
    failCount: 0,
  }),

  clearUploadError: () => set({ uploadError: null }),
}));
