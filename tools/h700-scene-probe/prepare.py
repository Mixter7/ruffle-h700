from pathlib import Path
import sys
root=Path(sys.argv[1]);src=Path(__file__).parent
(root/'sdl2test-u/src/main.rs').write_text((src/'main.rs').read_text(encoding='utf-8-sig'),encoding='utf-8')
p=root/'sdl2test-u/Cargo.toml'
s=p.read_text().replace('features = ["raw-window-handle"]','features = ["raw-window-handle", "bundled", "static-link"]')
p.write_text(s,encoding='utf-8')
# Only the Windows analysis copy gets desktop GLSL; H700 shaders stay untouched.
for p in list((root/'sdl2test-u/shaders').glob('*'))+[root/'sdl2test-u/src/gl_backend.rs']:
    s=p.read_text(encoding='utf-8').replace('#version 300 es','#version 330').replace('precision highp float;','').replace('precision mediump float;','')
    p.write_text(s,encoding='utf-8')
