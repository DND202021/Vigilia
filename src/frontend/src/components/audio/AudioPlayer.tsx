/**
 * Inline Audio Player component for replaying alert audio clips.
 */

import { useRef, useState, useEffect } from 'react';
import { audioClipsApi } from '../../services/api';
import { tokenStorage } from '../../services/api';

interface AudioPlayerProps {
  clipId: string;
  compact?: boolean;
  className?: string;
}

export function AudioPlayer({ clipId, compact = true, className = '' }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(false);

  const streamUrl = audioClipsApi.getStreamUrl(clipId);
  const token = tokenStorage.getAccessToken();

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => {
      setProgress(audio.currentTime);
    };
    const onLoadedMetadata = () => {
      setDuration(audio.duration);
    };
    const onEnded = () => {
      setIsPlaying(false);
      setProgress(0);
    };
    const onError = () => {
      setError(true);
      setIsPlaying(false);
    };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('error', onError);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('error', onError);
    };
  }, []);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch(() => setError(true));
    }
    setIsPlaying(!isPlaying);
  };

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  if (error) {
    return (
      <span className={`text-xs text-gray-400 ${className}`}>Audio unavailable</span>
    );
  }

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-1.5 ${className}`}>
        <audio ref={audioRef} src={`${streamUrl}?token=${token}`} preload="none" />
        <button
          onClick={togglePlay}
          className={`w-7 h-7 rounded-full flex items-center justify-center transition-colors ${
            isPlaying
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          )}
        </button>
        {isPlaying && (
          <span className="text-xs text-gray-500 tabular-nums">
            {formatTime(progress)}
          </span>
        )}
      </div>
    );
  }

  // Full player
  return (
    <div className={`bg-gray-50 rounded-lg p-3 ${className}`}>
      <audio ref={audioRef} src={`${streamUrl}?token=${token}`} preload="none" />
      <div className="flex items-center gap-3">
        <button
          onClick={togglePlay}
          className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
            isPlaying
              ? 'bg-blue-600 text-white'
              : 'bg-blue-100 text-blue-600 hover:bg-blue-200'
          }`}
        >
          {isPlaying ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          )}
        </button>

        <div className="flex-1">
          <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 rounded-full transition-all"
              style={{ width: duration ? `${(progress / duration) * 100}%` : '0%' }}
            />
          </div>
        </div>

        <span className="text-xs text-gray-500 tabular-nums w-12 text-right">
          {formatTime(progress)} / {formatTime(duration)}
        </span>
      </div>
    </div>
  );
}
