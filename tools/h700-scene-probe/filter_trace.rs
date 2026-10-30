// Diagnostic builds only: bounded intermediate RGBA snapshots. Never included
// in the gameplay binary and never used to measure gameplay performance.
impl GlRenderBackend {
    fn h700_trace_filter(&self, texture: glow::Texture, width: u32, height: u32, label: &str) {
        use std::sync::atomic::{AtomicUsize,Ordering};
        static COUNT: AtomicUsize=AtomicUsize::new(0);
        static BYTES: AtomicUsize=AtomicUsize::new(0);
        let Some(folder)=std::env::var_os("H700_FILTER_TRACE") else {return;};
        let bytes=width as usize*height as usize*4;
        if bytes==0 || bytes>16*1024*1024 {return;}
        let index=COUNT.fetch_add(1,Ordering::Relaxed);
        if index>=96 {return;}
        let previous=BYTES.fetch_add(bytes,Ordering::Relaxed);
        if previous+bytes>64*1024*1024 {return;}
        let result=(|| -> Result<(),String> {
            let mut pixels=vec![0u8;bytes];
            unsafe {
                let old_fbo=std::num::NonZeroU32::new(self.gl.get_parameter_i32(glow::READ_FRAMEBUFFER_BINDING) as u32).map(glow::NativeFramebuffer);
                let old_pack=std::num::NonZeroU32::new(self.gl.get_parameter_i32(glow::PIXEL_PACK_BUFFER_BINDING) as u32).map(glow::NativeBuffer);
                let fbo=self.gl.create_framebuffer()?;
                self.gl.bind_framebuffer(glow::READ_FRAMEBUFFER,Some(fbo));
                self.gl.framebuffer_texture_2d(glow::READ_FRAMEBUFFER,glow::COLOR_ATTACHMENT0,glow::TEXTURE_2D,Some(texture),0);
                let status=self.gl.check_framebuffer_status(glow::READ_FRAMEBUFFER);
                if status==glow::FRAMEBUFFER_COMPLETE {
                    self.gl.bind_buffer(glow::PIXEL_PACK_BUFFER,None);
                    self.gl.read_pixels(0,0,width as i32,height as i32,glow::RGBA,glow::UNSIGNED_BYTE,glow::PixelPackData::Slice(&mut pixels));
                    self.gl.bind_buffer(glow::PIXEL_PACK_BUFFER,old_pack);
                }
                self.gl.bind_framebuffer(glow::READ_FRAMEBUFFER,old_fbo);
                self.gl.delete_framebuffer(fbo);
                if status!=glow::FRAMEBUFFER_COMPLETE {return Err(format!("framebuffer {status:#x}"));}
            }
            let folder=std::path::Path::new(&folder);
            std::fs::create_dir_all(folder).map_err(|e|e.to_string())?;
            std::fs::write(folder.join(format!("{index:03}.rgba")),pixels).map_err(|e|e.to_string())?;
            std::fs::write(folder.join(format!("{index:03}.txt")),format!("{width} {height}\n{label}\n")).map_err(|e|e.to_string())?;
            Ok(())
        })();
        if let Err(error)=result {eprintln!("Filter trace failed: {error}");}
    }
}
