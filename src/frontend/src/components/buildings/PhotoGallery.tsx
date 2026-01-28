/**
 * PhotoGallery Component
 *
 * Displays building photos in a responsive grid with lightbox, filtering, and upload.
 */

import { useState, useEffect, useCallback } from 'react';
import { usePhotoStore } from '../../stores/photoStore';
import type { BuildingPhoto } from '../../types';
import { cn } from '../../utils';

interface PhotoGalleryProps {
  buildingId: string;
  floorPlanId?: string;
  onPhotoSelect?: (photo: BuildingPhoto) => void;
  onCaptureClick?: () => void;
  className?: string;
}

export function PhotoGallery({ buildingId, floorPlanId, onPhotoSelect: _onPhotoSelect, onCaptureClick, className }: PhotoGalleryProps) {
  const {
    photos,
    allTags,
    isLoading,
    isUploading,
    uploadProgress,
    error,
    filters,
    fetchPhotos,
    uploadPhoto,
    deletePhoto,
    setFilters,
    clearFilters,
    clearError,
  } = usePhotoStore();

  const [showUploadForm, setShowUploadForm] = useState(false);
  const [lightboxPhoto, setLightboxPhoto] = useState<BuildingPhoto | null>(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadTags, setUploadTags] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Set floor plan filter if provided
  useEffect(() => {
    if (floorPlanId) {
      setFilters({ floorPlanId });
    }
  }, [floorPlanId, setFilters]);

  // Fetch photos on mount and when filters change
  useEffect(() => {
    fetchPhotos(buildingId);
  }, [buildingId, filters, fetchPhotos]);

  // Handle file selection
  const handleFileSelect = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      return; // Only accept images
    }
    setSelectedFile(file);
    if (!uploadTitle) {
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

    const tags = uploadTags.split(',').map(t => t.trim()).filter(Boolean);

    const result = await uploadPhoto(buildingId, selectedFile, {
      title: uploadTitle,
      description: uploadDescription || undefined,
      floorPlanId: floorPlanId,
      tags: tags.length > 0 ? tags : undefined,
    });

    if (result) {
      setShowUploadForm(false);
      setSelectedFile(null);
      setUploadTitle('');
      setUploadDescription('');
      setUploadTags('');
    }
  };

  // Handle delete
  const handleDelete = async (photoId: string) => {
    await deletePhoto(photoId);
    setDeleteConfirmId(null);
    if (lightboxPhoto?.id === photoId) {
      setLightboxPhoto(null);
    }
  };

  // Toggle tag filter
  const toggleTagFilter = (tag: string) => {
    const currentTags = filters.tags || [];
    if (currentTags.includes(tag)) {
      setFilters({ tags: currentTags.filter(t => t !== tag) });
    } else {
      setFilters({ tags: [...currentTags, tag] });
    }
  };

  // Navigate lightbox
  const navigateLightbox = (direction: 'prev' | 'next') => {
    if (!lightboxPhoto) return;
    const currentIndex = photos.findIndex(p => p.id === lightboxPhoto.id);
    if (currentIndex === -1) return;

    const newIndex = direction === 'prev'
      ? (currentIndex - 1 + photos.length) % photos.length
      : (currentIndex + 1) % photos.length;
    setLightboxPhoto(photos[newIndex]);
  };

  return (
    <div className={cn('bg-white rounded-lg shadow', className)}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Photos</h3>
          <div className="flex items-center gap-2">
            {onCaptureClick && (
              <button
                onClick={onCaptureClick}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Capture
              </button>
            )}
            <button
              onClick={() => setShowUploadForm(true)}
              className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Upload
            </button>
          </div>
        </div>

        {/* Tag filters */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTagFilter(tag)}
                className={cn(
                  'px-2 py-0.5 text-xs font-medium rounded-full transition-colors',
                  filters.tags?.includes(tag)
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                )}
              >
                #{tag}
              </button>
            ))}
            {filters.tags && filters.tags.length > 0 && (
              <button
                onClick={clearFilters}
                className="px-2 py-0.5 text-xs text-gray-500 hover:text-gray-700"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
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

      {/* Upload form */}
      {showUploadForm && (
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Upload Photo</h4>

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
                <img
                  src={URL.createObjectURL(selectedFile)}
                  alt="Preview"
                  className="w-16 h-16 object-cover rounded"
                />
                <span className="text-sm text-gray-700">{selectedFile.name}</span>
                <button onClick={() => setSelectedFile(null)} className="text-gray-400 hover:text-gray-600">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <>
                <p className="text-sm text-gray-500 mb-2">Drag and drop an image here, or</p>
                <label className="cursor-pointer text-sm text-blue-600 hover:text-blue-700 font-medium">
                  Browse files
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                  />
                </label>
              </>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
              <input
                type="text"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                placeholder="Photo title"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Tags (comma separated)</label>
              <input
                type="text"
                value={uploadTags}
                onChange={(e) => setUploadTags(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                placeholder="entrance, exterior, damage"
              />
            </div>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={uploadDescription}
              onChange={(e) => setUploadDescription(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="Optional description..."
            />
          </div>

          {isUploading && (
            <div className="mb-3">
              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              onClick={() => { setShowUploadForm(false); setSelectedFile(null); setUploadTitle(''); setUploadDescription(''); setUploadTags(''); }}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
              disabled={isUploading}
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || !uploadTitle || isUploading}
              className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {isUploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </div>
      )}

      {/* Photo grid */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <svg className="animate-spin h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="ml-2 text-sm text-gray-500">Loading photos...</span>
          </div>
        ) : photos.length === 0 ? (
          <div className="py-12 text-center">
            <span className="text-4xl">{'\u{1F4F7}'}</span>
            <p className="mt-2 text-sm text-gray-500">No photos found</p>
            <button onClick={() => setShowUploadForm(true)} className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium">
              Upload your first photo
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {photos.map((photo) => (
              <div
                key={photo.id}
                className="relative group aspect-square rounded-lg overflow-hidden cursor-pointer bg-gray-100"
                onClick={() => setLightboxPhoto(photo)}
              >
                <img
                  src={photo.thumbnail_url || photo.file_url}
                  alt={photo.title}
                  className="w-full h-full object-cover transition-transform group-hover:scale-105"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="absolute bottom-0 left-0 right-0 p-2">
                    <p className="text-white text-xs font-medium truncate">{photo.title}</p>
                    {photo.tags && photo.tags.length > 0 && (
                      <div className="flex gap-1 mt-1 overflow-hidden">
                        {photo.tags.slice(0, 2).map((tag) => (
                          <span key={tag} className="text-[10px] text-white/80">#{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                {deleteConfirmId === photo.id ? (
                  <div className="absolute top-2 right-2 flex gap-1" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => handleDelete(photo.id)} className="p-1 text-xs text-white bg-red-600 rounded">Yes</button>
                    <button onClick={() => setDeleteConfirmId(null)} className="p-1 text-xs text-gray-800 bg-white rounded">No</button>
                  </div>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(photo.id); }}
                    className="absolute top-2 right-2 p-1 bg-black/50 rounded opacity-0 group-hover:opacity-100 transition-opacity text-white hover:bg-red-600"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightboxPhoto && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center" onClick={() => setLightboxPhoto(null)}>
          <button
            onClick={(e) => { e.stopPropagation(); navigateLightbox('prev'); }}
            className="absolute left-4 p-2 text-white hover:bg-white/20 rounded-full"
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <div className="max-w-4xl max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <img
              src={lightboxPhoto.file_url}
              alt={lightboxPhoto.title}
              className="max-h-[80vh] object-contain"
            />
            <div className="mt-2 text-white text-center">
              <h4 className="font-medium">{lightboxPhoto.title}</h4>
              {lightboxPhoto.description && <p className="text-sm text-gray-300 mt-1">{lightboxPhoto.description}</p>}
              {lightboxPhoto.tags && lightboxPhoto.tags.length > 0 && (
                <div className="flex justify-center gap-2 mt-2">
                  {lightboxPhoto.tags.map((tag) => (
                    <span key={tag} className="text-xs text-blue-300">#{tag}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <button
            onClick={(e) => { e.stopPropagation(); navigateLightbox('next'); }}
            className="absolute right-4 p-2 text-white hover:bg-white/20 rounded-full"
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <button
            onClick={() => setLightboxPhoto(null)}
            className="absolute top-4 right-4 p-2 text-white hover:bg-white/20 rounded-full"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

export default PhotoGallery;
