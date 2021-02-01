% from bottle import request
% from common.schedule import CronStructure
% from server.http_server import CRON_DICT
% from server.http_server import SettingsTabs

% setdefault("animations", {})
% setdefault("is_modify", False)

% rebase("base.tpl", page_title="Schedule")


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
                    % for category, items in CRON_DICT.items():
                        <div class="form-group">
                            <label for="cron_{{category}}">
                                {{category.title().replace("_", " ")}}
                            </label>
                            <select id="cron_{{category}}" class="form-control" name="cron_{{category}}_value">
                                <option value="*" {{"selected" if getattr(entry.CRON_STRUCTURE, category.upper()) is None else ""}}>Any</option>
                                % for item in items:
                                    <option value="{{item["value"]}}" {{"selected" if getattr(entry.CRON_STRUCTURE, category.upper()) == item["value"] else ""}}>
                                        {{item["text"]}}
                                    </option>
                                % end
                            </select>
                        </div>
                    % end
                </form>
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
                <a class="btn btn-danger float-right" href="{{"/settings/" + SettingsTabs.schedule_table.name if is_modify else "/"}}">
                    Cancel
                </a>
            </div>
        </div>
    </div>
</div>

<script>
    window.addEventListener("load", function(){
        btn_schedule_animation.onclick = function() {
            // add a hidden field that contains the selected animation name
            let hiddenField = document.createElement('input');
            hiddenField.type = 'hidden';
            hiddenField.name = "selected_animation_name";
            hiddenField.value = "{{entry.ANIMATION_SETTINGS.animation_name}}";
            cron_form.appendChild(hiddenField);

            // this selector and form is defined by 'animation/settings.tpl'
            let animation_form = document.getElementById("animation_settings_form_{{entry.ANIMATION_SETTINGS.animation_name}}");
            // copy the field values from the animation form
            for(form_item of animation_form.elements){
                hiddenField = document.createElement('input');
                hiddenField.type = 'hidden';
                hiddenField.name = form_item.name;
                // special case checkbox
                if(form_item.type == "checkbox"){
                    if(form_item.checked)
                        hiddenField.value = form_item.value;
                    else
                        hiddenField.value = "";
                } else {
                    hiddenField.value = form_item.value;
                }
                cron_form.appendChild(hiddenField);
            }

            // submit the form
            cron_form.action = this.formAction;
            cron_form.submit();
        }
    });
</script>
