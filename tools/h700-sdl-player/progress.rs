use ruffle_core::backend::storage::StorageBackend;
use ruffle_frontend_utils::backends::storage::DiskStorageBackend;
use std::{collections::BTreeMap, path::{Path, PathBuf, Component}, sync::{Arc, Mutex}};
#[derive(Default)]
struct Data { objects: BTreeMap<String,Option<Vec<u8>>>, failed: bool }
#[derive(Clone,Default)]
pub struct Progress(Arc<Mutex<Data>>);
pub struct Storage { disk: DiskStorageBackend, progress: Progress }
fn allowed(name: &str) -> bool {
    !name.is_empty() && !name.contains('\\') && !name.contains(':') && Path::new(name).components().all(|c| matches!(c,Component::Normal(_)))
}
impl Progress {
    pub fn storage(&self) -> Storage { Storage { disk:DiskStorageBackend::new(PathBuf::from("./")),progress:self.clone() } }
    pub fn save(&self, game:&str) -> Result<(),String> {
        let data=self.0.lock().unwrap();
        if data.failed { return Err("Falha ao gravar save interno; copia nao alterada".into()); }
        if !data.objects.values().any(|v| v.is_some()) { return Err("Este jogo ainda nao criou um save interno".into()); }
        let snapshot=serde_json::json!({"version":1,"game":game,"objects":data.objects});
        let path=Path::new("progress").join(format!("{}.json",game));
        std::fs::create_dir_all("progress").map_err(|e| e.to_string())?;
        let tmp=path.with_extension("json.tmp");
        use std::io::Write;
        let mut f=std::fs::File::create(&tmp).map_err(|e| e.to_string())?;
        f.write_all(snapshot.to_string().as_bytes()).and_then(|_| f.sync_all()).map_err(|e|e.to_string())?;
        std::fs::rename(tmp,path).map_err(|e|e.to_string())
    }
}
impl StorageBackend for Storage {
    fn get(&self,name:&str)->Option<Vec<u8>> {
        if !allowed(name) { return None; }
        let value=self.disk.get(name);
        self.progress.0.lock().unwrap().objects.insert(name.into(),value.clone());
        value
    }
    fn put(&mut self,name:&str,value:&[u8])->bool {
        if !allowed(name) { self.progress.0.lock().unwrap().failed=true; return false; }
        let ok=self.disk.put(name,value);
        let mut data=self.progress.0.lock().unwrap();
        if ok { data.objects.insert(name.into(),Some(value.to_vec())); } else { data.failed=true; }
        ok
    }
    fn remove_key(&mut self,name:&str) {
        if !allowed(name) { return; }
        self.disk.remove_key(name);
        let mut data=self.progress.0.lock().unwrap();
        if self.disk.get(name).is_some() { data.failed=true; } else { data.objects.insert(name.into(),None); }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn shared_object_names_cannot_escape_storage() {
        for name in ["../outside","/absolute","C:/outside","a/../../b","a\\b",""] { assert!(!allowed(name)); }
        assert!(allowed("localhost/games/test.swf/progress"));
    }
}
