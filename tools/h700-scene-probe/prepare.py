from pathlib import Path
import sys
root=Path(sys.argv[1]);src=Path(__file__).parent
(root/'sdl2test-u/src/main.rs').write_text((src/'main.rs').read_text(encoding='utf-8-sig'),encoding='utf-8')
p=root/'sdl2test-u/Cargo.toml'
s=p.read_text().replace('features = ["raw-window-handle"]','features = ["raw-window-handle", "bundled", "static-link"]')
p.write_text(s,encoding='utf-8')
# Preserve the exact GLES shaders for an optional GLES context. Desktop mode
# translates only their version/precision declarations at compilation time.
p=root/'sdl2test-u/src/gl_backend.rs'
s=p.read_text(encoding='utf-8')
old='            gl.shader_source(shader, glsl_src);'
assert s.count(old)==1
s=s.replace(old,'''            let desktop = glsl_src.replace("#version 300 es", "#version 330").replace("precision highp float;", "").replace("precision mediump float;", "");
            let source = if std::env::var_os("H700_CAPTURE_GLES").is_some() {glsl_src} else {&desktop};
            gl.shader_source(shader, source);''')
p.write_text(s,encoding='utf-8')
