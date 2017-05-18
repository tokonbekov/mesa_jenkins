function do_plot(bench_name, placeholder_id, click_id, dataset) {
    data = []
    var hardwares = ["skl", "bdw", "bsw", "bxt"];
    var colors = ["#edc240", "#afd8f8", "#cb4b4b", "#4da74d", "#9440ed"];
    var len = hardwares.length;
    var ymax = 0;
    for (var i = 0; i < len; i++) {
        var hardware = hardwares[i];
        if (!(hardware in dataset[bench_name])) {
            continue;
        }
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
        if (hardware in dataset[bench_name] && "UFO" in dataset[bench_name][hardware]) {
            var ufo_score = dataset[bench_name][hardware]["UFO"];
            markings.push({ color: colors[i], lineWidth: 2,
                            yaxis: { from: ufo_score, to: ufo_score } });
            if (ufo_score > ymax) {
                ymax = ufo_score;
            }
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
			min: 0.0,
            max: ymax,
            zoomRange: false
		},
		xaxis: {
			mode: "time",
	        minTickSize: [1, "day"]
		},
		legend: {
			position: "se"
		},
        zoom: {
			interactive: true
		},
		pan: {
			interactive: true
		}
    });

	var placeholder = $(placeholder_id);
    for (var i = 0; i < len; i++) {
        var hardware = hardwares[i];
        if ((hardware in dataset[bench_name]) && ("UFO" in dataset[bench_name][hardware])) {
            var ufo_score = dataset[bench_name][hardware]["UFO"];
            var o = plot.pointOffset({ y: ufo_score });
            placeholder.append("<div style='position:absolute;left:50px;bottom:" +
                               (10 + (25 * (i + 1))).toString() + "px;color:" +
                               colors[i] + ";font-size:smaller'>UFO " +
                               hardware + " : " + ufo_score.toFixed(3).toString() +
                               "<hr width=60 color='" + colors[i] +
                               "' size=2 align=LEFT></div>");
        }
    }

    $("div#dialog").dialog( {
        modal: true,
        buttons: {
            Ok: function() { $(this).dialog("close"); }
        }
    });
    $("div#dialog").dialog("close");
    
    /* This function will build some data below the graph, information about
     * the commit, standard deviation, the averaged score of the tests, and
     * will build buttons to build a newer and older sha.
     */
	$(placeholder_id).bind("plotclick", function (event, pos, item) {
	    if (item) {
            // Only try to get a previous sha if we are not on the oldest sha already
            if (item.dataIndex !== 0) {
                var prev_sha = dataset[bench_name][item.series.label]["mesa"][item.dataIndex - 1]["commit"].slice(5);
            } else {
                var prev_sha = '';
            }

            // The current sha is always valid
            var curr_sha = dataset[bench_name][item.series.label]["mesa"][item.dataIndex]["commit"].slice(5);
            
            // Only try to get the next sha if we are not on the newest sha
            if (item.dataIndex !== (dataset[bench_name][item.series.label]["mesa"].length - 1)) {
                var next_sha = dataset[bench_name][item.series.label]["mesa"][item.dataIndex + 1]["commit"].slice(5);
            } else {
                var next_sha = '';
            }

            // This builds the raw html for each button, simplifying the html
            // setup below somewhat
            var build_buttons = new Array(2);
            build_buttons[0] = '<input type="submit" id="build_old" value="Build Older">'
            build_buttons[1] = '<input type="submit" id="build_new" value="Build Newer">'

            // Build the table of data and the raw html for the buttons
            $(click_id).html(
                '<div><table><tr><td/><td/></tr>' +
                '<tr><td>Commit</td>' +
                '<td><a href="https://cgit.freedesktop.org/mesa/mesa/commit/?id=' + curr_sha + '">' + curr_sha  + '</a></td>' +
                '<tr><td>Score</td>' +
                '<td>' + dataset[bench_name][item.series.label]["mesa"][item.dataIndex]["score"] + '</td>' +
                '<tr><td>Standard Deviation</td>' +
                '<td>' + dataset[bench_name][item.series.label]["mesa"][item.dataIndex]["deviation"] + '</td>' +
                '</tr></table></div><br />' +
                '<div>' + build_buttons.join(' ') + '</div>'
            );

            // Setup the buttons, this registers the links to call when we're ready to build things
            $(function() { 
                $("#build_old").button().click(
                    function() { 
                        window.open("http://otc-mesa-ci.jf.intel.com/job/perf/buildWithParameters?token=noauth&revision=" + prev_sha + ":" + curr_sha).close();
                        $("div#dialog").html(
                            "<p>Build successfully submitted for sha between " + prev_sha + " and " + curr_sha + "</p>" +
                            '<p><a href="http://otc-mesa-ci.jf.intel.com/view/All/job/perf/">Jenkins Job</a></p>'
                        );
                        $("div#dialog").dialog("open");
                    }
                );
                $("#build_new").button().click(
                    function() {
                        window.open("http://otc-mesa-ci.jf.intel.com/job/perf/buildWithParameters?token=noauth&revision=" + curr_sha + ":" + next_sha).close();
                        $("div#dialog").html(
                            "<p>Build successfully submitted for sha between " + curr_sha + " and " + next_sha + "</p>" +
                            '<p><a href="http://otc-mesa-ci.jf.intel.com/view/All/job/perf/">Jenkins Job</a></p>'
                        );
                        $("div#dialog").dialog("open");
                    }
                );

                // Disable the build_old button if we are on the oldest value
                if (item.dataIndex === 0) {
                    $("#build_old").button("disable");
                } 
            });
		}
	});
}
