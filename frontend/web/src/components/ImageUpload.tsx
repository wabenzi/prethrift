import React, { useRef, useState, useCallback } from 'react';

interface ImageUploadProps {
  onImageSelect: (file: File, preview: string) => void;
  onImageRemove: () => void;
  currentImage?: string;
  accept?: string;
  maxSizeMB?: number;
  disabled?: boolean;
}

export default function ImageUpload({
  onImageSelect,
  onImageRemove,
  currentImage,
  accept = 'image/*',
  maxSizeMB = 10,
  disabled = false
}: ImageUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const validateAndProcessFile = useCallback((file: File) => {
    setUploadError(null);

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setUploadError('Please select an image file');
      return;
    }

    // Validate file size
    if (file.size > maxSizeMB * 1024 * 1024) {
      setUploadError(`File size must be less than ${maxSizeMB}MB`);
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      const preview = e.target?.result as string;
      onImageSelect(file, preview);
    };
    reader.readAsDataURL(file);
  }, [onImageSelect, maxSizeMB]);

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      validateAndProcessFile(file);
    }
  }, [validateAndProcessFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragOver(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    if (disabled) return;

    const file = e.dataTransfer.files[0];
    if (file) {
      validateAndProcessFile(file);
    }
  }, [disabled, validateAndProcessFile]);

  const handleRemoveImage = useCallback(() => {
    onImageRemove();
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setUploadError(null);
  }, [onImageRemove]);

  return (
    <div style={{ width: '100%' }}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileSelect}
        disabled={disabled}
        style={{ display: 'none' }}
      />

      {currentImage ? (
        // Image preview with remove option
        <div style={{
          position: 'relative',
          display: 'inline-block',
          borderRadius: 12,
          overflow: 'hidden',
          border: '2px solid #d4af37'
        }}>
          <img
            src={currentImage}
            alt="Selected"
            style={{
              width: 200,
              height: 200,
              objectFit: 'cover',
              display: 'block'
            }}
          />

          {!disabled && (
            <button
              onClick={handleRemoveImage}
              style={{
                position: 'absolute',
                top: 8,
                right: 8,
                width: 28,
                height: 28,
                borderRadius: '50%',
                border: 'none',
                background: 'rgba(0,0,0,0.7)',
                color: '#fff',
                cursor: 'pointer',
                fontSize: 14,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'background 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(211,47,47,0.8)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(0,0,0,0.7)';
              }}
              title="Remove image"
            >
              ✕
            </button>
          )}

          <div style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'linear-gradient(transparent, rgba(0,0,0,0.6))',
            color: '#fff',
            padding: '20px 12px 8px 12px',
            fontSize: 12,
            textAlign: 'center'
          }}>
            📷 Image selected
          </div>
        </div>
      ) : (
        // Upload area
        <div
          onClick={() => !disabled && fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            width: 200,
            height: 200,
            border: `2px dashed ${isDragOver ? '#d4af37' : '#ccc'}`,
            borderRadius: 12,
            background: isDragOver ? '#f9f6f1' : '#f8f8f8',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
            opacity: disabled ? 0.6 : 1
          }}
        >
          <div style={{
            fontSize: 32,
            marginBottom: 8,
            color: isDragOver ? '#d4af37' : '#999'
          }}>
            📷
          </div>

          <div style={{
            fontSize: 14,
            fontWeight: 500,
            color: '#666',
            marginBottom: 4,
            textAlign: 'center'
          }}>
            {isDragOver ? 'Drop image here' : 'Click to upload'}
          </div>

          <div style={{
            fontSize: 12,
            color: '#999',
            textAlign: 'center'
          }}>
            or drag and drop
          </div>

          <div style={{
            fontSize: 11,
            color: '#ccc',
            marginTop: 8,
            textAlign: 'center'
          }}>
            Max {maxSizeMB}MB
          </div>
        </div>
      )}

      {uploadError && (
        <div style={{
          marginTop: 8,
          padding: '8px 12px',
          background: '#ffebee',
          border: '1px solid #ffcdd2',
          borderRadius: 8,
          color: '#d32f2f',
          fontSize: 14
        }}>
          {uploadError}
        </div>
      )}
    </div>
  );
}
