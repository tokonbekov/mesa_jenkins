#!/usr/bin/python
import datetime
import os
import yaml
from . import ProjectMap, Options, RevisionSpecification, run_batch_command, Export

class PerfBuilder(object):
    def __init__(self, benchmark):
        self._benchmark = benchmark
        self._pm = ProjectMap()

    def build(self):
        # todo(majanes) possibly verify that benchmarks are in /opt
        pass
    def test(self):
        o = Options()
        save_dir = os.getcwd()
        hw = o.hardware[:3]
        mesa_dir = "/tmp/build_root/perf/" + hw + "/usr/local/lib"
        scores = []
        os.chdir(self._pm.project_source_dir("sixonix"))
        for _ in range(0,2):
            cmd = ["./glx.sh", mesa_dir, self._benchmark.upper()]
            print " ".join(cmd)
            (out, err) = run_batch_command(cmd, streamedOutput=False)
            if err:
                print "err: " + err
            scores.append(float(out.splitlines()[-1]))

        os.chdir(save_dir)
        result = yaml.load("{}")
        r = str(RevisionSpecification().revision("mesa"))
        scale = yaml.load(open(self._pm.project_build_dir("sixonix") + "/scale.yml"))[self._benchmark][hw]
        result[self._benchmark] = {hw: {"mesa=" + r: [{"score": scores, "scale": scale}]}}
        out_dir = "/tmp/build_root/perf/scores/" + self._benchmark + "/" + hw + "/mesa=" + r
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        outf = out_dir + "/" + datetime.datetime.now().isoformat() + ".yml"
        with open(outf, 'w') as of:
            yaml.dump(result, stream=of)
                
        Export().export_perf()

    def clean(self):
        pass


