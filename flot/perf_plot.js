function foo() {
    console.log("foo");
}

function do_plot(bench_name, placeholder_id, click_id, dataset) {
    data = []
    var hardwares = ["skl", "bdw"];
    var len = hardwares.length;
    for (var i = 0; i < len; i++) {
        var hardware = hardwares[i];
        var bench = dataset[bench_name][hardware];
        var d1 = {
            label: hardware,
            data:[]
        };
        for (var key in bench) {
            d1.data.push([bench[key]["date"] * 1000, bench[key]["score"]]);
        }
        data.push(d1);
    }
	$.plot(placeholder_id, data, {
        series: {
            lines: {
                show: true
            },
            points: {
                show:true
            }
        },
    	grid: {
			hoverable: false,
			clickable: true
		},
		yaxis: {
			min: 0.25
		},
		xaxis: {
			mode: "time",
	        minTickSize: [1, "day"]
		},
		legend: {
			position: "se"
		}
    });

	$(placeholder_id).bind("plotclick", function (event, pos, item) {
	    if (item) {
            $(click_id).text(dataset[bench_name][item.series.label][item.dataIndex]["commit"] +
                             " ==> score:" + dataset[bench_name][item.series.label][item.dataIndex]["score"] +
                             ", stddev: " + dataset[bench_name][item.series.label][item.dataIndex]["deviation"]);
		}
	});
}

$(function() {
    var data = {};
    $.ajax({
        dataType: 'text',
        url: "scores.json",
        data: data,
        success: function( data ) {
            // debugger;
            var d = JSON.parse(data);
            do_plot("OglBatch0", "#OglBatch0", "#click_OglBatch0", d);
            do_plot("OglBatch1", "#OglBatch1", "#click_OglBatch1", d);
            do_plot("OglBatch2", "#OglBatch2", "#click_OglBatch2", d);
            do_plot("OglBatch3", "#OglBatch3", "#click_OglBatch3", d);
            do_plot("OglBatch4", "#OglBatch4", "#click_OglBatch4", d);
            do_plot("OglBatch5", "#OglBatch5", "#click_OglBatch5", d);
            do_plot("OglBatch6", "#OglBatch6", "#click_OglBatch6", d);
            do_plot("OglBatch7", "#OglBatch7", "#click_OglBatch7", d);
            do_plot("OglCSCloth", "#OglCSCloth", "#click_OglCSCloth", d);
            do_plot("OglCSDof", "#OglCSDof", "#click_OglCSDof", d);
            do_plot("OglDeferred", "#OglDeferred", "#click_OglDeferred", d);
            do_plot("OglDeferredAA", "#OglDeferredAA", "#click_OglDeferredAA", d);
            do_plot("OglDrvRes", "#OglDrvRes", "#click_OglDrvRes", d);
            do_plot("OglDrvShComp", "#OglDrvShComp", "#click_OglDrvShComp", d);
            do_plot("OglDrvState", "#OglDrvState", "#click_OglDrvState", d);
            do_plot("OglFillPixel", "#OglFillPixel", "#click_OglFillPixel", d);
            do_plot("OglFillTexMulti", "#OglFillTexMulti", "#click_OglFillTexMulti", d);
            do_plot("OglFillTexSingle", "#OglFillTexSingle", "#click_OglFillTexSingle", d);
            do_plot("OglGeomPoint", "#OglGeomPoint", "#click_OglGeomPoint", d);
            do_plot("OglGeomTriList", "#OglGeomTriList", "#click_OglGeomTriList", d);
            do_plot("OglGeomTriStrip", "#OglGeomTriStrip", "#click_OglGeomTriStrip", d);
            do_plot("OglHdrBloom", "#OglHdrBloom", "#click_OglHdrBloom", d);
            do_plot("OglMultithread", "#OglMultithread", "#click_OglMultithread", d);
            do_plot("OglPSBump2", "#OglPSBump2", "#click_OglPSBump2", d);
            do_plot("OglPSBump8", "#OglPSBump8", "#click_OglPSBump8", d);
            do_plot("OglPSPhong", "#OglPSPhong", "#click_OglPSPhong", d);
            do_plot("OglPSPom", "#OglPSPom", "#click_OglPSPom", d);
            do_plot("OglShMapPcf", "#OglShMapPcf", "#click_OglShMapPcf", d);
            do_plot("OglShMapVsm", "#OglShMapVsm", "#click_OglShMapVsm", d);
            do_plot("OglTerrainFlyInst", "#OglTerrainFlyInst", "#click_OglTerrainFlyInst", d);
            do_plot("OglTerrainPanInst", "#OglTerrainPanInst", "#click_OglTerrainPanInst", d);
            do_plot("OglTerrainFlyTess", "#OglTerrainFlyTess", "#click_OglTerrainFlyTess", d);
            do_plot("OglTerrainPanTess", "#OglTerrainPanTess", "#click_OglTerrainPanTess", d);
            do_plot("OglTexFilterAniso", "#OglTexFilterAniso", "#click_OglTexFilterAniso", d);
            do_plot("OglTexFilterTri", "#OglTexFilterTri", "#click_OglTexFilterTri", d);
            do_plot("OglTexMem128", "#OglTexMem128", "#click_OglTexMem128", d);
            do_plot("OglTexMem512", "#OglTexMem512", "#click_OglTexMem512", d);
            do_plot("OglVSDiffuse1", "#OglVSDiffuse1", "#click_OglVSDiffuse1", d);
            do_plot("OglVSDiffuse8", "#OglVSDiffuse8", "#click_OglVSDiffuse8", d);
            do_plot("OglVSInstancing", "#OglVSInstancing", "#click_OglVSInstancing", d);
            do_plot("OglVSTangent", "#OglVSTangent", "#click_OglVSTangent", d);
            do_plot("OglZBuffer", "#OglZBuffer", "#click_OglZBuffer", d);
            do_plot("egypt", "#egypt", "#click_egypt", d);
            do_plot("egypt_o", "#egypt_o", "#click_egypt_o", d);
            do_plot("fill", "#fill", "#click_fill", d);
            do_plot("fill_o", "#fill_o", "#click_fill_o", d);
            do_plot("fur", "#fur", "#click_fur", d);
            do_plot("heaven", "#heaven", "#click_heaven", d);
            do_plot("manhattan", "#manhattan", "#click_manhattan", d);
            do_plot("manhattan_o", "#manhattan_o", "#click_manhattan_o", d);
            do_plot("plot3d", "#plot3d", "#click_plot3d", d);
            do_plot("trex", "#trex", "#click_trex", d);
            do_plot("trex_o", "#trex_o", "#click_trex_o", d);
            do_plot("triangle", "#triangle", "#click_triangle", d);
            do_plot("valley", "#valley", "#click_valley", d);
            do_plot("warsow", "#warsow", "#click_warsow", d);
            do_plot("xonotic", "#xonotic", "#click_xonotic", d);
        }
    });
	// Add the Flot version string to the footer
	$("#footer").prepend("Flot " + $.plot.version + " &ndash; ");
});
// end hiding script from old browsers -->
