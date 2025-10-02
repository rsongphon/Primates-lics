/**
 * Primate/Participant Store
 * Non-human primate subject management and welfare tracking
 */

import { create } from 'zustand';
import type { Primate, WelfareCheck } from '@/types';

interface RFIDDetection {
  primate_id: string;
  rfid_tag: string;
  device_id: string;
  detected_at: string;
}

interface PrimateState {
  // Primates
  primates: Primate[];
  selectedPrimate: Primate | null;
  setPrimates: (primates: Primate[]) => void;
  addPrimate: (primate: Primate) => void;
  updatePrimate: (id: string, updates: Partial<Primate>) => void;
  removePrimate: (id: string) => void;
  setSelectedPrimate: (primate: Primate | null) => void;
  getPrimate: (id: string) => Primate | undefined;
  getPrimateByRFID: (rfidTag: string) => Primate | undefined;

  // RFID detection tracking
  recentDetections: RFIDDetection[];
  addDetection: (detection: RFIDDetection) => void;
  clearDetections: () => void;

  // Welfare checks
  welfareChecks: Map<string, WelfareCheck[]>;
  addWelfareCheck: (primateId: string, check: WelfareCheck) => void;
  getWelfareChecks: (primateId: string) => WelfareCheck[];
  getLatestWelfareCheck: (primateId: string) => WelfareCheck | undefined;

  // Session tracking
  activeSessions: Map<string, { device_id: string; experiment_id: string; started_at: string }>;
  startSession: (primateId: string, deviceId: string, experimentId: string) => void;
  endSession: (primateId: string) => void;
  getActiveSession: (primateId: string) => { device_id: string; experiment_id: string; started_at: string } | undefined;

  // Loading and error states
  isLoading: boolean;
  error: string | null;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Utility
  clearPrimates: () => void;
  getActivePrimates: () => Primate[];
  getPrimatesBySpecies: (species: string) => Primate[];
  getPrimatesByTrainingLevel: (minLevel: number, maxLevel: number) => Primate[];
  getPrimatesByOrganization: (orgId: string) => Primate[];
}

export const usePrimateStore = create<PrimateState>((set, get) => ({
  // Initial state
  primates: [],
  selectedPrimate: null,
  recentDetections: [],
  welfareChecks: new Map(),
  activeSessions: new Map(),
  isLoading: false,
  error: null,

  // Primate management
  setPrimates: (primates) => set({ primates }),

  addPrimate: (primate) =>
    set((state) => ({
      primates: [...state.primates, primate],
    })),

  updatePrimate: (id, updates) =>
    set((state) => ({
      primates: state.primates.map((p) =>
        p.id === id ? { ...p, ...updates } : p
      ),
      selectedPrimate:
        state.selectedPrimate?.id === id
          ? { ...state.selectedPrimate, ...updates }
          : state.selectedPrimate,
    })),

  removePrimate: (id) =>
    set((state) => ({
      primates: state.primates.filter((p) => p.id !== id),
      selectedPrimate:
        state.selectedPrimate?.id === id ? null : state.selectedPrimate,
    })),

  setSelectedPrimate: (primate) => set({ selectedPrimate: primate }),

  getPrimate: (id) => get().primates.find((p) => p.id === id),

  getPrimateByRFID: (rfidTag) =>
    get().primates.find((p) => p.rfid_tag === rfidTag),

  // RFID detection tracking
  addDetection: (detection) =>
    set((state) => ({
      recentDetections: [detection, ...state.recentDetections].slice(0, 50), // Keep last 50 detections
    })),

  clearDetections: () => set({ recentDetections: [] }),

  // Welfare checks
  addWelfareCheck: (primateId, check) =>
    set((state) => {
      const newChecksMap = new Map(state.welfareChecks);
      const existingChecks = newChecksMap.get(primateId) || [];
      newChecksMap.set(primateId, [check, ...existingChecks]);

      return { welfareChecks: newChecksMap };
    }),

  getWelfareChecks: (primateId) =>
    get().welfareChecks.get(primateId) || [],

  getLatestWelfareCheck: (primateId) => {
    const checks = get().welfareChecks.get(primateId) || [];
    return checks[0]; // Assuming sorted by most recent first
  },

  // Session tracking
  startSession: (primateId, deviceId, experimentId) =>
    set((state) => {
      const newSessionsMap = new Map(state.activeSessions);
      newSessionsMap.set(primateId, {
        device_id: deviceId,
        experiment_id: experimentId,
        started_at: new Date().toISOString(),
      });

      // Update primate current device and experiment
      const primates = state.primates.map((p) =>
        p.id === primateId
          ? {
              ...p,
              current_device_id: deviceId,
              current_experiment_id: experimentId,
            }
          : p
      );

      return {
        activeSessions: newSessionsMap,
        primates,
      };
    }),

  endSession: (primateId) =>
    set((state) => {
      const newSessionsMap = new Map(state.activeSessions);
      newSessionsMap.delete(primateId);

      // Clear primate current device and experiment
      const primates = state.primates.map((p) =>
        p.id === primateId
          ? {
              ...p,
              current_device_id: undefined,
              current_experiment_id: undefined,
            }
          : p
      );

      return {
        activeSessions: newSessionsMap,
        primates,
      };
    }),

  getActiveSession: (primateId) =>
    get().activeSessions.get(primateId),

  // Loading and error
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  // Utility methods
  clearPrimates: () =>
    set({
      primates: [],
      selectedPrimate: null,
      recentDetections: [],
      welfareChecks: new Map(),
      activeSessions: new Map(),
    }),

  getActivePrimates: () =>
    get().primates.filter((p) => p.is_active),

  getPrimatesBySpecies: (species) =>
    get().primates.filter((p) => p.species === species),

  getPrimatesByTrainingLevel: (minLevel, maxLevel) =>
    get().primates.filter(
      (p) => p.training_level >= minLevel && p.training_level <= maxLevel
    ),

  getPrimatesByOrganization: (orgId) =>
    get().primates.filter((p) => p.organization_id === orgId),
}));
