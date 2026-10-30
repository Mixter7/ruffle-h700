import importlib.util, sys, types, tempfile, unittest, json
from pathlib import Path
from unittest import mock
SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE))
sys.modules['sdl2']=types.ModuleType('sdl2')
import progress_store, game_options
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.old=game_options.HERE; game_options.HERE=str(self.root)
    def tearDown(self):
        game_options.HERE=self.old; self.temp.cleanup()
    def snapshot(self, objects, game='one'):
        path=self.root/'progress'/f'{game}.json'; path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({'version':1,'game':game,'objects':objects}),encoding='utf-8')
    def test_controls_isolated_and_unknown_lines_kept(self):
        a=game_options.Controls('one.swf'); a.values[0]='F3'; a.save()
        b=game_options.Controls('two.swf'); self.assertEqual(b.values[0],'X')
        with open(a.path,'a') as f:f.write('FutureOption=keep\n')
        a=game_options.Controls('one.swf'); a.values[10]='W'; a.save()
        self.assertIn('FutureOption=keep',Path(a.path).read_text())
        self.assertEqual(game_options.Controls('one.swf').values[10],'W')
    def test_restore_and_backup_only_selected_objects(self):
        (self.root/'save.sol').write_bytes(b'new')
        (self.root/'other-game.sol').write_bytes(b'untouched')
        self.snapshot({'save':list(b'old')})
        progress_store.restore(self.root,'one.swf')
        self.assertEqual((self.root/'save.sol').read_bytes(),b'old')
        self.assertEqual((self.root/'other-game.sol').read_bytes(),b'untouched')
        backup=json.loads((self.root/'progress/one.before-load.json').read_text())
        self.assertEqual(bytes(backup['objects']['save']),b'new')
    def test_bad_snapshot_leaves_current_save_intact(self):
        for key,data in [('../outside',[1]),('/outside',[1]),('save',[300]),('save',[True])]:
            (self.root/'save.sol').write_bytes(b'current')
            self.snapshot({key:data})
            with self.assertRaises(ValueError): progress_store.restore(self.root,'one.swf')
            self.assertEqual((self.root/'save.sol').read_bytes(),b'current')
    def test_mid_restore_failure_rolls_back(self):
        for key in ['a','b']: (self.root/f'{key}.sol').write_bytes(b'current')
        self.snapshot({'a':[1],'b':[2]})
        original=progress_store.atomic_write; calls=[]
        def fail_once(path,data):
            calls.append(str(path))
            if str(path).endswith('b.sol') and calls.count(str(path))==1: raise OSError('simulated failure')
            return original(path,data)
        with mock.patch.object(progress_store,'atomic_write',fail_once):
            with self.assertRaises(OSError): progress_store.restore(self.root,'one.swf')
        for key in ['a','b']: self.assertEqual((self.root/f'{key}.sol').read_bytes(),b'current')
    def test_empty_copy_not_claimed_as_saved_progress(self):
        self.snapshot({'not-created':None})
        with self.assertRaises(ValueError): progress_store.read_snapshot(self.root,'one.swf')
if __name__=='__main__':unittest.main()
