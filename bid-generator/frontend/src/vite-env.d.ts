/// <reference types="vite/client" />
declare global {
  interface Window {
    electronAPI: {
      getBackendUrl: () => Promise<string>;
      isBackendRunning: () => Promise<boolean>;
      openFileDialog: (options?: any) => Promise<any>;
      openDirectoryDialog: () => Promise<string | null>;
      getUserDataPath: () => Promise<string>;
      openExternal: (url: string) => Promise<void>;
      minimizeWindow: () => Promise<void>;
      maximizeWindow: () => Promise<void>;
      closeWindow: () => Promise<void>;
      onBackendStatusChanged: (callback: (status: 'running' | 'stopped' | 'error') => void) => () => void;
    };
  }
}
export {}
