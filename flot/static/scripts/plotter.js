function do_plot(bench_name, placeholder_id, click_id, dataset) {
    data = []
    var hardwares = ["skl", "bdw"];
    var colors = ["#edc240", "#afd8f8", "#cb4b4b", "#4da74d", "#9440ed"];
    var len = hardwares.length;
    var ymax = 0;
    for (var i = 0; i < len; i++) {
        var hardware = hardwares[i];
        var bench = dataset[bench_name][hardware]["mesa"];
        var data_points = {
            errorbars: "y",
            show: true,
			yerr: {show:true, upperCap: "-", lowerCap: "-", color: colors[i]},
            lineWidth: 1
        }
        
        var d1 = {
            label: hardware,
            data: [],
            points: data_points
        };
        for (var key in bench) {
            var score = bench[key]["score"];
            var deviation = bench[key]["deviation"];
            var point = [bench[key]["date"] * 1000, score];
            if (deviation > 0.05) {
                point.push(deviation);
            } else {
                point.push(0);
            }
            d1.data.push(point);
            if (score + deviation > ymax) {
                ymax = score + deviation;
            }
        }
        data.push(d1);
    }
    var markings = []
    for (var i = 0; i < len; i++) {
        var hardware = hardwares[i];
        var ufo_score = dataset[bench_name][hardware]["UFO"];
        markings.push({ color: colors[i], lineWidth: 2,
                        yaxis: { from: ufo_score, to: ufo_score } });
        if (ufo_score > ymax) {
            ymax = ufo_score;
        }
    }
    ymax = Math.round(ymax * 10.0 + 0.5) / 10.0;
	var plot = $.plot(placeholder_id, data, {
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

	var placeholder = $(placeholder_id);
    for (var i = 0; i < len; i++) {
        var hardware = hardwares[i];
        var ufo_score = dataset[bench_name][hardware]["UFO"];
        var o = plot.pointOffset({ y: ufo_score });
        console.log("i:" + i);
        placeholder.append("<div style='position:absolute;left:" +
                           (75 * (i + 1)).toString() + "px;top:" + o.top +
                           "px;color:" + colors[i] + ";font-size:smaller'>GEOD: " +
                           hardware + "</div>");
    }
    
	$(placeholder_id).bind("plotclick", function (event, pos, item) {
	    if (item) {
            var sha = dataset[bench_name][item.series.label]["mesa"][item.dataIndex]["commit"].slice(5);
            $(click_id).html(
                '<table><tr><td/><td/></tr>' +
                '<tr><td>Commit</td>' +
                '<td><a href="https://cgit.freedesktop.org/mesa/mesa/commit/?id=' + sha + '">' + sha  + '</a></td>' +
                '<tr><td>Score</td>' +
                '<td>' + dataset[bench_name][item.series.label]["mesa"][item.dataIndex]["score"] + '</td>' +
                '<tr><td>Standard Deviation</td>' +
                '<td>' + dataset[bench_name][item.series.label]["mesa"][item.dataIndex]["deviation"] + '</td>' +
                '</tr></table>'
            );
		}
	});
}
