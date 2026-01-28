/**
 * Document Store (Zustand)
 *
 * Manages state for building document management: list, upload, delete.
 */

import { create } from 'zustand';
import { documentsApi } from '../services/api';
import type { BuildingDocument, DocumentCategory } from '../types';

interface DocumentStore {
  // Data
  documents: BuildingDocument[];
  selectedDocument: BuildingDocument | null;

  // Loading state
  isLoading: boolean;
  isUploading: boolean;
  uploadProgress: number;
  error: string | null;

  // Filters
  categoryFilter: DocumentCategory | null;

  // Actions
  fetchDocuments: (buildingId: string) => Promise<void>;
  uploadDocument: (buildingId: string, file: File, title: string, category: DocumentCategory, description?: string) => Promise<BuildingDocument | null>;
  updateDocument: (documentId: string, data: { title?: string; description?: string; category?: DocumentCategory }) => Promise<void>;
  deleteDocument: (documentId: string) => Promise<void>;
  selectDocument: (document: BuildingDocument | null) => void;
  setCategoryFilter: (category: DocumentCategory | null) => void;
  clearError: () => void;
}

const initialState = {
  documents: [] as BuildingDocument[],
  selectedDocument: null as BuildingDocument | null,
  isLoading: false,
  isUploading: false,
  uploadProgress: 0,
  error: null as string | null,
  categoryFilter: null as DocumentCategory | null,
};

export const useDocumentStore = create<DocumentStore>((set, get) => ({
  ...initialState,

  fetchDocuments: async (buildingId: string) => {
    set({ isLoading: true, error: null });
    try {
      const { categoryFilter } = get();
      const response = await documentsApi.list(buildingId, { category: categoryFilter || undefined });
      set({ documents: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch documents',
        isLoading: false,
      });
    }
  },

  uploadDocument: async (buildingId, file, title, category, description) => {
    set({ isUploading: true, uploadProgress: 0, error: null });
    try {
      const document = await documentsApi.upload(buildingId, file, { title, category, description }, (progress) => {
        set({ uploadProgress: progress });
      });
      set((state) => ({
        documents: [document, ...state.documents],
        isUploading: false,
        uploadProgress: 100,
      }));
      return document;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to upload document',
        isUploading: false,
        uploadProgress: 0,
      });
      return null;
    }
  },

  updateDocument: async (documentId, data) => {
    try {
      const updated = await documentsApi.update(documentId, data);
      set((state) => ({
        documents: state.documents.map((d) => (d.id === documentId ? updated : d)),
        selectedDocument: state.selectedDocument?.id === documentId ? updated : state.selectedDocument,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update document',
      });
    }
  },

  deleteDocument: async (documentId) => {
    try {
      await documentsApi.delete(documentId);
      set((state) => ({
        documents: state.documents.filter((d) => d.id !== documentId),
        selectedDocument: state.selectedDocument?.id === documentId ? null : state.selectedDocument,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete document',
      });
    }
  },

  selectDocument: (document) => {
    set({ selectedDocument: document });
  },

  setCategoryFilter: (category) => {
    set({ categoryFilter: category });
  },

  clearError: () => {
    set({ error: null });
  },
}));
