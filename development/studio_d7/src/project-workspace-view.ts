import {projectState, type ProjectInput, type ProjectState} from './unified-project-state';
export type ProjectObservationView = {input: ProjectInput; key: string};
/** Runs during render, before effects can clear a previous selection. */
export function projectWorkspaceView(view: ProjectObservationView | null, selectedKey: string | null, now: number): ProjectState | null {
  if (!view || !selectedKey || view.key !== selectedKey) return null;
  return projectState(view.input, now, 5_000);
}
