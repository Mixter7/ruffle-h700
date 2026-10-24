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
rep('                                dpad2wasd = !dpad2wasd;\n                                backbtn_pressed = false;', "                                break 'running;")
rep('use ruffle_video_external::backend::ExternalVideoBackend;','')
rep('    let mut use_mouse = false;', '    let mut use_mouse = false;\n    let mut h700_left_mouse = false;\n    let mut h700_right_mouse = false;')
rep('        for event in event_pump.poll_iter() {', '''        for event in event_pump.poll_iter() {
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
fn h700_trigger_pressed(was_pressed: bool, value: i16) -> bool {
    if was_pressed { value >= TRIGGER_RELEASE_THRESHOLD } else { value > TRIGGER_PRESS_THRESHOLD }
}
#[cfg(test)]
mod h700_mouse_tests {
    use super::*;
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
g.write_text(t.replace(old,'        1.0'),encoding='utf-8')
# Avoid unbounded debug output in gameplay. Keep errors and explicit startup diagnostics.
s=s.replace('println!("按钮按下: {:?}", button);','').replace('println!("按钮释放: {:?}", button);','')
p.write_text(s,encoding='utf-8')
c=root/'sdl2test-u/Cargo.toml'
c.write_text(c.read_text(encoding='utf-8').replace('ruffle_video_external = { path = "../video/external" }',''),encoding='utf-8')
print('H700 SDL/GLES3 adaptation applied; full-size textures, SELECT+START exit.')
