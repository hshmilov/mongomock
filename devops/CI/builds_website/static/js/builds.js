    var current_instances = [];
    var current_demo_details_i = 0;
    var show_terminated_instances = false;
    var current_demos = [];
    var current_demo_details_i = 0;

    var current_exports = [];
    var current_export_details_i = 0;
    var current_exports_in_progress = [];
    var show_completed_exports = false;

    var current_images = [];
    var current_image_details_i = 0;

    var current_configurations = [];
    var current_configuration_details_i = 0;
    var instance_vm_type = "instance";
    var code_source = "Branch";

    var last_custom_configuration_code = "";
    var is_in_custom_configuration_code = false;
    var github_token = "githubreadonly@axonius.com:3Zc0kRElHCzhHbM1u0LX";

    /* Global functions */
    function capitalize_str(str) {
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
    function new_modal(title, yes_function, fields, is_big, message) {
        var m = $("#generic_modal").clone();
        m.attr("id", "new_modal");
        m.find(".modal-title").text(title);

        // If the user requested a big modal, change the class to big.
        m.find(".modal-dialog").addClass("modal-lg");

        if (message == undefined ){
            message = "Fill in these details:";
        }

        message += "<br><br>";

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

        var yes_button = m.find("#generic_modal_yes_button");
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
    function wrap_modal_with_td(title, f, fields, message) {
        // Gets modal details and returns a td column that has a link that opens it.
            return $("<td>").html($("<a>").attr("href", "#").text("Click Here").
                    click(function() {
                        new_modal(title, f, fields, false, message);
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

    /* Instance menu functions */

    function update_instance_view(i) {
        rewrite_instances_table();
        update_instance_details(i);
    }
    function update_demo_view(i) {
        rewrite_demos_table();
        update_demo_details(i);
    }
    function rewrite_instances_table() {
        let dataSet = [];
        for (i in current_instances) {
            if (current_instances[i]['ec2']['state'] !== 'terminated' || show_terminated_instances === true) {
                data = [];
                db = current_instances[i]["db"];
                ec2 = current_instances[i]["ec2"];

                ip = ec2["private_ip_address"];
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

                if (db['configuration_name'] == undefined) {
                    db['configuration_name'] = "Unknown";
                    db['configuration_code'] = "Unknown";
                }

                let instance_and_system_status = ec2['instance_status'];
                if (instance_and_system_status == "ok") instance_and_system_status = ec2['system_status'];

                let public_link = ("elastic_ip_id" in db && db.elastic_ip_id !== '') ? "<a href='https://" + ec2.public_ip_address  + "' target='_blank'>https://" + ec2.public_ip_address + "</a>": '';

                // Capitalize owner name
                db["owner"] = capitalize_str(db["owner"])

                // Push all of the data
                data.push(parseInt(i) + 1);
                data.push(db["name"]);
                data.push(ec2['instance_type'])
                data.push(db["owner"]);
                data.push(ip_link);
                if (instance_and_system_status === "ok" || instance_and_system_status === undefined) {
                    data.push(ec2["state"]);
                }
                else {
                    data.push(ec2["state"] + " (" + instance_and_system_status + ")");
                }

                dataSet.push(data);
            }
        }

        update_datatable("instances_table", dataSet, update_instance_details)
    }
    function update_instance_details(i) {
        current_instance_details_i = i;
        var inst = current_instances[i];

        // if the first one is "ok", show the second one. otherwise show the first one.
        var instance_and_system_status = inst['ec2']['instance_status'];
        if (instance_and_system_status === "ok") instance_and_system_status = inst['ec2']['system_status'];

        var vm_info_data = [
            ["EC2 ID", inst['ec2']['id']],
            ["State", inst['ec2']['state']],
            ["Instance & System Status", instance_and_system_status],
            ["Image", inst['ec2']['image_description']],
            ["Instance Type", inst['ec2']['instance_type']],
            ["Key Name", inst['ec2']['key_name']],
            ["Private IP Address", inst['ec2']['private_ip_address']],
            ["VPC Name", inst['ec2']['vpc_name']],
            ["Subnet", inst['ec2']['subnet']]
        ];
        //("elastic_ip_id" in db && db.elastic_ip_id !== '') ? "<a href='https://" + ec2.public_ip_address  + "' target='_blank'>https://" + ec2.public_ip_address + "</a>": '';
        var instance_info_data = [
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

        var ec2_state = inst['ec2']['state'];
        if (ec2_state !== 'terminated' && ec2_state !== 'shutting-down') {
            actions_data = [
                ["Terminate", wrap_modal_with_td("Are you sure you want to terminate the instance?", function (yes_function) { return terminate_instance(yes_function, inst['ec2']['id']);})]
            ];

             if (ec2_state === "running") {
                 actions_data.unshift(["Stop", wrap_modal_with_td("Are you sure you want to stop the instance?", function (yes_function) { return stop_instance(yes_function, inst['ec2']['id']);})]);
             }
             else {
                 actions_data.unshift(["Start", wrap_modal_with_td("Are you sure you want to start the instance?", function (yes_function) { return start_instance(yes_function, inst['ec2']['id']);})]);
             }

             var bot_monitoring = inst['db']['bot_monitoring'];

            if (bot_monitoring == "false"){
                actions_data.unshift(["Enable Bot Monitoring",
                    wrap_modal_with_td("Are you sure you want to enable the bot monitoring?", function(yes_function) { return enable_bot_monitoring(yes_function, inst['ec2']['id']);})
                ]);
            }
            else {
                actions_data.unshift(["Disable Bot Monitoring",
                    wrap_modal_with_td("Are you sure you want to disable the bot monitoring?", function(yes_function) { return disable_bot_monitoring(yes_function, inst['ec2']['id']);})
                ]);
            }
        }

        var instance_info_and_actions_data = instance_info_data.concat(actions_data);

        update_panel("tbody_vm_info", vm_info_data);
        update_panel("tbody_instance_info", instance_info_and_actions_data);

        // update the configuration info because its a little bit different (needs colspan)
        /*
        var tci = $("#tbody_configuration_info").html("");
        $("<tr>").append($("<td>").text("Manifest File")).append($("<td>").append($("<a>").attr("target", "_blank").attr("href", "/instances/" + inst['ec2']['id'] + "/manifest").text("Click here"))).appendTo(tci);
        $("<tr>").append($("<td>").text("Configuration Name")).append($("<td>").text(inst['db']['configuration_name'])).appendTo(tci);
        $("<tr>").append($("<td>").attr("colspan", "2").append($("<pre>").append($("<code>").html(inst['db']['configuration_code'].replace("\n", "<br>"))))).appendTo(tci);

        // highlight it
        $('pre code').each(function(i, block) {
            hljs.highlightBlock(block);
        });
        */

    }
    function update_demo_details(i) {
        current_demo_details_i = i;
        var inst = current_demos[i];

        // if the first one is "ok", show the second one. otherwise show the first one.
        var instance_and_system_status = inst['ec2']['instance_status'];
        if (instance_and_system_status == "ok") instance_and_system_status = inst['ec2']['system_status'];

        var vm_info_data = [
            ["EC2 ID", inst['ec2']['id']],
            ["State", inst['ec2']['state']],
            ["Instance & System Status", instance_and_system_status],
            ["Image", inst['ec2']['image_description']],
            ["Instance Type", inst['ec2']['instance_type']],
            ["Key Name", inst['ec2']['key_name']],
            ["Private IP Address", inst['ec2']['private_ip_address']],
            ["VPC Name", inst['ec2']['vpc_name']],
            ["Subnet", inst['ec2']['subnet']]
        ];

        var demo_info_data = [
            ["Name", inst['db']['name']],
            ["Owner", inst['db']['owner']],
            ["Fork", inst['db']['fork']],
            ["Branch", inst['db']['branch']],
            ["Date Created", inst['db']['date']],
            ["Comments", (inst['db']['comments']) ? inst['db']['comments'].replace("\n", "<br>") : ""],
            ["Metadata", ""],        // Link to our CI system build link
            ["Credentials", wrap_modal_with_td("Are you sure you want to pull all the credentials?", function () { return get_credentials(inst['ec2']['private_ip_address'], inst['db']['fork'], inst['db']['branch']);})]
        ];

        var actions_data = [];  // if its termianted or shutting down we still provide an empty array to update_panel.

        /* Gets a function, wraps it with an are you sure modal, and returns a link object that
        links to it.
         */

        var ec2_state = inst['ec2']['state'];
        if (ec2_state !== 'terminated' && ec2_state !== 'shutting-down') {
             actions_data = [
                ["Terminate", wrap_modal_with_td("Are you sure you want to terminate the instance?", function () { return terminate_instance('', inst['ec2']['id']);})]
            ];

             if (ec2_state === "running") {
                 actions_data.unshift(["Stop", wrap_modal_with_td("Are you sure you want to stop the instance?", function () { return stop_instance('', inst['ec2']['id']);})]);
             }
             else {
                 actions_data.unshift(["Start", wrap_modal_with_td("Are you sure you want to start the instance?", function () { return start_instance('', inst['ec2']['id']);})]);
             }
        }

        instance_info_and_actions_data = demo_info_data.concat(actions_data);

        update_panel("tbody_demo_info", vm_info_data);
        update_panel("tbody_demo_instance_info", instance_info_and_actions_data);

        /*
        // update the configuration info because its a little bit different (needs colspan)
        var tci = $("#tbody_configuration_info").html("");
        $("<tr>").append($("<td>").text("Manifest File")).append($("<td>").append($("<a>").attr("target", "_blank").attr("href", "/instances/" + inst['ec2']['id'] + "/manifest").text("Click here"))).appendTo(tci);
        $("<tr>").append($("<td>").text("Configuration Name")).append($("<td>").text(inst['db']['configuration_name'])).appendTo(tci);
        $("<tr>").append($("<td>").attr("colspan", "2").append($("<pre>").append($("<code>").html(inst['db']['configuration_code'].replace("\n", "<br>"))))).appendTo(tci);

        // highlight it
        $('pre code').each(function(i, block) {
            hljs.highlightBlock(block);
        });
        */

    }
    function start_instance(always_function, instance_id) {
        var data = {};
        data["action"] = "start";
        $.ajax({url: "/instances/" + instance_id, type: "POST", data: data})
            .done(function(data) {
                current_instances = data["current"];
                update_instance_view(current_demo_details_i);
            })
            .fail(exception_modal)
            .always(always_function);
    }
    function stop_instance(always_function, instance_id) {
        var data = {};
        data["action"] = "stop";
        $.ajax({url: "/instances/" + instance_id, type: "POST", data: data})
            .done(function(data) {
                current_instances = data["current"];
                update_instance_view(current_demo_details_i);
            })
            .fail(exception_modal)
            .always(always_function);
    }
    function terminate_instance(always_function, instance_id) {
        console.log("terminating " + instance_id);
        $.ajax({url: "/instances/" + instance_id, type: "DELETE", data: {}})
            .done(function(data) {
                current_instances = data["current"];
                update_instance_view(current_demo_details_i);
            })
            .fail(exception_modal)
            .always(always_function);
    }

    function disable_bot_monitoring(always_function, instance_id) {
        console.log("Disabling bot monitoring for " + instance_id);
        $.ajax({url: "/instances/" + instance_id + "/bot_monitoring", type: "POST", data: {'status': false}})
            .done(function(data) {
                current_instances = data["current"];
                update_instance_view(current_demo_details_i);
            })
            .fail(exception_modal)
            .always(always_function);
    }

    function enable_bot_monitoring(always_function, instance_id) {
        console.log("Enabling bot monitoring for " + instance_id);
        $.ajax({url: "/instances/" + instance_id + "/bot_monitoring", type: "POST", data: {'status': true}})
            .done(function(data) {
                current_instances = data["current"];
                update_instance_view(current_demo_details_i);
            })
            .fail(exception_modal)
            .always(always_function);
    }

    function get_credentials(demo_ip, fork, branch) {
        console.log("getting credentials " + demo_ip);
        let credentials_list = [];
        let client_details_regex = /client_details = ([^}]+?})/;
        // Getting all the registered plugins from the system
        $.ajax({url: "https://"+ demo_ip + ":5050/api/register", type: "Get"})
            .done(function(data) {
                // Filter adapters
                let adapters_unique_names = Object.keys(data).filter(function (current_registered_plugin_unique_name){
                    return data[current_registered_plugin_unique_name].plugin_type === "Adapter"
                });

                // For each adapter call get every credentials file from the branch on github.
                let num_of_adapters = adapters_unique_names.length;
                for (let i in adapters_unique_names) {
                    let current_adapter_name = data[adapters_unique_names[i]].plugin_name.substring(0, data[adapters_unique_names[i]].plugin_name.length - "_adapter".length);
                    $.ajax({
                        url: "https://api.github.com/repos/" + fork + "/contents/testing/test_credentials/test_" + current_adapter_name + "_credentials.py?ref=" + branch,
                        type: "Get",
                        beforeSend: function (xhr) {
                            var token_hash = "Basic " + btoa(github_token);
                            xhr.setRequestHeader('Authorization', token_hash);
                        }
                    })
                        .done(function (data) {
                            let creds_file_contents = atob(data.content);
                            let match = client_details_regex.exec(creds_file_contents);
                            credentials_list.push(current_adapter_name + ":" + match[1]);
                            num_of_adapters--;
                        })
                        .fail(function () {
                            num_of_adapters--;
                        });
                }

                // Try until all the separate get credentials calls return (or fail).
                function checkFlag() {
                    if(num_of_adapters > 0) {
                        window.setTimeout(checkFlag, 100); /* this checks the flag every 100 milliseconds*/
                    } else {
                        let element = document.createElement('a');
                        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(credentials_list.join('\n')));
                        element.setAttribute('download', 'credentials.txt');

                        element.style.display = 'none';
                        document.body.appendChild(element);

                        element.click();

                        document.body.removeChild(element);
                    }
                }
                checkFlag();


            })
            .fail(exception_modal);
    }
    function export_instance(always_function, fields) {
        let data = {};
        data["action"] = "export";
        data["version"] = fields[0].value;
        data["fork"] = fields[1].value;
        data["branch"] = fields[2].value;
        data["client_name"] = fields[3].value;
        data["comments"] = fields[4].value;

        $.ajax({url: "/exports", type: "POST", data: data})
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
    function empty_server_checkbox(is_empty_server) {
        $("#new_vm_adapters_options").prop("disabled", is_empty_server);
        $("#new_vm_set_credentials").prop("disabled", is_empty_server);
    }
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
            $("#new_instance_fork_and_branch_select_cell").hide();
            $("#new_instance_release_select_cell").show();
            new_instance_modal_branch_change($("#new_vm_release")[0].value, 'axonius/cortex')
        }
        else {
            $("#new_instance_release_select_cell").hide();
            $("#new_instance_fork_and_branch_select_cell").show()
            new_instance_modal_branch_change($("#new_vm_branch")[0].value, $("#new_vm_fork")[0].value)
        }
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
    function add_new_instance() {
        var data = {};

        var instance_type = (instance_vm_type === "demo") ? "Demo-VM" : "Builds-VM";
        var is_public = (instance_vm_type == "demo");

        if (code_source === "Release") {
            data["fork"] = 'axonius/cortex';
            data["branch"] = $("#new_vm_release")[0].value;
        }
        else {
            data["fork"] = $("#new_vm_fork")[0].value;
            data["branch"] = $("#new_vm_branch")[0].value;
        }

        data["name"] = $("#new_vm_name")[0].value;
        data["ec2_type"] = $("#new_vm_ec2_instance_type")[0].value;
        data["public"] = is_public;
        data["set_credentials"] = $("#new_vm_set_credentials")[0].checked;
        data["empty"] = $("#new_vm_empty_server")[0].checked;
        data["adapters"] = $("#new_vm_adapters_options option:selected").map(function () {
            return $(this).text();
        }).get().join(',');

        $("#new_instance_modal_add_button").text("Loading..");
        $("#new_instance_modal_add_button").prop("disabled", true);

        $.ajax({url: "/instances?instance_type=" + instance_type, type: "POST", data: data})
            .done(function(data) {
                if (instance_vm_type !== "demo") {
                    current_instances = data["current"];
                    update_instance_view(0);
                }
                else {
                    current_demos = data["current"];
                    update_demo_view(0)
                }


            })
            .fail(exception_modal)
            .always(function() {
                $("#new_instance_modal").modal("hide");
                $("#new_instance_modal_add_button").text("Add");
                $("#new_instance_modal_add_button").prop("disabled", false)
            });
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
    function rewrite_demos_table() {
        var dataSet = [];
        for (i in current_demos) {
            if (current_demos[i]['ec2']['state'] != 'terminated' || show_terminated_instances == true) {
                data = [];
                db = current_demos[i]["db"];
                ec2 = current_demos[i]["ec2"];

                ip = ec2["private_ip_address"];
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

                if (db['configuration_name'] == undefined) {
                    db['configuration_name'] = "Unknown";
                    db['configuration_code'] = "Unknown";
                }

                var instance_and_system_status = ec2['instance_status'];
                if (instance_and_system_status == "ok") instance_and_system_status = ec2['system_status'];

                var public_link = ("elastic_ip_id" in db && db.elastic_ip_id !== '') ? "<a href='https://" + ec2.public_ip_address  + "' target='_blank'>https://" + ec2.public_ip_address + "</a>": '';

                // Capitalize owner name
                db["owner"] = capitalize_str(db["owner"])

                // Push all of the data
                data.push(parseInt(i) + 1);
                data.push(db["name"]);
                data.push(db["owner"]);
                data.push(ip_link);
                data.push(public_link);
                if (instance_and_system_status === "ok" || instance_and_system_status === undefined) {
                    data.push(ec2["state"]);
                }
                else {
                    data.push(ec2["state"] + " (" + instance_and_system_status + ")");
                }

                dataSet.push(data);
            }
        }

        update_datatable("demos_table", dataSet, update_demo_details)
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
            ["Last Modified", exp['date']],
            ["Download Link", exp['download_link']],
            ["ami ID", exp['ami_id']],
            ["Log", wrap_modal_with_td("Log File", function() {}, [], "<textarea style='width: 100%; height: 60vh;'>" + exp['log'] + "</textarea>")],
            ["Delete", wrap_modal_with_td("Are you sure you want to delete this export?", delete_export)]
        ];

        update_panel("tbody_export_info", export_info_data);

        // update the configuration info because its a little bit different (needs colspan)
        var tci = $("#tbody_export_configuration").html("");
        // $("<tr>").append($("<td>").text("Manifest File")).append($("<td>").append($("<a>").attr("target", "_blank").attr("href", "/exports/" + exp['s3']['Key'] + "/manifest").text("Click here"))).appendTo(tci);
        // $("<tr>").append($("<td>").text("Configuration Name")).append($("<td>").text(exp['db']['configuration_name'])).appendTo(tci);
        // $("<tr>").append($("<td>").attr("colspan", "2").append($("<pre>").append($("<code>").html(exp['db']['configuration_code'].replace("\n", "<br>"))))).appendTo(tci);

        // highlight it
        $('pre code').each(function(i, block) {
            hljs.highlightBlock(block);
        });
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
    function get_export_url(key_name, el) {

        $.ajax({url: "/exports/" + key_name + "/url", type: "GET"})
            .done(function(data) {
                url = data["result"]["url"];
                $(el).parent().html("<a href='" + url + "'>Click here</a>");
            })
            .fail(exception_modal)
    }
    function open_running_export_log(export_id) {
        // $.ajax({url: "/exports/" + export_id + "/status", type: "GET"})
        //     .done(function (data) {
        //         new_modal("log", null, null, true, data);
        //     })
        $.ajax({
            url: "/exports/" + export_id + "/status",
            type: "GET"}).done(function (data) {
                new_modal("Log", function() {}, [], true, "<textarea style='width: 100%; height: 60vh;'>" + data['result']['value'] + "</textarea>");
        })
    }
    function delete_export(always_function) {
        var id = current_exports[current_export_details_i]['version'];
        var data = {}

        $.ajax({url: "/exports/" + id, type: "DELETE", data: data})
            .done(function(data) {
                current_exports = data["current"];
                rewrite_exports_table();
                update_export_details(0);
            })
            .fail(exception_modal)
            .always(always_function);
    }

    /* Images functions */
    function rewrite_images_table() {
        dataSet = [];
        for (var i in current_images) {
            var db = current_images[i]['db'];
            var ecr = current_images[i]['ecr'];
            var data = [];

            // Try to understand what is the build status link.
            var build_link = "Unknown";

            if (db['teamcityBuildId'] !== undefined) {
                var bid = db['teamcityBuildId'];
                build_link = $("<a>").attr("target", "_blank").attr("href", "https://teamcity.axonius.local/viewLog.html?buildId=" + bid);
                $("<img>").attr("src", "https://teamcity.axonius.local/app/rest/builds/" + bid + "/statusIcon.svg").appendTo(build_link);
            }

            // Push all of the data
            data.push(parseInt(i) + 1);
            data.push(ecr["repository"]);
            data.push(ecr["imageTags"].join("<br>"));
            data.push(ecr["imagePushedAt"]);
            data.push(ecr["size"]);
            data.push($("<div>").append(build_link).html());

            dataSet.push(data);
        }

        update_datatable("images_table", dataSet, update_image_details);
    }
    function update_image_details(i) {
        current_image_details_i = i;
        var im = current_images[i];

        if (im == undefined) {
            return false;
        }

        // get docker pull command
        var docker_pull_command =
            "<pre><code>#!/bin/bash<br />" +
            "export AWS_ACCESS_KEY_ID=AKIAJG3SN4BBL6VNUBYQ<br />" +
            "export AWS_SECRET_ACCESS_KEY=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<br />" +
            "export AWS_DEFAULT_REGION=us-east-2<br />" +
            "sudo `aws ecr get-login --no-include-email --region us-east-2`<br /><br>" +
            "sudo docker pull 405773942477.dkr.ecr.us-east-2.amazonaws.com/" + im['ecr']['repository'] + ":" + im['ecr']['imageTags'][0] +
            "<br /><br># To make your life easier:<br />" +
            "sudo docker tag 405773942477.dkr.ecr.us-east-2.amazonaws.com/" + im['ecr']['repository']  + ":" + im['ecr']['imageTags'][0] +
            " " + im['ecr']['repository'] + ":" + im['ecr']['imageTags'][0] +
            "</code></pre>";

        var image_info_data = [
            ["Repository", im['ecr']['repository']],
            ["Image Digest", im['ecr']['imageDigest']],
            ["Image Pushed At", im['ecr']['imagePushedAt']],
            ["Image Tags", im['ecr']['imageTags'].join(", ")],
            ["Size", im['ecr']['size']],
            ["Delete", wrap_modal_with_td("Are you sure you want to delete this image?", delete_image)],
            ["DB Metadata", $("<code>").text(JSON.stringify(im['db'], null, 2))],
            ["Docker Pull Command", docker_pull_command]
        ];

        update_panel("tbody_images_info", image_info_data);
    }
    function delete_image(always_function) {
        var ecr = current_images[current_image_details_i]['ecr']
        var data = {"repositoryName": ecr["repository"], "imageDigest": ecr["imageDigest"] }

        $.ajax({url: "/images", type: "DELETE", data: data})
            .done(function(data) {
                current_images = data["current"];
                rewrite_images_table();
                update_image_details(0);
            })
            .fail(exception_modal)
            .always(always_function);
    }

    /* Configurations functions */
    function add_configuration_modal() {
        new_modal("Add A New Configuration", add_new_configuration, [
            {"name": "Configuration Name"},
            {"name": "Author"},
            {"name": "Purpose"},
            {"name": "Code", "type": "textarea", "rows": 15}
        ], true);
    }
    function update_configuration_modal() {
        var cc = current_configurations[current_configuration_details_i]
        new_modal("Update Configuration", update_configuration, [
            {"name": "Configuration Name", "value": cc['name']},
            {"name": "Author", "value": cc['author']},
            {"name": "Purpose", "value": cc['purpose']},
            {"name": "Code", "type": "textarea", "rows": 15, "value": cc["code"]}
        ], true);
    }
    function add_new_configuration(always_function, fields) {
        var data = {};
        data["name"] = fields[0].value;
        data["author"] = fields[1].value;
        data["purpose"] = fields[2].value;
        data["code"] = fields[3].value;

        $.ajax({url: "/configurations", type: "POST", data: data})
            .done(function(data) {
                current_configurations = data["current"];
                rewrite_configurations_table();
                update_configuration_details(data.length - 1);
            })
            .fail(exception_modal)
            .always(always_function);
    }
    function update_configuration(always_function, fields) {
        var data = {};
        data["name"] = fields[0].value;
        data["author"] = fields[1].value;
        data["purpose"] = fields[2].value;
        data["code"] = fields[3].value;
        var id = current_configurations[current_configuration_details_i]['_id']

        $.ajax({url: "/configurations/" + id, type: "POST", data: data})
            .done(function(data) {
                current_configurations = data["current"];
                rewrite_configurations_table();
                update_configuration_details(current_configuration_details_i);
            })
            .fail(exception_modal)
            .always(always_function);
    }
    function rewrite_configurations_table() {
        dataSet = [];
        for (var i in current_configurations) {
            var con = current_configurations[i];
            var data = [];

            // Push all of the data
            data.push(parseInt(i) + 1);
            data.push(con["name"]);
            data.push(con["author"]);
            data.push(con["date"]);
            data.push(con["purpose"]);
            dataSet.push(data);
        }

        update_datatable("configurations_table", dataSet, update_configuration_details);

        // update the configurations picker we have on the new instance modal.
        var select = $("#new_instance_configuration_picker").html("");
        for (i in current_configurations) {
            select.append($("<option>").attr("value", i).text(current_configurations[i]["name"]));
        }
        select.append($("<option>").attr("value", "-1").text("Custom"));
        new_instance_modal_change_configuration_code(0);
    }
    function update_configuration_details(i) {
        current_configuration_details_i = i;
        var con = current_configurations[i];

        if (con === undefined) {
            return false;
        }

        //update_panel("tbody_images_info", image_info_data);
        var tbody = $("#tbody_configuration_code");
        var code = $("<pre>").append($("<code>").html(con['code'].replace("\n", "<br>")));
        tbody.html("")

        $("<tr>").append($("<td>").text("Configuration Name")).append($("<td>").text(con['name'])).appendTo(tbody);
        $("<tr>")
            .append($("<td>").text("Update Configuration"))
            .append($("<td>").append($("<a>").attr("href", "#").text("Click Here").attr("onclick", "update_configuration_modal(); return false;")))
            .appendTo(tbody);
        $("<tr>")
            .append($("<td>").text("Delete Configuration"))
            .append(
                wrap_modal_with_td("Are you sure you want to delete this configuration?", delete_configuration)
            )
            .appendTo(tbody);
        $("<tr>").append($("<td>").attr("colspan", "2").append(code)).appendTo(tbody);

        // syntax highlight
         code.each(function(i, block) {
            hljs.highlightBlock(block);
          });
    }
    function delete_configuration(always_function) {
        var id = current_configurations[current_configuration_details_i]['_id'];
        var data = {};

        $.ajax({url: "/configurations/" + id, type: "DELETE", data: data})
            .done(function(data) {
                current_configurations = data["current"];
                rewrite_configurations_table();
                update_configuration_details(0);
            })
            .fail(exception_modal)
            .always(always_function);
    }

    /* Initialization and menu */
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
                { title: "Owner" },
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
        /*

        $("#images_table").DataTable({
            columns: [
                { title: "#" },
                { title: "Repository" },
                { title: "Tags" },
                { title: "Image Date"},
                { title: "Image Size"},
                { title: "Build"}
            ]
        });

        $("#configurations_table").DataTable({
            columns: [
                { title: "#" },
                { title: "Name" },
                { title: "Author" },
                { title: "Date" },
                { title: "Purpose"},
            ]
        });
        */

        update_datatable("instances_table", [["1", "Loading...", "", "", "", ""]]);
        update_datatable("demos_table", [["1", "Loading...", "", "", "", "", ""]]);
        update_datatable("exports_table", [["1", "Loading...", "", "", "", "", "", "", ""]]);
        update_datatable("exports_in_progress_table", [["1", "Loading...", "", "", "", "", "", "", "", ""]]);
        // update_datatable("images_table", [["1", "Loading...", "", "", "", ""]]);
        // update_datatable("configurations_table", [["1", "Loading...", "", "", ""]]);

        // load all data.
        flush_url("/instances?instance_type=Builds-VM", function(data) {
            current_instances = data["current"];
            rewrite_instances_table();
            // Get the first not terminated instance.
            for (var i in current_instances) {
                if (current_instances[i]['ec2']['state'] !== 'terminated') {
                    update_instance_details(i);
                    break;
                }
            }
        });
        flush_url("/instances?instance_type=Demo-VM", function(data) {
            current_demos = data["current"];
            rewrite_demos_table();
            // Get the first not terminated instance.
            for (i in current_demos) {
                if (current_demos[i]['ec2']['state'] != 'terminated') {
                    update_demo_details(i);
                    break;
                }
            }
        });
        flush_url("/exports", function(data) {
            current_exports = data["current"];
            rewrite_exports_table();
            update_export_details(0);
        });
        flush_url("/exportsinprogress", function(data) {
            current_exports_in_progress = data["current"];
            rewrite_exports_in_progress_table();
        });
        /*
        flush_url("/images", function(data) {
            current_images = data["current"];
            rewrite_images_table();
            update_image_details(0);
        });

        flush_url("/configurations", function(data) {
            current_configurations = data["current"];
            rewrite_configurations_table();
            update_configuration_details(0);
        });
        */
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