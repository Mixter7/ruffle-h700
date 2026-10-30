from pathlib import Path

def adapt(root):
    p=root/'sdl2test-u/src/main.rs'
    s=p.read_text(encoding='utf-8')
    def rep(old,new):
        nonlocal s
        assert s.count(old)==1, old[:90]
        s=s.replace(old,new)
    rep('    let mut last_frame_time = Instant::now();',
        '    let mut h700_perf = H700Perf::new();\n    let mut last_frame_time = Instant::now();')
    rep('        if pause_menu.active {\n            if needs_redraw {',
        '        if pause_menu.active {\n            h700_perf = H700Perf::new();\n            if needs_redraw {')
    rep('        if needs_redraw {\n            if let Some(player) = playerbox.as_ref() {',
        '''        let h700_tick_us = tick_time.elapsed().as_micros() as u64;
        let mut h700_render_us = 0;
        let mut h700_swap_us = 0;
        if needs_redraw {
            let h700_render_start = Instant::now();
            if let Some(player) = playerbox.as_ref() {''')
    rep('''            window.gl_swap_window();
        }

        // Player''','''            h700_render_us = h700_render_start.elapsed().as_micros() as u64;
            let h700_swap_start = Instant::now();
            window.gl_swap_window();
            h700_swap_us = h700_swap_start.elapsed().as_micros() as u64;
        }
        h700_perf.record(h700_tick_us, h700_render_us, h700_swap_us, needs_redraw);

        // Player''')
    s+='\n'+Path(__file__).with_name('timing.rs').read_text(encoding='utf-8')
    p.write_text(s,encoding='utf-8')
