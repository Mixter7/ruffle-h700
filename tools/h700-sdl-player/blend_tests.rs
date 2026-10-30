#[cfg(test)]
mod h700_gpu_tests {
    use super::*;
    fn rect(c:Color,x:f32,y:f32,w:f32,h:f32)->CommandList {
        let mut v=CommandList::new();v.draw_rect(c,Matrix::create_box(w,h,Twips::from_pixels(x as f64),Twips::from_pixels(y as f64)));v
    }
    fn expected(s:[f32;4],d:[f32;4],mode:BlendMode)->[f32;4] {
        let mut out=[0.0;4];
        for i in 0..3 {
            let cs=if s[3]>0.0{s[i]/s[3]}else{0.0};let cd=if d[3]>0.0{d[i]/d[3]}else{0.0};
            let b=match mode {BlendMode::Multiply=>cs*cd,BlendMode::Darken=>cs.min(cd),BlendMode::HardLight=>if cs<0.5{2.0*cs*cd}else{1.0-2.0*(1.0-cs)*(1.0-cd)},_=>cs};
            out[i]=(1.0-s[3])*d[i]+(1.0-d[3])*s[i]+s[3]*d[3]*b;
        }
        out[3]=s[3]+d[3]-s[3]*d[3];out
    }
    fn rgba(c:Color)->[f32;4]{let a=c.a as f32/255.0;[c.r as f32/255.0*a,c.g as f32/255.0*a,c.b as f32/255.0*a,a]}
    fn close(actual:&[u8],expected:[f32;4]) {for i in 0..4 {assert!((actual[i] as f32-expected[i]*255.0).abs()<3.5,"pixel {:?}, expected {:?}",actual,expected);}}
    #[test]
    fn gles_blends_preserve_alpha_masks_nested_groups_and_following_draws() {
        if std::env::var_os("H700_GL_TEST").is_none(){return;}
        let sdl=sdl2::init().unwrap();let video=sdl.video().unwrap();
        video.gl_attr().set_context_profile(sdl2::video::GLProfile::GLES);video.gl_attr().set_context_version(3,0);
        let window=video.window("render-test",16,16).opengl().hidden().build().unwrap();let _context=window.gl_create_context().unwrap();
        let gl=unsafe{glow::Context::from_loader_function(|s|video.gl_get_proc_address(s) as *const _)};
        let mut r=unsafe{GlRenderBackend::new(gl,16,16,StageQuality::Low).unwrap()};
        let target=r.create_empty_texture(std::num::NonZeroU32::new(16).unwrap(),std::num::NonZeroU32::new(16).unwrap()).unwrap();let texture=as_registry_data(&target).texture;
        let source=Color{r:196,g:64,b:128,a:128};let dest=Color{r:64,g:160,b:224,a:128};
        for mode in [BlendMode::Multiply,BlendMode::Darken,BlendMode::HardLight] {
            for sa in [0,128,255] {for da in [0,128,255] {
                let s=Color{a:sa,..source};let d=Color{a:da,..dest};
                let mut list=rect(d,0.0,0.0,16.0,16.0);
                list.blend(rect(s,0.0,0.0,8.0,8.0),RenderBlendMode::Builtin(mode));
                list.draw_rect(Color::WHITE,Matrix::create_box(2.0,2.0,Twips::from_pixels(12.0),Twips::from_pixels(12.0)));
                r.render_to_texture(texture,16,16,Some(Color::from_rgba(0)),list).unwrap();
                let data=r.read_texture_pixels(&target,PixelRegion::for_whole_size(16,16));
                close(&data[(2*16+2)*4..(2*16+2)*4+4],expected(rgba(s),rgba(d),mode));
                close(&data[(10*16+2)*4..(10*16+2)*4+4],rgba(d));
                close(&data[(12*16+12)*4..(12*16+12)*4+4],[1.0;4]);
                assert_eq!(unsafe{r.gl.get_error()},glow::NO_ERROR);
            }}
        }
        let mut masked=rect(dest,0.0,0.0,16.0,16.0);
        let mask=Matrix::create_box(8.0,16.0,Twips::ZERO,Twips::ZERO);
        masked.push_mask();masked.draw_rect(Color::WHITE,mask);masked.activate_mask();
        let mut group=rect(source,0.0,0.0,16.0,16.0);
        group.blend(rect(dest,0.0,0.0,16.0,16.0),RenderBlendMode::Builtin(BlendMode::Darken));
        masked.blend(group,RenderBlendMode::Builtin(BlendMode::Multiply));
        masked.deactivate_mask();masked.draw_rect(Color::WHITE,mask);masked.pop_mask();
        r.render_to_texture(texture,16,16,Some(Color::from_rgba(0)),masked).unwrap();
        let data=r.read_texture_pixels(&target,PixelRegion::for_whole_size(16,16));
        close(&data[(2*16+2)*4..(2*16+2)*4+4],expected(expected(rgba(dest),rgba(source),BlendMode::Darken),rgba(dest),BlendMode::Multiply));
        close(&data[(2*16+12)*4..(2*16+12)*4+4],rgba(dest));
        assert_eq!(unsafe{r.gl.get_error()},glow::NO_ERROR);
    }
}
