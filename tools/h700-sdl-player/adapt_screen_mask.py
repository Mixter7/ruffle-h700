from pathlib import Path

def adapt(root):
    p=root/'sdl2test-u/src/gl_backend.rs'
    s=p.read_text(encoding='utf-8')
    def rep(a,b):
        nonlocal s
        assert s.count(a)==1,(a,s.count(a))
        s=s.replace(a,b)
    rep('    h700_blend_pool: Vec<H700BlendTarget>,','    h700_blend_pool: Vec<H700BlendTarget>,\n    h700_screen_texture: Option<BitmapHandle>,\n    h700_screen_stencil_bits: i32,')
    rep('            h700_blend_pool: Vec::new(),','            h700_blend_pool: Vec::new(),\n            h700_screen_texture: None,\n            h700_screen_stencil_bits: unsafe { gl.get_parameter_i32(0x0D57 /* GL_STENCIL_BITS (GLES) */) },')
    # gl has moved into the struct by this point; query before construction.
    rep('        let mut renderer = Self {','        let h700_screen_stencil_bits = unsafe { gl.get_parameter_i32(0x0D57 /* GL_STENCIL_BITS (GLES) */) };\n        eprintln!("H700 screen stencil bits={h700_screen_stencil_bits}");\n        let mut renderer = Self {')
    rep('            h700_screen_stencil_bits: unsafe { gl.get_parameter_i32(0x0D57 /* GL_STENCIL_BITS (GLES) */) },','            h700_screen_stencil_bits,')
    rep('''    fn render_to_screen(&mut self, clear: Color, commands: CommandList) -> Result<(), BitmapError> {
        let use_stencil = Self::commands_use_stencil(&commands);''','''    fn render_to_screen(&mut self, clear: Color, commands: CommandList) -> Result<(), BitmapError> {
        let use_stencil = Self::commands_use_stencil(&commands);
        if use_stencil && self.h700_screen_stencil_bits == 0 {
            return self.h700_render_screen_via_texture(clear, commands);
        }''')
    s+='''
impl GlRenderBackend {
    fn h700_render_screen_via_texture(&mut self, clear: Color, commands: CommandList) -> Result<(), BitmapError> {
        let w=self.renderbuffer_width.max(1) as u32;
        let h=self.renderbuffer_height.max(1) as u32;
        let resize=self.h700_screen_texture.as_ref().map_or(true,|v| {
            let e=as_registry_data(v);e.width.get()!=w || e.height.get()!=h
        });
        if resize {
            self.h700_screen_texture=Some(self.create_empty_texture(NonZeroU32::new(w).unwrap(),NonZeroU32::new(h).unwrap())?);
            eprintln!("H700 screen: using stencil-backed texture {w}x{h}");
        }
        let target=self.h700_screen_texture.as_ref().unwrap().clone();
        let texture=as_registry_data(&target).texture;
        self.render_to_texture(texture,w,h,Some(if self.is_transparent {Color::from_rgba(0)} else {clear}),commands)?;
        let mut presentation=CommandList::new();
        presentation.render_bitmap(target,Transform::default(),false,PixelSnapping::Never);
        self.render_commands_to_surface(self.screen_surface(clear,false),presentation)
    }
    #[cfg(test)]
    fn h700_test_screen_mask_fallback(&mut self) {
        let mut commands=CommandList::new();
        let mask=Matrix::create_box(8.0,16.0,Twips::ZERO,Twips::ZERO);
        commands.push_mask();commands.draw_rect(Color::WHITE,mask);commands.activate_mask();
        commands.draw_rect(Color::WHITE,Matrix::create_box(16.0,16.0,Twips::ZERO,Twips::ZERO));
        commands.deactivate_mask();commands.draw_rect(Color::WHITE,mask);commands.pop_mask();
        self.h700_render_screen_via_texture(Color::BLACK,commands).unwrap();
        let mut pixels=[0u8;16*16*4];
        unsafe {self.gl.read_pixels(0,0,16,16,glow::RGBA,glow::UNSIGNED_BYTE,glow::PixelPackData::Slice(&mut pixels));}
        assert_eq!(&pixels[(8*16+2)*4..(8*16+2)*4+3],&[255,255,255]);
        assert_eq!(&pixels[(8*16+12)*4..(8*16+12)*4+3],&[0,0,0]);
        assert_eq!(unsafe{self.gl.get_error()},glow::NO_ERROR);
    }
}
'''
    rep('        r.h700_test_recycled_texture_binding();','        r.h700_test_screen_mask_fallback();\n        r.h700_test_recycled_texture_binding();')
    p.write_text(s,encoding='utf-8')
