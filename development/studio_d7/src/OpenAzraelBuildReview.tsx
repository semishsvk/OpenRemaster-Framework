import {BuildStatusOverview} from "./BuildStatusOverview";
import {SceneComparison} from "./SceneComparison";

const archivedSource = {
  projectId: "OpenAzrael",
  checkpoint: "candidate-v205-iter2",
  sourceRelativePath: "OpenAzrael/builds/20261007-195229__LEGACY-MIGRATION__OpenAzrael-build/candidate-v205-iter2/ACCEPTANCE.json",
  sourceSha256: "16ed66f786a84a8c19285aaa4547c78a1c498e03e8752fca15cd30fcaf25ca3a",
};

export function OpenAzraelBuildReview({projects}: {projects: readonly {id: string}[]}) {
  if (!projects.some(project => project.id === archivedSource.projectId)) return null;

  return <details className="panel openazrael-build-review">
    <summary>OpenAzrael build review</summary>
    <BuildStatusOverview records={[archivedSource]}/>
    <SceneComparison/>
  </details>;
}
