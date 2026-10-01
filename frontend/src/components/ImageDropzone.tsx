import { Camera, ImagePlus, X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

interface ImageDropzoneProps {
  files: File[];
  onChange: (files: File[]) => void;
  max?: number;
  label?: string;
}

export function ImageDropzone({
  files,
  onChange,
  max = 8,
  label = 'Drop character images here',
}: ImageDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const previews = useMemo(() => files.map((file) => URL.createObjectURL(file)), [files]);

  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews]);

  function add(list: FileList | null) {
    if (!list) return;
    const images = Array.from(list).filter((file) => file.type.startsWith('image/'));
    onChange([...files, ...images].slice(0, max));
  }

  return (
    <div className="field">
      <div
        className={`dropzone${dragging ? ' dragging' : ''}`}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          add(e.dataTransfer.files);
        }}
      >
        <span className="empty-icon">
          <ImagePlus size={22} />
        </span>
        <strong>{label}</strong>
        <span className="faint">or click to browse. Up to {max} PNG, JPG, or WEBP images.</span>
        <input
          ref={inputRef}
          hidden
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => add(e.target.files)}
        />
      </div>
      <div className="row">
        <button type="button" className="btn btn-sm" onClick={() => cameraRef.current?.click()}>
          <Camera size={14} /> Take a photo
        </button>
        <input
          ref={cameraRef}
          hidden
          type="file"
          accept="image/*"
          capture="environment"
          onChange={(e) => add(e.target.files)}
        />
      </div>
      {files.length > 0 && (
        <div className="thumb-strip">
          {previews.map((url, index) => (
            <div className="thumb" key={url}>
              <img src={url} alt={files[index].name} />
              <button
                type="button"
                aria-label={`Remove ${files[index].name}`}
                onClick={() => onChange(files.filter((_, i) => i !== index))}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
