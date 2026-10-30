struct H700BlendTarget {
    gl: Arc<glow::Context>,
    source: glow::Texture,
    backdrop: glow::Texture,
    fbo: glow::Framebuffer,
    stencil: glow::Renderbuffer,
    width: i32,
    height: i32,
}
impl Drop for H700BlendTarget {
    fn drop(&mut self) { unsafe {
        self.gl.delete_texture(self.source); self.gl.delete_texture(self.backdrop);
        self.gl.delete_framebuffer(self.fbo); self.gl.delete_renderbuffer(self.stencil);
    }}
}
impl GlRenderBackend {
    fn h700_acquire_blend_target(&mut self,w:i32,h:i32)->Result<H700BlendTarget,BitmapError> {
        if let Some(i)=self.h700_blend_pool.iter().position(|t|t.width==w && t.height==h) {
            return Ok(self.h700_blend_pool.swap_remove(i));
        }
        let source=self.create_filter_texture(w as u32,h as u32)?;
        let backdrop=match self.create_filter_texture(w as u32,h as u32) { Ok(t)=>t,Err(e)=>{unsafe{self.gl.delete_texture(source)};return Err(e);} };
        unsafe {
            let fbo=match self.gl.create_framebuffer(){Ok(v)=>v,Err(e)=>{self.gl.delete_texture(source);self.gl.delete_texture(backdrop);return Err(BitmapError::Unimplemented(e.into()));}};
            let stencil=match self.gl.create_renderbuffer(){Ok(v)=>v,Err(e)=>{self.gl.delete_texture(source);self.gl.delete_texture(backdrop);self.gl.delete_framebuffer(fbo);return Err(BitmapError::Unimplemented(e.into()));}};
            let target=H700BlendTarget {gl:self.gl.clone(),source,backdrop,fbo,stencil,width:w,height:h};
            let parent=std::num::NonZeroU32::new(self.gl.get_parameter_i32(glow::FRAMEBUFFER_BINDING) as u32).map(glow::NativeFramebuffer);
            self.gl.bind_framebuffer(glow::FRAMEBUFFER,Some(fbo));
            self.gl.framebuffer_texture_2d(glow::FRAMEBUFFER,glow::COLOR_ATTACHMENT0,glow::TEXTURE_2D,Some(source),0);
            self.gl.bind_renderbuffer(glow::RENDERBUFFER,Some(stencil));
            self.gl.renderbuffer_storage(glow::RENDERBUFFER,glow::STENCIL_INDEX8,w,h);
            self.gl.framebuffer_renderbuffer(glow::FRAMEBUFFER,glow::STENCIL_ATTACHMENT,glow::RENDERBUFFER,Some(stencil));
            let status=self.gl.check_framebuffer_status(glow::FRAMEBUFFER);
            self.gl.bind_framebuffer(glow::FRAMEBUFFER,parent);
            if status!=glow::FRAMEBUFFER_COMPLETE { return Err(BitmapError::Unimplemented(format!("blend framebuffer incomplete: {status:#x}").into())); }
            Ok(target)
        }
    }
    fn h700_composite_blend(&mut self,commands:CommandList,mode:swf::BlendMode) {
        let w=self.renderbuffer_width.max(1);let h=self.renderbuffer_height.max(1);
        let target=match self.h700_acquire_blend_target(w,h){Ok(t)=>t,Err(e)=>{h700_report_render_error(&format!("blend allocation: {e}"));commands.execute(self);return;}};
        let mask=self.mask_state;let masks=self.num_masks;
        let saved=self.save_surface_state();
        unsafe {
            let parent=std::num::NonZeroU32::new(self.gl.get_parameter_i32(glow::FRAMEBUFFER_BINDING) as u32).map(glow::NativeFramebuffer);
            let scissor=self.gl.is_enabled(glow::SCISSOR_TEST);
            // Copy the backdrop on the GPU; never read pixels back to the CPU.
            self.gl.active_texture(glow::TEXTURE0);
            self.gl.bind_texture(glow::TEXTURE_2D,Some(target.backdrop));
            self.gl.copy_tex_sub_image_2d(glow::TEXTURE_2D,0,0,0,0,0,w,h);
            self.active_texture_2d.set(None);
            self.gl.bind_framebuffer(glow::FRAMEBUFFER,Some(target.fbo));
            self.gl.viewport(0,0,w,h);
            self.gl.disable(glow::SCISSOR_TEST);
            self.reset_render_state();
            self.gl.stencil_mask(0xff);
            self.gl.clear_color(0.0,0.0,0.0,0.0);
            self.gl.clear(glow::COLOR_BUFFER_BIT|glow::STENCIL_BUFFER_BIT);
            // Preserve the parent's view matrix: both textures use the same orientation.
            commands.execute(self);
            self.gl.bind_framebuffer(glow::FRAMEBUFFER,parent);
            self.restore_surface_state(saved);
            self.mask_state=mask;self.num_masks=masks;self.mask_state_dirty=true;
            self.set_stencil_state();
            if scissor { self.gl.enable(glow::SCISSOR_TEST); }
            self.gl.disable(glow::BLEND);
            let program=&self.h700_blend_program;
            self.gl.use_program(Some(program.program));
            self.gl.bind_vertex_array(Some(self.h700_blend_vao));
            self.bind_texture_unit(0,target.source);
            self.bind_texture_unit(1,target.backdrop);
            self.gl.uniform_1_i32(program.uniform("source_image"),0);
            self.gl.uniform_1_i32(program.uniform("backdrop_image"),1);
            self.gl.uniform_2_f32(program.uniform("image_size"),w as f32,h as f32);
            self.gl.uniform_1_i32(program.uniform("blend_mode"),mode as i32);
            self.gl.draw_arrays(glow::TRIANGLES,0,3);
            self.gl.active_texture(glow::TEXTURE0);
            self.gl.enable(glow::BLEND);
            let blend=self.blend_modes.last().cloned().unwrap_or(RenderBlendMode::Builtin(swf::BlendMode::Normal));
            self.apply_blend_mode(blend);
        }
        self.active_program=std::ptr::null();self.active_gradient=std::ptr::null();self.active_bitmap_draw=std::ptr::null();
        self.mult_color=None;self.add_color=None;self.active_texture_2d.set(None);self.active_vertex_array.set(None);
        // Bound retained memory; nested groups release their own targets independently.
        let bytes=self.h700_blend_pool.iter().map(|t|t.width as u64*t.height as u64*9).sum::<u64>();
        if self.h700_blend_pool.len()<4 && bytes+w as u64*h as u64*9<=32*1024*1024 {self.h700_blend_pool.push(target);}
    }
}
