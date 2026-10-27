use glow::HasContext;
use std::io::Write;
mod gl_backend;
use ruffle_core::{PlayerBuilder,tag_utils::SwfMovie};
fn main()->Result<(),Box<dyn std::error::Error>> {
    let args:Vec<String>=std::env::args().collect();
    if args.len()<3 {return Err("usage: scene-probe <local.swf> <output-folder> [frames=600]".into());}
    let path=std::fs::canonicalize(&args[1])?;
    let bytes=std::fs::read(&path)?;
    let movie=SwfMovie::from_data(&bytes,url::Url::from_file_path(&path).map_err(|_|"invalid path")?.to_string(),None)?;
    let w=movie.width().to_pixels().max(1.0) as u32;let h=movie.height().to_pixels().max(1.0) as u32;
    let frames:u32=args.get(3).map(|v|v.parse()).transpose()?.unwrap_or(600);
    let sdl=sdl2::init()?;let video=sdl.video()?;
    video.gl_attr().set_context_profile(sdl2::video::GLProfile::Compatibility);
    video.gl_attr().set_context_version(3,3);video.gl_attr().set_stencil_size(8);
    let window=video.window("H7Flash scene capture",w,h).opengl().hidden().build()?;
    let _context=window.gl_create_context()?;
    let gl=unsafe{glow::Context::from_loader_function(|s|video.gl_get_proc_address(s) as *const _)};
    eprintln!("Scene capture GPU: {}",unsafe{gl.get_parameter_string(glow::RENDERER)});
    let read_gl=unsafe{glow::Context::from_loader_function(|s|video.gl_get_proc_address(s) as *const _)};
    let renderer=unsafe{gl_backend::GlRenderBackend::new(gl,w,h,ruffle_render::quality::StageQuality::Low)?};
    let player=PlayerBuilder::new().with_movie(movie).with_renderer(renderer).with_autoplay(true).with_viewport_dimensions(w,h,1.0).build();
    let output=std::path::Path::new(&args[2]);std::fs::create_dir_all(output)?;
    let mut events=sdl.event_pump()?;
    for frame in 1..=frames {
        for _ in events.poll_iter() {}
        let mut player=player.lock().unwrap();
        let dt=1000.0/player.frame_rate().max(1.0);
        player.tick(ruffle_common::duration::FloatDuration::from_millis(dt));player.render();
        if [1,60,180,600].contains(&frame) || frame==frames {
            let mut pixels=vec![0u8;(w*h*4) as usize];
            unsafe{read_gl.read_pixels(0,0,w as i32,h as i32,glow::RGBA,glow::UNSIGNED_BYTE,glow::PixelPackData::Slice(&mut pixels));}
            let mut file=std::fs::File::create(output.join(format!("frame-{frame:04}.ppm")))?;
            write!(file,"P6\n{w} {h}\n255\n")?;
            for y in (0..h).rev(){for x in 0..w{let i=((y*w+x)*4) as usize;file.write_all(&pixels[i..i+3])?;}}
            eprintln!("captured frame {frame}");
        }
    }
    Ok(())
}
