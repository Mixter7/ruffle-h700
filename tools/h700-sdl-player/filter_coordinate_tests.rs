#[cfg(test)]
mod h700_filter_coordinate_tests {
    use super::*;
    #[test]
    fn gles_filter_quads_cover_entire_target_and_identity_preserves_orientation() {
        if std::env::var_os("H700_GL_TEST").is_none() { return; }
        let sdl=sdl2::init().unwrap();let video=sdl.video().unwrap();
        video.gl_attr().set_context_profile(sdl2::video::GLProfile::GLES);
        video.gl_attr().set_context_version(3,0);
        let window=video.window("filter-coverage",16,16).opengl().hidden().build().unwrap();
        let _context=window.gl_create_context().unwrap();
        let gl=unsafe{glow::Context::from_loader_function(|s|video.gl_get_proc_address(s) as *const _)};
        let mut r=unsafe{GlRenderBackend::new(gl,16,16,StageQuality::Low).unwrap()};
        let (w,h)=(13u32,9u32);
        let target=r.register_bitmap(Bitmap::new(w,h,BitmapFormat::Rgba,[0,0,255,255].repeat((w*h) as usize))).unwrap();
        let texture=as_registry_data(&target).texture;
        let legacy=FILTER_COMMON_VERTEX_GLSL.replace("gl_Position = vec4(position * 2.0 - 1.0, 0.0, 1.0);",
            "gl_Position = vec4(position * 2.0 - 1.0, 0.0, 1.0); gl_Position.y = 1.0 - gl_Position.y;");
        let shaders=[legacy.as_str(),FILTER_COMMON_VERTEX_GLSL,FILTER_BLUR_VERTEX_GLSL,
            FILTER_GLOW_VERTEX_GLSL,FILTER_BEVEL_VERTEX_GLSL,FILTER_DISPLACEMENT_MAP_VERTEX_GLSL];
        for (index,vertex) in shaders.iter().enumerate() {
            r.update_texture(&target,Bitmap::new(w,h,BitmapFormat::Rgba,[0,0,255,255].repeat((w*h) as usize)),PixelRegion::for_whole_size(w,h)).unwrap();
            let vs=GlRenderBackend::compile_shader(&r.gl,glow::VERTEX_SHADER,vertex).unwrap();
            let fs=GlRenderBackend::compile_shader(&r.gl,glow::FRAGMENT_SHADER,
                "#version 300 es\nprecision highp float; out vec4 result; void main(){result=vec4(1,0,0,1);}").unwrap();
            unsafe {
                let program=r.gl.create_program().unwrap();r.gl.attach_shader(program,vs);r.gl.attach_shader(program,fs);
                r.gl.link_program(program);assert!(r.gl.get_program_link_status(program),"{}",r.gl.get_program_info_log(program));
                let vao=r.gl.create_vertex_array().unwrap();let buffer=r.gl.create_buffer().unwrap();
                r.gl.bind_vertex_array(Some(vao));r.gl.bind_buffer(glow::ARRAY_BUFFER,Some(buffer));
                let vertices=[0.0f32,0.0,1.0,0.0,1.0,1.0,0.0,1.0];
                r.gl.buffer_data_u8_slice(glow::ARRAY_BUFFER,bytemuck::cast_slice(&vertices),glow::STATIC_DRAW);
                let location=r.gl.get_attrib_location(program,"position").unwrap();
                r.gl.enable_vertex_attrib_array(location);r.gl.vertex_attrib_pointer_f32(location,2,glow::FLOAT,false,8,0);
                r.render_filter_to_texture(texture,w,h,program,vao,buffer,bytemuck::cast_slice(&vertices),|_|Ok(())).unwrap();
                let pixels=r.read_texture_pixels(&target,PixelRegion::for_whole_size(w,h));
                let covered=pixels.chunks_exact(4).filter(|p|*p==[255,0,0,255]).count();
                if index==0 {assert!(covered>0 && covered<(w*h) as usize,"legacy defect must reproduce");}
                else {assert_eq!(covered,(w*h) as usize,"filter vertex shader {index} left pixels unwritten");}
                r.gl.delete_program(program);r.gl.delete_shader(vs);r.gl.delete_shader(fs);
                r.gl.delete_vertex_array(vao);r.gl.delete_buffer(buffer);
            }
        }
        // Exercise the real color-matrix pipeline with different values in every
        // row, including transparent pixels: neither clipping nor a Y flip passes.
        let data:Vec<u8>=(0..w*h).flat_map(|i| if i%7==0 {[0,0,0,0]} else {[(i%w*11) as u8,(i/w*19) as u8,48,255]}).collect();
        let source=r.register_bitmap(Bitmap::new(w,h,BitmapFormat::Rgba,data.clone())).unwrap();
        r.run_color_matrix_filter(as_registry_data(&source).texture,texture,w,h,
            &swf::ColorMatrixFilter{matrix:GlRenderBackend::identity_color_matrix()}).unwrap();
        let pixels=r.read_texture_pixels(&target,PixelRegion::for_whole_size(w,h));
        assert!(pixels.iter().zip(&data).all(|(a,b)|(*a as i16-*b as i16).abs()<=1),"identity filter flipped or changed the image");
        assert_eq!(unsafe{r.gl.get_error()},glow::NO_ERROR);
    }
}
