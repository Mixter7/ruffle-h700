from pathlib import Path
import sys, re
root=Path(sys.argv[1])
p=root/'sdl2test-u/src/main.rs'
s=p.read_text(encoding='utf-8')
def rep(old,new):
    global s
    assert s.count(old)==1,(old,s.count(old))
    s=s.replace(old,new)
rep('gl_attr.set_context_profile(GLProfile::Core);','gl_attr.set_context_profile(GLProfile::GLES);')
rep('gl_attr.set_context_version(4, 1);','gl_attr.set_context_version(3, 0);\n    gl_attr.set_stencil_size(8);\n    gl_attr.set_double_buffer(true);')
rep('.window("Ruffle SDL2 Player", width, height)','.window("H7Flash SDL experimental", width, height)\n        .fullscreen_desktop()')
rep('    let (sender, receiver) = mpsc::channel::<RuffleEvent>();','''    use glow::HasContext;
    unsafe {
        println!("H700 SDL driver={} renderer={} version={}", video_subsystem.current_video_driver(), gl.get_parameter_string(glow::RENDERER), gl.get_parameter_string(glow::VERSION));
    }
    let _ = video_subsystem.gl_set_swap_interval(sdl2::video::SwapInterval::VSync);
    let (sender, receiver) = mpsc::channel::<RuffleEvent>();''')
rep('''                        Button::Start => {
                            if backbtn_pressed {
                                dpad2wasd = !dpad2wasd;
                                backbtn_pressed = false;
                            }
                        }''', '')
rep('use ruffle_video_external::backend::ExternalVideoBackend;','')
rep('    let mut use_mouse = false;', '    let mut use_mouse = false;\n    let mut h700_left_mouse = false;\n    let mut h700_right_mouse = false;\n    let mut h700_exit_chord = H700ExitChord::default();')
rep('        for event in event_pump.poll_iter() {', '''        for event in event_pump.poll_iter() {
            // Track both orders before forwarding START or toggling the cursor.
            match &event {
                Event::ControllerButtonDown { button, .. } => {
                    if h700_exit_chord.update(*button, true) { break 'running; }
                }
                Event::ControllerButtonUp { button, .. } => { h700_exit_chord.update(*button, false); }
                Event::ControllerDeviceRemoved { .. } => { h700_exit_chord = H700ExitChord::default(); }
                _ => {}
            }
            if matches!(event, Event::ControllerButtonDown { button: Button::Guide, .. }) {
                // Release mouse buttons before hiding the cursor, even with R2/L2 held.
                if let Some(player) = playerbox.as_ref() {
                    let mut player = player.player.lock().unwrap();
                    for (pressed, button) in [(h700_left_mouse, RMouseBtn::Left), (h700_right_mouse, RMouseBtn::Right)] {
                        if pressed {
                            player.handle_event(PlayerEvent::MouseUp { x: mouse_x as f64, y: mouse_y as f64, button });
                        }
                    }
                }
                h700_left_mouse = false;
                h700_right_mouse = false;
                use_mouse = !use_mouse;
                needs_redraw = true;
                println!("H700 mouse={}", use_mouse);
                continue;
            }
            if matches!(event, Event::ControllerButtonUp { button: Button::Guide, .. }) { continue; }
            let mouse_trigger = match &event {
                Event::ControllerAxisMotion { axis: Axis::TriggerRight, value, .. } if use_mouse => Some((true, *value)),
                Event::ControllerAxisMotion { axis: Axis::TriggerLeft, value, .. } if use_mouse => Some((false, *value)),
                Event::ControllerButtonDown { button: Button::Paddle2, .. } if use_mouse => Some((true, i16::MAX)),
                Event::ControllerButtonUp { button: Button::Paddle2, .. } if use_mouse => Some((true, 0)),
                Event::ControllerButtonDown { button: Button::Paddle1, .. } if use_mouse => Some((false, i16::MAX)),
                Event::ControllerButtonUp { button: Button::Paddle1, .. } if use_mouse => Some((false, 0)),
                _ => None,
            };
            if let Some((left, value)) = mouse_trigger {
                let state = if left { &mut h700_left_mouse } else { &mut h700_right_mouse };
                let pressed = h700_trigger_pressed(*state, value);
                if pressed != *state {
                    *state = pressed;
                    let button = if left { RMouseBtn::Left } else { RMouseBtn::Right };
                    let event = if pressed {
                        PlayerEvent::MouseDown { x: mouse_x as f64, y: mouse_y as f64, button, index: None }
                    } else {
                        PlayerEvent::MouseUp { x: mouse_x as f64, y: mouse_y as f64, button }
                    };
                    if let Some(player) = playerbox.as_ref() { player.player.lock().unwrap().handle_event(event); }
                    needs_redraw = true;
                }
                continue;
            }''')
# MENU is consumed before ordinary keyboard forwarding. Remove the old exit and
# secondary toggle so there is a single owner of cursor/button state.
rep('''                        Button::Guide => {
                            println!("Guide 键按下退出");
                            break 'running;
                        }''','')
rep('''                        Button::X => {
                            if backbtn_pressed {
                                use_mouse = !use_mouse;
                                backbtn_pressed = false;
                            }
                        }''','')
s,n=re.subn(r'                    if use_mouse && button == Button::Y \{.*?(?=                    if !use_mouse)', '', s, flags=re.S)
assert n==2,n
s += '''
#[derive(Default)]
struct H700ExitChord { menu: bool, start: bool }
impl H700ExitChord {
    fn update(&mut self, button: Button, pressed: bool) -> bool {
        match button {
            Button::Guide => self.menu = pressed,
            Button::Start => self.start = pressed,
            _ => return false,
        }
        self.menu && self.start
    }
}
fn h700_trigger_pressed(was_pressed: bool, value: i16) -> bool {
    if was_pressed { value >= TRIGGER_RELEASE_THRESHOLD } else { value > TRIGGER_PRESS_THRESHOLD }
}
#[cfg(test)]
mod h700_mouse_tests {
    use super::*;
    #[test]
    fn exit_requires_menu_and_start_held_in_either_order() {
        for (first, second) in [(Button::Guide, Button::Start), (Button::Start, Button::Guide)] {
            let mut chord = H700ExitChord::default();
            assert!(!chord.update(first, true));
            assert!(!chord.update(first, false));
            assert!(!chord.update(second, true));
            assert!(chord.update(first, true));
        }
        let mut chord = H700ExitChord::default();
        assert!(!chord.update(Button::Back, true));
        assert!(!chord.update(Button::Start, true));
        assert!(!chord.update(Button::Paddle2, true));
    }
    #[test]
    fn trigger_click_has_hysteresis_and_releases() {
        assert!(!h700_trigger_pressed(false, 0));
        assert!(h700_trigger_pressed(false, i16::MAX));
        assert!(h700_trigger_pressed(true, 0x6000));
        assert!(!h700_trigger_pressed(false, 0x6000));
        assert!(!h700_trigger_pressed(true, 0));
    }
}
'''
# Full-sized textures even at low quality: do not confuse resolution reduction with speedup.
g=root/'sdl2test-u/src/gl_backend.rs'
t=g.read_text(encoding='utf-8')
old='''        match self.quality {
            StageQuality::Low => 0.5,
            StageQuality::Medium => 0.75,
            _ => 1.0,
        }'''
assert t.count(old)==1
t=t.replace(old,'        1.0')
blend_start=t.index('        let (blend_op, src_rgb, dst_rgb) = match mode {')
blend_end=t.index('        unsafe {',blend_start)
t=t[:blend_start]+'        let (blend_op, src_rgb, dst_rgb) = h700_blend_factors(mode);\n'+t[blend_end:]
t += '''
// Same premultiplied-alpha Screen state as upstream Ruffle's wgpu renderer.
fn h700_blend_factors(mode: RenderBlendMode) -> (u32, u32, u32) {
    match mode {
        RenderBlendMode::Builtin(BlendMode::Screen) => (glow::FUNC_ADD, glow::ONE, glow::ONE_MINUS_SRC_COLOR),
        RenderBlendMode::Builtin(BlendMode::Add) => (glow::FUNC_ADD, glow::ONE, glow::ONE),
        RenderBlendMode::Builtin(BlendMode::Subtract) => (glow::FUNC_REVERSE_SUBTRACT, glow::ONE, glow::ONE),
        _ => (glow::FUNC_ADD, glow::ONE, glow::ONE_MINUS_SRC_ALPHA),
    }
}
#[cfg(test)]
mod h700_blend_tests {
    use super::*;
    // Evaluate the factors used by the actual renderer, then compare against
    // the independent straight-color compositing definition of Screen.
    fn channel(src: f32, dst: f32, alpha: f32, mode: BlendMode) -> f32 {
        let (op, sf, df)=h700_blend_factors(RenderBlendMode::Builtin(mode));
        assert_eq!(sf, glow::ONE);
        let factor=match df {
            glow::ONE => 1.0,
            glow::ONE_MINUS_SRC_COLOR => 1.0-src,
            glow::ONE_MINUS_SRC_ALPHA => 1.0-alpha,
            _ => panic!("unexpected factor"),
        };
        if op==glow::FUNC_REVERSE_SUBTRACT { dst*factor-src } else { src+dst*factor }
    }
    #[test]
    fn screen_matches_compositing_with_partial_transparency() {
        for sa in [0.0,0.25,0.5,1.0] {
            for da in [0.0,0.25,0.75,1.0] {
                for s in [0.0,0.2,0.7,1.0] {
                    for d in [0.0,0.4,0.8,1.0] {
                        let blended=1.0-(1.0-s)*(1.0-d);
                        let expected=(1.0-sa)*da*d+(1.0-da)*sa*s+sa*da*blended;
                        let actual=channel(sa*s,da*d,sa,BlendMode::Screen);
                        assert!((actual-expected).abs()<0.00001);
                    }
                }
            }
        }
    }
    #[test]
    fn screen_black_preserves_background_and_white_lightens() {
        assert!((channel(0.0,0.6,1.0,BlendMode::Screen)-0.6).abs()<0.00001);
        assert!((channel(1.0,0.6,1.0,BlendMode::Screen)-1.0).abs()<0.00001);
        assert!((channel(0.2,0.6,0.5,BlendMode::Normal)-0.5).abs()<0.00001);
        assert!((channel(0.2,0.6,0.5,BlendMode::Add)-0.8).abs()<0.00001);
        assert!((channel(0.2,0.6,0.5,BlendMode::Subtract)-0.4).abs()<0.00001);
    }
}
'''
g.write_text(t,encoding='utf-8')
# Avoid unbounded debug output in gameplay. Keep errors and explicit startup diagnostics.
s=s.replace('println!("按钮按下: {:?}", button);','').replace('println!("按钮释放: {:?}", button);','')
p.write_text(s,encoding='utf-8')
c=root/'sdl2test-u/Cargo.toml'
c.write_text(c.read_text(encoding='utf-8').replace('ruffle_video_external = { path = "../video/external" }',''),encoding='utf-8')
print('H700 SDL/GLES3 adaptation applied; full-size textures, MENU+START exit.')
from adapt_pause import adapt
adapt(root)
from adapt_graphics import adapt as adapt_graphics
adapt_graphics(root)
from adapt_blend import adapt as adapt_blend
adapt_blend(root)
from adapt_pixel_probe import adapt as adapt_pixel_probe
adapt_pixel_probe(root)
from adapt_resource_cache import adapt as adapt_resource_cache
adapt_resource_cache(root)
from adapt_screen_mask import adapt as adapt_screen_mask
adapt_screen_mask(root)
