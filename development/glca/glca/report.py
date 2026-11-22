"""Read-only Studio-compatible evidence view. No commands or admission endpoint."""
from html import escape

VIEWS = ('Game Logic', 'World Map', 'Puzzle Dependencies', 'Completion Paths',
         'Softlock Analysis', 'Fidelity Validation')


def render(pilot, world, backwards):
    e = lambda value: escape(str(value), quote=True)
    descriptions = [
        f"Source only: {pilot['decoded_program_records']} decoded program records; victory predicate UNKNOWN.",
        f"{len(world['rooms'])} rooms with catalogued objects. Room adjacency and traversability remain unverified.",
        f"{len(backwards['possible_prerequisite_programs'])} possible predecessor programs from direct call references; guards unresolved.",
        'HOLD: no proven original ending or legal full-game completion path.',
        f"{pilot['r49_static_candidates']} broad static candidates; zero confirmed softlocks. Intended original dead ends must be preserved.",
        'HOLD: no aligned authentic reference/remaster trace pair. Save/load, ownership, actor handoff and timing remain unverified.',
    ]
    sections = ''.join(f'<section id="view-{i}"><h2>{e(name)}</h2><p>{e(description)}</p></section>'
                       for i, (name, description) in enumerate(zip(VIEWS, descriptions)))
    links = ''.join(f'<a href="#view-{i}">{e(name)}</a> ' for i, name in enumerate(VIEWS))
    rooms = ', '.join(e(room) for room in world['rooms'])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>OpenZak — Game Logic</title><style>
body{{font:17px system-ui,sans-serif;max-width:960px;margin:auto;padding:24px;background:#111827;color:#f3f4f6}}
a{{color:#93c5fd;display:inline-block;padding:8px}}a:focus{{outline:3px solid #fbbf24}}
section{{padding:12px 0;border-bottom:1px solid #4b5563}}p{{line-height:1.6}}
summary{{cursor:pointer}}code{{overflow-wrap:anywhere}}
</style><h1>OpenZak — Game Logic</h1>
<p><strong>HOLD · Source analysis only · Isolated shadow evaluation</strong></p>
<p>This local report is a staged evidence view for Studio integration. It cannot run tasks or authorize releases.</p>
<nav aria-label="Game logic views">{links}</nav><main>{sections}
<details><summary>Developer Mode diagnostics</summary>
<p>Candidate system operations: SC139:1863, SC153:1068. Neither is a verified victory script.</p>
<p>Room IDs: {rooms}</p><p>CFG uncertainties: {e(pilot['cfg_unknowns'])}.</p>
</details></main></html>'''
