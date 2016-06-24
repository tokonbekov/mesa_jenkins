function do_plot(bench_name, placeholder_id, click_id, dataset) {
    data = []
    var hardwares = ["skl", "bdw"];
    var colors = ["#edc240", "#afd8f8", "#cb4b4b", "#4da74d", "#9440ed"];
    var len = hardwares.length;
    var ymax = 0;
    for (var i = 0; i < len; i++) {
        var hardware = hardwares[i];
        var bench = dataset[bench_name][hardware]["mesa"];
        var d1 = {
            label: hardware,
            data:[]
        };
        for (var key in bench) {
            var score = bench[key]["score"]
            d1.data.push([bench[key]["date"] * 1000, score]);
            if (score > ymax) {
                ymax = score;
            }
        }
        data.push(d1);
    }
    var markings = []
    for (var i = 0; i < len; i++) {
        var hardware = hardwares[i];
        var ufo_score = dataset[bench_name][hardware]["UFO"];
        markings.push({ color: colors[i], lineWidth: 2, yaxis: { from: ufo_score, to: ufo_score } });
        if (ufo_score > ymax) {
            ymax = ufo_score;
        }
    }
    ymax = Math.round(ymax * 10.0 + 0.5) / 10.0;
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
			clickable: true,
            markings: markings
		},
		yaxis: {
			min: 0.25,
            max: ymax
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
