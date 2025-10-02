/**
 * Task Store
 * Task builder and template management
 */

import { create } from 'zustand';
import type { Task, TaskExecution } from '@/types';

interface TaskBuilderState {
  // Visual flow editor state
  nodes: Array<{
    id: string;
    type: string;
    position: { x: number; y: number };
    data: Record<string, unknown>;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type?: string;
  }>;
}

interface TaskState {
  // Tasks
  tasks: Task[];
  selectedTask: Task | null;
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  setSelectedTask: (task: Task | null) => void;
  getTask: (id: string) => Task | undefined;

  // Task builder
  builderState: TaskBuilderState;
  setBuilderState: (state: TaskBuilderState) => void;
  updateBuilderNodes: (
    nodes: TaskBuilderState['nodes']
  ) => void;
  updateBuilderEdges: (
    edges: TaskBuilderState['edges']
  ) => void;
  clearBuilder: () => void;

  // Task execution tracking
  executions: TaskExecution[];
  addExecution: (execution: TaskExecution) => void;
  updateExecution: (id: string, updates: Partial<TaskExecution>) => void;
  getExecutionsByTask: (taskId: string) => TaskExecution[];

  // Templates
  templates: Task[];
  setTemplates: (templates: Task[]) => void;
  getTemplatesByCategory: (category: string) => Task[];

  // Loading and error states
  isLoading: boolean;
  error: string | null;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Utility
  clearTasks: () => void;
  getPublishedTasks: () => Task[];
  getTasksByOrganization: (orgId: string) => Task[];
}

export const useTaskStore = create<TaskState>((set, get) => ({
  // Initial state
  tasks: [],
  selectedTask: null,
  builderState: {
    nodes: [],
    edges: [],
  },
  executions: [],
  templates: [],
  isLoading: false,
  error: null,

  // Task management
  setTasks: (tasks) => set({ tasks }),

  addTask: (task) =>
    set((state) => ({
      tasks: [...state.tasks, task],
    })),

  updateTask: (id, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) => (t.id === id ? { ...t, ...updates } : t)),
      selectedTask:
        state.selectedTask?.id === id
          ? { ...state.selectedTask, ...updates }
          : state.selectedTask,
    })),

  removeTask: (id) =>
    set((state) => ({
      tasks: state.tasks.filter((t) => t.id !== id),
      selectedTask: state.selectedTask?.id === id ? null : state.selectedTask,
    })),

  setSelectedTask: (task) => set({ selectedTask: task }),

  getTask: (id) => get().tasks.find((t) => t.id === id),

  // Task builder
  setBuilderState: (state) => set({ builderState: state }),

  updateBuilderNodes: (nodes) =>
    set((state) => ({
      builderState: { ...state.builderState, nodes },
    })),

  updateBuilderEdges: (edges) =>
    set((state) => ({
      builderState: { ...state.builderState, edges },
    })),

  clearBuilder: () =>
    set({
      builderState: {
        nodes: [],
        edges: [],
      },
    }),

  // Task execution tracking
  addExecution: (execution) =>
    set((state) => ({
      executions: [...state.executions, execution],
    })),

  updateExecution: (id, updates) =>
    set((state) => ({
      executions: state.executions.map((e) =>
        e.id === id ? { ...e, ...updates } : e
      ),
    })),

  getExecutionsByTask: (taskId) =>
    get().executions.filter((e) => e.task_id === taskId),

  // Templates
  setTemplates: (templates) => set({ templates }),

  getTemplatesByCategory: (category) =>
    get().templates.filter(
      (t) => t.task_metadata?.category === category
    ),

  // Loading and error
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  // Utility methods
  clearTasks: () =>
    set({
      tasks: [],
      selectedTask: null,
      executions: [],
    }),

  getPublishedTasks: () =>
    get().tasks.filter((t) => t.is_published),

  getTasksByOrganization: (orgId) =>
    get().tasks.filter((t) => t.organization_id === orgId),
}));
