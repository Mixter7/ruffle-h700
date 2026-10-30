from pathlib import Path

def adapt(root):
    shaders=root/'sdl2test-u/shaders'
    for name in ['filter_common.vert','filter_blur.vert','filter_glow.vert',
                 'filter_bevel.vert','filter_displacement_map.vert']:
        path=shaders/name
        source=path.read_text(encoding='utf-8')
        bad='    gl_Position.y = 1.0 - gl_Position.y;'
        assert source.count(bad)==1, name
        # These quads and their texture coordinates both span [0,1]. Offscreen
        # textures use the same bottom-origin convention. The preceding *2-1
        # already covers clip space [-1,1]; subtracting it from 1 covers [0,2],
        # clips half the quad and leaves part of pooled textures unwritten.
        source=source.replace(bad,'    // Offscreen position and UV share the same orientation.')
        path.write_text(source,encoding='utf-8')
    backend=root/'sdl2test-u/src/gl_backend.rs'
    source=backend.read_text(encoding='utf-8')
    source+='\n'+(Path(__file__).with_name('filter_coordinate_tests.rs')).read_text(encoding='utf-8')
    backend.write_text(source,encoding='utf-8')
