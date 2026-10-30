from pathlib import Path
import sys
root=Path(sys.argv[1]);src=Path(__file__).parent
(root/'sdl2test-u/src/main.rs').write_text((src/'main.rs').read_text(encoding='utf-8-sig'),encoding='utf-8')
p=root/'sdl2test-u/Cargo.toml'
s=p.read_text()
if sys.platform == 'win32':
    s=s.replace('features = ["raw-window-handle"]','features = ["raw-window-handle", "bundled", "static-link"]')
p.write_text(s,encoding='utf-8')
# Fixed RNG seed is confined to this diagnostic build. Gameplay builds retain
# their normal randomness. This does not freeze Date or asynchronous loading.
p=root/'core/src/avm_rng.rs'
s=p.read_text(encoding='utf-8')
old='    get_current_date_time().timestamp_micros() as u32'
assert s.count(old)==1
s=s.replace(old,'    std::env::var("H700_CAPTURE_SEED").ok().and_then(|s| s.parse::<u32>().ok()).unwrap_or(12345).max(1)')
p.write_text(s,encoding='utf-8')
# Preserve the exact GLES shaders for an optional GLES context. Desktop mode
# translates only their version/precision declarations at compilation time.
p=root/'sdl2test-u/src/gl_backend.rs'
s=p.read_text(encoding='utf-8')
old='            gl.shader_source(shader, glsl_src);'
assert s.count(old)==1
s=s.replace(old,'''            let desktop = glsl_src.replace("#version 300 es", "#version 330").replace("precision highp float;", "").replace("precision mediump float;", "");
            let source = if std::env::var_os("H700_CAPTURE_GLES").is_some() {glsl_src} else {&desktop};
            let precise = source.replace("uniform sampler2D", "uniform highp sampler2D");
            let source = if std::env::var_os("H700_CAPTURE_PRECISE_SAMPLERS").is_some() {&precise} else {source};
            gl.shader_source(shader, source);''')
# Compare the PBO transfer path with synchronous uploads of identical RGBA
# bytes, without changing any game's content or the console build.
old='''        let mut pbo = match self.acquire_upload_pbo() {'''
assert s.count(old)==1
s=s.replace(old,'''        if std::env::var_os("H700_CAPTURE_DIRECT_UPLOAD").is_some() {
            let mut bytes=vec![0u8;rgba_texture_bytes(region.width(),region.height())];
            write_bitmap_rgba_region_to_slice(&mut bytes,bitmap,texture_width,texture_height,region);
            unsafe {
                self.gl.bind_buffer(glow::PIXEL_UNPACK_BUFFER,None);
                if allocate {
                    self.gl.tex_image_2d(glow::TEXTURE_2D,0,glow::RGBA8 as i32,texture_width as i32,texture_height as i32,0,glow::RGBA,glow::UNSIGNED_BYTE,None);
                }
                self.gl.tex_sub_image_2d(glow::TEXTURE_2D,0,region.x_min as i32,region.y_min as i32,region.width() as i32,region.height() as i32,glow::RGBA,glow::UNSIGNED_BYTE,glow::PixelUnpackData::Slice(&bytes));
            }
            return Ok(());
        }
'''+old)
# Trace the actual source and each cache filter result to locate the first
# stage whose alpha/color differs on Mali. This code is diagnostic-only.
old='''        let mut temp_textures = Vec::new();
        let mut current = destination_texture;'''
assert s.count(old)==1
s=s.replace(old,'''        self.h700_trace_filter(destination_texture,width,height,"source before filters");
'''+old)
old='''            if let Err(error) = step_result {
                result = Err(error);
                break;
            }
        }

        if result.is_ok() && current != destination_texture'''
assert s.count(old)==1
s=s.replace(old,'''            if let Err(error) = step_result {
                result = Err(error);
                break;
            }
            self.h700_trace_filter(current,width,height,&format!("after {filter:?}"));
        }

        if result.is_ok() && current != destination_texture''')
s+='\n'+(src/'filter_trace.rs').read_text(encoding='utf-8')
p.write_text(s,encoding='utf-8')
