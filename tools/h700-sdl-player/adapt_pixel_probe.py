from pathlib import Path

def adapt(root):
    src=Path(__file__).parent
    p=root/'sdl2test-u/src/gl_backend.rs'
    s=p.read_text(encoding='utf-8')
    old='        Ok(renderer)\n    }'
    assert s.count(old)==1
    s=s.replace(old,'        renderer.h700_run_pixel_probe();\n\n'+old)
    s+='\n'+(src/'pixel_probe.rs').read_text(encoding='utf-8-sig')
    # Same checks are also mandatory in the existing GLES CI context.
    old='        let target=r.create_empty_texture(std::num::NonZeroU32::new(16).unwrap(),std::num::NonZeroU32::new(16).unwrap()).unwrap();'
    assert s.count(old)==1
    s=s.replace(old,'        assert!(r.h700_pixel_probe().unwrap().is_empty(), "device pixel probes failed");\n'+old)
    p.write_text(s,encoding='utf-8')
