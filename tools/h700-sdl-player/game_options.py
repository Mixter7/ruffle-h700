"""Per-game control editor shared with the in-game SDL player."""
import os, json, tempfile, ctypes, time
import sdl2
import progress_store

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'controls.json'), encoding='utf-8') as f:
    SPEC = json.load(f)
BUTTONS, KEYS = SPEC['buttons'], SPEC['keys']

class Controls:
    def __init__(self, game):
        self.path = os.path.join(HERE, 'state', 'keymap', os.path.splitext(os.path.basename(game))[0] + '.cfg')
        try:
            with open(self.path, encoding='utf-8') as f: self.original = f.read()
        except FileNotFoundError: self.original = ''
        mapping = {}
        for line in self.original.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                if v.strip() in KEYS: mapping[k.strip()] = v.strip()
        self.values = [mapping.get(name, default) for name, _, default in BUTTONS]

    def save(self):
        names = {b[0] for b in BUTTONS}
        lines = [line for line in self.original.splitlines() if line.split('=', 1)[0].strip() not in names]
        lines += [name + '=' + value for (name, _, _), value in zip(BUTTONS, self.values)]
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, temp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
                f.write('\n'.join(lines) + '\n'); f.flush(); os.fsync(f.fileno())
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp): os.unlink(temp)


def run(win, surf, font, game, swap=False):
    """Return False only when SDL requests that the application close."""
    config = Controls(game)
    editing, selected, message = False, 0, ''
    confirm_load = False
    W, H = surf.contents.w, surf.contents.h
    def fill(x, y, w, h, color):
        sdl2.SDL_FillRect(surf, sdl2.SDL_Rect(x, y, w, h), (color[0]<<16)|(color[1]<<8)|color[2])
    def text(y, value, color=(235,240,255)):
        font.draw(surf, 1, 20, y, value[:max(1,(W-40)//font.metrics(1)[0])], color)
    ev = sdl2.SDL_Event()
    dirty = True
    while True:
        if dirty:
            fill(0,0,W,H,(16,20,38))
            text(18, 'CONTROLES DO JOGO' if editing else 'OPCOES DO JOGO', (85,205,255))
            text(44, os.path.basename(game))
            lines = ([f'{name:<9} < {value} >' for (name,_,_),value in zip(BUTTONS,config.values)] + ['Salvar controles']) if editing else (['Cancelar', 'Confirmar carregar progresso'] if confirm_load else ['Controles', 'Carregar progresso', 'Voltar a lista'])
            first = max(0, selected-8)
            for i,line in enumerate(lines[first:first+9],first):
                y=80+(i-first)*29
                if i==selected: fill(12,y-3,W-24,27,(30,85,135))
                text(y,line)
            if not editing: text(365,'Substitui o progresso atual. Copia de seguranca automatica.' if confirm_load else 'Carregar recupera a copia do save interno do jogo',(165,175,195))
            text(H-80,message,(210,210,145))
            text(H-53,'Cima/baixo: botao  Esq/dir: tecla  L/R: pular' if editing else 'A: escolher  B/START: voltar')
            text(H-27,'A em Salvar: aplicar  B: cancelar' if editing else 'Configuracao exclusiva deste jogo')
            sdl2.SDL_UpdateWindowSurface(win); dirty=False
        while sdl2.SDL_PollEvent(ctypes.byref(ev)):
            action = None
            if ev.type == sdl2.SDL_QUIT: return False
            if ev.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                b=ev.cbutton.button
                action={sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:'up',sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:'down',sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:'left',sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:'right',sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:'prev',sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:'next',sdl2.SDL_CONTROLLER_BUTTON_START:'back',sdl2.SDL_CONTROLLER_BUTTON_BACK:'back',sdl2.SDL_CONTROLLER_BUTTON_GUIDE:'back',sdl2.SDL_CONTROLLER_BUTTON_B if swap else sdl2.SDL_CONTROLLER_BUTTON_A:'ok',sdl2.SDL_CONTROLLER_BUTTON_A if swap else sdl2.SDL_CONTROLLER_BUTTON_B:'back'}.get(b)
            elif ev.type == sdl2.SDL_KEYDOWN:
                action={sdl2.SDLK_UP:'up',sdl2.SDLK_DOWN:'down',sdl2.SDLK_LEFT:'left',sdl2.SDLK_RIGHT:'right',sdl2.SDLK_RETURN:'ok',sdl2.SDLK_ESCAPE:'back',sdl2.SDLK_z:'ok',sdl2.SDLK_x:'back'}.get(ev.key.keysym.sym)
            elif ev.type == sdl2.SDL_JOYBUTTONDOWN and not sdl2.SDL_IsGameController(ev.jbutton.which):
                action={0:'back' if swap else 'ok',1:'ok' if swap else 'back',7:'back'}.get(ev.jbutton.button)
            elif ev.type == sdl2.SDL_JOYHATMOTION and not sdl2.SDL_IsGameController(ev.jhat.which):
                action={sdl2.SDL_HAT_UP:'up',sdl2.SDL_HAT_DOWN:'down',sdl2.SDL_HAT_LEFT:'left',sdl2.SDL_HAT_RIGHT:'right'}.get(ev.jhat.value)
            if not action: continue
            dirty=True
            count=len(BUTTONS)+1 if editing else (2 if confirm_load else 3)
            if action=='up': selected=(selected-1)%count
            elif action=='down': selected=(selected+1)%count
            elif action=='back':
                if confirm_load:
                    confirm_load=False; selected=1; continue
                if not editing: return True
                editing=False; selected=0; config=Controls(game); message='Alteracoes nao salvas descartadas'
            elif editing and selected<len(BUTTONS) and action in ('left','right','prev','next'):
                step={'left':-1,'right':1,'prev':-10,'next':10}[action]
                config.values[selected]=KEYS[(KEYS.index(config.values[selected])+step)%len(KEYS)]
            elif action=='ok':
                if editing and selected==len(BUTTONS):
                    try:
                        config.save(); editing=False; selected=0; message='Controles salvos para este jogo'
                    except OSError as e: message='Falha ao salvar: '+str(e)
                elif not editing:
                    if confirm_load:
                        if selected==1:
                            try:
                                progress_store.restore(os.path.join(HERE,'state'), game)
                                message='Progresso carregado. Volte e inicie o jogo.'
                            except (OSError, ValueError) as e: message='Falha ao carregar: '+str(e)
                        confirm_load=False; selected=1
                    elif selected==2: return True
                    elif selected==1:
                        try:
                            progress_store.read_snapshot(os.path.join(HERE,'state'),game)
                            confirm_load=True; selected=0; message=''
                        except FileNotFoundError: message='Nenhuma copia. Use Salvar progresso durante o jogo.'
                        except (OSError, ValueError) as e: message='Copia invalida: '+str(e)
                    else: editing=True; selected=0; message=''
        time.sleep(.016)
