from pathlib import Path
import shutil

def adapt(root):
    src=Path(__file__).parent
    for name in ['pause_menu.rs','controls_generated.rs','pause_font.bin','progress.rs']:
        shutil.copyfile(src/name,root/'sdl2test-u/src'/name)
    p=root/'sdl2test-u/src/main.rs'
    s=p.read_text(encoding='utf-8')
    def rep(old,new):
        nonlocal s
        assert s.count(old)==1,(old[:80],s.count(old))
        s=s.replace(old,new)
    rep('mod keycodes;', 'mod keycodes;\nmod pause_menu;\nmod progress;')
    rep('    let mut last_frame_time = Instant::now();', '    let progress = progress::Progress::default();\n    let mut last_frame_time = Instant::now();')
    rep('.with_storage(Box::new(DiskStorageBackend::new(PathBuf::from("./"))))', '.with_storage(Box::new(progress.storage()))')
    rep('    let (sender, receiver) = mpsc::channel::<RuffleEvent>();', '    let pause_gl = unsafe { glow::Context::from_loader_function(|s| video_subsystem.gl_get_proc_address(s) as *const _) };\n    let (sender, receiver) = mpsc::channel::<RuffleEvent>();')
    rep('    let keymap = keycodes::KeyMap::load', '    let mut keymap = keycodes::KeyMap::load')
    rep('    let mut use_mouse = false;', '''    let mut pause_menu = pause_menu::PauseMenu::new();
    let mut pause_was_playing = true;
    let mut held_keys = std::collections::HashSet::<Keycode>::new();
    let mut use_mouse = false;''')
    anchor='            if matches!(event, Event::ControllerButtonDown { button: Button::Guide, .. }) {'
    rep(anchor,'''            let start_down = matches!(event, Event::ControllerButtonDown { button: Button::Start, .. });
            if pause_menu.active {
                let action = match &event {
                    Event::ControllerButtonDown { button, .. } => pause_menu.button(*button, &keymap_path),
                    Event::Quit { .. } => pause_menu::Action::Exit,
                    Event::Window { win_event: WindowEvent::Close, .. } => pause_menu::Action::Exit,
                    _ => pause_menu::Action::None,
                };
                match action {
                    pause_menu::Action::Save => {
                        if let Some(player) = playerbox.as_ref() { player.player.lock().unwrap().flush_shared_objects(); }
                        pause_menu.message = match progress.save(swf_name) {
                            Ok(()) => "Copia do progresso salva".into(),
                            Err(e) => e,
                        };
                    }
                    pause_menu::Action::Exit => break 'running,
                    pause_menu::Action::Resume | pause_menu::Action::SendStart => {
                        let send_start = matches!(action, pause_menu::Action::SendStart);
                        pause_menu.active = false;
                        if let Some(updated) = keycodes::KeyMap::load(&keymap_path) { keymap = updated; }
                        if let Some(player) = playerbox.as_ref() {
                            let mut player = player.player.lock().unwrap();
                            player.set_is_playing(pause_was_playing);
                            if send_start {
                                if let Some(key) = keycodes::sdl2_keycode_to_ruffle_key_descriptor(keymap.button_to_keycode(Button::Start, false)) {
                                    player.handle_event(PlayerEvent::KeyDown { key });
                                    if let LogicalKey::Character(c) = key.logical_key { player.handle_event(PlayerEvent::TextInput { codepoint: c }); }
                                    player.handle_event(PlayerEvent::KeyUp { key });
                                }
                            }
                        }
                        last_frame_time = Instant::now();
                        v_mouse = keycodes::VirtualMouse::new(mouse_x as f32, mouse_y as f32);
                    }
                    pause_menu::Action::None => {}
                }
                needs_redraw = true;
                // Device changes must still reach SDL's controller bookkeeping.
                if !matches!(event, Event::ControllerDeviceAdded { .. } | Event::ControllerDeviceRemoved { .. }) { continue; }
            } else if start_down {
                if let Some(player) = playerbox.as_ref() {
                    let mut player = player.player.lock().unwrap();
                    for kc in held_keys.drain() {
                        if let Some(key) = keycodes::sdl2_keycode_to_ruffle_key_descriptor(kc) { player.handle_event(PlayerEvent::KeyUp { key }); }
                    }
                    for (pressed, button) in [(h700_left_mouse, RMouseBtn::Left), (h700_right_mouse, RMouseBtn::Right)] {
                        if pressed { player.handle_event(PlayerEvent::MouseUp { x: mouse_x as f64, y: mouse_y as f64, button }); }
                    }
                    pause_was_playing = player.is_playing();
                    player.set_is_playing(false);
                }
                h700_left_mouse = false; h700_right_mouse = false;
                left_trigger_active = false; right_trigger_active = false;
                pause_menu.open(&keymap_path);
                needs_redraw = true;
                continue;
            }
            if matches!(event, Event::ControllerButtonUp { button: Button::Start, .. }) { continue; }
            // Track forwarded keys so opening the menu cannot leave a key held.
            match &event {
                Event::ControllerButtonDown { button, .. } if !use_mouse && *button != Button::Guide => { held_keys.insert(keymap.button_to_keycode(*button, dpad2wasd)); }
                Event::ControllerButtonUp { button, .. } => { held_keys.remove(&keymap.button_to_keycode(*button, dpad2wasd)); }
                Event::KeyDown { keycode: Some(k), .. } => { held_keys.insert(*k); }
                Event::KeyUp { keycode: Some(k), .. } => { held_keys.remove(k); }
                Event::ControllerAxisMotion { axis, value, .. } if !use_mouse => {
                    let button = match axis { Axis::TriggerLeft => Some(Button::Paddle1), Axis::TriggerRight => Some(Button::Paddle2), _ => None };
                    if let Some(b) = button {
                        let k = keymap.button_to_keycode(b, dpad2wasd);
                        if *value > TRIGGER_PRESS_THRESHOLD { held_keys.insert(k); }
                        else if *value < TRIGGER_RELEASE_THRESHOLD { held_keys.remove(&k); }
                    }
                }
                _ => {}
            }
'''+anchor)
    rep('''        if use_mouse {
            let previous_mouse_position''','''        if pause_menu.active {
            if needs_redraw {
                let (w,h) = window.drawable_size();
                unsafe { pause_menu.draw(&pause_gl,w as i32,h as i32); }
                window.gl_swap_window();
            }
            last_frame_time = Instant::now();
            sleep(Duration::from_millis(16));
            continue;
        }
        if use_mouse {
            let previous_mouse_position''')
    p.write_text(s,encoding='utf-8')
    p=root/'sdl2test-u/src/keycodes.rs'
    s=p.read_text(encoding='utf-8')
    s=s.replace('        "Select" => Some(Button::Back),','''        "Select" => Some(Button::Back),
        "Up" => Some(Button::DPadUp),
        "Down" => Some(Button::DPadDown),
        "Left" => Some(Button::DPadLeft),
        "Right" => Some(Button::DPadRight),''')
    p.write_text(s,encoding='utf-8')

    p=root/'sdl2test-u/Cargo.toml'
    s=p.read_text(encoding='utf-8').replace('[dependencies]', '[dependencies]\nserde_json = "1"')
    p.write_text(s,encoding='utf-8')
