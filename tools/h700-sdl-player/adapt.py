from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'sdl2test-u/src/main.rs'
s=p.read_text(encoding='utf-8')
def rep(old,new):
    global s
    assert s.count(old)==1,(old,s.count(old))
    s=s.replace(old,new)
rep('gl_attr.set_context_profile(GLProfile::Core);','gl_attr.set_context_profile(GLProfile::GLES);')
rep('gl_attr.set_context_version(4, 1);','gl_attr.set_context_version(3, 0);\n    gl_attr.set_stencil_size(8);\n    gl_attr.set_double_buffer(true);')
rep('.window("Ruffle SDL2 Player", width, height)','.window("H7Flash SDL experimental", width, height)\n        .fullscreen_desktop()')
rep('    let (sender, receiver) = mpsc::channel::<RuffleEvent>();','''    use glow::HasContext;
    unsafe {
        println!("H700 SDL driver={} renderer={} version={}", video_subsystem.current_video_driver(), gl.get_parameter_string(glow::RENDERER), gl.get_parameter_string(glow::VERSION));
    }
    let _ = video_subsystem.gl_set_swap_interval(sdl2::video::SwapInterval::VSync);
    let (sender, receiver) = mpsc::channel::<RuffleEvent>();''')
rep('                                dpad2wasd = !dpad2wasd;\n                                backbtn_pressed = false;', "                                break 'running;")
rep('use ruffle_video_external::backend::ExternalVideoBackend;','')
# Full-sized textures even at low quality: do not confuse resolution reduction with speedup.
g=root/'sdl2test-u/src/gl_backend.rs'
t=g.read_text(encoding='utf-8')
old='''        match self.quality {
            StageQuality::Low => 0.5,
            StageQuality::Medium => 0.75,
            _ => 1.0,
        }'''
assert t.count(old)==1
g.write_text(t.replace(old,'        1.0'),encoding='utf-8')
# Avoid unbounded debug output in gameplay. Keep errors and explicit startup diagnostics.
s=s.replace('println!("按钮按下: {:?}", button);','').replace('println!("按钮释放: {:?}", button);','')
p.write_text(s,encoding='utf-8')
c=root/'sdl2test-u/Cargo.toml'
c.write_text(c.read_text(encoding='utf-8').replace('ruffle_video_external = { path = "../video/external" }',''),encoding='utf-8')
print('H700 SDL/GLES3 adaptation applied; full-size textures, SELECT+START exit.')
