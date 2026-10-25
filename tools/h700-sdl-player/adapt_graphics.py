from pathlib import Path

def adapt(root):
    p=root/'core/src/player.rs'
    s=p.read_text(encoding='utf-8')
    old='        commands.draw_rect(Color::RED, Matrix::create_box(20.0, 20.0, Twips::from_pixels(mouse_x as f64), Twips::from_pixels(mouse_y as f64 )));'
    assert s.count(old)==1
    # White arrow with black outline; tip is exactly the mouse hit position.
    rows=["X", "XX", "X.X", "X..X", "X...X", "X....X", "X.....X", "X......X", "X.......X", "X........X", "X.........X", "X..........X", "X...........X", "X............X", "X......XXXXXXXX", "X...X..X", "X..XX..X", "X.X  X..X", "XX   X..X", "X     X..X", "      X..X", "       XX"]
    spans=[]
    for y,row in enumerate(rows):
        x=0
        while x<len(row):
            c=row[x];end=x+1
            while end<len(row) and row[end]==c:end+=1
            if c!=' ':spans.append((x,y,end-x,'WHITE' if c=='.' else 'BLACK'))
            x=end
    new='        // H700 pointer: white arrow outlined in black.\n'
    for x,y,w,color in spans:
        new+=f'        commands.draw_rect(Color::{color}, Matrix::create_box({w}.0, 1.0, Twips::from_pixels(mouse_x as f64 + {x}.0), Twips::from_pixels(mouse_y as f64 + {y}.0)));\n'
    s=s.replace(old,new.rstrip())
    p.write_text(s,encoding='utf-8')
    p=root/'sdl2test-u/src/gl_backend.rs'
    s=p.read_text(encoding='utf-8')
    anchor='        let (blend_op, src_rgb, dst_rgb) = h700_blend_factors(mode);'
    assert s.count(anchor)==1
    s=s.replace(anchor,'        h700_report_blend(&mode);\n'+anchor)
    anchor='    fn render_alpha_mask(&mut self, maskee_commands: CommandList, _mask_commands: CommandList) {\n'
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''        static REPORTED: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
        if !REPORTED.swap(true, std::sync::atomic::Ordering::Relaxed) {
            eprintln!("H700 graphics: alpha mask requested; this renderer currently ignores its mask");
        }
''')
    for message in ['Failed to render cache entry on glow backend: {error}', 'Failed to apply cache-entry filters on glow backend: {error}', 'Failed to render frame on glow backend: {error}']:
        old='log::warn!("'+message+'");'
        assert old in s
        s=s.replace(old,'h700_report_render_error(&format!("'+message+'"));')
    s+='''
// Log each blend mode once per process, not once per object/frame.
fn h700_report_blend(mode: &RenderBlendMode) {
    use std::sync::atomic::{AtomicU32, Ordering};
    static SEEN: AtomicU32 = AtomicU32::new(0);
    if let RenderBlendMode::Builtin(blend) = mode {
        let bit = 1u32 << (*blend as u32);
        if SEEN.fetch_or(bit, Ordering::Relaxed) & bit == 0 {
            eprintln!("H700 graphics: blend requested {:?}", blend);
        }
    }
}
fn h700_report_render_error(message: &str) {
    use std::sync::atomic::{AtomicU32, Ordering};
    static COUNT: AtomicU32 = AtomicU32::new(0);
    if COUNT.fetch_add(1, Ordering::Relaxed) < 8 { eprintln!("H700 graphics: {}", message); }
}
'''
    p.write_text(s,encoding='utf-8')
