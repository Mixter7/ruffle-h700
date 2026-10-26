// Small offscreen checks run once before a movie loads, on the device's own driver.
// Never read pixels during gameplay; diagnostics do not alter renderer settings.
impl GlRenderBackend {
    fn h700_pixel_probe(&mut self) -> Result<Vec<String>, BitmapError> {
        use ruffle_render::shape_utils::{DrawPath, DrawCommand, FillRule};
        struct NoBitmaps;
        impl BitmapSource for NoBitmaps {
            fn bitmap_size(&self, _:u16)->Option<ruffle_render::bitmap::BitmapSize>{None}
            fn bitmap_handle(&self,_:u16,_:&mut dyn RenderBackend)->Option<BitmapHandle>{None}
        }
        let mut failures=Vec::new();
        let mut check=|name:&str,got:&[u8],want:[u8;4]| {
            if got.iter().zip(want).any(|(a,b)|(*a as i16-b as i16).abs()>3) {
                failures.push(format!("{name}: got {got:?}, expected {want:?}"));
            }
        };
        let size=NonZeroU32::new(16).unwrap();
        let target=self.create_empty_texture(size,size)?;
        let texture=as_registry_data(&target).texture;
        for (name,format,pixel) in [
            ("rgba-pbo",BitmapFormat::Rgba,vec![64,32,16,128]),
            ("rgb-pbo",BitmapFormat::Rgb,vec![32,96,192]),
        ] {
            let data=pixel.repeat(16*16);
            let handle=self.register_bitmap(Bitmap::new(16,16,format,data))?;
            let raw=self.read_texture_pixels(&handle,PixelRegion::for_whole_size(16,16));
            let expected=if format==BitmapFormat::Rgb {[32,96,192,255]} else {[64,32,16,128]};
            check(name,&raw[0..4],expected);
            let mut commands=CommandList::new();
            commands.render_bitmap(handle.clone(),Transform::default(),false,PixelSnapping::Never);
            self.render_to_texture(texture,16,16,Some(Color::from_rgba(0)),commands)?;
            let raw=self.read_texture_pixels(&target,PixelRegion::for_whole_size(16,16));
            check(&format!("{name}-draw"),&raw[(8*16+8)*4..(8*16+8)*4+4],expected);
            if format==BitmapFormat::Rgba {
                let update=[8,16,32,64].repeat(16*16);
                self.update_texture(&handle,Bitmap::new(16,16,format,update),PixelRegion{x_min:3,y_min:4,x_max:7,y_max:9})?;
                let raw=self.read_texture_pixels(&handle,PixelRegion::for_whole_size(16,16));
                check("rgba-direct-update",&raw[(5*16+4)*4..(5*16+4)*4+4],[8,16,32,64]);
                check("rgba-update-outside",&raw[0..4],expected);
            }
        }
        let style=swf::FillStyle::LinearGradient(swf::Gradient {
            matrix:swf::Matrix{a:swf::Fixed16::from_f32(320.0/32768.0),d:swf::Fixed16::from_f32(320.0/32768.0),tx:Twips::new(160),ty:Twips::new(160),..swf::Matrix::IDENTITY},
            spread:GradientSpread::Pad,interpolation:GradientInterpolation::Rgb,
            records:vec![swf::GradientRecord{ratio:0,color:Color{r:255,g:0,b:0,a:128}},swf::GradientRecord{ratio:255,color:Color{r:0,g:0,b:255,a:128}}],
        });
        let point=|x,y|swf::Point::new(Twips::new(x),Twips::new(y));
        let bounds=swf::Rectangle{x_min:Twips::ZERO,y_min:Twips::ZERO,x_max:Twips::new(320),y_max:Twips::new(320)};
        let shape=DistilledShape{id:0,shape_bounds:bounds,edge_bounds:bounds,paths:vec![DrawPath::Fill{style:&style,winding_rule:FillRule::EvenOdd,commands:vec![DrawCommand::MoveTo(point(0,0)),DrawCommand::LineTo(point(320,0)),DrawCommand::LineTo(point(320,320)),DrawCommand::LineTo(point(0,320)),DrawCommand::LineTo(point(0,0))]}]};
        let shape=ShapeHandle(Arc::new(self.register_shape_internal(shape,&NoBitmaps)?));
        let mut commands=CommandList::new();
        commands.render_shape(shape,Transform::default());
        self.render_to_texture(texture,16,16,Some(Color::from_rgba(0)),commands)?;
        let raw=self.read_texture_pixels(&target,PixelRegion::for_whole_size(16,16));
        check("gradient-left",&raw[(8*16+2)*4..(8*16+2)*4+4],[108,0,20,128]);
        check("gradient-right",&raw[(8*16+13)*4..(8*16+13)*4+4],[20,0,108,128]);
        let error=unsafe{self.gl.get_error()};
        if error!=glow::NO_ERROR {failures.push(format!("OpenGL error {error:#x}"));}
        Ok(failures)
    }
    fn h700_run_pixel_probe(&mut self) {
        if std::env::var("H700_GRAPHICS_PROBE").as_deref()==Ok("0") {return;}
        let result=self.h700_pixel_probe();
        // Probe handles are dropped; invalidate object-name caches before the game.
        self.active_texture_2d.set(None);self.active_vertex_array.set(None);
        self.reset_render_state();
        match result {
            Ok(failures) if failures.is_empty()=>eprintln!("H700 pixel probe v1: PASS texture upload, bitmap alpha, partial update, gradient"),
            Ok(failures)=>for failure in failures {eprintln!("H700 pixel probe v1: FAIL {failure}");},
            Err(error)=>eprintln!("H700 pixel probe v1: ERROR {error}"),
        }
    }
}
