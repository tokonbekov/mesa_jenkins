#!/usr/bin/python3
# encoding=utf-8
# Copyright © 2016 Intel Corporation

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Flask webpage for performance data."""

import flask  # pylint: disable=import-error
from mako.lookup import TemplateLookup

APP = flask.Flask(__name__)

# TODO: Add a modules directory and possibly cache
TEMPLATES = TemplateLookup('templates')

# TODO: It might be better to autodiscover this list
_BENCHMARKS = [
    'OglBatch0',
    'OglBatch1',
    'OglBatch2',
    'OglBatch3',
    'OglBatch4',
    'OglBatch5',
    'OglBatch6',
    'OglBatch7',
    'OglCSCloth',
    'OglCSDof',
    'OglDeferred',
    'OglDeferredAA',
    'OglDrvRes',
    'OglDrvShComp',
    'OglDrvState',
    'OglFillPixel',
    'OglFillTexMulti',
    'OglFillTexSingle',
    'OglGeomPoint',
    'OglGeomTriList',
    'OglGeomTriStrip',
    'OglHdrBloom',
    'OglMultithread',
    'OglPSBump2',
    'OglPSBump8',
    'OglPSPhong',
    'OglPSPom',
    'OglShMapPcf',
    'OglShMapVsm',
    'OglTerrainFlyInst',
    'OglTerrainPanInst',
    'OglTerrainFlyTess',
    'OglTerrainPanTess',
    'OglTexFilterAniso',
    'OglTexFilterTri',
    'OglTexMem128',
    'OglTexMem512',
    'OglVSDiffuse1',
    'OglVSDiffuse8',
    'OglVSInstancing',
    'OglVSTangent',
    'OglZBuffer',
    'egypt',
    'egypt_o',
    'fill',
    'fill_o',
    'fur',
    'heaven',
    'manhattan',
    'manhattan_o',
    'plot3d',
    'trex',
    'trex_o',
    'triangle',
    'valley',
    'warsow',
    'xonotic',
]


@APP.route('/')
def front():
    return TEMPLATES.get_template('all.html.mako').render(
        benchmarks=_BENCHMARKS,
        css=flask.url_for('static', filename='examples.css'),
        plotjs=flask.url_for('static', filename='scripts/perf_plot.js'),
        javascript=flask.url_for('static', filename='javascript'),
    )


if __name__ == '__main__':
    APP.run()
