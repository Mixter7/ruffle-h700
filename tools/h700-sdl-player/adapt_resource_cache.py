from pathlib import Path

def adapt(root):
    p=root/'sdl2test-u/src/gl_backend.rs'
    s=p.read_text(encoding='utf-8')
    # A deleted texture name may be returned again by glGenTextures. A cache hit
    # is not proof that this newly generated name has ever been bound.
    for marker in ['    fn register_bitmap(', '    fn create_empty_texture(']:
        start=s.index(marker)
        pos=s.index('        self.bind_texture_2d(texture);',start)
        s=s[:pos]+s[pos:].replace('        self.bind_texture_2d(texture);','        self.h700_bind_fresh_texture(texture);',1)
    old='            self.bind_vertex_array(Some(vao));\n            Ok(vao)'
    assert s.count(old)==1
    s=s.replace(old,'            self.active_vertex_array.set(None);\n'+old)
    old='''    fn collect_released_resources(&mut self) {
        self.texture_resources'''
    new='''    fn collect_released_resources(&mut self) {
        if self.texture_resources.iter().any(|r| r.weak.strong_count() == 0) {
            self.active_texture_2d.set(None);
        }
        self.texture_resources'''
    assert s.count(old)==1
    s=s.replace(old,new)
    s+='''
impl GlRenderBackend {
    fn h700_bind_fresh_texture(&self, texture: glow::Texture) {
        self.active_texture_2d.set(None);
        self.bind_texture_2d(texture);
    }
    #[cfg(test)]
    fn h700_test_recycled_texture_binding(&mut self) {
        unsafe {
            self.gl.active_texture(glow::TEXTURE0);
            self.gl.bind_texture(glow::TEXTURE_2D, None);
            let texture = self.gl.create_texture().unwrap();
            // Deterministically reproduce the cache left by a deleted object,
            // even on drivers whose glGenTextures does not reuse IDs quickly.
            self.active_texture_2d.set(Some(texture));
            self.bind_texture_2d(texture);
            assert_eq!(self.gl.get_parameter_i32(glow::TEXTURE_BINDING_2D), 0,
                "the legacy cached bind must reproduce the skipped binding");
            self.h700_bind_fresh_texture(texture);
            assert!(self.gl.is_texture(texture));
            assert_ne!(self.gl.get_parameter_i32(glow::TEXTURE_BINDING_2D), 0);
            self.gl.delete_texture(texture);
            self.active_texture_2d.set(None);
        }
    }
}
'''
    old='        assert!(r.h700_pixel_probe().unwrap().is_empty(), "device pixel probes failed");'
    assert s.count(old)==1
    s=s.replace(old,'        r.h700_test_recycled_texture_binding();\n'+old)
    p.write_text(s,encoding='utf-8')
