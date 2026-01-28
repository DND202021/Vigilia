/**
 * DocumentManager Component
 *
 * Manages building documents: list, upload, view, delete with category filtering.
 */

import { useState, useEffect, useCallback } from 'react';
import { useDocumentStore } from '../../stores/documentStore';
import type { BuildingDocument, DocumentCategory } from '../../types';
import { cn } from '../../utils';

const CATEGORY_LABELS: Record<DocumentCategory, string> = {
  pre_plan: 'Pre-Plan',
  floor_plan: 'Floor Plan',
  permit: 'Permit',
  inspection: 'Inspection Report',
  manual: 'Manual',
  other: 'Other',
};

const CATEGORY_ICONS: Record<DocumentCategory, string> = {
  pre_plan: '\u{1F4CB}',
  floor_plan: '\u{1F3D7}\uFE0F',
  permit: '\u{1F4DC}',
  inspection: '\u{1F50D}',
  manual: '\u{1F4D6}',
  other: '\u{1F4C4}',
};

const FILE_TYPE_ICONS: Record<string, string> = {
  pdf: '\u{1F4D5}',
  doc: '\u{1F4DD}',
  docx: '\u{1F4DD}',
  xls: '\u{1F4CA}',
  xlsx: '\u{1F4CA}',
  jpg: '\u{1F5BC}\uFE0F',
  jpeg: '\u{1F5BC}\uFE0F',
  png: '\u{1F5BC}\uFE0F',
  default: '\u{1F4C4}',
};

interface DocumentManagerProps {
  buildingId: string;
  onDocumentSelect?: (document: BuildingDocument) => void;
  className?: string;
}

export function DocumentManager({ buildingId, onDocumentSelect, className }: DocumentManagerProps) {
  // Use the document store
  const {
    documents,
    isLoading,
    isUploading,
    uploadProgress,
    error,
    categoryFilter,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
    setCategoryFilter,
    clearError,
  } = useDocumentStore();

  // Local state
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadCategory, setUploadCategory] = useState<DocumentCategory>('other');
  const [uploadDescription, setUploadDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Fetch documents on mount and when filter changes
  useEffect(() => {
    fetchDocuments(buildingId);
  }, [buildingId, categoryFilter, fetchDocuments]);

  // Handle file selection
  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    if (!uploadTitle) {
      // Auto-fill title from filename
      setUploadTitle(file.name.replace(/\.[^/.]+$/, ''));
    }
    setShowUploadForm(true);
  }, [uploadTitle]);

  // Handle drag and drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  // Handle upload
  const handleUpload = async () => {
    if (!selectedFile || !uploadTitle) return;

    const result = await uploadDocument(buildingId, selectedFile, uploadTitle, uploadCategory, uploadDescription || undefined);

    if (result) {
      // Reset form
      setShowUploadForm(false);
      setSelectedFile(null);
      setUploadTitle('');
      setUploadCategory('other');
      setUploadDescription('');
    }
  };

  // Handle delete
  const handleDelete = async (docId: string) => {
    await deleteDocument(docId);
    setDeleteConfirmId(null);
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Get file type from URL or file_type
  const getFileIcon = (doc: BuildingDocument): string => {
    const ext = doc.file_type?.toLowerCase() || doc.file_url.split('.').pop()?.toLowerCase() || '';
    return FILE_TYPE_ICONS[ext] || FILE_TYPE_ICONS.default;
  };

  return (
    <div className={cn('bg-white rounded-lg shadow', className)}>
      {/* Header with category filter */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Documents</h3>
          <button
            onClick={() => setShowUploadForm(true)}
            className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 transition-colors"
          >
            Upload Document
          </button>
        </div>

        {/* Category filter pills */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setCategoryFilter(null)}
            className={cn(
              'px-2.5 py-1 text-xs font-medium rounded-full transition-colors',
              categoryFilter === null
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            All
          </button>
          {(Object.keys(CATEGORY_LABELS) as DocumentCategory[]).map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={cn(
                'px-2.5 py-1 text-xs font-medium rounded-full transition-colors',
                categoryFilter === cat
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {CATEGORY_ICONS[cat]} {CATEGORY_LABELS[cat]}
            </button>
          ))}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mx-4 mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <span className="text-sm text-red-700">{error}</span>
          <button onClick={clearError} className="text-red-500 hover:text-red-700">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Upload form overlay */}
      {showUploadForm && (
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Upload New Document</h4>

          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            className={cn(
              'border-2 border-dashed rounded-lg p-4 text-center mb-3 transition-colors',
              dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
            )}
          >
            {selectedFile ? (
              <div className="flex items-center justify-center gap-2">
                <span className="text-2xl">{FILE_TYPE_ICONS[selectedFile.name.split('.').pop()?.toLowerCase() || ''] || FILE_TYPE_ICONS.default}</span>
                <span className="text-sm text-gray-700">{selectedFile.name}</span>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <>
                <p className="text-sm text-gray-500 mb-2">Drag and drop a file here, or</p>
                <label className="cursor-pointer text-sm text-blue-600 hover:text-blue-700 font-medium">
                  Browse files
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                  />
                </label>
              </>
            )}
          </div>

          {/* Form fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
              <input
                type="text"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Document title"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Category *</label>
              <select
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value as DocumentCategory)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {(Object.keys(CATEGORY_LABELS) as DocumentCategory[]).map((cat) => (
                  <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={uploadDescription}
              onChange={(e) => setUploadDescription(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={2}
              placeholder="Optional description..."
            />
          </div>

          {/* Upload progress */}
          {isUploading && (
            <div className="mb-3">
              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Form buttons */}
          <div className="flex justify-end gap-2">
            <button
              onClick={() => {
                setShowUploadForm(false);
                setSelectedFile(null);
                setUploadTitle('');
                setUploadDescription('');
              }}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
              disabled={isUploading}
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || !uploadTitle || isUploading}
              className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </div>
      )}

      {/* Document list */}
      <div className="divide-y divide-gray-100">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <svg className="animate-spin h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="ml-2 text-sm text-gray-500">Loading documents...</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="py-12 text-center">
            <span className="text-4xl">{'\u{1F4C1}'}</span>
            <p className="mt-2 text-sm text-gray-500">No documents found</p>
            <button
              onClick={() => setShowUploadForm(true)}
              className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Upload your first document
            </button>
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className="px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => onDocumentSelect?.(doc)}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl flex-shrink-0">{getFileIcon(doc)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900 truncate">{doc.title}</span>
                    <span className="px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-600 rounded">
                      {CATEGORY_LABELS[doc.category]}
                    </span>
                    {doc.version > 1 && (
                      <span className="text-[10px] text-gray-400">v{doc.version}</span>
                    )}
                  </div>
                  {doc.description && (
                    <p className="text-xs text-gray-500 truncate mt-0.5">{doc.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    <span>{formatFileSize(doc.file_size)}</span>
                    <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    {doc.uploaded_by_name && <span>by {doc.uploaded_by_name}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <a
                    href={doc.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-1.5 text-gray-400 hover:text-blue-600 rounded hover:bg-blue-50"
                    title="Download"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  </a>
                  {deleteConfirmId === doc.id ? (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="p-1 text-xs text-white bg-red-600 rounded hover:bg-red-700"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => setDeleteConfirmId(null)}
                        className="p-1 text-xs text-gray-600 bg-gray-200 rounded hover:bg-gray-300"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(doc.id); }}
                      className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-red-50"
                      title="Delete"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default DocumentManager;
