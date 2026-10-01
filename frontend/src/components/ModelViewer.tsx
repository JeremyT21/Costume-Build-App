import { Bounds, Center, OrbitControls } from '@react-three/drei';
import { Canvas, useLoader } from '@react-three/fiber';
import { Pause, Play, RotateCcw } from 'lucide-react';
import { Suspense, useMemo, useRef, useState } from 'react';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { toCreasedNormals } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

import { motionEnabled } from '../motion';

const CREASE_ANGLE = Math.PI / 6;

interface ModelViewerProps {
  url: string;
  color?: string;
}

function StlMesh({ url, color }: ModelViewerProps) {
  const raw = useLoader(STLLoader, url);
  // Smooth curved surfaces while keeping sharp edges crisp.
  const geometry = useMemo(() => toCreasedNormals(raw, CREASE_ANGLE), [raw]);
  return (
    // STL files are Z-up; rotate so the part stands upright.
    <mesh geometry={geometry} rotation={[-Math.PI / 2, 0, 0]} castShadow receiveShadow>
      <meshStandardMaterial color={color} metalness={0.35} roughness={0.42} />
    </mesh>
  );
}

/** Interactive STL preview: drag to rotate, scroll to zoom, right-drag to pan. */
export function ModelViewer({ url, color = '#a7afbf' }: ModelViewerProps) {
  const [spinning, setSpinning] = useState(motionEnabled);
  const controls = useRef<OrbitControlsImpl>(null);

  return (
    <div className="viewer">
      <Canvas camera={{ position: [260, 200, 320], fov: 40, near: 1, far: 10000 }} dpr={[1, 2]}>
        <hemisphereLight args={['#ffffff', '#3a3f4b', 0.9]} />
        <directionalLight position={[300, 500, 300]} intensity={1.6} />
        <directionalLight position={[-400, 200, -200]} intensity={0.6} />
        <Suspense fallback={null}>
          <Bounds fit clip observe margin={1.25}>
            <Center>
              <StlMesh url={url} color={color} />
            </Center>
          </Bounds>
        </Suspense>
        <OrbitControls
          ref={controls}
          makeDefault
          autoRotate={spinning}
          autoRotateSpeed={1.2}
          enableDamping={motionEnabled()}
          dampingFactor={0.08}
        />
      </Canvas>
      <span className="viewer-hint">Drag to rotate, scroll to zoom</span>
      <div className="viewer-controls">
        <button
          type="button"
          className="btn btn-sm icon-btn"
          aria-label={spinning ? 'Pause rotation' : 'Auto-rotate'}
          onClick={() => setSpinning((s) => !s)}
        >
          {spinning ? <Pause size={14} /> : <Play size={14} />}
        </button>
        <button
          type="button"
          className="btn btn-sm icon-btn"
          aria-label="Reset view"
          onClick={() => controls.current?.reset()}
        >
          <RotateCcw size={14} />
        </button>
      </div>
    </div>
  );
}
