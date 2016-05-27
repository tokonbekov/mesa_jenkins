#!/usr/bin/python

import glob
import json
import os.path as path
import sys
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs

class MesaStats:
    def __init__(self):
        self.opts = bs.Options()


    def merge_scores(self, all_scores, score):
        for k,v in score.iteritems():
            if k not in all_scores:
                # initialize default
                if isinstance(v, list):
                    all_scores[k] = []
                else:
                    all_scores[k] = {}

            if isinstance(v, list):
                all_scores[k] += v
            else:
                self.merge_scores(all_scores[k], v)

    def test(self):
        # create per-benchmark-per-platform files containing all
        # scores to date

        # at a later point, we may want to combine data sets so
        # developers can see all skylake benchmarks together, for
        # example.

        # canoninical path is
        # /mnt/jenkins/results/perf/mesa={rev}/m64/scores/{benchmark}/{platform}/{date}.json:
        all_scores = {}
        for a_score_file in glob.glob(self.opts.result_path +
                                      "/../*/m64/scores/*/*/*.json"):
            with open(a_score_file, "r") as f:
                a_score = json.load(f)
            self.merge_scores(all_scores, a_score)
        with open(self.opts.result_path + "/../scores.json", "w") as of:
            json.dump(all_scores, fp=of)

    def build(self):
        pass
    def clean(self):
        pass


bs.build(MesaStats())
