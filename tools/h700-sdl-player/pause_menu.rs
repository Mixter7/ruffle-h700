use glow::HasContext;
use sdl2::controller::Button;
use std::path::Path;
include!("controls_generated.rs");
const FONT: &[u8] = include_bytes!("pause_font.bin");

#[derive(Clone, Copy)]
pub enum Action { None, Resume, Exit, SendStart, Save }
pub struct PauseMenu {
    pub active: bool,
    editing: bool,
    selected: usize,
    values: Vec<String>,
    original: String,
    pub message: String,
}
impl PauseMenu {
    pub fn new() -> Self { Self { active:false, editing:false, selected:0, values:vec![], original:String::new(), message:String::new() } }
    pub fn open(&mut self, path: &str) {
        self.active=true; self.editing=false; self.selected=0; self.message.clear();
        self.original=std::fs::read_to_string(path).unwrap_or_default();
        self.values=BUTTONS.iter().map(|(name,_,default)| {
            self.original.lines().filter_map(|line| line.split_once('='))
                .filter(|(k,v)| k.trim()==*name && KEYS.contains(&v.trim()))
                .map(|(_,v)| v.trim().to_string()).last().unwrap_or_else(|| default.to_string())
        }).collect();
    }
    fn save(&self, path: &str) -> std::io::Result<()> {
        let mut output=String::new();
        for line in self.original.lines() {
            if line.split_once('=').map_or(false, |(k,_)| BUTTONS.iter().any(|(name,_,_)| *name==k.trim())) { continue; }
            output.push_str(line); output.push('\n');
        }
        for ((name,_,_), value) in BUTTONS.iter().zip(&self.values) { output.push_str(&format!("{}={}\n",name,value)); }
        let path=Path::new(path);
        if let Some(parent)=path.parent() { std::fs::create_dir_all(parent)?; }
        let temp=path.with_extension("cfg.tmp");
        use std::io::Write;
        let mut file=std::fs::File::create(&temp)?;
        file.write_all(output.as_bytes())?; file.sync_all()?;
        std::fs::rename(temp,path)
    }
    pub fn button(&mut self, button: Button, path: &str) -> Action {
        if button==Button::Start { return Action::Resume; }
        if self.editing {
            let count=BUTTONS.len()+1;
            match button {
                Button::DPadUp => self.selected=(self.selected+count-1)%count,
                Button::DPadDown => self.selected=(self.selected+1)%count,
                Button::DPadLeft | Button::DPadRight | Button::LeftShoulder | Button::RightShoulder if self.selected<BUTTONS.len() => {
                    let step=match button { Button::DPadLeft=>-1, Button::LeftShoulder=>-10, Button::RightShoulder=>10, _=>1 };
                    let current=KEYS.iter().position(|k| *k==self.values[self.selected]).unwrap_or(0);
                    self.values[self.selected]=KEYS[(current as i32+step).rem_euclid(KEYS.len() as i32) as usize].to_string();
                }
                Button::A if self.selected==BUTTONS.len() => {
                    match self.save(path) {
                        Ok(()) => { self.editing=false; self.selected=1; self.message="Controles salvos para este jogo".into(); }
                        Err(e) => { self.message=format!("Falha ao salvar: {}",e); }
                    }
                }
                Button::B => { self.editing=false; self.selected=1; self.message="Alteracoes nao salvas descartadas".into(); }
                _=>{}
            }
        } else {
            match button {
                Button::DPadUp=>self.selected=(self.selected+4)%5,
                Button::DPadDown=>self.selected=(self.selected+1)%5,
                Button::B=>return Action::Resume,
                Button::A=>match self.selected {
                    0=>return Action::Resume,
                    1=>{ self.open(path); self.editing=true; },
                    2=>return Action::SendStart,
                    3=>return Action::Save,
                    4=>return Action::Exit,
                    _=>{}
                },
                _=>{}
            }
        }
        Action::None
    }
    pub unsafe fn draw(&self, gl: &glow::Context, width:i32,height:i32) {
        gl.bind_framebuffer(glow::FRAMEBUFFER,None);
        gl.color_mask(true,true,true,true);
        gl.disable(glow::SCISSOR_TEST);
        gl.clear_color(0.06,0.08,0.15,1.0); gl.clear(glow::COLOR_BUFFER_BIT);
        gl.enable(glow::SCISSOR_TEST);
        let rect=|x:i32,y:i32,w:i32,h:i32,c:[f32;3]| {
            gl.scissor(x*width/640,(480-y-h)*height/480,w*width/640,h*height/480);
            gl.clear_color(c[0],c[1],c[2],1.0); gl.clear(glow::COLOR_BUFFER_BIT);
        };
        let text=|x:i32,y:i32,s:&str,c:[f32;3]| {
            for (i,ch) in s.chars().take(66).enumerate() {
                let ch=if (32..256).contains(&(ch as usize)) { ch as usize } else { 63 };
                for yy in 0..FONT_H { for xx in 0..FONT_W {
                    if FONT[(ch-32)*(FONT_W*FONT_H) as usize+(yy*FONT_W+xx) as usize]>80 {
                        rect(x+i as i32*FONT_W+xx,y+yy,1,1,c);
                    }
                }}
            }
        };
        text(20,18,if self.editing {"CONTROLES DESTE JOGO"} else {"H7FLASH - JOGO PAUSADO"},[0.35,0.8,1.0]);
        let lines:Vec<String>=if self.editing {
            BUTTONS.iter().zip(&self.values).map(|((name,_,_),v)|format!("{:<9}  < {} >",name,v))
            .chain(std::iter::once("Salvar controles".into())).collect()
        } else { vec!["Continuar".into(),"Controles".into(),"Enviar tecla START ao jogo".into(),"Salvar progresso".into(),"Voltar a lista de jogos".into()] };
        let first=self.selected.saturating_sub(9);
        for (index,line) in lines.iter().enumerate().skip(first).take(10) {
            let y=62+(index-first) as i32*29;
            if index==self.selected { rect(12,y-3,616,27,[0.12,0.33,0.52]); }
            text(24,y,line,[0.94,0.95,1.0]);
        }
        if !self.editing { text(20,365,"Salvar progresso copia o save interno do jogo",[0.65,0.68,0.75]); }
        text(20,396,&self.message,[0.8,0.8,0.6]);
        text(20,425,if self.editing {"Cima/baixo: botao  Esq/dir: tecla  L/R: pular"} else {"Cima/baixo: escolher  A: confirmar  B: voltar"},[0.7,0.75,0.85]);
        text(20,451,if self.editing {"A em Salvar: aplicar  B: cancelar  START: continuar"} else {"START: continuar  MENU + START: sair"},[0.7,0.75,0.85]);
        gl.disable(glow::SCISSOR_TEST);
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn editor_roundtrip_keeps_other_settings_and_applies_per_game() {
        let dir=std::env::temp_dir().join(format!("h7flash-controls-{}-{}",std::process::id(),std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        std::fs::create_dir_all(&dir).unwrap();
        let path=dir.join("game.cfg");
        std::fs::write(&path,"# custom\nB=F2\nFutureOption=keep\n").unwrap();
        let mut menu=PauseMenu::new(); menu.open(path.to_str().unwrap());
        assert_eq!(menu.values[1],"F2");
        menu.values[1]="Space".into(); menu.save(path.to_str().unwrap()).unwrap();
        let contents=std::fs::read_to_string(&path).unwrap();
        assert!(contents.contains("FutureOption=keep"));
        let map=crate::keycodes::KeyMap::load(&path).unwrap();
        assert_eq!(map.button_to_keycode(Button::A,false),sdl2::keyboard::Keycode::Space);
        assert_eq!(map.button_to_keycode(Button::DPadUp,false),sdl2::keyboard::Keycode::Up);
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn pause_start_resumes_and_save_is_a_separate_action() {
        let mut menu=PauseMenu::new();
        assert!(matches!(menu.button(Button::Start,"unused"),Action::Resume));
        menu.selected=3;
        assert!(matches!(menu.button(Button::A,"unused"),Action::Save));
    }
}
