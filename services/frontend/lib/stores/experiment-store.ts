/**
 * Experiment Store
 * Experiment management and real-time progress tracking
 */

import { create } from 'zustand';
import type { Experiment, ExperimentState as ExperimentStatus } from '@/types';

interface ExperimentProgress {
  experiment_id: string;
  current_trial: number;
  total_trials: number;
  success_rate: number;
  last_update: string;
}

interface ExperimentState {
  // Experiments
  experiments: Experiment[];
  selectedExperiment: Experiment | null;
  setExperiments: (experiments: Experiment[]) => void;
  addExperiment: (experiment: Experiment) => void;
  updateExperiment: (id: string, updates: Partial<Experiment>) => void;
  removeExperiment: (id: string) => void;
  setSelectedExperiment: (experiment: Experiment | null) => void;
  getExperiment: (id: string) => Experiment | undefined;

  // Progress tracking
  experimentProgress: Map<string, ExperimentProgress>;
  updateExperimentProgress: (experimentId: string, progress: ExperimentProgress) => void;
  getExperimentProgress: (experimentId: string) => ExperimentProgress | undefined;

  // State management
  updateExperimentState: (experimentId: string, state: ExperimentStatus) => void;

  // Loading and error states
  isLoading: boolean;
  error: string | null;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Utility
  clearExperiments: () => void;
  getActiveExperiments: () => Experiment[];
  getExperimentsByDevice: (deviceId: string) => Experiment[];
  getExperimentsByPrimate: (primateId: string) => Experiment[];
  getExperimentsByOrganization: (orgId: string) => Experiment[];
}

export const useExperimentStore = create<ExperimentState>((set, get) => ({
  // Initial state
  experiments: [],
  selectedExperiment: null,
  experimentProgress: new Map(),
  isLoading: false,
  error: null,

  // Experiment management
  setExperiments: (experiments) => set({ experiments }),

  addExperiment: (experiment) =>
    set((state) => ({
      experiments: [...state.experiments, experiment],
    })),

  updateExperiment: (id, updates) =>
    set((state) => ({
      experiments: state.experiments.map((e) =>
        e.id === id ? { ...e, ...updates } : e
      ),
      selectedExperiment:
        state.selectedExperiment?.id === id
          ? { ...state.selectedExperiment, ...updates }
          : state.selectedExperiment,
    })),

  removeExperiment: (id) =>
    set((state) => ({
      experiments: state.experiments.filter((e) => e.id !== id),
      selectedExperiment:
        state.selectedExperiment?.id === id ? null : state.selectedExperiment,
    })),

  setSelectedExperiment: (experiment) => set({ selectedExperiment: experiment }),

  getExperiment: (id) => get().experiments.find((e) => e.id === id),

  // Progress tracking
  updateExperimentProgress: (experimentId, progress) =>
    set((state) => {
      const newProgressMap = new Map(state.experimentProgress);
      newProgressMap.set(experimentId, progress);

      return { experimentProgress: newProgressMap };
    }),

  getExperimentProgress: (experimentId) =>
    get().experimentProgress.get(experimentId),

  // State management
  updateExperimentState: (experimentId, state: ExperimentStatus) =>
    set((prevState) => ({
      experiments: prevState.experiments.map((e) =>
        e.id === experimentId
          ? {
              ...e,
              state,
              ...(state === 'running' && !e.actual_start
                ? { actual_start: new Date().toISOString() }
                : {}),
              ...(state === 'completed' && !e.actual_end
                ? { actual_end: new Date().toISOString() }
                : {}),
            }
          : e
      ),
      selectedExperiment:
        prevState.selectedExperiment?.id === experimentId
          ? {
              ...prevState.selectedExperiment,
              state,
              ...(state === 'running' && !prevState.selectedExperiment.actual_start
                ? { actual_start: new Date().toISOString() }
                : {}),
              ...(state === 'completed' && !prevState.selectedExperiment.actual_end
                ? { actual_end: new Date().toISOString() }
                : {}),
            }
          : prevState.selectedExperiment,
    })),

  // Loading and error
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  // Utility methods
  clearExperiments: () =>
    set({
      experiments: [],
      selectedExperiment: null,
      experimentProgress: new Map(),
    }),

  getActiveExperiments: () =>
    get().experiments.filter(
      (e) => e.state === 'running' || e.state === 'paused'
    ),

  getExperimentsByDevice: (deviceId) =>
    get().experiments.filter((e) => e.device_id === deviceId),

  getExperimentsByPrimate: (primateId) =>
    get().experiments.filter((e) => e.primate_id === primateId),

  getExperimentsByOrganization: (orgId) =>
    get().experiments.filter((e) => e.organization_id === orgId),
}));
