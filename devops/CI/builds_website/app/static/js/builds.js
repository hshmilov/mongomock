    var current_instances = [];
    var show_terminated_instances = false;
    var current_demos = [];
    var current_demo_details_i = 0;

    var current_exports = [];
    var current_export_details_i = 0;
    var current_exports_in_progress = [];
    var show_completed_exports = false;
    var advanced_usage = false;

    var current_auto_tests_in_progress = [];

    var current_configurations = [];
    var instance_vm_type = "instance";
    var code_source = "Branch";
    var CLOUD_DEFAULT_KEY = 'Builds-VM-Key';

    var last_custom_configuration_code = "";
    var is_in_custom_configuration_code = false;
    var github_token = "githubreadonly@axonius.com:3Zc0kRElHCzhHbM1u0LX";


    /* Global functions */
    function capitalize_str(str) {
        if (str === undefined || str.length == 0) {
            return "Unknown";
        }
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    function update_panel(panel_id, data) {
        /* Takes a panel id and an array of arrays representing the data, and updates it.

        For example:
        data = [["Delete", $("<a>").attr("href", "/delete")]];
        update_panel("panel_id", data);
        */

        var panel = $("#" + panel_id).html("");

        for (var i = 0; i < data.length; i++) {
            var tr = $("<tr>");
            $("<td>").append(data[i][0]).appendTo(tr);
            $("<td>").append(data[i][1]).appendTo(tr);
            panel.append(tr);
        }

        // syntax highlight
         $('pre code').each(function(i, block) {
            hljs.highlightBlock(block);
        });
    }
    function flush_url(url_to_flush, success_function){
        $.ajax({url: url_to_flush, type: "GET", success: success_function})
            .fail(exception_modal);
    }
    function new_modal(title, yes_function, fields, is_big, message, validation) {
        var m = $("#generic_modal").clone();
        m.attr("id", "new_modal");
        m.find(".modal-title").text(title);

        // If the user requested a big modal, change the class to big.
        m.find(".modal-dialog").addClass("modal-lg");

        if (message == undefined ){
            message = "Fill in these details:";
        }

        message += "<br><br>";

        if (validation !== undefined) {
            message = 'Please confirm your action by typing <code>' + validation + '</code>: <br><br>'
            validation_button = $('<input>').addClass('modal-input').addClass('form-control').attr('type', 'text').attr('placeholder', validation);
        }

        // build the body

        if (fields != undefined) {
            var modal_body = m.find(".modal-body");
            modal_body.html(message);
            var fields_table = $("<table>").addClass("new_instance_table");
            for (var i in fields) {
                var field = fields[i];
                var tr = $("<tr>");
                if (field['type'] == 'textarea') {
                    var input = $("<textarea>").attr("rows", field['rows']).text(field["value"]);
                }
                else {
                    var input = $("<input>").attr("type", "text").attr("value", field["value"]);
                }
                input.addClass("modal-input").addClass("form-control").attr("name", field['name']).attr("placeholder", field['name']);
                if (field["disabled"] == true) {
                    input.attr("disabled", "true");
                }
                $("<td>").text(field['name']).appendTo(tr);
                $("<td>").append(input).appendTo(tr);
                tr.appendTo(fields_table);
            }
            modal_body.append(fields_table);
        }

        var yes_button = m.find("#generic_modal_yes_button").prop('disabled', true);
        if (validation !== undefined) {
            $(validation_button).on('input', function() { yes_button.prop("disabled", $(validation_button).val() !== validation)});
            modal_body.append(validation_button);
        }

        yes_button.one("click", function() {
            yes_button.text("Loading..");
            yes_button.prop("disabled", true)

            var results = [];
            var all_inputs = m.find(".modal-input")
            for (var i = 0; i < all_inputs.length; i++) {
                field = all_inputs[i];
                results.push({"name": field.name, "value": field.value, "rows": 2});
            }

            // call the yes function and make the modal hide
            yes_function(function() {
                m.modal("hide").on("hidden.bs.modal", function() {
                    m.remove();
                });
            }, results);
        });

        // show the modal
        $("#main_container").append(m);
        m.modal();
    }
    function wrap_modal_with_td(title, f, fields, message, validation) {
        // Gets modal details and returns a td column that has a link that opens it.
            return $("<td>").html($("<a>").attr("href", "#").text("Click Here").
                    click(function() {
                        new_modal(title, f, fields, false, message, validation);
                        return false;
                }));
        }

    function exception_modal(data) {
                $("#modal_error .modal-body")[0].innerText = data.responseText;
                $("#modal_error").modal()
    }
    function update_datatable(table_id, dataSet, onclick_function) {
        var table = $("#" + table_id);
        table.DataTable().clear();
        table.DataTable().rows.add(dataSet);
        table.DataTable().draw()

        if (onclick_function != undefined) {
            table.find("tr").css("cursor", "pointer");
            table.on("click", "tbody tr", function() {
                table.find("tbody").children().removeClass("active")
                $(this).toggleClass("active");

                var id = parseInt($(this).children()[0].innerHTML) - 1; // The id is in the first column.
                onclick_function(id);
            });
        }
    }

    // Update and rewrite functions
    function rewrite_instances_table() {
        let dataSet = [];
        for (i in current_instances) {
            if (current_instances[i]['cloud']['state'] !== 'terminated' || show_terminated_instances === true) {
                data = [];
                db = current_instances[i]["db"];
                cloud = current_instances[i]["cloud"];

                ip = cloud["private_ip"];
                ip_link = "";
                if (ip != null) {
                    // Yep i know its a bad thing....
                    if (Date.parse(db["date"]) < Date.parse("2018-04-22")) {
                        ip_link = "<a href='http://" + ip + "' target='_blank'>http://" + ip + "</a>";
                    }
                    else {
                        ip_link = "<a href='https://" + ip + "' target='_blank'>https://" + ip + "</a>";
                    }
                }

                // Push all of the data
                data.push(parseInt(i) + 1);
                data.push(db['name'] || cloud['name']);
                data.push(cloud['type'])
                data.push(capitalize_str(db["owner"]));
                data.push(ip_link);
                data.push(cloud['state']);

                dataSet.push(data);
            }
        }

        update_datatable("instances_table", dataSet, update_instance_details)
    }
    function rewrite_demos_table() {
        let dataSet = [];
        for (i in current_demos) {
            if (current_demos[i]['cloud']['state'] !== 'terminated' || show_terminated_instances === true) {
                data = [];
                db = current_demos[i]["db"];
                cloud = current_demos[i]["cloud"];

                ip = cloud["private_ip"];
                public_ip = cloud["public_ip"]
                ip_link = "";
                if (ip != null) {
                    // Yep i know its a bad thing....
                    if (Date.parse(db["date"]) < Date.parse("2018-04-22")) {
                        ip_link = "<a href='http://" + ip + "' target='_blank'>http://" + ip + "</a>";
                    }
                    else {
                        ip_link = "<a href='https://" + ip + "' target='_blank'>https://" + ip + "</a>";
                    }
                }

                public_ip_link = "";
                if (ip != null) {
                    // Yep i know its a bad thing....
                    if (Date.parse(db["date"]) < Date.parse("2018-04-22")) {
                        public_ip_link = "<a href='http://" + public_ip + "' target='_blank'>http://" + public_ip + "</a>";
                    }
                    else {
                        public_ip_link = "<a href='https://" + public_ip + "' target='_blank'>https://" + public_ip + "</a>";
                    }
                }

                // Push all of the data
                data.push(parseInt(i) + 1);
                data.push(db['name'] || cloud['name']);
                data.push(cloud['type'])
                data.push(ip_link);
                data.push(public_ip_link);
                data.push(cloud['state']);

                dataSet.push(data);
            }
        }
        update_datatable("demos_table", dataSet, update_demo_details)
    }
    function rewrite_auto_tests_table() {
        let dataSet = [];
        for (i in current_auto_tests_in_progress) {
            if (current_auto_tests_in_progress[i]['cloud']['state'] !== 'terminated' || show_terminated_instances === true) {
                data = [];
                db = current_auto_tests_in_progress[i]["db"];
                cloud = current_auto_tests_in_progress[i]["cloud"];

                ip = cloud["private_ip"];
                ip_link = "";
                if (ip != null) {
                    // Yep i know its a bad thing....
                    if (Date.parse(db["date"]) < Date.parse("2018-04-22")) {
                        ip_link = "<a href='http://" + ip + "' target='_blank'>http://" + ip + "</a>";
                    } else {
                        ip_link = "<a href='https://" + ip + "' target='_blank'>https://" + ip + "</a>";
                    }
                }

                // Push all of the data
                data.push(parseInt(i) + 1);
                data.push(db['name'] || cloud['name']);
                data.push(cloud['type'])
                data.push(capitalize_str(db["owner"]));
                data.push(ip_link);
                data.push(cloud['state']);

                dataSet.push(data);
            }
        }

        update_datatable("auto_tests_table", dataSet, update_auto_test_details)
    }
    function rewrite_exports_table() {
        dataSet = []
        for (i in current_exports) {
            var export_i = current_exports[i];
            var data = [];

            // Capitalize owner name
            export_i["owner"] = capitalize_str(export_i["owner"])

            // Push all of the data
            data.push(parseInt(i) + 1);
            data.push(export_i["version"]);
            data.push(export_i["owner"]);
            data.push(export_i["fork"]);
            data.push(export_i["branch"]);
            data.push(export_i["client_name"]);
            data.push(export_i["comments"]);
            data.push(export_i["status"]);
            data.push(export_i["date"]);
            dataSet.push(data);
        }

        update_datatable("exports_table", dataSet, update_export_details)
    }
    function rewrite_exports_in_progress_table() {
        // Update all exports currently in progress.
        let dataSet = [];
        for (var i in current_exports_in_progress) {
            var export_i = current_exports_in_progress[i];
            if (show_completed_exports === true || export_i['status'] !== 'completed') {
                var data = [];

                // Capitalize owner name
                export_i["owner"] = capitalize_str(export_i["owner"])

                // Push all of the data
                data.push(parseInt(i) + 1);
                data.push(export_i["version"]);
                data.push(export_i["owner"]);
                data.push(export_i["fork"]);
                data.push(export_i["branch"]);
                data.push(export_i["client_name"]);
                data.push(export_i["comments"]);
                data.push("<a herf=\"javascript:void(0);\" onclick=\"open_running_export_log('" + export_i["version"]  + "')\">Click Here</a>");
                data.push(export_i["status"]);
                data.push(export_i["date"]);
                dataSet.push(data);
            }
        }
        update_datatable("exports_in_progress_table", dataSet)
    }


    // Update instance details functions
    function update_instance_details(i) {
        current_instance_details_i = i;
        var inst = current_instances[i];
        var inst_name = inst['db']['name'] || inst['cloud']['name']

        security_groups = inst['cloud']['security_groups']
        if (security_groups !== undefined) {
            security_groups = security_groups.join(',')
        }

        icon = '<img style="width: 32px" src="/static/images/' + inst['cloud']['cloud'] + '.png" />&nbsp;&nbsp;'
        var vm_info_data = [
            ["Cloud", icon + inst['cloud']['cloud']],
            ["Cloud ID", inst['cloud']['id']],
            ["State", inst['cloud']['state']],
            ["Image Id", inst['cloud']['image_id']],
            ["Image", inst['cloud']['image']],
            ["Instance Type", inst['cloud']['type']],
            ["Key Name", inst['cloud']['key_name'] || inst['db']['key_name']],
            ["Private IP Address", inst['cloud']['private_ip']],
            ["Public IP Address", inst['cloud']['public_ip']],
            ["Security Groups", security_groups],
            ["Subnet", inst['cloud']['subnet']]
        ];

        var instance_info_data = [
            ["Name", inst['db']['name']],
            ["Owner", inst['db']['owner']],
            ["Fork", ("fork" in inst['db']) ? inst['db']['fork'] : ""],
            ["Branch", ("branch" in inst['db']) ? inst['db']['branch'] : ""],
            ["Date Created", inst['db']['date']],
            ["Comments", (inst['db']['comments']) ? inst['db']['comments'].replace("\n", "<br>") : ""]
        ];

        var actions_data = [];  // if its terminated or shutting down we still provide an empty array to update_panel.

        /* Gets a function, wraps it with an are you sure modal, and returns a link object that
        links to it.
         */

        var cloud_state = inst['cloud']['state'];
        if (cloud_state !== 'terminated' && cloud_state !== 'shutting-down' && cloud_state !== 'pending') {
            actions_data = [
                ["Terminate", wrap_modal_with_td("Are you sure you want to terminate " + inst_name + "?", function (yes_function) { return terminate_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]
            ];

             if (cloud_state === "running") {
                 actions_data.unshift(["Stop", wrap_modal_with_td("Are you sure you want to stop " + inst_name + "?", function (yes_function) { return stop_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]);
             }
             else {
                 actions_data.unshift(["Start", wrap_modal_with_td("Are you sure you want to start " + inst_name + "?", function (yes_function) { return start_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]);
             }

             var bot_monitoring = inst['db']['bot_monitoring'];

            if (bot_monitoring === "false"){
                actions_data.unshift(["Enable Bot Monitoring",
                    wrap_modal_with_td("Are you sure you want to enable the bot monitoring for " + inst_name + "?", function(yes_function) { return enable_bot_monitoring(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)
                ]);
            }
            else {
                actions_data.unshift(["Disable Bot Monitoring",
                    wrap_modal_with_td("Are you sure you want to disable the bot monitoring for " + inst_name + "?", function(yes_function) { return disable_bot_monitoring(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)
                ]);
            }
        }

        var instance_info_and_actions_data = instance_info_data.concat(actions_data);

        update_panel("tbody_vm_info", vm_info_data);
        update_panel("tbody_instance_info", instance_info_and_actions_data);

    }
    function update_demo_details(i) {
        current_demo_details_i = i;
        var inst = current_demos[i];
        var inst_name = inst['db']['name'] || inst['cloud']['name']

        security_groups = inst['cloud']['security_groups']
        if (security_groups !== undefined) {
            security_groups = security_groups.join(',')
        }

        icon = '<img style="width: 32px" src="/static/images/' + inst['cloud']['cloud'] + '.png" />&nbsp;&nbsp;'
        var vm_info_data = [
            ["Cloud", icon + inst['cloud']['cloud']],
            ["Cloud ID", inst['cloud']['id']],
            ["State", inst['cloud']['state']],
            ["Image Id", inst['cloud']['image_id']],
            ["Image", inst['cloud']['image']],
            ["Instance Type", inst['cloud']['type']],
            ["Key Name", inst['cloud']['key_name']],
            ["Private IP Address", inst['cloud']['private_ip']],
            ["Public IP Address", inst['cloud']['public_ip']],
            ["Security Groups", security_groups],
            ["Subnet", inst['cloud']['subnet']]
        ];

        var demo_info_data = [
            ["Name", inst['db']['name']],
            ["Owner", inst['db']['owner']],
            ["Fork", ("fork" in inst['db']) ? inst['db']['fork'] : ""],
            ["Branch", ("branch" in inst['db']) ? inst['db']['branch'] : ""],
            ["Date Created", inst['db']['date']],
            ["Comments", (inst['db']['comments']) ? inst['db']['comments'].replace("\n", "<br>") : ""]
        ];

        var actions_data = [];  // if its termianted or shutting down we still provide an empty array to update_panel.

        /* Gets a function, wraps it with an are you sure modal, and returns a link object that
        links to it.
         */

        var cloud_state = inst['cloud']['state'];
        if (cloud_state !== 'terminated' && cloud_state !== 'shutting-down' && cloud_state !== 'pending')
        {
             actions_data = [
                ["Terminate", wrap_modal_with_td("Are you sure you want to terminate " + inst_name + "?", function (yes_function) { return terminate_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]
            ];

             if (cloud_state === "running") {
                 actions_data.unshift(["Stop", wrap_modal_with_td("Are you sure you want to stop " + inst_name + "?", function (yes_function) { return stop_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]);
             }
             else {
                 actions_data.unshift(["Start", wrap_modal_with_td("Are you sure you want to start " + inst_name + "?", function (yes_function) { return start_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]);
             }
        }

        instance_info_and_actions_data = demo_info_data.concat(actions_data);

        update_panel("tbody_demo_info", vm_info_data);
        update_panel("tbody_demo_instance_info", instance_info_and_actions_data);

    }
    function update_auto_test_details(i) {
        current_instance_details_i = i;
        var inst = current_auto_tests_in_progress[i];
        var inst_name = inst['db']['name'] || inst['cloud']['name']

        security_groups = inst['cloud']['security_groups']
        if (security_groups !== undefined) {
            security_groups = security_groups.join(',')
        }

        icon = '<img style="width: 32px" src="/static/images/' + inst['cloud']['cloud'] + '.png" />&nbsp;&nbsp;'
        var vm_info_data = [
            ["Cloud", icon + inst['cloud']['cloud']],
            ["Cloud ID", inst['cloud']['id']],
            ["State", inst['cloud']['state']],
            ["Image Id", inst['cloud']['image_id']],
            ["Image", inst['cloud']['image']],
            ["Instance Type", inst['cloud']['type']],
            ["Key Name", inst['cloud']['key_name']],
            ["Private IP Address", inst['cloud']['private_ip']],
            ["Public IP Address", inst['cloud']['public_ip']],
            ["Security Groups", security_groups],
            ["Subnet", inst['cloud']['subnet']]
        ];

        var instance_info_data = [
            ["Name", inst['db']['name']],
            ["Owner", inst['db']['owner']],
            ["Fork", ("fork" in inst['db']) ? inst['db']['fork'] : ""],
            ["Branch", ("branch" in inst['db']) ? inst['db']['branch'] : ""],
            ["Date Created", inst['db']['date']],
            ["Comments", (inst['db']['comments']) ? inst['db']['comments'].replace("\n", "<br>") : ""]
        ];

        var actions_data = [];  // if its terminated or shutting down we still provide an empty array to update_panel.

        /* Gets a function, wraps it with an are you sure modal, and returns a link object that
        links to it.
         */

        var cloud_state = inst['cloud']['state'];
        if (cloud_state !== 'terminated' && cloud_state !== 'shutting-down' && cloud_state !== 'pending') {
            actions_data = [
                ["Terminate", wrap_modal_with_td("Are you sure you want to terminate " + inst_name + "?", function (yes_function) { return terminate_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]
            ];

             if (cloud_state === "running") {
                 actions_data.unshift(["Stop", wrap_modal_with_td("Are you sure you want to stop " + inst_name + "?", function (yes_function) { return stop_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]);
             }
             else {
                 actions_data.unshift(["Start", wrap_modal_with_td("Are you sure you want to start " + inst_name + "?", function (yes_function) { return start_instance(yes_function, inst['cloud']['cloud'], inst['cloud']['id']);}, [], undefined, inst_name)]);
             }
        }

        additional_data = instance_info_data.concat(actions_data);

        update_panel("tbody_auto_instance_info", vm_info_data);
        update_panel("tbody_auto_instance_info_additional", additional_data);

    }
    function update_export_details(i) {
        current_export_details_i = i;
        let exp = current_exports[i];

        if (exp === undefined) {
            return false;
        }

        let export_info_data = [
            ["Version", exp['version']],
            ["Owner", exp['owner']],
            ["Fork", exp['fork']],
            ["Branch", exp['branch']],
            ["Client Name", exp['client_name']],
            ["Comments", exp['comments']],
            ["Status", exp['status']],
            ["Git Hash", exp['git_hash']],
            ["Last Modified", exp['date']],
            ["Download Link", exp['download_link']],
            ["ami ID", exp['ami_id']],
            ["Log", '<a href="/api/exports/' + exp['version'] + '/log" target="_blank">Click here</a>'],
            ["Delete", wrap_modal_with_td("Are you sure you want to delete this export?", delete_export, [], undefined, exp['version'])]
        ];

        update_panel("tbody_export_info", export_info_data);

        // highlight it
        $('pre code').each(function(i, block) {
            hljs.highlightBlock(block);
        });
    }

    // Instance actions and API's to the backend
    function start_instance(always_function, cloud, instance_id) {
        var data = {};
        $.ajax({url: "/api/instances/" + cloud + "/" + instance_id + "/start", type: "POST", data: data})
            .done(rewrite_all_tables)
            .fail(exception_modal)
            .always(always_function);
    }
    function stop_instance(always_function, cloud, instance_id) {
        var data = {};
        $.ajax({url: "/api/instances/" + cloud + "/" + instance_id + "/stop", type: "POST", data: data})
            .done(rewrite_all_tables)
            .fail(exception_modal)
            .always(always_function);
    }
    function terminate_instance(always_function, cloud, instance_id) {
        console.log("terminating " + instance_id);
        $.ajax({url: "/api/instances/" + cloud + "/" + instance_id + "/delete", type: "POST", data: {}})
            .done(rewrite_all_tables)
            .fail(exception_modal)
            .always(always_function);
    }
    function add_new_instance() {
        var data = {};
        if (instance_vm_type === 'demo') {
            var vm_type = 'Demo-VM';
            var is_public = true;
        }
        else if (instance_vm_type === 'instance') {
            var vm_type = 'Builds-VM';
            var is_public = false;
        }

        data["name"] = $("#new_vm_name")[0].value;
        data["type"] = $("#new_vm_instance_type")[0].value;
        data["cloud"] = $("#new_vm_cloud")[0].value;
        data["public"] = is_public;
        data['vm_type'] = vm_type;

        data['config'] = {};
        data['config']["set_credentials"] = $("#new_vm_set_credentials")[0].checked;
        data['config']["empty"] = $("#new_vm_empty_server")[0].checked;
        data['config']["adapters"] = $("#new_vm_adapters_options option:selected").map(function () {
            return $(this).text();
        }).get();

        if (code_source === "Release") {
            data['config']["fork"] = 'axonius/cortex';
            data['config']["branch"] = $("#new_vm_release")[0].value;
            data['key_name'] = CLOUD_DEFAULT_KEY;
        } else if (code_source === "Branch") {
            data['config']["fork"] = $("#new_vm_fork")[0].value;
            data['config']["branch"] = $("#new_vm_branch")[0].value;
            data['key_name'] = CLOUD_DEFAULT_KEY;
        } else {
            data['config']["fork"] = '';
            data['config']["branch"] = '';
            data['config']["image"] = $("#new_vm_image")[0].value;
            // No need to put a key to an image.
        }

        counter = 60;
        $("#new_instance_modal_add_button").prop("disabled", true).text(counter);
        var interval = setInterval(function() {
            counter--;
            $("#new_instance_modal_add_button").text(counter);
            if (counter === 0){
                clearInterval(interval);
            }
        }, 1000)

        $.ajax(
            {
                url: "/api/instances",
                type: "POST",
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                data: JSON.stringify(data)
            }
            )
            .done(rewrite_all_tables)
            .fail(exception_modal)
            .always(function() {
                clearInterval(interval);
                $("#new_instance_modal").modal("hide");
                $("#new_instance_modal_add_button").text("Add");
                $("#new_instance_modal_add_button").prop("disabled", false)
            });
    }
    function disable_bot_monitoring(always_function, cloud, instance_id) {
        console.log("Disabling bot monitoring for " + instance_id);
        $.ajax({url: "/api/instances/" + cloud + "/" + instance_id + "/bot_monitoring", type: "POST", data: {'status': false}})
            .done(rewrite_all_tables)
            .fail(exception_modal)
            .always(always_function);
    }
    function enable_bot_monitoring(always_function, cloud, instance_id) {
        console.log("Enabling bot monitoring for " + instance_id);
        $.ajax({url: "/api/instances/" + cloud + "/" + instance_id + "/bot_monitoring", type: "POST", data: {'status': true}})
            .done(rewrite_all_tables)
            .fail(exception_modal)
            .always(always_function);
    }
    function export_instance(always_function, fields) {
        let data = {};
        data["action"] = "export";
        data["version"] = fields[0].value;
        data["fork"] = fields[1].value;
        data["branch"] = fields[2].value;
        data["client_name"] = fields[3].value;
        data["comments"] = fields[4].value;

        $.ajax({url: "/api/exports", type: "POST", data: data})
            .done(function(data) {
                flush_url("/exportsinprogress", function(data) {
                    current_exports_in_progress = data["current"];
                    rewrite_exports_in_progress_table();
                    changeMenu($("#vm_exports_link"));
                });
            })
            .fail(exception_modal)
            .always(always_function);
    }


    // Modal functions
    function add_instance_modal() {
        instance_vm_type = "instance";
        // $("#new_instance_configuration_cell").show();
        // $("#new_instance_configuration_code_cell").show();
        // $("#new_instance_adapters_cell").hide();
        $("#new_vm_empty_server_label").show();
        $('#new_instance_modal').modal();
    }
    function add_demo_modal() {
        instance_vm_type = "demo";
        // $("#new_instance_configuration_cell").hide();
        // $("#new_instance_configuration_code_cell").hide();
        // $("#new_instance_adapters_cell").show();
        $("#new_vm_empty_server_label").hide();
        $('#new_instance_modal').modal();
    }
    function add_export_modal() {
        new_modal("Export", export_instance, [
                {"name": "Version Name/Number"},
                {"name": "Fork", "value": "axonius"},
                {"name": "Branch", "value": "develop"},
                {"name": "Client Name"},
                {"name": "Comments"}
            ], true, "Please fill in the following details:")
    }

    // Others
    function new_instance_modal_change_configuration_code(index) {
        let ta = $("#new_instance_configuration_code"); // the textarea.
        if (index == current_configurations.length) {
            // The last configuration is always "custom"
            ta.val(last_custom_configuration_code).removeAttr("disabled");
            is_in_custom_configuration_code = true;
        }
        else {
            if (is_in_custom_configuration_code == true) {
                last_custom_configuration_code = ta.val();
                is_in_custom_configuration_code = false;
            }
            ta.val(current_configurations[index]['code']).attr("disabled", "true");
        }
    }
    function new_instance_by_release_code_change(code_choice_option) {
        code_source = code_choice_option;
        if (code_choice_option === "Release") {
            // Showing the correct Branch, Release or AMI ID select
            $("#new_instance_fork_and_branch_select_cell").hide();
            $("#new_instance_ami_select_cell").hide();
            $("#new_instance_release_select_cell").show();

            // Remove Warning
            $("#export_instance_warning").hide();

            // Setting up the default  for Releases
            $("#new_vm_empty_server").prop("checked", false);
            $("#new_vm_empty_server").prop("disabled", false);
            $("#new_vm_set_credentials").prop("checked", true);
            empty_server_checkbox(false)
            new_instance_modal_branch_change($("#new_vm_release")[0].value, 'axonius/cortex')
        } else if ((code_choice_option === "Branch")) {
            // Showing the correct Branch, Release or AMI ID select
            $("#new_instance_release_select_cell").hide();
            $("#new_instance_ami_select_cell").hide();
            $("#new_instance_fork_and_branch_select_cell").show()

            // Remove Warning
            $("#export_instance_warning").hide();

            // Setting up the default "Configurations" for "Branch"
            $("#new_vm_empty_server").prop("checked", false);
            $("#new_vm_empty_server").prop("disabled", false);
            $("#new_vm_set_credentials").prop("checked", true);
            empty_server_checkbox(false)
            new_instance_modal_branch_change($("#new_vm_branch")[0].value, $("#new_vm_fork")[0].value)
        } else {
            // Showing the correct Branch, Release or AMI ID select
            $("#new_instance_release_select_cell").hide();
            $("#new_instance_fork_and_branch_select_cell").hide();
            $("#new_instance_ami_select_cell").show();

            // Show Warning!
            $("#export_instance_warning").show();

            // Setting up the default "Configurations" for "AMI"
            $("#new_vm_empty_server").prop("checked", false);
            $("#new_vm_set_credentials").prop("checked", false);
            $("#new_vm_empty_server").prop("disabled", true);
            empty_server_checkbox(true)
        }
    }
    function new_instance_modal_fork_change(fork_name, page_number) {
        var select = $("#new_vm_branch");
        if (page_number === 1) {
            select.html("");
        }
        $.ajax({
            url: "https://api.github.com/repos/" + fork_name + "/branches?page=" + page_number,
            type: "GET",
            beforeSend: function (xhr) {
                var token_hash = "Basic " + btoa(github_token);
                xhr.setRequestHeader('Authorization', token_hash);
            }
        }).done(function (data) {
            data.forEach(function (i) {
                if (i.name == "develop"){
                    select.append($("<option selected>").attr("value", i.name).text(i.name));
                }
                else {
                    select.append($("<option>").attr("value", i.name).text(i.name));
                }
            });

            if (data.length !== 0) {
                new_instance_modal_fork_change(fork_name, page_number + 1);
            }
            else {
                new_instance_modal_branch_change($("#new_vm_branch").val());
            }
        })
            .fail(exception_modal)
    }
    function new_instance_modal_branch_change(branch_name, fork_name) {
        if (typeof fork_name === 'undefined') {
            fork_name = $('#new_vm_fork').val();
        }

        var select = $("#new_vm_adapters_options").html("");

        select.append($("<option>").attr("value", "ALL").text("ALL"));
        $.ajax({url: "https://api.github.com/repos/" + fork_name + "/contents/testing/services/adapters?ref=" + branch_name,
            type: "GET",
            beforeSend: function (xhr) {
                var token_hash = "Basic " + btoa(github_token);
                xhr.setRequestHeader('Authorization', token_hash);
            }})
            .done(function(data) {
                data.forEach(function (i) {
                    if (i.name !== "__init__.py") {
                        let option_name = i.name.substring(0, i.name.length - "_service.py".length);
                        select.append($("<option>").attr("value", option_name).text(option_name));
                    }
                });
            })
            .fail(exception_modal)
    }
    function empty_server_checkbox(is_empty_server) {
        $("#new_vm_adapters_options").prop("disabled", is_empty_server);
        $("#new_vm_set_credentials").prop("disabled", is_empty_server);
    }
    function load_release_list(page_number) {
        var select = $("#new_vm_release");

        $.ajax({url: "https://api.github.com/repos/axonius/cortex/tags?page=" + page_number,
            type: "GET",
            beforeSend: function (xhr) {
                var token_hash = "Basic " + btoa(github_token);
                xhr.setRequestHeader('Authorization', token_hash);
            }})
            .done(function(data) {
                data.forEach(function (i) {
                        select.append($("<option>").attr("value", i.name).text(i.name));
                });

                if (data.length !== 0) {
                    load_release_list(page_number + 1);
                }
            })
            .fail(exception_modal)
    }
    function load_ami_list(exports_data) {
        var select = $("#new_vm_image");

        exports_data.forEach(function (i) {
            if (i.ami_id) {
                select.append($("<option>").addClass('aws').attr("value", i.ami_id).text(i.version).hide());
            }
            else if (i.gcp_id) {
                select.append($("<option>").addClass('gcp').attr("value", i.gcp_id).text(i.version));
            }
        });
    }
    function load_fork_list() {
        var select = $("#new_vm_fork").html("");
        select.append($("<option>").attr("value", "axonius/cortex").text("axonius/cortex"));
        $.ajax({url: "https://api.github.com/repos/axonius/cortex/forks",
            type: "GET",
            beforeSend: function (xhr) {
                var token_hash = "Basic " + btoa(github_token);
                xhr.setRequestHeader('Authorization', token_hash);
            }})
            .done(function(data) {
                data.forEach(function (i) {
                    select.append($("<option>").attr("value", i.full_name).text(i.full_name));
                });

                new_instance_modal_change_configuration_code(0);
            }).fail(exception_modal)
    }
    function chooseCloud(cloud){
        console.log(cloud)
        if (cloud === 'aws') {
            $('.aws').show()
            $('.gcp').hide()
            $('#new_vm_instance_type option.aws:first').prop('selected', true);
            $('#new_vm_image option.aws:first').prop('selected', true);
        }
        else if (cloud === 'gcp') {
            $('.aws').hide()
            $('.gcp').show()
            $('#new_vm_image option.gcp:first').prop('selected', true);
        }
    }

    function toggle_terminated_instances_view() {
        if (show_terminated_instances === false) {
            show_terminated_instances = true;
            $("#ttiv_text").text("Hide");
        }
        else {
            show_terminated_instances = false;
            $("#ttiv_text").text("Show");
        }
        rewrite_instances_table();
    }
    function toggle_advance_usage() {
        if (advanced_usage === false) {
            advanced_usage = true;
            $('.awsoption').show();
            chooseCloud('aws');
            $("#advanced_usage_text").text("Hide");
        }
        else {
            advanced_usage = false;
            $('.awsoption').hide();
            chooseCloud('gcp');
            $('#new_vm_cloud').val('gcp');
            $("#advanced_usage_text").text("Show");
        }
    }

    /* Export menu functions */
    function toggle_completed_exports_view() {
        if (show_completed_exports == false) {
            show_completed_exports = true;
            $("#tcev_text").text("Hide");
        }
        else {
            show_completed_exports = false;
            $("#tcev_text").text("Show");
        }
        rewrite_exports_in_progress_table();
    }

    function open_running_export_log(export_id) {
        $.ajax({
            url: "/api/exports/" + export_id + "/status",
            type: "GET"}).done(function (data) {
                new_modal("Log", function() {}, [], true, "<textarea style='width: 100%; height: 60vh;'>" + data['result']['value'] + "</textarea>");
        })
    }
    function delete_export(always_function) {
        var id = current_exports[current_export_details_i]['version'];
        var data = {}

        $.ajax({url: "/api/exports/" + id, type: "DELETE", data: data})
            .done(function(data) {
                current_exports = data["current"];
                rewrite_exports_table();
                update_export_details(0);
            })
            .fail(exception_modal)
            .always(always_function);
    }

    /* Initialization and menu */
    function rewrite_all_tables(data) {
        current_instances = [];
        current_demos = [];
        current_auto_tests_in_progress = [];
        for (let i in data["result"]) {
            let instance = data["result"][i];
            let vm_type = instance["cloud"]["tags"]["VM-Type"] || instance["cloud"]["tags"]["vm-type"];
            vm_type = vm_type.toLowerCase();

            if (vm_type === "demo-vm") {
                current_demos.push(instance);
            }

            else if (vm_type === "auto-test-vm") {
                current_auto_tests_in_progress.push(instance);
            }

            else {
                // Everything which is not identified goes to the main page
                current_instances.push(instance);
            }

        }

        rewrite_instances_table();
        // Get the first not terminated instance.
        for (var i in current_instances) {
            if (current_instances[i]['cloud']['state'] !== 'terminated') {
                update_instance_details(i);
                break;
            }
        }

        rewrite_demos_table();
        // Get the first not terminated instance.
        for (var i in current_demos) {
            if (current_demos[i]['cloud']['state'] !== 'terminated') {
                update_demo_details(i);
                break;
            }
        }

        rewrite_auto_tests_table();
        // Get the first not terminated instance.
        for (var i in current_auto_tests_in_progress) {
            if (current_auto_tests_in_progress[i]['cloud']['state'] !== 'terminated') {
                update_auto_test_details(i);
                break;
            }
        }
    }

    $(document).ready(function() {
        load_fork_list();
        new_instance_modal_fork_change('axonius/cortex', 1);
        load_release_list(1);

        // initialize datatables.
        if (window.location.hash === "") {
        window.location.hash = "vm_instances";
        }
        found = $("a[href='" + window.location.hash + "']");
        if (found.length > 0) {
            changeMenu(found[0]);
        }

        $("#instances_table").DataTable({
            columns: [
                { title: "#" },
                { title: "Instance Name" },
                { title: "Instance Type" },
                { title: "Owner" },
                { title: "Private Address" },
                { title: "State" }
            ]
        });
        $("#demos_table").DataTable({
            columns: [
                { title: "#" },
                { title: "Demo Name" },
                { title: "Instance Type" },
                { title: "Private Address" },
                { title: "Public Address" },
                { title: "State" }
            ]
        });
        $("#exports_table").DataTable({
            columns: [
                { title: "#" },
                { title: "Version" },
                { title: "Owner" },
                { title: "Fork" },
                { title: "Branch" },
                { title: "Client Name" },
                { title: "Comments" },
                { title: "Status" },
                { title: "Last Modified" }
            ]
        });
        $("#auto_tests_table").DataTable({
            columns: [
                { title: "#" },
                { title: "Instance Name" },
                { title: "Instance Type" },
                { title: "Owner" },
                { title: "Private Address" },
                { title: "State" }
            ]
        });

        $("#exports_in_progress_table").DataTable({
            columns: [
                { title: "#" },
                { title: "Version" },
                { title: "Owner" },
                { title: "Fork" },
                { title: "Branch" },
                { title: "Client Name" },
                { title: "Comments" },
                { title: "Log" },
                { title: "Status" },
                { title: "Last Modified" }
            ]
        });

        update_datatable("instances_table", [["1", "Loading...", "", "", "", ""]]);
        update_datatable("demos_table", [["1", "Loading...", "", "", "", "", ""]]);
        update_datatable("exports_table", [["1", "Loading...", "", "", "", "", "", "", ""]]);
        update_datatable("exports_in_progress_table", [["1", "Loading...", "", "", "", "", "", "", "", ""]]);
        update_datatable("auto_tests_table", [["1", "Loading...", "", "", "", ""]]);

        // load all data.
        flush_url("/api/instances", rewrite_all_tables);
        
        flush_url("/api/exports", function(data) {
            current_exports = data["result"];
            rewrite_exports_table();
            update_export_details(0);
            load_ami_list(current_exports)
        });

        flush_url("/api/exportsinprogress", function(data) {
            current_exports_in_progress = data["current"];
            rewrite_exports_in_progress_table();
        });
    });

    function changeMenu(link) {
        $("li").removeClass("active");
        $(link).parent().addClass("active");

        $(".hidden_container").hide();
        $($(link).attr("href")).show();

        // we return false, to make the page not go to the actual anchor, because its not at the top of the page,
        // so it makes the page bump down. instead, we just change the url.
        history.pushState(null, null, $(link).attr('href'))
        return false;

    }