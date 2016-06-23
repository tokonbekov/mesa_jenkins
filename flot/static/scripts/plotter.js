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
