% from bottle import request
% from common.schedule import CronStructure
% from server.http_server import CRON_DICT
% from server.http_server import SettingsTabs

% setdefault("animations", {})
% setdefault("is_modify", False)

% rebase("base.tpl", page_title="Schedule")


<%
    def xstr(s):
        return '' if s is None else str(s)
    end
%>


<div class="row">
    <div class="col">
        <div class="card">
            <div class="card-header" id="animation_collapse_header">
                <a class="btn btn-link" data-toggle="collapse" href="#animation_collapse_body" role="button" aria-expanded="false" aria-controls="animation_collapse_body">
                    <span class="icon bi-pencil-fill"></span>
                    <span>Change Settings: {{entry.ANIMATION_SETTINGS.animation_name.title()}}</span>
                </a>
            </div>
            <div id="animation_collapse_body" class="collapse" aria-labelledby="animation_collapse_header">
                <div class="card-body">
                    % include("animation/settings.tpl", animation_settings=entry.ANIMATION_SETTINGS)
                </div>
            </div>
        </div>
    </div>
</div>
<div class="row pt-3">
    <div class="col">
        <div class="card">
            <div class="card-header">
                Schedule
            </div>
            <div class="card-body">
                <form id="cron_form" method="post" autocomplete="off">
                    % for category in CRON_DICT.keys():
                        <div class="form-group">
                            <label for="cron_{{category}}_select_text_container">
                                {{category.title().replace("_", " ")}}
                            </label>
                            <div id="cron_{{category}}_select_text_container" class="input-group">
                                <input id="cron_{{category}}_select_text" type="text" class="form-control" name="cron_{{category}}_select_value" placeholder="Any" value="{{xstr(getattr(entry.CRON_STRUCTURE, category.upper()))}}" aria-describedby="cron_{{category}}_select_btn">
                                <div class="input-group-append">
                                    <button id="cron_{{category}}_select_btn" type="button" class="btn btn-outline-secondary dropdown-toggle" data-toggle="modal" data-target="#cron_{{category}}_modal">
                                        Select
                                    </button>
                                </div>
                            </div>
                        </div>
                    % end
                </form>
                % for category, items in CRON_DICT.items():
                    <form id="cron_{{category}}_modal_form" autocomplete="off">
                        <div class="modal fade" id="cron_{{category}}_modal" tabindex="-1" aria-labelledby="cron_{{category}}_modal_label" aria-hidden="true">
                            <div class="modal-dialog modal-sm modal-dialog-centered modal-dialog-scrollable">
                                <div class="modal-content">
                                    <div class="modal-header pb-2">
                                        <div class="container-fluid">
                                            <div class="row">
                                                <h5 class="modal-title" id="cron_{{category}}_modal_label">{{category.title().replace("_", " ")}}</h5>
                                                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                                    <span aria-hidden="true">&times;</span>
                                                </button>
                                            </div>
                                            <div class="row pt-3 form-check">
                                                <input id="cron_{{category}}_modal_check_all" class="form-check-input all-checkbox" type="checkbox" onclick="mark_modal_checkboxes(cron_{{category}}_modal_form, this.checked);">
                                                <label class="form-check-label" for="cron_{{category}}_modal_check_all">
                                                    afdsL
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="modal-body">
                                        % for item in items:
                                            <div class="form-check">
                                                <input id="cron_{{category}}_modal_check_{{item["value"]}}" class="form-check-input" type="checkbox" name="{{item["value"]}}" onclick="update_all_checked_checkbox(cron_{{category}}_modal_form);">
                                                <label class="form-check-label" for="cron_{{category}}_modal_check_{{item["value"]}}">
                                                    {{item["text"]}}
                                                </label>
                                            </div>
                                        % end
                                    </div>
                                    <div class="modal-footer">
                                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                                        <button id="cron_{{category}}_modal_apply" type="button" class="btn btn-primary" data-dismiss="modal">Set</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>
                % end
            </div>
            <div class="card-footer">
                <button id="btn_schedule_animation" type="submit" class="btn btn-primary float-right ml-3" formaction="{{request.url if is_modify else "/schedule/create"}}">
                    <span class="icon bi-clock-fill"></span>
                    % if is_modify:
                        <span>Apply</span>
                    % else:
                        <span>Schedule</span>
                    % end
                </button>
                <a class="btn btn-danger float-right" href="{{"/schedule" if is_modify else "/"}}">
                    Cancel
                </a>
            </div>
        </div>
    </div>
</div>

<script>
    function* get_all_checkboxes_of_modal(modal_form) {
        for(let form_item of modal_form.elements){
            if(form_item.type == "checkbox" && form_item.name)
                yield form_item;
        }
    }

    function update_all_checked_checkbox_label(modal_form) {
        let all_checkbox = modal_form.getElementsByClassName("all-checkbox")[0]

        // the nextElementSibling is the label
        if(all_checkbox.checked)
            all_checkbox.nextElementSibling.textContent = "Uncheck ALL";
        else
            all_checkbox.nextElementSibling.textContent = "Check ALL";
    }

    function update_all_checked_checkbox(modal_form, only_label){
        let all_checkbox = modal_form.getElementsByClassName("all-checkbox")[0]
        let all_checked = true;

        for(let checkbox of get_all_checkboxes_of_modal(modal_form)){
            if(! checkbox.checked){
                all_checked = false;
                break;
            }
        }

        all_checkbox.checked = all_checked;
        update_all_checked_checkbox_label(modal_form);
    }

    function mark_modal_checkboxes(modal_form, checked) {
        for(let checkbox of get_all_checkboxes_of_modal(modal_form)){
            checkbox.checked = checked;
        }

        update_all_checked_checkbox_label(modal_form);
    }

    window.addEventListener("load", function(){
        var category_names = [{{!",".join(["'%s'" % category for category in CRON_DICT.keys()])}}];
        var categories = {};

        // get the elements
        for(let name of category_names){
            categories[name] = {
                "form": document.getElementById("cron_" + name + "_modal_form"),
                "modal": document.getElementById("cron_" + name + "_modal"),
                "text": document.getElementById("cron_" + name + "_select_text"),
                "btn_apply": document.getElementById("cron_" + name + "_modal_apply")
            };
        }

        // add an event listener to each modal
        for(let cat in categories){
            categories[cat].modal.addEventListener('show.bs.modal', function(event){
                // check selected checkboxes
                for(let val of categories[cat].text.value.split(",")){
                    if(val)
                        document.getElementById("cron_" + cat + "_modal_check_" + val).checked = true;
                }

                // set value of (un)check all checkbox
                update_all_checked_checkbox(categories[cat].form);
            }, false);
            categories[cat].modal.addEventListener('hide.bs.modal', function(event){
                if(event.explicitOriginalTarget == categories[cat].btn_apply){
                    // save values only if the apply button of the modal was clicked
                    let selected_values = [];
                    for(let form_item of get_all_checkboxes_of_modal(categories[cat].form)){
                        if(form_item.checked)
                            selected_values.push(form_item.name);
                    }
                    categories[cat].text.value = selected_values.join(",");
                }
            }, false);
            categories[cat].modal.addEventListener('hidden.bs.modal', function(event){
                // reset form if modal isn't visible anymore
                categories[cat].form.reset();
            }, false);
        }

        // main apply button
        btn_schedule_animation.onclick = function() {
            let form_data = {};

            // add a hidden field that contains the selected animation name
            form_data["selected_animation_name"] = "{{entry.ANIMATION_SETTINGS.animation_name}}";

            // this selector and form is defined by 'animation/settings.tpl'
            let animation_form = document.getElementById("animation_settings_form_{{entry.ANIMATION_SETTINGS.animation_name}}");
            // copy the field values from the animation form
            for(let form_item of animation_form.elements){
                let value = "";
                // special case checkbox
                if(form_item.type == "checkbox"){
                    if(form_item.checked)
                        value = form_item.value;
                } else {
                    value = form_item.value;
                }
                form_data[form_item.name] = value;
            }

            // add the data to the main form
            for(form_item_name in form_data){
                let hiddenField = document.createElement('input');
                hiddenField.type = 'hidden';
                hiddenField.name = form_item_name;
                hiddenField.value = form_data[form_item_name];
                cron_form.appendChild(hiddenField);
            }
            // submit it
            cron_form.action = this.formAction;
            cron_form.submit();
        }
    });
</script>
