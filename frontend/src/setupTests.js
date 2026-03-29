import '@testing-library/jest-dom'

// Mock Three.js WebGL context — jsdom has no WebGL support
vi.mock('three', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    WebGLRenderer: vi.fn().mockImplementation(() => ({
      setSize: vi.fn(),
      setPixelRatio: vi.fn(),
      render: vi.fn(),
      dispose: vi.fn(),
      domElement: document.createElement('canvas'),
    })),
  }
})

// Mock @react-three/fiber Canvas so tests don't need WebGL
vi.mock('@react-three/fiber', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    Canvas: ({ children }) => <div data-testid="r3f-canvas">{children}</div>,
    useFrame: vi.fn(),
    useThree: vi.fn(() => ({ gl: {}, scene: {}, camera: {} })),
  }
})

// Mock @react-three/drei
vi.mock('@react-three/drei', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    OrbitControls: () => null,
  }
})
