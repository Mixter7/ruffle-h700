// Wall-clock timings, not GPU queries. Render is CPU submission time; swap
// includes display synchronization and any driver/GPU blocking there.
struct H700Perf {
    start: Instant,
    loops: u64,
    presents: u64,
    total: [u64; 3],
    peak: [u64; 3],
}
impl H700Perf {
    fn new() -> Self {
        Self { start: Instant::now(), loops: 0, presents: 0, total: [0;3], peak: [0;3] }
    }
    fn record(&mut self, tick: u64, render: u64, swap: u64, presented: bool) {
        self.loops += 1;
        self.presents += u64::from(presented);
        for (i,value) in [tick,render,swap].into_iter().enumerate() {
            self.total[i] += value;
            self.peak[i] = self.peak[i].max(value);
        }
        let seconds = self.start.elapsed().as_secs_f64();
        if seconds >= 10.0 {
            let loop_count = self.loops.max(1) as f64;
            let presents = self.presents.max(1) as f64;
            println!("H700 timing seconds={:.2} loops={} presents={} presents_per_second={:.2} tick_avg_ms={:.3} render_submit_avg_ms={:.3} swap_avg_ms={:.3} tick_max_ms={:.3} render_submit_max_ms={:.3} swap_max_ms={:.3} tick_wall_percent={:.1} render_submit_wall_percent={:.1} swap_wall_percent={:.1}",
                seconds, self.loops, self.presents, self.presents as f64/seconds,
                self.total[0] as f64/loop_count/1000.0,
                self.total[1] as f64/presents/1000.0,self.total[2] as f64/presents/1000.0,
                self.peak[0] as f64/1000.0,self.peak[1] as f64/1000.0,self.peak[2] as f64/1000.0,
                self.total[0] as f64/seconds/10000.0,self.total[1] as f64/seconds/10000.0,self.total[2] as f64/seconds/10000.0);
            *self = Self::new();
        }
    }
}
