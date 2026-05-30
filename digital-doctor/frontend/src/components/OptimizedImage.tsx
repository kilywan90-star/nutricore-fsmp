import { useState } from 'react';
import { Skeleton } from 'antd';

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number | string;
  height?: number | string;
  className?: string;
  style?: React.CSSProperties;
  lazy?: boolean;
  placeholderHeight?: number;
}

export default function OptimizedImage({
  src,
  alt,
  width,
  height,
  className,
  style,
  lazy = true,
  placeholderHeight = 200,
}: OptimizedImageProps) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div
        style={{
          width,
          height: height || placeholderHeight,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f5f5f5',
          color: '#bbb',
          borderRadius: 4,
          ...style,
        }}
      >
        图片加载失败
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', display: 'inline-block', ...style }}>
      {!loaded && (
        <Skeleton.Image
          active
          style={{
            width: width || '100%',
            height: height || placeholderHeight,
          }}
        />
      )}
      <img
        src={src}
        alt={alt}
        width={width}
        height={height}
        className={className}
        loading={lazy ? 'lazy' : undefined}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
        style={{
          display: loaded ? 'inline-block' : 'none',
          objectFit: 'cover',
        }}
      />
    </div>
  );
}
