from pathlib import Path
import shutil

def adapt(root):
    src=Path(__file__).parent
    shutil.copyfile(src/'blend.frag',root/'sdl2test-u/shaders/h700_blend.frag')
    p=root/'sdl2test-u/src/gl_backend.rs';s=p.read_text(encoding='utf-8')
    def rep(a,b):
        nonlocal s
        assert s.count(a)==1,(a[:90],s.count(a))
        s=s.replace(a,b)
    rep('    shape_tessellator: ShapeTessellator,','''    h700_blend_program: FilterProgram,
    h700_blend_vao: glow::VertexArray,
    h700_blend_pool: Vec<H700BlendTarget>,
    shape_tessellator: ShapeTessellator,''')
    rep('        let color_program = ShaderProgram::new', '''        let blend_vertex=Self::compile_shader(&gl,glow::VERTEX_SHADER,r#"#version 300 es
precision highp float;
void main(){vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));gl_Position=vec4(p*2.0-1.0,0.0,1.0);}
"#)?;
        let blend_fragment=Self::compile_shader(&gl,glow::FRAGMENT_SHADER,include_str!("../shaders/h700_blend.frag"))?;
        let h700_blend_program=FilterProgram::new(&gl,&blend_vertex,&blend_fragment,&["source_image","backdrop_image","image_size","blend_mode"],&[])?;
        gl.delete_shader(blend_vertex);gl.delete_shader(blend_fragment);
        let h700_blend_vao=gl.create_vertex_array().map_err(|e|BitmapError::Unimplemented(e.into()))?;
        let color_program = ShaderProgram::new''')
    rep('            color_program,','            h700_blend_program,\n            h700_blend_vao,\n            h700_blend_pool: Vec::new(),\n            color_program,')
    rep('            self.gl.delete_program(self.gradient_program.program);','''            self.gl.delete_program(self.gradient_program.program);
            self.gl.delete_program(self.h700_blend_program.program);
            self.gl.delete_vertex_array(self.h700_blend_vao);''')
    rep('''    fn blend(&mut self, commands: CommandList, blend: RenderBlendMode) {
        self.push_blend_mode(blend);''','''    fn blend(&mut self, commands: CommandList, blend: RenderBlendMode) {
        h700_report_blend(&blend);
        if let RenderBlendMode::Builtin(mode @ (swf::BlendMode::Multiply | swf::BlendMode::Darken | swf::BlendMode::HardLight)) = &blend {
            if self.mask_state != MaskState::DrawMaskStencil && self.mask_state != MaskState::ClearMaskStencil {
                self.h700_composite_blend(commands,*mode);
                return;
            }
        }
        self.push_blend_mode(blend);''')
    s+='\n'+(src/'blend_impl.rs').read_text(encoding='utf-8-sig')
    s+='\n'+(src/'blend_tests.rs').read_text(encoding='utf-8-sig')
    p.write_text(s,encoding='utf-8')
