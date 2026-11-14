const captures = [
  {
    file: "original-r1083.png",
    label: "Original · DOSBox-X R1083",
    alt: "Original R1 corridor and door with help text in the HUD.",
    path: "oracle/R1069-DIOS-Standalone/runs/R1083-menu-capture/captures/r_003.png",
    sha256: "7768f3c193e2f1e529d1a47178e1b4db36afdac3ad12ba4acd6b8d68264c4fe4",
  },
  {
    file: "remaster-r1073.png",
    label: "Remaster · R1073",
    alt: "Remastered R1 corridor and door with system startup messages in the HUD.",
    path: "oracle/R1069-DIOS-Standalone/captures/R1078-packaged-fixed.png",
    sha256: "92d6240305c766e1bd96953851d1905c3bfa73f3d3085e7a901564c5a9fd978c",
  },
] as const;

export function SceneComparison() {
  return <section className="portfolio-evidence" aria-label="Original and remaster scene comparison">
    <div className="portfolio-evidence-heading"><h5>Original and remaster</h5><span className="tag tag-hold">FIDELITY HOLD</span></div>
    <details>
      <summary>Compare R1 corridor captures</summary>
      <div className="scene-comparison">
        {captures.map(capture => <figure key={capture.file}>
          <img src={`./fidelity/openazrael-r1/${capture.file}`} alt={capture.alt} width={640} height={480} loading="lazy"/>
          <figcaption>{capture.label}</figcaption>
        </figure>)}
      </div>
      <p>The original shows help text. The remaster shows system startup messages. Camera position and HUD phase were only partially synchronized.</p>
      <details>
        <summary>Capture sources</summary>
        <p>Comparison report <code>R1083-NATIVE-DOSBOX-FRAMEBUFFER-R1-ORACLE.md</code></p>
        {captures.map(capture => <dl key={capture.file}>
          <dt>{capture.label}</dt>
          <dd><code>{capture.path}</code><br/>SHA-256 <code>{capture.sha256}</code></dd>
        </dl>)}
      </details>
    </details>
  </section>;
}
